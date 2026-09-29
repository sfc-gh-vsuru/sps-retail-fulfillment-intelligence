-- ============================================================================
-- SPS Retail Fulfillment Intelligence — Deploy Streamlit Apps
-- Step 5: Create Streamlit apps using native runtime (no container)
-- Run AFTER upload_data.sh has uploaded app files to STREAMLIT_STAGE
-- ============================================================================

USE DATABASE SPS_RETAIL_AI;
USE SCHEMA PUBLIC;

-- 1. SPS Fulfillment Intelligence (cross-retailer overview)
CREATE OR REPLACE STREAMLIT SPS_FULFILLMENT_INTELLIGENCE
    ROOT_LOCATION = '@SPS_RETAIL_AI.PUBLIC.STREAMLIT_STAGE/sps_fulfillment_intelligence'
    MAIN_FILE = '/streamlit_app.py'
    QUERY_WAREHOUSE = 'COCOWH'
    TITLE = 'SPS Fulfillment Intelligence'
    COMMENT = 'Cross-retailer fulfillment health, ML risk predictions, supplier performance';

-- 2. SPS + Foot Locker
CREATE OR REPLACE STREAMLIT SPS_FOOT_LOCKER
    ROOT_LOCATION = '@SPS_RETAIL_AI.PUBLIC.STREAMLIT_STAGE/sps_foot_locker'
    MAIN_FILE = '/streamlit_app.py'
    QUERY_WAREHOUSE = 'COCOWH'
    TITLE = 'SPS + Foot Locker'
    COMMENT = 'Launch readiness, size availability, multi-banner fulfillment';

-- 3. SPS + Bass Pro Shops
CREATE OR REPLACE STREAMLIT SPS_BASS_PRO
    ROOT_LOCATION = '@SPS_RETAIL_AI.PUBLIC.STREAMLIT_STAGE/sps_bass_pro'
    MAIN_FILE = '/streamlit_app.py'
    QUERY_WAREHOUSE = 'COCOWH'
    TITLE = 'SPS + Bass Pro Shops'
    COMMENT = 'Seasonal availability, inventory weeks-of-supply, supplier reliability';

-- 4. SPS + Urban Outfitters
CREATE OR REPLACE STREAMLIT SPS_URBAN_OUTFITTERS
    ROOT_LOCATION = '@SPS_RETAIL_AI.PUBLIC.STREAMLIT_STAGE/sps_urban_outfitters'
    MAIN_FILE = '/streamlit_app.py'
    QUERY_WAREHOUSE = 'COCOWH'
    TITLE = 'SPS + Urban Outfitters'
    COMMENT = 'Replacement PO tracking, URBN short SKU crosswalk, pre-ship readiness risk';

-- 5. SPS Partner Value Lab
CREATE OR REPLACE STREAMLIT SPS_PARTNER_VALUE_LAB
    ROOT_LOCATION = '@SPS_RETAIL_AI.PUBLIC.STREAMLIT_STAGE/sps_partner_value_lab'
    MAIN_FILE = '/streamlit_app.py'
    QUERY_WAREHOUSE = 'COCOWH'
    TITLE = 'SPS Partner Value Lab'
    COMMENT = 'Multi-retailer comparison, ML accuracy by retailer, feature importance, data value';

-- Verify all apps are deployed
SHOW STREAMLITS IN DATABASE SPS_RETAIL_AI;
