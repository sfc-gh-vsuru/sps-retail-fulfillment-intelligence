# Setup Guide — SPS Retail Fulfillment Intelligence

**Data Join + AI/ML for Retail Supply Chain**

This guide walks through complete replication of the SPS Retail Fulfillment Intelligence project from scratch: database, tables, data load, views, ML model, predictions, and Streamlit dashboards.

---

## Prerequisites

| Requirement | Details |
|------------|---------|
| Snowflake account | Any edition (Standard or higher); tested on `sfsenorthamerica-demo_vsuru` |
| Role | `ACCOUNTADMIN` or a custom role with `CREATE DATABASE`, `CREATE WAREHOUSE`, `CREATE STREAMLIT` |
| Snowflake CLI | `snow` CLI v3.14+ ([install guide](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation)) |
| Warehouse | `MEDIUM` or larger recommended for ML training; `SMALL` is fine for data loading |
| Data files | Located in `data/` directory of this project |
| Streamlit apps | Located in `streamlit_apps/` directory (5 apps, each with `snowflake.yml` and `streamlit_app.py`) |

---

## Step 1: Create Database and Schemas

```sql
-- Run as ACCOUNTADMIN or role with CREATE DATABASE privilege
USE ROLE ACCOUNTADMIN;

CREATE DATABASE IF NOT EXISTS SPS_RETAIL_AI;

USE DATABASE SPS_RETAIL_AI;

CREATE SCHEMA IF NOT EXISTS SHARED;
CREATE SCHEMA IF NOT EXISTS FOOT_LOCKER;
CREATE SCHEMA IF NOT EXISTS BASS_PRO;
CREATE SCHEMA IF NOT EXISTS URBAN_OUTFITTERS;
CREATE SCHEMA IF NOT EXISTS ML_MODELS;
CREATE SCHEMA IF NOT EXISTS STAGING;
```

---

## Step 2: Create Internal Stage and Upload Data Files

### Create the stage

```sql
USE SCHEMA SPS_RETAIL_AI.STAGING;

CREATE OR REPLACE STAGE SPS_DATA_STAGE
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);
```

### Upload data files

Use the `upload_data.sh` script below or run the `PUT` commands manually.

#### Option A: Shell script

Save and run the following as `setup/upload_data.sh`:

```bash
#!/bin/bash
# upload_data.sh — Upload all CSV data files to the SPS_DATA_STAGE internal stage
# Usage: bash setup/upload_data.sh <snowflake_connection_name>
#
# Prerequisites: snow CLI v3.14+ configured with a valid connection

set -euo pipefail

CONN="${1:-coco_conn}"
STAGE="@SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE"
DATA_DIR="$(cd "$(dirname "$0")/../data" && pwd)"

echo "=== Uploading SPS Retail AI data files ==="
echo "Connection: ${CONN}"
echo "Stage:      ${STAGE}"
echo "Data dir:   ${DATA_DIR}"
echo ""

# Shared schema tables
for file in retailer supplier location item purchase_order po_line shipment receipt invoice retail_calendar; do
  echo "Uploading ${file}.csv ..."
  snow stage copy "${DATA_DIR}/shared/${file}.csv" "${STAGE}/shared/" --connection "${CONN}" --overwrite
done

# SPS Activity (gzipped — large file)
echo "Uploading sps_activity.csv.gz ..."
snow stage copy "${DATA_DIR}/shared/sps_activity.csv.gz" "${STAGE}/shared/" --connection "${CONN}" --overwrite

# Urban Outfitters schema
echo "Uploading sku_crosswalk.csv ..."
snow stage copy "${DATA_DIR}/urban_outfitters/sku_crosswalk.csv" "${STAGE}/urban_outfitters/" --connection "${CONN}" --overwrite

# ML Models schema
echo "Uploading training_data.csv ..."
snow stage copy "${DATA_DIR}/ml_models/training_data.csv" "${STAGE}/ml_models/" --connection "${CONN}" --overwrite

echo ""
echo "=== Upload complete ==="
snow stage list-files "${STAGE}/" --connection "${CONN}"
```

#### Option B: Manual PUT commands (from SnowSQL or Snowsight worksheet)

```sql
-- Shared tables
PUT file:///path/to/data/shared/retailer.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/supplier.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/location.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/item.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/purchase_order.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/po_line.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/shipment.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/receipt.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/invoice.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/retail_calendar.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file:///path/to/data/shared/sps_activity.csv.gz @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Urban Outfitters
PUT file:///path/to/data/urban_outfitters/sku_crosswalk.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/urban_outfitters/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;

-- ML Models
PUT file:///path/to/data/ml_models/training_data.csv @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/ml_models/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
```

---

## Step 3: Create Tables and Load Data

### 3a: Create tables

