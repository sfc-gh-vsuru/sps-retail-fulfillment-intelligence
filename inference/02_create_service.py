"""
Inference Add-On — Step 2: Deploy FULFILLMENT_RISK_XGB V2 as a real-time inference service (SPCS)
with a public HTTPS endpoint.

Takes ~10 minutes. Run in the background and monitor with:
    DESCRIBE SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC;
    SHOW ENDPOINTS IN SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC;

Run:
    SNOWFLAKE_CONNECTION_NAME=coco_conn inference/.venv/bin/python inference/02_create_service.py
"""

from snowflake.ml.registry import Registry

from snowpark_session import create_snowpark_session

DATABASE = "SPS_RETAIL_AI"
SCHEMA = "ML_INFERENCE"
MODEL_NAME = "FULFILLMENT_RISK_XGB"
VERSION = "V2"
SERVICE_NAME = "FULFILLMENT_RISK_SVC"
COMPUTE_POOL = "SYSTEM_COMPUTE_POOL_CPU"


def main() -> None:
    session = create_snowpark_session()
    session.use_database(DATABASE)
    session.use_schema(SCHEMA)

    reg = Registry(session=session, database_name=DATABASE, schema_name=SCHEMA)
    mv = reg.get_model(MODEL_NAME).version(VERSION)

    print(f"Creating service {DATABASE}.{SCHEMA}.{SERVICE_NAME} on {COMPUTE_POOL} ...")
    mv.create_service(
        service_name=SERVICE_NAME,
        service_compute_pool=COMPUTE_POOL,
        ingress_enabled=True,
        max_instances=1,
    )
    print("Service created successfully.")
    print(mv.list_services())


if __name__ == "__main__":
    main()
