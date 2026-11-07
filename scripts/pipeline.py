"""Build aggregate datasets from DVSA monthly CSVs. Only aggregate rows leave scratch."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
HOST = 'https://edh-dvsa-data-gov-uk-files-prod.s3.eu-west-1.amazonaws.com/'
FAMILIES = ['Evoque', 'Velar', 'Range Rover', 'Range Rover Sport']


def fetch(cache, name):
    path = cache / name
    if not path.exists():
        tmp = path.with_suffix(path.suffix + '.partial')
        with urllib.request.urlopen(HOST + name, timeout=120) as src, tmp.open('wb') as dst:
            shutil.copyfileobj(src, dst, 4 * 1024 ** 2)
        tmp.replace(path)
    return path


def lookup(cache):
    def rows(kind):
        with fetch(cache, f'dft_item_{kind}_extract.csv').open(encoding='utf-8-sig') as f:
            return [r for r in csv.DictReader(f) if r['test_class_id'] == '4']
    groups = {r['test_item_id']: r for r in rows('group')}
    records = []
    for detail in rows('detail'):
        key = detail['test_item_id']
        visited = set()
        while key in groups and groups[key]['parent_id'] != '0':
            if key in visited:
                raise ValueError('Cycle in defect lookup')
            visited.add(key)
            key = groups[key]['parent_id']
        category = groups.get(key, {}).get('item_name', 'Unmapped defect').strip().capitalize()
        description = detail['rfr_insp_manual_desc'] or detail['rfr_desc']
        records.append((int(detail['rfr_id']),category,description))
    return records


def export(con, query, path):
    data = con.execute(query)
    with path.open('w',encoding='utf-8',newline='') as stream:
        w = csv.writer(stream)
        w.writerow([c[0] for c in data.description])
        while batch := data.fetchmany(8192):
            w.writerows(batch)


def standardised(con):
    # One pooled reference mix per period. Require all four families to have
    # >=30 tests in each included stratum; disclose retained population share.
    con.execute('''CREATE TABLE comparison AS
      WITH expanded AS (
       SELECT month[:4] AS period,* FROM cohort UNION ALL SELECT 'Combined' AS period,* FROM cohort
      ), cells AS (
       SELECT period,family,age_band,mileage_band,sum(tests) n,sum(initial_fails) f
       FROM expanded WHERE family!='Unmapped' GROUP BY ALL
      ), totals AS (SELECT period,family,sum(n) n,sum(f) f FROM cells GROUP BY ALL),
      common AS (
       SELECT period,age_band,mileage_band,sum(n) weight FROM cells
       WHERE age_band!='Unknown' AND mileage_band!='Unknown'
       GROUP BY ALL HAVING count(*)=4 AND min(n)>=30
      ), weighted AS (
       SELECT period,family,sum(weight*f/n)/sum(weight) adjusted,sum(n) retained,count(*) strata
       FROM cells JOIN common USING(period,age_band,mileage_band) GROUP BY ALL
      )
      SELECT t.period,t.family,t.n AS tests,t.f/t.n AS observed_rate,w.adjusted AS adjusted_rate,
       coalesce(w.retained,0)/t.n AS support_share,coalesce(w.strata,0) AS common_strata
      FROM totals t LEFT JOIN weighted w USING(period,family)''')


def build(cache, out, years, months=None):
    cache.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    audit = {'years':years, 'months_requested':months or 'all', 'members':[]}
    with tempfile.TemporaryDirectory(dir=cache) as scratch:
        work=Path(scratch)
        con=duckdb.connect(str(work/'stage.duckdb'))
        con.execute("SET threads=3; SET memory_limit='1500MB'")
        con.execute('CREATE TABLE inspections(id BIGINT PRIMARY KEY,month VARCHAR,raw_model VARCHAR,family VARCHAR,age_band VARCHAR,mileage_band VARCHAR,outcome VARCHAR)')
        con.execute('CREATE TABLE observations(id BIGINT,rfr_id BIGINT,code VARCHAR)')
        con.execute('CREATE TABLE lookup(rfr_id BIGINT PRIMARY KEY,category VARCHAR,description VARCHAR)')
        con.executemany('INSERT INTO lookup VALUES(?,?,?)',lookup(cache))
        for kind, sql in [('result','tests'),('item','items')]:
            statement=(ROOT/'sql'/f'{sql}.sql').read_text()
            for year in years:
                source=f'dft_test_{kind}_extracts_{year}.zip'
                with zipfile.ZipFile(fetch(cache,source)) as z:
                    members=sorted(i for i in z.namelist() if i.lower().endswith('.csv'))
                    desired = set(months or range(1,13))
                    selected = [i for i in members if int(Path(i).stem[-2:]) in desired]
                    if len(selected)!=len(desired): raise ValueError(f'Unexpected month coverage: {source}')
                    for name in selected:
                        print('Processing',name,flush=True)
                        temporary=work/'monthly.csv'
                        with z.open(name) as src, temporary.open('wb') as dst:
                            shutil.copyfileobj(src,dst,4*1024**2)
                        con.read_csv(str(temporary),header=True,quotechar=chr(34),escapechar=chr(92),delimiter=",",all_varchar=True,sample_size=10000).create_view('input_rows',replace=True)
                        con.execute(statement)
                        audit['members'].append({'archive':source, 'member':name,'bytes':z.getinfo(name).file_size,'crc32':format(z.getinfo(name).CRC,'08x')})
                        temporary.unlink()
        con.execute((ROOT/'sql/aggregate.sql').read_text())
        standardised(con)
        files={'cohorts':'SELECT * FROM cohort ORDER BY cohort_id',
               'categories':'SELECT * FROM category_counts ORDER BY cohort_id,category',
               'reasons':'SELECT * FROM reason_counts ORDER BY cohort_id,category,rfr_id',
               'comparison':'SELECT * FROM comparison ORDER BY period,family',
               'model_mapping':'SELECT raw_model,family,count(*) AS tests FROM inspections GROUP BY ALL ORDER BY tests DESC,raw_model'}
        for name,query in files.items(): export(con,query,out/(name+'.csv'))
        audit['eligible_tests']=con.execute('SELECT count(*) FROM inspections').fetchone()[0]
        audit['initial_fails']=con.execute("SELECT count(*) FROM inspections WHERE outcome IN ('F','PRS')").fetchone()[0]
        audit['failed_tests_without_linked_failure_item']=con.execute("SELECT count(*) FROM inspections i WHERE outcome IN ('F','PRS') AND NOT EXISTS(SELECT 1 FROM observations o WHERE o.id=i.id)").fetchone()[0]
        audit['unmapped_defect_items']=con.execute('SELECT count(*) FROM observations o ANTI JOIN lookup l USING(rfr_id)').fetchone()[0]
        assert not con.execute('SELECT count(*) FROM category_counts JOIN cohort USING(cohort_id) WHERE affected>initial_fails OR affected>items').fetchone()[0]
        assert con.execute('SELECT sum(tests) FROM cohort').fetchone()[0]==audit['eligible_tests']
        audit['distinct_tests_in_categories']=con.execute('SELECT count(distinct id) FROM tagged').fetchone()[0]
        audit['hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.csv')}
        (out/'audit.json').write_text(json.dumps(audit,indent=2))
        con.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,default=ROOT/'raw');p.add_argument('--out',type=Path,default=ROOT/'data')
    p.add_argument('--years',type=int,nargs='+',default=[2024,2025]);p.add_argument('--months',type=int,nargs='+')
    a=p.parse_args();build(a.cache,a.out,a.years,a.months)