```sql
USE SCHEMA SPS_RETAIL_AI.SHARED;

-- Retailer (3 rows)
CREATE OR REPLACE TABLE RETAILER (
    RETAILER_ID         NUMBER PRIMARY KEY,
    RETAILER_NAME       VARCHAR,
    ENTERPRISE_NAME     VARCHAR,
    INDUSTRY_SEGMENT    VARCHAR,
    DEFAULT_CURRENCY    VARCHAR,
    EDI_PARTNER         BOOLEAN,
    PO_REVISION_METHOD  VARCHAR,
    USES_UPC            BOOLEAN,
    ACTIVITY_GRAIN      VARCHAR
);

-- Supplier (20 rows)
CREATE OR REPLACE TABLE SUPPLIER (
    SUPPLIER_ID            NUMBER PRIMARY KEY,
    SUPPLIER_NAME          VARCHAR,
    REGION                 VARCHAR,
    COUNTRY                VARCHAR,
    CATEGORY_SPECIALTY     VARCHAR,
    RELIABILITY_TIER       VARCHAR,
    AVG_LEAD_DAYS          NUMBER,
    LEAD_VARIABILITY_DAYS  NUMBER,
    ONBOARDED_DATE         DATE
);

-- Location (60 rows)
CREATE OR REPLACE TABLE LOCATION (
    LOCATION_ID          NUMBER PRIMARY KEY,
    RETAILER_ID          NUMBER REFERENCES RETAILER(RETAILER_ID),
    STORE_NUMBER         VARCHAR,
    STORE_NAME           VARCHAR,
    LOCATION_TYPE        VARCHAR,
    ADDRESS              VARCHAR,
    CITY                 VARCHAR,
    STATE                VARCHAR,
    POSTAL_CODE          VARCHAR,
    COUNTRY              VARCHAR,
    REGION               VARCHAR,
    CLIMATE              VARCHAR,
    BANNER               VARCHAR,
    STORE_CLASSIFICATION VARCHAR,
    STORE_SIZE           VARCHAR
);

-- Item (3,580 rows)
CREATE OR REPLACE TABLE ITEM (
    ITEM_ID              NUMBER PRIMARY KEY,
    RETAILER_ID          NUMBER REFERENCES RETAILER(RETAILER_ID),
    SPS_RETAILER_NAME_KEY VARCHAR,
    CATEGORY_NAME        VARCHAR,
    PRODUCT_GROUP_NAME   VARCHAR,
    GENDER               VARCHAR,
    STYLE_NUMBER         VARCHAR,
    COLOR_NAME           VARCHAR,
    SIZE_NAME            VARCHAR,
    UPC                  VARCHAR,
    SKU                  VARCHAR,
    URBN_SHORT_SKU       VARCHAR,
    BRAND_NAME           VARCHAR,
    MSRP                 NUMBER,
    COST                 NUMBER,
    SUPPLIER_ID          NUMBER REFERENCES SUPPLIER(SUPPLIER_ID),
    DEPARTMENT_NAME      VARCHAR,
    PRODUCT_SEASON       VARCHAR,
    LAUNCH_DATE          DATE,
    EXIT_DATE            DATE
);

-- Purchase Order (10,476 rows)
CREATE OR REPLACE TABLE PURCHASE_ORDER (
    PO_ID                   NUMBER PRIMARY KEY,
    PO_NUMBER               VARCHAR,
    PO_VERSION              NUMBER,
    RETAILER_ID             NUMBER REFERENCES RETAILER(RETAILER_ID),
    SUPPLIER_ID             NUMBER REFERENCES SUPPLIER(SUPPLIER_ID),
    SHIP_TO_LOCATION_ID     NUMBER REFERENCES LOCATION(LOCATION_ID),
    ORDER_DATE              DATE,
    REQUESTED_SHIP_DATE     DATE,
    REQUESTED_DELIVERY_DATE DATE,
    PO_STATUS               VARCHAR,
    REVISION_TYPE           VARCHAR,
    IS_REPLACEMENT_850      BOOLEAN,
    ORIGINAL_PO_ID          NUMBER,
    TOTAL_UNITS             NUMBER,
    TOTAL_COST              NUMBER,
    TOTAL_RETAIL            NUMBER,
    ACCEPTANCE_STATUS       VARCHAR
);

-- PO Line (51,143 rows)
CREATE OR REPLACE TABLE PO_LINE (
    PO_LINE_ID    NUMBER PRIMARY KEY,
    PO_ID         NUMBER REFERENCES PURCHASE_ORDER(PO_ID),
    LINE_NUMBER   NUMBER,
    ITEM_ID       NUMBER REFERENCES ITEM(ITEM_ID),
    ORDERED_QTY   NUMBER,
    UNIT_PRICE    NUMBER,
    LINE_TOTAL    NUMBER,
    LINE_STATUS   VARCHAR,
    SHIPPED_QTY   NUMBER,
    RECEIVED_QTY  NUMBER,
    INVOICED_QTY  NUMBER
);

-- Shipment (9,919 rows)
CREATE OR REPLACE TABLE SHIPMENT (
    SHIPMENT_ID             NUMBER PRIMARY KEY,
    ASN_NUMBER              VARCHAR,
    PO_ID                   NUMBER REFERENCES PURCHASE_ORDER(PO_ID),
    SUPPLIER_ID             NUMBER REFERENCES SUPPLIER(SUPPLIER_ID),
    RETAILER_ID             NUMBER REFERENCES RETAILER(RETAILER_ID),
    CARRIER                 VARCHAR,
    SHIP_DATE               DATE,
    ESTIMATED_DELIVERY_DATE DATE,
    ACTUAL_DELIVERY_DATE    DATE,
    SHIPMENT_STATUS         VARCHAR,
    TOTAL_UNITS             NUMBER,
    TOTAL_CARTONS           NUMBER,
    ON_TIME_FLAG            BOOLEAN,
    IN_FULL_FLAG            BOOLEAN
);

-- Receipt (9,919 rows)
CREATE OR REPLACE TABLE RECEIPT (
    RECEIPT_ID             NUMBER PRIMARY KEY,
    SHIPMENT_ID            NUMBER REFERENCES SHIPMENT(SHIPMENT_ID),
    PO_ID                  NUMBER REFERENCES PURCHASE_ORDER(PO_ID),
    LOCATION_ID            NUMBER REFERENCES LOCATION(LOCATION_ID),
    RETAILER_ID            NUMBER REFERENCES RETAILER(RETAILER_ID),
    RECEIPT_DATE           DATE,
    TOTAL_RECEIVED_UNITS   NUMBER,
    TOTAL_DAMAGED_UNITS    NUMBER,
    RECEIPT_STATUS         VARCHAR,
    DAYS_LATE              NUMBER
);

-- Invoice (9,919 rows)
CREATE OR REPLACE TABLE INVOICE (
    INVOICE_ID       NUMBER PRIMARY KEY,
    INVOICE_NUMBER   VARCHAR,
    PO_ID            NUMBER REFERENCES PURCHASE_ORDER(PO_ID),
    SHIPMENT_ID      NUMBER REFERENCES SHIPMENT(SHIPMENT_ID),
    SUPPLIER_ID      NUMBER REFERENCES SUPPLIER(SUPPLIER_ID),
    RETAILER_ID      NUMBER REFERENCES RETAILER(RETAILER_ID),
    INVOICE_DATE     DATE,
    DUE_DATE         DATE,
    INVOICE_TOTAL    NUMBER,
    PAYMENT_STATUS   VARCHAR,
    MISMATCH_FLAG    BOOLEAN,
    MISMATCH_REASON  VARCHAR
);

-- Retail Calendar (106 rows)
CREATE OR REPLACE TABLE RETAIL_CALENDAR (
    PERIOD_ENDING_DATE NUMBER PRIMARY KEY,
    FISCAL_YEAR        NUMBER,
    FISCAL_QUARTER     NUMBER,
    FISCAL_MONTH       NUMBER,
    FISCAL_WEEK        NUMBER,
    IS_HOLIDAY_WEEK    BOOLEAN,
    SEASON             VARCHAR
);

-- SPS Activity (2,888,606 rows)
CREATE OR REPLACE TABLE SPS_ACTIVITY (
    SPS_CUSTOMER_ITEM_KEY            VARCHAR,
    SPS_RETAILER_NAME_KEY            VARCHAR,
    SPS_CUSTOMER_LOCATION_KEY        VARCHAR,
    SPS_ITEM_MAPPING_KEY             VARCHAR,
    PERIOD_ENDING_DATE               NUMBER,
    NET_SALES_UNITS                  NUMBER,
    NET_SALES_RETAIL                 NUMBER,
    INVENTORY_UNITS                  NUMBER,
    ON_ORDER_UNITS                   NUMBER,
    RECEIPT_UNITS                    NUMBER,
    IN_TRANSIT_UNITS                 NUMBER,
    CUSTOMER_RETURN_UNITS            NUMBER,
    TOTAL_MARKDOWN_VALUES            NUMBER,
    CORPORATE_UNIT_ADJUSTED_COST     NUMBER,
    CORPORATE_UNIT_ACQUIRED_COST     NUMBER,
    CORPORATE_UNIT_OWNED_RETAIL_PRICE NUMBER,
    RETAILER_ID                      NUMBER,
    ITEM_ID                          NUMBER,
    LOCATION_ID                      NUMBER,
    CATEGORY_NAME                    VARCHAR,
    PRODUCT_GROUP_NAME               VARCHAR,
    SEASON                           VARCHAR,
    FISCAL_YEAR                      NUMBER,
    IS_HOLIDAY_WEEK                  BOOLEAN
);
```

