CREATE OR REPLACE VIEW committed_normalized_events AS
SELECT n.*
FROM normalized_events AS n
INNER JOIN run_manifests AS m
    ON n.pipeline_run_id = m.pipeline_run_id
WHERE m.schema_version = 'hydra-aws-market-pipeline-manifest/v1'
  AND m.outputs['normalized_events.jsonl'].sha256 IS NOT NULL;
