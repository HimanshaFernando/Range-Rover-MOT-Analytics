CREATE TABLE cohort AS
SELECT row_number() OVER(ORDER BY month,family,age_band,mileage_band) AS cohort_id,*
FROM (SELECT month,family,age_band,mileage_band,count(*) AS tests,
 count_if(outcome IN ('F','PRS')) AS initial_fails,count_if(outcome='PRS') AS prs
 FROM inspections GROUP BY ALL) a;
CREATE VIEW assigned AS SELECT i.*,c.cohort_id FROM inspections i JOIN cohort c
USING(month,family,age_band,mileage_band);
CREATE VIEW tagged AS SELECT a.cohort_id,o.id,o.rfr_id,
 coalesce(l.category,'Unmapped defect') AS category,
 coalesce(l.description,'Unmapped reason') AS description
 FROM observations o JOIN assigned a USING(id) LEFT JOIN lookup l USING(rfr_id);
CREATE TABLE category_counts AS SELECT cohort_id,category,count(distinct id) AS affected,
 count(*) AS items FROM tagged GROUP BY ALL;
CREATE TABLE reason_counts AS SELECT cohort_id,category,rfr_id,description,
 count(distinct id) AS affected,count(*) AS items FROM tagged GROUP BY ALL;
