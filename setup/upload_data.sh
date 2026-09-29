#!/bin/bash
# ============================================================================
# SPS Retail Fulfillment Intelligence — Upload Data & App Files to Snowflake
# Run AFTER 01_environment.sql (stages must exist)
# Requires: Snowflake CLI (snow) v3.14+ with connection 'coco_conn' configured
# ============================================================================

set -e

CONN="${1:-coco_conn}"
SNOW="snow"

echo "=== Uploading CSV data files to DATA_STAGE ==="

# Shared dimension and transaction tables
for file in data/shared/retailer.csv data/shared/supplier.csv data/shared/location.csv \
            data/shared/item.csv data/shared/retail_calendar.csv \
            data/shared/purchase_order.csv data/shared/po_line.csv \
            data/shared/shipment.csv data/shared/receipt.csv data/shared/invoice.csv; do
    echo "  Uploading $file ..."
    $SNOW stage copy "$file" "@SPS_RETAIL_AI.PUBLIC.DATA_STAGE/$(dirname $file)/" \
        --overwrite --connection "$CONN" 2>&1 | tail -1
done

# SPS Activity (gzipped, ~43MB)
echo "  Uploading data/shared/sps_activity.csv.gz (large file) ..."
$SNOW stage copy "data/shared/sps_activity.csv.gz" "@SPS_RETAIL_AI.PUBLIC.DATA_STAGE/shared/" \
    --overwrite --connection "$CONN" 2>&1 | tail -1

# ML training data
echo "  Uploading data/ml_models/training_data.csv ..."
$SNOW stage copy "data/ml_models/training_data.csv" "@SPS_RETAIL_AI.PUBLIC.DATA_STAGE/ml_models/" \
    --overwrite --connection "$CONN" 2>&1 | tail -1

# Urban Outfitters SKU crosswalk
echo "  Uploading data/urban_outfitters/sku_crosswalk.csv ..."
$SNOW stage copy "data/urban_outfitters/sku_crosswalk.csv" "@SPS_RETAIL_AI.PUBLIC.DATA_STAGE/urban_outfitters/" \
    --overwrite --connection "$CONN" 2>&1 | tail -1

echo ""
echo "=== Uploading Streamlit app files to STREAMLIT_STAGE ==="

for app in sps_fulfillment_intelligence sps_foot_locker sps_bass_pro sps_urban_outfitters sps_partner_value_lab; do
    echo "  Uploading apps/${app}.py ..."
    $SNOW stage copy "apps/${app}.py" "@SPS_RETAIL_AI.PUBLIC.STREAMLIT_STAGE/${app}/streamlit_app.py" \
        --overwrite --connection "$CONN" 2>&1 | tail -1
done

echo ""
echo "=== Upload complete ==="
echo "Next steps:"
echo "  1. Run setup/02_load_data.sql  (create tables and load CSVs)"
echo "  2. Run setup/03_views.sql      (create analytical views)"
echo "  3. Run setup/04_ml_model.sql   (train ML model and generate predictions)"
echo "  4. Run setup/05_streamlit_apps.sql (deploy Streamlit dashboards)"