```sql
-- Urban Outfitters schema: SKU Crosswalk (650 rows)
USE SCHEMA SPS_RETAIL_AI.URBAN_OUTFITTERS;

CREATE OR REPLACE TABLE SKU_CROSSWALK (
    ITEM_ID             NUMBER,
    URBN_SHORT_SKU      VARCHAR,
    VENDOR_UPC          VARCHAR,
    VENDOR_STYLE_NUMBER VARCHAR,
    STYLE_NUMBER        VARCHAR,
    COLOR_NAME          VARCHAR,
    SIZE_NAME           VARCHAR,
    MAPPING_STATUS      VARCHAR,
    VALID_FROM          DATE,
    VALID_TO            DATE
);
```

```sql
-- ML Models schema: Training Data (9,919 rows)
USE SCHEMA SPS_RETAIL_AI.ML_MODELS;

CREATE OR REPLACE TABLE TRAINING_DATA (
    PO_ID                NUMBER,
    RETAILER_ID          NUMBER,
    SUPPLIER_ID          NUMBER,
    TOTAL_UNITS          NUMBER,
    TOTAL_COST           NUMBER,
    PO_VERSION           NUMBER,
    IS_REPLACEMENT_850   BOOLEAN,
    SUPPLIER_AVG_LEAD    NUMBER,
    SUPPLIER_LEAD_VAR    NUMBER,
    SUPPLIER_REGION      VARCHAR,
    DESTINATION_REGION   VARCHAR,
    DESTINATION_SIZE     VARCHAR,
    LOCATION_TYPE        VARCHAR,
    ORDER_DOW            NUMBER,
    ORDER_MONTH          NUMBER,
    DAYS_TO_DELIVER      NUMBER,
    DAYS_TO_SHIP         NUMBER,
    LINE_COUNT           NUMBER,
    TOTAL_LINE_QTY       NUMBER,
    DISTINCT_ITEMS       NUMBER,
    HIST_ON_TIME_RATE    NUMBER,
    HIST_IN_FULL_RATE    NUMBER,
    HIST_OTIF_RATE       NUMBER,
    HIST_AVG_DAYS_LATE   NUMBER,
    HIST_PO_COUNT        NUMBER,
    IS_LATE_OR_SHORT     NUMBER
);
```

