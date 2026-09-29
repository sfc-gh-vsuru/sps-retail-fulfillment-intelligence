-- =============================================================================
-- SPS Fulfillment Intelligence — Sample Queries for Cortex Analyst (Cowork)
-- These are the types of questions you can ask in Snowsight's Cortex Analyst UI
-- Each query maps to an insight shown in the Streamlit dashboards
-- =============================================================================

USE DATABASE SPS_RETAIL_AI;
USE SCHEMA SHARED;
USE WAREHOUSE COCOWH;

-- =============================================================================
-- Q1: OTIF Performance by Retailer
-- Dashboard: SPS Fulfillment Intelligence — Fulfillment KPIs
-- Ask Cowork: "What is the OTIF rate for each retailer?"
-- =============================================================================
SELECT
    r.RETAILER_NAME,
    COUNT(DISTINCT s.SHIPMENT_ID) AS total_shipments,
    ROUND(AVG(CASE WHEN s.ON_TIME_FLAG THEN 1 ELSE 0 END) * 100, 1) AS on_time_pct,
    ROUND(AVG(CASE WHEN s.IN_FULL_FLAG THEN 1 ELSE 0 END) * 100, 1) AS in_full_pct,
    ROUND(AVG(CASE WHEN s.ON_TIME_FLAG AND s.IN_FULL_FLAG THEN 1 ELSE 0 END) * 100, 1) AS otif_pct
FROM SPS_RETAIL_AI.SHARED.SHIPMENT s
JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON s.RETAILER_ID = r.RETAILER_ID
GROUP BY r.RETAILER_NAME
ORDER BY otif_pct DESC;


-- =============================================================================
-- Q2: Highest-Risk Suppliers (ML Predictions)
-- Dashboard: SPS Fulfillment Intelligence — ML Risk Predictions
-- Ask Cowork: "Which suppliers have the highest risk of late or short deliveries?"
-- =============================================================================
SELECT
    sup.SUPPLIER_NAME,
    sup.REGION AS supplier_region,
    sup.RELIABILITY_TIER,
    COUNT(*) AS total_predictions,
    SUM(fp.PREDICTION:"class"::INT) AS predicted_at_risk,
    ROUND(SUM(fp.PREDICTION:"class"::INT)::FLOAT / COUNT(*) * 100, 1) AS risk_rate_pct
FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS fp
JOIN SPS_RETAIL_AI.SHARED.SUPPLIER sup ON fp.SUPPLIER_ID = sup.SUPPLIER_ID
GROUP BY sup.SUPPLIER_NAME, sup.REGION, sup.RELIABILITY_TIER
ORDER BY risk_rate_pct DESC
LIMIT 10;


-- =============================================================================
-- Q3: Invoice Mismatch Rate by Retailer
-- Dashboard: SPS Fulfillment Intelligence — Invoice Reconciliation
-- Ask Cowork: "What is the invoice mismatch rate by retailer?"
-- =============================================================================
SELECT
    r.RETAILER_NAME,
    COUNT(i.INVOICE_ID) AS total_invoices,
    SUM(CASE WHEN i.MISMATCH_FLAG THEN 1 ELSE 0 END) AS mismatched_invoices,
    ROUND(SUM(CASE WHEN i.MISMATCH_FLAG THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(COUNT(i.INVOICE_ID), 0) * 100, 1) AS mismatch_rate_pct
FROM SPS_RETAIL_AI.SHARED.INVOICE i
JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON i.RETAILER_ID = r.RETAILER_ID
GROUP BY r.RETAILER_NAME
ORDER BY mismatch_rate_pct DESC;


-- =============================================================================
-- Q4: Top Product Categories by Order Value
-- Dashboard: SPS + Foot Locker / Bass Pro / Urban Outfitters
-- Ask Cowork: "What are the top product categories by total order value across all retailers?"
-- =============================================================================
SELECT
    it.CATEGORY_NAME,
    r.RETAILER_NAME,
    COUNT(DISTINCT pl.PO_ID) AS po_count,
    SUM(pl.LINE_TOTAL) AS total_order_value,
    SUM(pl.ORDERED_QTY) AS total_units_ordered
FROM SPS_RETAIL_AI.SHARED.PO_LINE pl
JOIN SPS_RETAIL_AI.SHARED.ITEM it ON pl.ITEM_ID = it.ITEM_ID
JOIN SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po ON pl.PO_ID = po.PO_ID
JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON po.RETAILER_ID = r.RETAILER_ID
GROUP BY it.CATEGORY_NAME, r.RETAILER_NAME
ORDER BY total_order_value DESC;


-- =============================================================================
-- Q5: ML Model Accuracy by Retailer
-- Dashboard: SPS Partner Value Lab — ML Accuracy
-- Ask Cowork: "How does the ML model accuracy compare across retailers?"
-- =============================================================================
SELECT
    r.RETAILER_NAME,
    COUNT(*) AS total_predictions,
    SUM(CASE WHEN fp.PREDICTION:"class"::INT = fp.IS_LATE_OR_SHORT THEN 1 ELSE 0 END) AS correct_predictions,
    ROUND(SUM(CASE WHEN fp.PREDICTION:"class"::INT = fp.IS_LATE_OR_SHORT THEN 1 ELSE 0 END)::FLOAT
        / COUNT(*) * 100, 1) AS accuracy_pct
FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS fp
JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON fp.RETAILER_ID = r.RETAILER_ID
GROUP BY r.RETAILER_NAME
ORDER BY accuracy_pct DESC;


-- =============================================================================
-- BONUS: Average Days Late by Supplier and Retailer
-- Ask Cowork: "Which suppliers are consistently late for each retailer?"
-- =============================================================================
SELECT
    r.RETAILER_NAME,
    sup.SUPPLIER_NAME,
    sup.RELIABILITY_TIER,
    COUNT(*) AS shipment_count,
    ROUND(AVG(rec.DAYS_LATE), 1) AS avg_days_late,
    ROUND(AVG(CASE WHEN s.ON_TIME_FLAG THEN 1 ELSE 0 END) * 100, 1) AS on_time_pct
FROM SPS_RETAIL_AI.SHARED.SHIPMENT s
JOIN SPS_RETAIL_AI.SHARED.RECEIPT rec ON s.SHIPMENT_ID = rec.SHIPMENT_ID
JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON s.RETAILER_ID = r.RETAILER_ID
JOIN SPS_RETAIL_AI.SHARED.SUPPLIER sup ON s.SUPPLIER_ID = sup.SUPPLIER_ID
GROUP BY r.RETAILER_NAME, sup.SUPPLIER_NAME, sup.RELIABILITY_TIER
HAVING COUNT(*) >= 10
ORDER BY avg_days_late DESC;
