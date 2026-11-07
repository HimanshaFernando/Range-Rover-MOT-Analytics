# Scope, metric definitions and reconciliation

**Source** — Driver and Vehicle Standards Agency, Great Britain. Use the new paired 2024 and 2025 releases dated 22 June 2026 listed on [DVSA Open Data](https://open.data.dvsa.gov.uk/mot-anonymised/index.html). Both releases use monthly CSV members. Read DVSA's test outcome/type and rejection-item lookup tables together with the post-May 2018 user guide. Other extracts listed for 2024 use an earlier packaging scheme.

**Population** — Each eligible class 4 normal test (NT) contributes one test. Include outcomes P, F and PRS. F and PRS count as initial failures. Re-tests, appeals, aborted, refused and abandoned tests are excluded. Passing after rectification is reported separately. Counts describe inspections; a vehicle returning for another eligible inspection can contribute again.

**Model rules** — Normalise make and model text. Keep Land Rover/Range Rover makes and recognisable Range Rover family tokens. Match Evoque and Velar first; then explicit Sport, SPRT and SPT labels. Remaining explicitly named Range Rover variants enter Range Rover; unresolved in-scope aliases enter Unmapped. Discovery Sport is excluded. A label lacking any recognised token cannot be recovered by this classifier. Inspect every extracted label and its count in data/model_mapping.csv. Family is an interpretation of recorded model text, without VIN validation.

**Age/mileage** — Approximate completed years from first-use date to test date using 365.2425 days/year. Age bands are 0–4, 5–9, 10–14 and 15+ years. Unavailable, future or sentinel 1971-01-01 first-use dates are unknown. Recorded test mileage bands are below 40k, 40–79k, 80–119k and 120k+. Non-positive or implausible readings above one million are unknown. The catalogue guide discusses odometer conversion changes starting in 2022. These bands depend on the published mileage field.

**Defects** — Join rejection items via test ID to eligible F or PRS tests, retaining F (fail) and P (rectified) item codes. Resolve each rejection ID using its class 4 detail row and follow the inspection-item hierarchy to its top category. Missing lookups are retained and flagged. Advisory A and minor M records are outside the failure-item measure.

| Measure | Definition |
|---|---|
| Initial tests | All eligible tests in the selected cohort |
| Initial failure rate | (F + PRS) / eligible tests |
| Affected per 1,000 | Distinct eligible tests having at least one F/P item in a selected category / all eligible tests × 1,000 |
| Failure items | Number of recorded F/P item rows; repeated items on an inspection are retained |
| Expected affected inspections | Scenario volume × selected affected-test rate; category counts overlap |
| Adjusted failure rate | Direct standardisation of family-specific stratum failure rates with pooled initial-test weights, on common support |
| Support share | The fraction of a family's initial tests in eligible common strata |

**Common support** — Calculate separately for each year and for the combined release. Restrict to known age/mileage cells in which all four mapped families have at least 30 inspections each. Compute pooled weights over those cells, then normalise and apply the same weights to each family. Observed rates include all eligible tests. Common-support coverage and any change in composition must accompany comparisons. Empty support gives a blank adjusted rate. This is descriptive standardisation, not a causal estimate.

**Scenario** — Choose a single workload volume (default 200). Results estimate affected inspections for a hypothetical workshop whose mix matches the selected cohort. Categories may overlap; summing the rows would overstate the number of distinct vehicles. The dashboard does not infer labour hours or stock quantities.

**Checks** — Inspection primary keys are unique. Aggregated tests reconcile to eligible inspection rows. Category affected tests cannot exceed item rows or initial failures. Data/audit.json records source members, bytes, CRC32 and CSV hashes, missing links and unmapped defects. The unit fixture includes repeated brake items, a rectified failure, a retest and Discovery Sport.

**Attribution** — Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Independent portfolio analysis. JLR and Range Rover names are used to identify vehicles.