### 3b: Load data from stage

```sql
-- Shared tables
USE SCHEMA SPS_RETAIL_AI.SHARED;

COPY INTO RETAILER FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/retailer.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO SUPPLIER FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/supplier.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO LOCATION FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/location.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO ITEM FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/item.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO PURCHASE_ORDER FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/purchase_order.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO PO_LINE FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/po_line.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO SHIPMENT FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/shipment.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO RECEIPT FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/receipt.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO INVOICE FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/invoice.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

COPY INTO RETAIL_CALENDAR FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/retail_calendar.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

-- SPS Activity: gzipped file, ~2.9M rows
COPY INTO SPS_ACTIVITY FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/shared/sps_activity.csv.gz
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1 COMPRESSION = 'GZIP');

-- Urban Outfitters
USE SCHEMA SPS_RETAIL_AI.URBAN_OUTFITTERS;

COPY INTO SKU_CROSSWALK FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/urban_outfitters/sku_crosswalk.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

-- ML Models
USE SCHEMA SPS_RETAIL_AI.ML_MODELS;

COPY INTO TRAINING_DATA FROM @SPS_RETAIL_AI.STAGING.SPS_DATA_STAGE/ml_models/training_data.csv
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);
```

### 3c: Verify row counts

```sql
SELECT 'RETAILER' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM SPS_RETAIL_AI.SHARED.RETAILER
UNION ALL SELECT 'SUPPLIER', COUNT(*) FROM SPS_RETAIL_AI.SHARED.SUPPLIER
UNION ALL SELECT 'LOCATION', COUNT(*) FROM SPS_RETAIL_AI.SHARED.LOCATION
UNION ALL SELECT 'ITEM', COUNT(*) FROM SPS_RETAIL_AI.SHARED.ITEM
UNION ALL SELECT 'PURCHASE_ORDER', COUNT(*) FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER
UNION ALL SELECT 'PO_LINE', COUNT(*) FROM SPS_RETAIL_AI.SHARED.PO_LINE
UNION ALL SELECT 'SHIPMENT', COUNT(*) FROM SPS_RETAIL_AI.SHARED.SHIPMENT
UNION ALL SELECT 'RECEIPT', COUNT(*) FROM SPS_RETAIL_AI.SHARED.RECEIPT
UNION ALL SELECT 'INVOICE', COUNT(*) FROM SPS_RETAIL_AI.SHARED.INVOICE
UNION ALL SELECT 'RETAIL_CALENDAR', COUNT(*) FROM SPS_RETAIL_AI.SHARED.RETAIL_CALENDAR
UNION ALL SELECT 'SPS_ACTIVITY', COUNT(*) FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY
UNION ALL SELECT 'SKU_CROSSWALK', COUNT(*) FROM SPS_RETAIL_AI.URBAN_OUTFITTERS.SKU_CROSSWALK
UNION ALL SELECT 'TRAINING_DATA', COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.TRAINING_DATA
ORDER BY TABLE_NAME;
```

**Expected counts:**

| Table | Rows |
|-------|------|
| RETAILER | 3 |
| SUPPLIER | 20 |
| LOCATION | 60 |
| ITEM | 3,580 |
| PURCHASE_ORDER | 10,476 |
| PO_LINE | 51,143 |
| SHIPMENT | 9,919 |
| RECEIPT | 9,919 |
| INVOICE | 9,919 |
| RETAIL_CALENDAR | 106 |
| SPS_ACTIVITY | 2,888,606 |
| SKU_CROSSWALK | 650 |
| TRAINING_DATA | 9,919 |

