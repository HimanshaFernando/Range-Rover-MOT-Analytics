# Range Rover MOT & Service Analytics

A Power BI report for a service manager comparing initial MOT failures, defect priorities and hypothetical inspection workload across four Range Rover families in Great Britain. The included report contains **238,894 initial inspections** for **January–March 2024 and January–March 2025**. These are matched quarters. The pipeline can rebuild both full calendar years from the national archives.

**[Read the findings](analysis/SERVICE_BRIEFING.md) · [Inspect the KPI definitions](docs/METHODS.md) · [Open the Power BI project](powerbi/RoverMOT.pbip)**

## Open on Windows

1. Extract the entire ZIP. Keep the Power BI project file and its two adjacent folders together.
2. Open **powerbi/RoverMOT.pbip** in a current version of Power BI Desktop. If prompted, enable the Desktop project and enhanced report format options under Preview features, then restart Desktop.
3. Select **Home → Refresh** to populate the model from the embedded aggregate snapshot. The project carries the data inside its import queries. No database connection, login or absolute path is needed to load these aggregates.
4. Select a report page and use the slicers. If desired, use **Save as** in Desktop to create a local PBIX copy.

## Report pages

| Page | Use it to |
|---|---|
| Inspection overview | Filter by model, age, mileage and month. Inspect failure rate together with initial test count and rectification counts. |
| Fair model comparison | Choose a year or Combined, then switch between observed and standardised rates. Read the support share to see how much of each fleet contributes to the adjustment. Select one period and one basis at a time. |
| Service priorities | Rank categories by affected tests per 1,000. Select a category to inspect its recorded reason descriptions. The reason table counts failure items. |
| Workshop scenario | Select the expected number of initial inspections. The table applies the observed rates for the selected vehicle mix, with a default volume of 200. |

## Project contents

- **powerbi/** — editable Power BI Desktop project, four PBIR pages, semantic model, measures and portable data imports.
- **data/** — aggregated CSVs, reviewed model labels, source member manifest and reconciliation counts.
- **sql/** — eligibility and model mapping, failure-item matching, test-level deduplication and aggregation.
- **scripts/** — data acquisition, DuckDB pipeline, report generator and evidence-based briefing.
- **analysis/** — service briefing, fair comparison and scenario interpretation.
- **tests/** and **.github/workflows/** — hand-calculated metric tests, aggregate reconciliation, embedded-data and visual-binding checks.

## Reproduce the included results

Use Python 3.12. From the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/pipeline.py --years 2024 2025 --months 1 2 3
.\.venv\Scripts\python.exe scripts/build_report.py
.\.venv\Scripts\python.exe scripts/briefing.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The DVSA publishes large annual ZIPs containing monthly files. Even a three-month rebuild downloads the annual archives initially; allow tens of GB of free storage, broadband and enough time. Monthly CSVs are processed one at a time. The included Power BI snapshot opens without these downloads.

For **full calendar years**, omit `--months 1 2 3` in the pipeline command. **REBUILD_WINDOWS.bat** runs the full-year version and regenerates the report and briefing. This changes your local data snapshot. Update any release-specific README totals before publishing a new release. **RUN_WINDOWS.bat** opens the existing report.

## Validation and limits

The matched-quarter aggregates were produced from the published monthly CSV members. Member CRCs were checked during data preparation. Automated checks cover repeated failure items, a pass after rectification, retest exclusion, cohort totals, embedded import payloads and visual bindings. The PBIR report and project JSON files were validated against Microsoft's published schemas. Local Power BI Desktop rendering, a complete 24-month rebuild and hosted GitHub CI still require execution in those environments.

A registered vehicle may undergo multiple eligible inspections. Outcomes describe the condition recorded at the test date. The scenario estimates affected inspections. It provides no evidence on warranty spend, repair prices or engine failure rates. This independent portfolio project has no JLR affiliation.

## Sources

- [DVSA anonymised MOT archives and reference tables](https://open.data.dvsa.gov.uk/mot-anonymised/index.html)
- [DVSA definitions for initial tests, failures and category rates](https://www.gov.uk/government/statistical-data-sets/mot-testing-data-for-great-britain)
- [Microsoft Power BI Desktop project report format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)

Contains public sector information licensed under the Open Government Licence v3.0. Include this attribution when reusing derived data.
