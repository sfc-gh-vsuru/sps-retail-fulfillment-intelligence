-- ============================================================================
-- SPS Retail Fulfillment Intelligence — Environment Setup
-- Step 1: Database, schemas, warehouse, stage, file format
-- ============================================================================

USE ROLE CORTEXCODECLIROLE;  -- or your role with CREATE DATABASE

CREATE DATABASE IF NOT EXISTS SPS_RETAIL_AI
  COMMENT = 'SPS Commerce Retail Fulfillment Intelligence - AI/ML Demo with Foot Locker, Bass Pro Shops, Urban Outfitters';

USE DATABASE SPS_RETAIL_AI;

CREATE SCHEMA IF NOT EXISTS SHARED COMMENT = 'Shared dimensions, SPS activity data, and cross-retailer entities';
CREATE SCHEMA IF NOT EXISTS FOOT_LOCKER COMMENT = 'Foot Locker fulfillment transactions, launch readiness, and predictions';
CREATE SCHEMA IF NOT EXISTS BASS_PRO COMMENT = 'Bass Pro Shops fulfillment transactions, seasonal demand, and predictions';
CREATE SCHEMA IF NOT EXISTS URBAN_OUTFITTERS COMMENT = 'Urban Outfitters fulfillment transactions, PO revisions, SKU crosswalk, and predictions';
CREATE SCHEMA IF NOT EXISTS ML_MODELS COMMENT = 'ML feature stores, training datasets, predictions, and model artifacts';
CREATE SCHEMA IF NOT EXISTS STAGING COMMENT = 'Intermediate tables for data generation and transformation';

CREATE WAREHOUSE IF NOT EXISTS COCOWH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 120
  AUTO_RESUME = TRUE;

USE WAREHOUSE COCOWH;

-- Stage for CSV data files
CREATE STAGE IF NOT EXISTS SPS_RETAIL_AI.PUBLIC.DATA_STAGE
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'CSV data files for table loading';

-- Stage for Streamlit app files
CREATE STAGE IF NOT EXISTS SPS_RETAIL_AI.PUBLIC.STREAMLIT_STAGE
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Streamlit app source files';

-- CSV file format
CREATE FILE FORMAT IF NOT EXISTS SPS_RETAIL_AI.PUBLIC.CSV_FORMAT
  TYPE = 'CSV'
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 1
  NULL_IF = ('', 'NULL');