---

## Step 4: Create Views

### 4a: Cross-retailer fulfillment KPI view

```sql
USE SCHEMA SPS_RETAIL_AI.SHARED;

CREATE OR REPLACE VIEW V_FULFILLMENT_KPI AS
SELECT
    po.PO_ID,
    po.PO_NUMBER,
    r.RETAILER_NAME,
    sup.SUPPLIER_NAME,
    sup.RELIABILITY_TIER,
    loc.STORE_NAME,
    loc.REGION,
    loc.STATE,
    po.ORDER_DATE,
    po.REQUESTED_SHIP_DATE,
    po.REQUESTED_DELIVERY_DATE,
    po.PO_STATUS,
    po.TOTAL_UNITS,
    po.TOTAL_COST,
    s.SHIP_DATE,
    s.ACTUAL_DELIVERY_DATE,
    s.ON_TIME_FLAG,
    s.IN_FULL_FLAG,
    CASE WHEN s.ON_TIME_FLAG AND s.IN_FULL_FLAG THEN TRUE ELSE FALSE END AS OTIF_FLAG,
    rec.RECEIPT_DATE,
    rec.TOTAL_RECEIVED_UNITS,
    rec.TOTAL_DAMAGED_UNITS,
    rec.DAYS_LATE,
    inv.INVOICE_TOTAL,
    inv.PAYMENT_STATUS,
    inv.MISMATCH_FLAG,
    inv.MISMATCH_REASON,
    DATEDIFF('day', po.ORDER_DATE, s.SHIP_DATE) AS DAYS_ORDER_TO_SHIP,
    DATEDIFF('day', s.SHIP_DATE, s.ACTUAL_DELIVERY_DATE) AS DAYS_IN_TRANSIT,
    DATEDIFF('day', po.ORDER_DATE, s.ACTUAL_DELIVERY_DATE) AS DAYS_ORDER_TO_DELIVERY
FROM PURCHASE_ORDER po
JOIN RETAILER r ON po.RETAILER_ID = r.RETAILER_ID
JOIN SUPPLIER sup ON po.SUPPLIER_ID = sup.SUPPLIER_ID
JOIN LOCATION loc ON po.SHIP_TO_LOCATION_ID = loc.LOCATION_ID
LEFT JOIN SHIPMENT s ON po.PO_ID = s.PO_ID
LEFT JOIN RECEIPT rec ON po.PO_ID = rec.PO_ID
LEFT JOIN INVOICE inv ON po.PO_ID = inv.PO_ID;
```

### 4b: Foot Locker views

```sql
USE SCHEMA SPS_RETAIL_AI.FOOT_LOCKER;

CREATE OR REPLACE VIEW V_PURCHASE_ORDERS AS
SELECT
    po.PO_ID, po.PO_NUMBER, po.ORDER_DATE, po.REQUESTED_SHIP_DATE,
    po.REQUESTED_DELIVERY_DATE, po.PO_STATUS, po.TOTAL_UNITS, po.TOTAL_COST,
    sup.SUPPLIER_NAME, sup.RELIABILITY_TIER,
    loc.STORE_NAME, loc.BANNER, loc.STORE_CLASSIFICATION, loc.STORE_SIZE,
    loc.REGION, loc.STATE, loc.CITY,
    s.SHIP_DATE, s.ACTUAL_DELIVERY_DATE, s.ON_TIME_FLAG, s.IN_FULL_FLAG,
    CASE WHEN s.ON_TIME_FLAG AND s.IN_FULL_FLAG THEN TRUE ELSE FALSE END AS OTIF_FLAG
FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
JOIN SPS_RETAIL_AI.SHARED.LOCATION loc ON po.SHIP_TO_LOCATION_ID = loc.LOCATION_ID
JOIN SPS_RETAIL_AI.SHARED.SUPPLIER sup ON po.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN SPS_RETAIL_AI.SHARED.SHIPMENT s ON po.PO_ID = s.PO_ID
WHERE po.RETAILER_ID = (SELECT RETAILER_ID FROM SPS_RETAIL_AI.SHARED.RETAILER WHERE RETAILER_NAME = 'Foot Locker');

CREATE OR REPLACE VIEW V_WEEKLY_ACTIVITY AS
SELECT
    a.PERIOD_ENDING_DATE, a.NET_SALES_UNITS, a.NET_SALES_RETAIL,
    a.INVENTORY_UNITS, a.ON_ORDER_UNITS, a.RECEIPT_UNITS,
    a.IN_TRANSIT_UNITS, a.CUSTOMER_RETURN_UNITS, a.IS_HOLIDAY_WEEK,
    i.CATEGORY_NAME, i.PRODUCT_GROUP_NAME, i.SIZE_NAME, i.COLOR_NAME,
    i.GENDER, i.BRAND_NAME, i.MSRP,
    loc.STORE_NAME, loc.BANNER, loc.STORE_CLASSIFICATION, loc.STORE_SIZE, loc.REGION
FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY a
JOIN SPS_RETAIL_AI.SHARED.ITEM i ON a.ITEM_ID = i.ITEM_ID
JOIN SPS_RETAIL_AI.SHARED.LOCATION loc ON a.LOCATION_ID = loc.LOCATION_ID
WHERE a.RETAILER_ID = (SELECT RETAILER_ID FROM SPS_RETAIL_AI.SHARED.RETAILER WHERE RETAILER_NAME = 'Foot Locker');
```

