-- Grain: one synthetic observation, NOT one unique physical machine.
DROP VIEW IF EXISTS observation_health;
DROP VIEW IF EXISTS quality_summary;
CREATE VIEW observation_health AS
SELECT o.observation_id, o.product_id, o.product_type,
       o.air_temperature_k, o.process_temperature_k, o.rotational_speed_rpm,
       o.torque_nm, o.tool_wear_min, o.machine_failure,
       ROUND(o.process_temperature_k - o.air_temperature_k, 2) AS temperature_gap_k,
       ROUND(o.torque_nm * o.rotational_speed_rpm * 0.10471975511965977, 2) AS power_w,
       p.split, p.model_score, p.model_alert, p.monitoring_alert
FROM observations o JOIN predictions p USING (observation_id);

CREATE VIEW quality_summary AS
SELECT product_type, split, COUNT(*) AS observations,
       SUM(machine_failure) AS failures,
       AVG(machine_failure) AS failure_rate,
       SUM(model_alert) AS model_alerts,
       SUM(CASE WHEN model_alert=1 AND machine_failure=1 THEN 1 ELSE 0 END) AS true_positives,
       SUM(CASE WHEN model_alert=1 AND machine_failure=0 THEN 1 ELSE 0 END) AS false_positives
FROM observation_health
GROUP BY product_type, split;
