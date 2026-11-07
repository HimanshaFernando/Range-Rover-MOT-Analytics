"""Write a concise service-planning briefing from the released aggregates."""
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/'data'/(name+'.csv')).open(encoding='utf-8') as f:
        return list(csv.DictReader(f))

def main():
    cohort=read('cohorts')
    audit=json.loads((ROOT/'data/audit.json').read_text())
    tests=audit['eligible_tests']; failed=audit['initial_fails']
    index={x['cohort_id']:x for x in cohort}
    counts=Counter(); byfamily=defaultdict(Counter); totals=Counter()
    for x in cohort:totals[x['family']]+=int(x['tests'])
    for x in read('categories'):
        counts[x['category']]+=int(x['affected'])
        byfamily[index[x['cohort_id']]['family']][x['category']]+=int(x['affected'])
    months=', '.join(str(x) for x in audit['months_requested']) if isinstance(audit['months_requested'],list) else 'January–December'
    rows=['# Service planning briefing','',f'GB class 4 Range Rover family inspections | {months} in '+', '.join(map(str,audit['years'])),
        '',f'Of **{tests:,}** eligible initial inspections, **{failed:,} ({failed/tests:.1%})** failed as presented, including passes after rectification at the station.']
    cat,n=counts.most_common(1)[0]
    rows+=['','## Inspection priority','',f'**{cat}** appeared in {n:,} distinct initial inspections ({1000*n/tests:.1f} per 1,000), the most frequent failure category in this selection. Start a workshop review with this category and check the reasons table for its most common recorded items.','',
        '| Family | Leading category | Affected tests | Per 1,000 initial tests |','|---|---|---:|---:|']
    for family,sc in sorted(byfamily.items()):
        cat,n=sc.most_common(1)[0];rows.append(f'| {family} | {cat} | {n:,} | {1000*n/totals[family]:.1f} |')
    rows+=['','## Like-for-like comparisons','','The adjusted estimate uses the same pooled age and mileage distribution for each family. Only cells with 30 or more initial tests in every family contribute. The support column shows how much of each family contributes.','','| Family | Observed fail rate | Adjusted rate | Support |','|---|---:|---:|---:|']
    for row in read('comparison'):
        if row['period']=='Combined':
            adj=f"{float(row['adjusted_rate']):.1%}" if row['adjusted_rate'] else 'Insufficient support'
            rows.append(f"| {row['family']} | {float(row['observed_rate']):.1%} | {adj} | {float(row['support_share']):.1%} |")
    cat,n=counts.most_common(1)[0]
    rows+=['','## Workshop scenario','',f'For 200 future initial inspections with the same mix, the observed {cat.lower()} rate implies about **{round(200*n/tests)} affected inspections**. A single vehicle can appear in several categories. This scenario assumes stable rates and fleet mix. Service bookings, repair labour, repair prices and parts consumption require separate data.','',
           '## Interpretation','','The outcome describes condition at the MOT test. Age and mileage adjustment addresses two measured differences. Vehicle use, prior maintenance and local testing practices can also influence the comparison. Model names are rule-mapped from tester records. See data/model_mapping.csv for the exact labels and docs/METHODS.md for eligibility.','',
           f"Coverage checks: {audit['failed_tests_without_linked_failure_item']:,} initially failed inspections without a linked F/P item; {audit['unmapped_defect_items']:,} unclassified recorded failure items.",'',
           'Contains public sector information licensed under the Open Government Licence v3.0. Source: DVSA anonymised MOT test results and failure items.']
    (ROOT/'analysis/SERVICE_BRIEFING.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
if __name__=='__main__':main()
