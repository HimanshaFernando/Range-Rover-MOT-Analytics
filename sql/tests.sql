-- input_rows = one monthly national result file. Count NT only, retain PRS.
INSERT INTO inspections
WITH scoped AS (
  SELECT try_cast(test_id AS BIGINT) AS id, upper(trim(model)) AS raw_model,
         try_cast(test_date AS DATE) AS day, try_cast(first_use_date AS DATE) AS first_day,
         try_cast(test_mileage AS BIGINT) AS miles, test_result AS outcome
  FROM input_rows
  WHERE test_class_id='4' AND test_type='NT' AND test_result IN ('F','P','PRS')
    AND regexp_replace(upper(trim(make)),'[^A-Z]','','g') IN ('LANDROVER','RANGEROVER')
), named AS (
  SELECT *, CASE
    WHEN contains(raw_model,'EVOQUE') THEN 'Evoque'
    WHEN contains(raw_model,'VELAR') THEN 'Velar'
    WHEN regexp_matches(raw_model,'(RANGE ?ROVER|R ROVER|R/R|R/RVR|R RVR|RROVER|R R |RR ).*SP(ORT|RT|T)') THEN 'Range Rover Sport'
    WHEN regexp_matches(raw_model,'^(RANGE ?ROVER|R ROVER|R/R|RROVER)( |$)') THEN 'Range Rover'
    ELSE 'Unmapped' END AS family
  FROM scoped
  WHERE regexp_matches(raw_model,'EVOQUE|VELAR|RANGE ?ROVER|R ROVER|R/R|R RVR|RROVER|^RR |^R R ')
), aged AS (
 SELECT *,floor(date_diff('day',first_day,day)/365.2425) AS approx_age FROM named
)
SELECT id, strftime(day,'%Y-%m') AS month,raw_model,family,
 CASE WHEN first_day IS NULL OR first_day=DATE '1971-01-01' OR approx_age<0 THEN 'Unknown'
      WHEN approx_age<5 THEN '0-4 years' WHEN approx_age<10 THEN '5-9 years'
      WHEN approx_age<15 THEN '10-14 years' ELSE '15+ years' END AS age_band,
 CASE WHEN miles IS NULL OR miles<=0 OR miles>1000000 THEN 'Unknown'
      WHEN miles<40000 THEN '0-39k' WHEN miles<80000 THEN '40-79k'
      WHEN miles<120000 THEN '80-119k' ELSE '120k+' END AS mileage_band,outcome
FROM aged;
