-- ============================================================================
-- SPS Retail Fulfillment Intelligence — ML Model & Predictions
-- Step 4: Train classification model and generate predictions
-- Run AFTER 02_load_data.sql (training_data must be loaded)
-- ============================================================================

USE DATABASE SPS_RETAIL_AI;
USE SCHEMA ML_MODELS;

-- ── Step 1: Train the Fulfillment Risk Classification Model ─
-- Uses SNOWFLAKE.ML.CLASSIFICATION — Snowflake's native ML classification
-- Target: IS_LATE_OR_SHORT (0 = on-time & in-full, 1 = late or short)
-- Training data: 9,919 POs with 22 features derived from SPS + retailer joined data
-- Expected: ~91% accuracy, ~99.6% precision, ~52.5% recall

CREATE OR REPLACE SNOWFLAKE.ML.CLASSIFICATION FULFILLMENT_RISK_MODEL(
    INPUT_DATA => SYSTEM$REFERENCE('TABLE', 'SPS_RETAIL_AI.ML_MODELS.TRAINING_DATA'),
    TARGET_COLNAME => 'IS_LATE_OR_SHORT'
);

-- ── Step 2: Generate Predictions ────────────────────────────
-- Score every PO in the training set (in production, score new/open POs)
-- PREDICTION column is VARIANT: {"class": 0|1, "probability": {"0": float, "1": float}}

CREATE OR REPLACE TABLE ML_MODELS.FULFILLMENT_PREDICTIONS AS
SELECT *,
    FULFILLMENT_RISK_MODEL!PREDICT(
        INPUT_DATA => OBJECT_CONSTRUCT(
            'RETAILER_ID', RETAILER_ID,
            'SUPPLIER_ID', SUPPLIER_ID,
            'TOTAL_UNITS', TOTAL_UNITS,
            'TOTAL_COST', TOTAL_COST,
            'PO_VERSION', PO_VERSION,
            'IS_REPLACEMENT_850', IS_REPLACEMENT_850,
            'SUPPLIER_AVG_LEAD', SUPPLIER_AVG_LEAD,
            'SUPPLIER_LEAD_VAR', SUPPLIER_LEAD_VAR,
            'SUPPLIER_REGION', SUPPLIER_REGION,
            'DESTINATION_REGION', DESTINATION_REGION,
            'DESTINATION_SIZE', DESTINATION_SIZE,
            'LOCATION_TYPE', LOCATION_TYPE,
            'ORDER_DOW', ORDER_DOW,
            'ORDER_MONTH', ORDER_MONTH,
            'DAYS_TO_DELIVER', DAYS_TO_DELIVER,
            'DAYS_TO_SHIP', DAYS_TO_SHIP,
            'LINE_COUNT', LINE_COUNT,
            'TOTAL_LINE_QTY', TOTAL_LINE_QTY,
            'DISTINCT_ITEMS', DISTINCT_ITEMS,
            'HIST_ON_TIME_RATE', HIST_ON_TIME_RATE,
            'HIST_IN_FULL_RATE', HIST_IN_FULL_RATE,
            'HIST_OTIF_RATE', HIST_OTIF_RATE,
            'HIST_AVG_DAYS_LATE', HIST_AVG_DAYS_LATE,
            'HIST_PO_COUNT', HIST_PO_COUNT
        )
    ) AS PREDICTION
FROM ML_MODELS.TRAINING_DATA;

-- ── Step 3: Build Feature Summary Table ─────────────────────

CREATE OR REPLACE TABLE ML_MODELS.FULFILLMENT_FEATURES AS
SELECT
    t.PO_ID, t.RETAILER_ID, t.SUPPLIER_ID,
    po.ORDER_DATE, po.REQUESTED_SHIP_DATE, po.REQUESTED_DELIVERY_DATE,
    t.TOTAL_UNITS, t.TOTAL_COST, t.PO_VERSION, t.IS_REPLACEMENT_850,
    po.ACCEPTANCE_STATUS,
    CASE
        WHEN t.HIST_OTIF_RATE >= 0.90 THEN 'A'
        WHEN t.HIST_OTIF_RATE >= 0.80 THEN 'B'
        WHEN t.HIST_OTIF_RATE >= 0.70 THEN 'C'
        ELSE 'D'
    END AS SUPPLIER_TIER_HIDDEN,
    t.SUPPLIER_AVG_LEAD, t.SUPPLIER_LEAD_VAR, t.SUPPLIER_REGION,
    t.DESTINATION_REGION, t.DESTINATION_SIZE, t.LOCATION_TYPE,
    t.ORDER_DOW, t.ORDER_MONTH,
    t.DAYS_TO_DELIVER, t.DAYS_TO_SHIP,
    t.LINE_COUNT, t.TOTAL_LINE_QTY, t.DISTINCT_ITEMS,
    t.HIST_ON_TIME_RATE, t.HIST_IN_FULL_RATE, t.HIST_OTIF_RATE,
    t.HIST_AVG_DAYS_LATE, t.HIST_PO_COUNT,
    t.IS_LATE_OR_SHORT,
    DATEDIFF('day', po.REQUESTED_DELIVERY_DATE, s.ACTUAL_DELIVERY_DATE) AS ACTUAL_DAYS_LATE,
    s.ON_TIME_FLAG,
    s.IN_FULL_FLAG
FROM ML_MODELS.TRAINING_DATA t
JOIN SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po ON t.PO_ID = po.PO_ID
JOIN SPS_RETAIL_AI.SHARED.SHIPMENT s ON t.PO_ID = s.PO_ID;

-- ── Step 4: Verify Model Accuracy ───────────────────────────

SELECT
    ROUND(SUM(CASE WHEN PREDICTION:"class"::INT = IS_LATE_OR_SHORT THEN 1 ELSE 0 END)::FLOAT
        / COUNT(*) * 100, 1) AS ACCURACY_PCT,
    ROUND(SUM(CASE WHEN PREDICTION:"class"::INT = 1 AND IS_LATE_OR_SHORT = 1 THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(SUM(CASE WHEN PREDICTION:"class"::INT = 1 THEN 1 ELSE 0 END), 0) * 100, 1) AS PRECISION_PCT,
    ROUND(SUM(CASE WHEN PREDICTION:"class"::INT = 1 AND IS_LATE_OR_SHORT = 1 THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(SUM(CASE WHEN IS_LATE_OR_SHORT = 1 THEN 1 ELSE 0 END), 0) * 100, 1) AS RECALL_PCT,
    COUNT(*) AS TOTAL_POS
FROM ML_MODELS.FULFILLMENT_PREDICTIONS;

-- ── Step 5: View Feature Importance ─────────────────────────

CALL FULFILLMENT_RISK_MODEL!SHOW_FEATURE_IMPORTANCE();
