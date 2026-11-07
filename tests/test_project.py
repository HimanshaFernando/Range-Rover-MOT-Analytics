import base64
import csv
import json
import re
import unittest
import zlib
from pathlib import Path

import duckdb

ROOT=Path(__file__).resolve().parents[1]


class MetricTests(unittest.TestCase):
    def test_initial_tests_model_mapping_and_multiple_items(self):
        db=duckdb.connect()
        db.execute('CREATE TABLE input_rows(test_id varchar,model varchar,test_date date,first_use_date date,test_mileage int,test_result varchar,test_class_id varchar,test_type varchar,make varchar)')
        for i,name,outcome,kind in [(1,'RR SPORT HSE','F','NT'),(2,'R ROVER SPRT HSE','PRS','NT'),(3,'RANGE ROVER SPORT','P','NT'),(4,'RANGE ROVER SPORT','P','RT'),(5,'DISCOVERY SPORT','F','NT'),(6,'RANGE ROVER EVOQUE','ABA','NT')]:
            db.execute("INSERT INTO input_rows VALUES(?,?,'2024-01-21','2017-06-30',50100,?,'4',?,'LAND ROVER')",[i,name,outcome,kind])
        db.execute('CREATE TABLE inspections(id bigint,month varchar,raw_model varchar,family varchar,age_band varchar,mileage_band varchar,outcome varchar)')
        db.execute((ROOT/'sql/tests.sql').read_text())
        self.assertEqual(db.execute('select distinct family from inspections').fetchall(),[('Range Rover Sport',)])
        db.execute("CREATE TABLE observations AS SELECT * FROM (VALUES(1,10,'F'),(1,11,'F'),(2,10,'P')) AS v(id,rfr_id,code)")
        db.execute("CREATE TABLE lookup AS SELECT * FROM (VALUES(10,'Brakes','A'),(11,'Brakes','B')) AS v(rfr_id,category,description)")
        db.execute((ROOT/'sql/aggregate.sql').read_text())
        self.assertEqual(db.execute('select tests,initial_fails,prs from cohort').fetchone(),(3,2,1))
        self.assertEqual(db.execute('select affected,items from category_counts').fetchone(),(2,3))
        db.close()

    def test_delivered_aggregates(self):
        with (ROOT/'data/cohorts.csv').open() as f: records=list(csv.DictReader(f))
        audit=json.loads((ROOT/'data/audit.json').read_text())
        self.assertEqual(sum(int(r['tests']) for r in records),audit['eligible_tests'])
        self.assertEqual(sum(int(r['initial_fails']) for r in records),audit['initial_fails'])
        ids={r['cohort_id']:int(r['initial_fails']) for r in records}
        with (ROOT/'data/categories.csv').open() as f:
            for r in csv.DictReader(f):
                self.assertLessEqual(int(r['affected']),min(ids[r['cohort_id']],int(r['items'])))

    def test_embedded_powerbi_payloads_and_visual_bindings(self):
        folder=ROOT/'powerbi'
        model=json.loads(next(folder.rglob('model.bim')).read_text())['model']
        schema={t['name']:{c['name'] for c in t['columns']+t.get('measures',[])} for t in model['tables']}
        files={'Cohorts':'cohorts','Defects':'categories','Reasons':'reasons','Comparison':'comparison'}
        for t in model['tables']:
            if t['name'] not in files:continue
            m=t['partitions'][0]['source']['expression'][1]
            parts=m.split('Text.Combine({')[1].split('})')[0]
            encoded=''.join(re.findall(r'"([A-Za-z0-9+/=]+)"',parts))
            self.assertEqual(zlib.decompress(base64.b64decode(encoded),-15),(ROOT/'data'/(files[t['name']]+'.csv')).read_bytes())
        pages=list(folder.rglob('page.json'));self.assertEqual(len(pages),4)
        for path in folder.rglob('visual.json'):
            vis=json.loads(path.read_text())['visual']
            for role in vis['query']['queryState'].values():
                for proj in role['projections']:
                    tab,col=proj['queryRef'].split('.',1)
                    self.assertIn(col,schema[tab])