### 4c: Bass Pro views

```sql
USE SCHEMA SPS_RETAIL_AI.BASS_PRO;

CREATE OR REPLACE VIEW V_PURCHASE_ORDERS AS
SELECT
    po.PO_ID, po.PO_NUMBER, po.ORDER_DATE, po.REQUESTED_SHIP_DATE,
    po.REQUESTED_DELIVERY_DATE, po.PO_STATUS, po.TOTAL_UNITS, po.TOTAL_COST,
    sup.SUPPLIER_NAME, sup.RELIABILITY_TIER, sup.CATEGORY_SPECIALTY,
    loc.STORE_NAME, loc.REGION, loc.CLIMATE, loc.STORE_CLASSIFICATION, loc.STORE_SIZE,
    loc.STATE, loc.CITY,
    s.SHIP_DATE, s.ACTUAL_DELIVERY_DATE, s.ON_TIME_FLAG, s.IN_FULL_FLAG,
    CASE WHEN s.ON_TIME_FLAG AND s.IN_FULL_FLAG THEN TRUE ELSE FALSE END AS OTIF_FLAG
FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
JOIN SPS_RETAIL_AI.SHARED.LOCATION loc ON po.SHIP_TO_LOCATION_ID = loc.LOCATION_ID
JOIN SPS_RETAIL_AI.SHARED.SUPPLIER sup ON po.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN SPS_RETAIL_AI.SHARED.SHIPMENT s ON po.PO_ID = s.PO_ID
WHERE po.RETAILER_ID = (SELECT RETAILER_ID FROM SPS_RETAIL_AI.SHARED.RETAILER WHERE RETAILER_NAME = 'Bass Pro Shops');

CREATE OR REPLACE VIEW V_WEEKLY_ACTIVITY AS
SELECT
    a.PERIOD_ENDING_DATE, a.NET_SALES_UNITS, a.NET_SALES_RETAIL,
    a.INVENTORY_UNITS, a.ON_ORDER_UNITS, a.RECEIPT_UNITS,
    a.IN_TRANSIT_UNITS, a.IS_HOLIDAY_WEEK,
    i.CATEGORY_NAME, i.PRODUCT_GROUP_NAME, i.PRODUCT_SEASON, i.BRAND_NAME,
    i.MSRP, i.COST,
    loc.STORE_NAME, loc.REGION, loc.CLIMATE, loc.STORE_CLASSIFICATION, loc.STORE_SIZE
FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY a
JOIN SPS_RETAIL_AI.SHARED.ITEM i ON a.ITEM_ID = i.ITEM_ID
JOIN SPS_RETAIL_AI.SHARED.LOCATION loc ON a.LOCATION_ID = loc.LOCATION_ID
WHERE a.RETAILER_ID = (SELECT RETAILER_ID FROM SPS_RETAIL_AI.SHARED.RETAILER WHERE RETAILER_NAME = 'Bass Pro Shops');
```

### 4d: Urban Outfitters views

