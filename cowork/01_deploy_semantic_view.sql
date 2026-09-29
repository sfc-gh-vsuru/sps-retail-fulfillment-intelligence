-- =============================================================================
-- SPS Fulfillment Intelligence — Semantic View Deployment
-- Deploy the semantic model as a Snowflake Semantic View for Cortex Analyst
-- =============================================================================
-- Run this from the project root:
--   cat cowork/01_deploy_semantic_view.sql | snow sql --connection coco_conn
--
-- Or build the full deployment SQL:
--   1. Write header:  echo "CALL SYSTEM\$CREATE_SEMANTIC_VIEW_FROM_YAML('SPS_RETAIL_AI.PUBLIC', \$\$" > /tmp/sv.sql
--   2. Append YAML:   cat cowork/sps_fulfillment_intelligence_semantic_model.yaml >> /tmp/sv.sql
--   3. Close call:    echo "\$\$);" >> /tmp/sv.sql
--   4. Execute:       snow sql -f /tmp/sv.sql --connection coco_conn
-- =============================================================================

USE ROLE CORTEXCODECLIROLE;
USE WAREHOUSE COCOWH;
USE DATABASE SPS_RETAIL_AI;
USE SCHEMA PUBLIC;

-- Step 1: Create a stage for the semantic model YAML (optional, for backup)
CREATE STAGE IF NOT EXISTS SPS_RETAIL_AI.PUBLIC.SEMANTIC_STAGE;

-- Step 2: Upload the YAML to stage (optional backup)
-- snow stage copy cowork/sps_fulfillment_intelligence_semantic_model.yaml @SPS_RETAIL_AI.PUBLIC.SEMANTIC_STAGE --connection coco_conn

-- Step 3: Create the semantic view using SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML
-- The YAML content must be wrapped in dollar-quoted string ($$..$$)
-- See shell commands above for the full deployment workflow

-- Verify deployment:
SHOW SEMANTIC VIEWS IN SPS_RETAIL_AI.PUBLIC;

-- Grant access for other roles if needed:
-- GRANT SELECT ON SEMANTIC VIEW SPS_RETAIL_AI.PUBLIC.SPS_FULFILLMENT_INTELLIGENCE TO ROLE <role_name>;
