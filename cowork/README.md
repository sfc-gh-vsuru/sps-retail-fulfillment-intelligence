# Cortex Analyst (Cowork) — SPS Fulfillment Intelligence

This folder contains the semantic view definition and sample queries for using
**Cortex Analyst** in Snowsight to ask natural-language questions about SPS
Commerce fulfillment data.

## Files

| File | Purpose |
|---|---|
| `sps_fulfillment_intelligence_semantic_model.yaml` | Semantic view YAML — 9 tables, 16 relationships, 5 verified queries |
| `01_deploy_semantic_view.sql` | Deployment script to create the semantic view in Snowflake |
| `02_sample_queries.sql` | SQL versions of the 5 test questions plus a bonus query |

## How to Use in Snowsight

1. Deploy the semantic view (see `01_deploy_semantic_view.sql`)
2. In Snowsight, open **Cortex Analyst** from the left nav
3. Select the `SPS_FULFILLMENT_INTELLIGENCE` semantic view
4. Ask questions in natural language

## Test Questions

Try these 5 questions to validate the semantic view covers the same insights as the Streamlit dashboards:

| # | Question | Maps to Dashboard |
|---|---|---|
| 1 | What is the OTIF rate for each retailer? | Fulfillment Intelligence — KPIs |
| 2 | Which suppliers have the highest risk of late or short deliveries? | Fulfillment Intelligence — ML Risk |
| 3 | What is the invoice mismatch rate by retailer? | Fulfillment Intelligence — Invoice Reconciliation |
| 4 | What are the top product categories by total order value across all retailers? | Foot Locker / Bass Pro / Urban Outfitters |
| 5 | How does the ML model accuracy compare across retailers? | Partner Value Lab — ML Accuracy |

## Semantic Model Coverage

**Tables:** PURCHASE_ORDER, PO_LINE, SHIPMENT, RECEIPT, INVOICE, RETAILER, SUPPLIER, LOCATION, ITEM, FULFILLMENT_PREDICTIONS

**Key relationships:** PO → Retailer, PO → Supplier, PO → Location, Shipment → PO, Receipt → Shipment, Invoice → PO, PO Line → Item, Predictions → PO