```sql
USE SCHEMA SPS_RETAIL_AI.URBAN_OUTFITTERS;

CREATE OR REPLACE VIEW V_PURCHASE_ORDERS AS
SELECT
    po.PO_ID, po.PO_NUMBER, po.ORDER_DATE, po.REQUESTED_SHIP_DATE,
    po.REQUESTED_DELIVERY_DATE, po.PO_STATUS, po.TOTAL_UNITS, po.TOTAL_COST,
    po.IS_REPLACEMENT_850, po.REVISION_TYPE, po.ORIGINAL_PO_ID, po.PO_VERSION,
    CASE WHEN po.IS_REPLACEMENT_850 THEN 'REPLACEMENT' ELSE 'ORIGINAL' END AS PO_TYPE_LABEL,
    sup.SUPPLIER_NAME, sup.RELIABILITY_TIER,
    loc.STORE_NAME, loc.REGION, loc.STORE_CLASSIFICATION, loc.STORE_SIZE,
    loc.STATE, loc.CITY,
    s.SHIP_DATE, s.ACTUAL_DELIVERY_DATE, s.ON_TIME_FLAG, s.IN_FULL_FLAG,
    CASE WHEN s.ON_TIME_FLAG AND s.IN_FULL_FLAG THEN TRUE ELSE FALSE END AS OTIF_FLAG
FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
JOIN SPS_RETAIL_AI.SHARED.LOCATION loc ON po.SHIP_TO_LOCATION_ID = loc.LOCATION_ID
JOIN SPS_RETAIL_AI.SHARED.SUPPLIER sup ON po.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN SPS_RETAIL_AI.SHARED.SHIPMENT s ON po.PO_ID = s.PO_ID
WHERE po.RETAILER_ID = (SELECT RETAILER_ID FROM SPS_RETAIL_AI.SHARED.RETAILER WHERE RETAILER_NAME = 'Urban Outfitters');

CREATE OR REPLACE VIEW V_WEEKLY_ACTIVITY AS
SELECT
    a.PERIOD_ENDING_DATE, a.NET_SALES_UNITS, a.NET_SALES_RETAIL,
    a.INVENTORY_UNITS, a.ON_ORDER_UNITS, a.RECEIPT_UNITS,
    a.IN_TRANSIT_UNITS, a.CUSTOMER_RETURN_UNITS, a.IS_HOLIDAY_WEEK,
    i.CATEGORY_NAME, i.PRODUCT_GROUP_NAME, i.URBN_SHORT_SKU, i.BRAND_NAME,
    i.MSRP, i.STYLE_NUMBER, i.COLOR_NAME, i.SIZE_NAME,
    loc.STORE_NAME, loc.REGION, loc.STORE_CLASSIFICATION,
    xw.MAPPING_STATUS AS SKU_MAPPING_STATUS
FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY a
JOIN SPS_RETAIL_AI.SHARED.ITEM i ON a.ITEM_ID = i.ITEM_ID
JOIN SPS_RETAIL_AI.SHARED.LOCATION loc ON a.LOCATION_ID = loc.LOCATION_ID
LEFT JOIN SPS_RETAIL_AI.URBAN_OUTFITTERS.SKU_CROSSWALK xw ON i.ITEM_ID = xw.ITEM_ID
WHERE a.RETAILER_ID = (SELECT RETAILER_ID FROM SPS_RETAIL_AI.SHARED.RETAILER WHERE RETAILER_NAME = 'Urban Outfitters');
```

---

## Step 5: Create and Train ML Model

```sql
USE SCHEMA SPS_RETAIL_AI.ML_MODELS;

-- Train a classification model to predict IS_LATE_OR_SHORT
CREATE OR REPLACE SNOWFLAKE.ML.CLASSIFICATION FULFILLMENT_RISK_MODEL(
    INPUT_DATA => SYSTEM$REFERENCE('TABLE', 'SPS_RETAIL_AI.ML_MODELS.TRAINING_DATA'),
    TARGET_COLNAME => 'IS_LATE_OR_SHORT'
);
```

