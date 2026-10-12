-- =============================================================================
-- Inference Add-On — Teardown (rollback)
-- Removes ONLY what the add-on created. The dashboard demo is unaffected.
-- =============================================================================

-- Pause instead of removing (keeps the endpoint URL; resumes on next request or ALTER ... RESUME):
-- ALTER SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC SUSPEND;

DROP SERVICE IF EXISTS SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC;
DROP SCHEMA  IF EXISTS SPS_RETAIL_AI.ML_INFERENCE CASCADE;   -- model FULFILLMENT_RISK_XGB, SAMPLE_REQUESTS
