-- =============================================================================
-- Inference Add-On — Step 0: Isolated schema
-- Additive only. Everything the add-on creates lives in SPS_RETAIL_AI.ML_INFERENCE,
-- so the dashboard demo (ML_MODELS, SHARED, retailer schemas, Streamlit apps) is untouched.
-- SAMPLE_REQUESTS is created by 01_train_register.py from the model's own hold-out scores.
-- =============================================================================

USE ROLE CORTEXCODECLIROLE;
USE WAREHOUSE COCOWH;

CREATE SCHEMA IF NOT EXISTS SPS_RETAIL_AI.ML_INFERENCE
    COMMENT = 'Inference add-on: Model Registry model + SPCS real-time endpoint. Isolated from the dashboard demo.';

-- Baseline (record before and after the add-on; numbers must match)
SELECT
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.TRAINING_DATA)           AS TRAINING_DATA,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS) AS FULFILLMENT_PREDICTIONS,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_FEATURES)    AS FULFILLMENT_FEATURES,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER)             AS PURCHASE_ORDER,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.SHIPMENT)                   AS SHIPMENT;
