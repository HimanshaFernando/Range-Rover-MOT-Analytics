INSERT INTO observations
SELECT i.id,try_cast(x.rfr_id AS BIGINT) AS rfr_id, x.rfr_type_code
FROM input_rows x JOIN inspections i ON i.id=try_cast(x.test_id AS BIGINT)
WHERE x.rfr_type_code IN ('F','P') AND i.outcome IN ('F','PRS');