Training takes 2-5 minutes on a `MEDIUM` warehouse. The model achieves:
- **91.3% accuracy** overall
- **99.6% precision** on risk flags (when it says "at risk," it's almost always right)
- **52.5% recall** (catches about half of actual failures)
- **18.3% failure rate** in the data (realistic for retail fulfillment)

---

## Step 6: Generate Predictions

```sql
USE SCHEMA SPS_RETAIL_AI.ML_MODELS;

-- Score all training records to create a predictions table for dashboards
CREATE OR REPLACE TABLE FULFILLMENT_PREDICTIONS AS
SELECT
    td.*,
    FULFILLMENT_RISK_MODEL!PREDICT(
        INPUT_DATA => OBJECT_CONSTRUCT(*)
    ) AS PREDICTION_RESULT,
    PREDICTION_RESULT:"class"::NUMBER AS PREDICTED_RISK,
    PREDICTION_RESULT:"probability"::OBJECT AS PREDICTION_PROBABILITIES
FROM TRAINING_DATA td;
```

---

## Step 7: Deploy Streamlit Dashboards

The project includes 5 Streamlit apps in `streamlit_apps/`, each with a `snowflake.yml` configuration. Deploy using the Snowflake CLI.

### 7a: Deploy each app

```bash
# From the project root directory
cd streamlit_apps/sps_fulfillment_intelligence
snow streamlit deploy --connection coco_conn --replace

cd ../sps_foot_locker
snow streamlit deploy --connection coco_conn --replace

cd ../sps_bass_pro
snow streamlit deploy --connection coco_conn --replace

cd ../sps_urban_outfitters
snow streamlit deploy --connection coco_conn --replace

cd ../sps_partner_value_lab
snow streamlit deploy --connection coco_conn --replace
```

Each `snowflake.yml` already specifies:
- The database (`SPS_RETAIL_AI`)
- The schema for the app
- The warehouse to use
- The main file (`streamlit_app.py`)
- Native Streamlit runtime (not container)

### 7b: Alternative — Manual CREATE STREAMLIT

If you prefer to create the apps via SQL instead of CLI:

```sql
-- Example for the main fulfillment intelligence dashboard
-- First, create a stage and upload the app file
CREATE OR REPLACE STAGE SPS_RETAIL_AI.SHARED.STREAMLIT_STAGE;
PUT file:///path/to/streamlit_apps/sps_fulfillment_intelligence/streamlit_app.py
  @SPS_RETAIL_AI.SHARED.STREAMLIT_STAGE/sps_fulfillment_intelligence/ OVERWRITE=TRUE AUTO_COMPRESS=FALSE;

CREATE OR REPLACE STREAMLIT SPS_RETAIL_AI.SHARED.SPS_FULFILLMENT_INTELLIGENCE
  ROOT_LOCATION = '@SPS_RETAIL_AI.SHARED.STREAMLIT_STAGE/sps_fulfillment_intelligence'
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = '<YOUR_WAREHOUSE>';

-- Repeat for each of the 5 apps, adjusting schema and stage paths
```

---

## Verification Checklist

After completing all steps, verify:

- [ ] 13 tables loaded with expected row counts (Step 3c)
- [ ] `V_FULFILLMENT_KPI` returns data for all 3 retailers
- [ ] Each retailer's `V_PURCHASE_ORDERS` and `V_WEEKLY_ACTIVITY` views return data
- [ ] `FULFILLMENT_RISK_MODEL` exists: `SHOW SNOWFLAKE.ML.CLASSIFICATION;`
- [ ] `FULFILLMENT_PREDICTIONS` table has 9,919 rows with non-null predictions
- [ ] All 5 Streamlit apps are accessible from Snowsight

---

## Repo Structure

```
sps_retail_fulfillment_intelligence/
│
├── README.md                       ← Project overview and dashboards
├── SETUP.md                        ← Full replication guide (you are here)
├── DEMO_TALK_TRACK.md              ← Presenter walk-through
│
├── datamodels/                     ← Data model references per company
│   ├── SPS_DATAMODEL.md
│   ├── FOOTLOCKER_DATAMODEL.md
│   ├── BASSPRO_DATAMODEL.md
│   └── URBANOUTFITTERS_DATAMODEL.md
│
├── apps/                           ← 5 Streamlit dashboard source files
│   ├── sps_fulfillment_intelligence.py
│   ├── sps_foot_locker.py
│   ├── sps_bass_pro.py
│   ├── sps_urban_outfitters.py
│   └── sps_partner_value_lab.py
│
├── data/                           ← All datasets as CSV
│   ├── shared/                     ← 11 tables (retailer, supplier, item, ...)
│   │   └── sps_activity.csv.gz    ← 2.9M rows, gzipped (~43MB)
│   ├── ml_models/                  ← ML training data
│   └── urban_outfitters/           ← SKU crosswalk
│
├── setup/                          ← SQL + shell scripts for full replication
│   ├── 01_environment.sql          ← Database, schemas, stages
│   ├── 02_load_data.sql            ← CREATE TABLE + COPY INTO
│   ├── 03_views.sql                ← Analytical views
│   ├── 04_ml_model.sql             ← SNOWFLAKE.ML.CLASSIFICATION train + predict
│   ├── 05_streamlit_apps.sql       ← CREATE STREAMLIT (native runtime)
│   └── upload_data.sh              ← Upload data + apps to Snowflake stages
│
├── images/                         ← Dashboard screenshots
│
└── src_docs/                       ← Internal only (gitignored)
    ├── PLAN.md                     ← Original project plan
    ├── RESEARCH.md                 ← Research findings and sources
    ├── DATA_AND_ML_CONTRACTS.md    ← Field-level data contracts
    ├── PUBLISHED_ACTIVITY_SCHEMA.csv
    ├── VERIFIED_SHARE_SCHEMA.csv
    └── sql/                        ← Original data generation scripts
```

---

## Quick Start

```bash
# 1. Create database, schemas, and stages
snow sql -f setup/01_environment.sql --connection coco_conn

# 2. Upload CSV data and Streamlit apps to Snowflake stages
bash setup/upload_data.sh coco_conn

# 3. Create tables and load data
snow sql -f setup/02_load_data.sql --connection coco_conn

# 4. Create analytical views
snow sql -f setup/03_views.sql --connection coco_conn

# 5. Train ML model and generate predictions
snow sql -f setup/04_ml_model.sql --connection coco_conn

# 6. Deploy Streamlit dashboards
snow sql -f setup/05_streamlit_apps.sql --connection coco_conn
```

**Prerequisites:** Snowflake account, [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) v3.14+, a role with `CREATE DATABASE` privileges.

---

## Documentation

| Document | Description |
|---|---|
| [SETUP.md](SETUP.md) | Complete replication guide with verification steps |
| [DEMO_TALK_TRACK.md](DEMO_TALK_TRACK.md) | Presenter script: executive opening → 5 dashboards → closing |
| [SPS_DATAMODEL.md](datamodels/SPS_DATAMODEL.md) | SPS Commerce data model (EDI documents + activity feed) |
| [FOOTLOCKER_DATAMODEL.md](datamodels/FOOTLOCKER_DATAMODEL.md) | Foot Locker data model (banners, sizes, launches) |
| [BASSPRO_DATAMODEL.md](datamodels/BASSPRO_DATAMODEL.md) | Bass Pro Shops data model (seasons, regions, climate) |
| [URBANOUTFITTERS_DATAMODEL.md](datamodels/URBANOUTFITTERS_DATAMODEL.md) | Urban Outfitters data model (SKU crosswalk, replacement POs) |
