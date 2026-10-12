"""
Inference Add-On — Step 1: Train an XGBoost fulfillment risk model and log it to the Model Registry.

Reads  : SPS_RETAIL_AI.ML_MODELS.TRAINING_DATA          (read-only, shared with the dashboards)
Writes : SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_XGB (new model version)
         SPS_RETAIL_AI.ML_INFERENCE.SAMPLE_REQUESTS      (demo POs, overwritten)

Versions:
  V1 — pre-ship features only. ROC AUC ~0.50: in this dataset late/short is driven by actual
       delivery timing, so pre-ship signals carry no information. Kept for reference, not deployed.
  V2 — same inputs as the dashboard model (adds DAYS_TO_SHIP, DAYS_TO_DELIVER). Deployed.
       Use case: score a shipment once its ship/delivery timing is known.

Run:
    SNOWFLAKE_CONNECTION_NAME=coco_conn inference/.venv/bin/python inference/01_train_register.py
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from snowflake.ml.registry import Registry
from xgboost import XGBClassifier

from snowpark_session import create_snowpark_session

DATABASE = "SPS_RETAIL_AI"
SCHEMA = "ML_INFERENCE"
MODEL_NAME = "FULFILLMENT_RISK_XGB"
VERSION = "V2"
TARGET = "IS_LATE_OR_SHORT"

# Same inputs as the dashboard classification model (identifiers PO_ID / SUPPLIER_ID excluded).
CATEGORICAL = ["RETAILER_ID", "SUPPLIER_REGION", "DESTINATION_REGION", "DESTINATION_SIZE", "LOCATION_TYPE"]
NUMERIC = [
    "IS_REPLACEMENT_850", "PO_VERSION", "TOTAL_UNITS", "TOTAL_COST", "LINE_COUNT", "TOTAL_LINE_QTY",
    "DISTINCT_ITEMS", "ORDER_DOW", "ORDER_MONTH", "SUPPLIER_AVG_LEAD", "SUPPLIER_LEAD_VAR",
    "HIST_ON_TIME_RATE", "HIST_IN_FULL_RATE", "HIST_OTIF_RATE", "HIST_AVG_DAYS_LATE", "HIST_PO_COUNT",
    "DAYS_TO_SHIP", "DAYS_TO_DELIVER",
]
FEATURES = CATEGORICAL + NUMERIC


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Consistent dtypes so the registry signature is simple: strings + float64."""
    out = df[FEATURES].copy()
    for c in CATEGORICAL:
        out[c] = out[c].fillna("UNKNOWN").astype(str)
    out["IS_REPLACEMENT_850"] = out["IS_REPLACEMENT_850"].astype(bool).astype(int)
    for c in NUMERIC:
        out[c] = pd.to_numeric(out[c], errors="coerce").astype("float64")
    return out


def main() -> None:
    session = create_snowpark_session()
    session.use_database(DATABASE)
    session.use_schema(SCHEMA)

    raw = session.table(f"{DATABASE}.ML_MODELS.TRAINING_DATA").to_pandas()
    X = prepare(raw)
    y = raw[TARGET].astype(int)
    print(f"Loaded {len(raw):,} POs | late/short rate {y.mean():.1%} | {len(FEATURES)} features")

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, raw.index, test_size=0.2, stratify=y, random_state=42
    )

    pipeline = Pipeline([
        ("encode", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL)],
            remainder="passthrough",
        )),
        ("xgb", XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9,
            eval_metric="logloss", random_state=42,
        )),
    ])
    pipeline.fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = {
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision": round(precision_score(y_test, pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, pred), 4),
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
    }
    print("Hold-out metrics (20% test set):", metrics)

    reg = Registry(session=session, database_name=DATABASE, schema_name=SCHEMA)
    models = reg.show_models()
    if not models.empty and MODEL_NAME in models["name"].str.upper().tolist():
        versions = reg.get_model(MODEL_NAME).show_versions()["name"].str.upper().tolist()
        if VERSION.upper() in versions:
            raise SystemExit(f"{MODEL_NAME} {VERSION} already exists — bump VERSION instead of overwriting.")

    mv = reg.log_model(
        pipeline,
        model_name=MODEL_NAME,
        version_name=VERSION,
        sample_input_data=X_train.head(20),
        conda_dependencies=["xgboost==3.2.0", "scikit-learn==1.7.2"],
        target_platforms=["WAREHOUSE", "SNOWPARK_CONTAINER_SERVICES"],
        comment="Fulfillment risk (XGBoost), same inputs as the dashboard model. Served via SPCS REST.",
    )
    for k, v in metrics.items():
        mv.set_metric(k, v)
    print(f"Registered {DATABASE}.{SCHEMA}.{MODEL_NAME} version {VERSION}")
    for f in mv.show_functions():
        print("  function:", f["name"])

    # Demo samples: the 3 clearest LOW-risk and 3 clearest HIGH-risk POs from the hold-out set.
    test = raw.loc[idx_test].copy()
    test["EXPECTED_RISK_PROB"] = proba.round(4)
    picks = pd.concat([
        test.nsmallest(3, "EXPECTED_RISK_PROB").assign(SAMPLE_LABEL="Low risk"),
        test.nlargest(3, "EXPECTED_RISK_PROB").assign(SAMPLE_LABEL="High risk"),
    ])
    picks["ACTUAL_OUTCOME"] = picks[TARGET].map({0: "Delivered OTIF", 1: "Late/short"})
    samples = pd.concat(
        [picks[["PO_ID", "SAMPLE_LABEL", "ACTUAL_OUTCOME", "EXPECTED_RISK_PROB"]].reset_index(drop=True),
         prepare(picks).reset_index(drop=True)],
        axis=1,
    )
    session.write_pandas(samples, "SAMPLE_REQUESTS", database=DATABASE, schema=SCHEMA,
                         auto_create_table=True, overwrite=True)
    print("SAMPLE_REQUESTS refreshed:")
    print(samples[["PO_ID", "SAMPLE_LABEL", "ACTUAL_OUTCOME", "EXPECTED_RISK_PROB", "RETAILER_ID", "HIST_OTIF_RATE"]])


if __name__ == "__main__":
    main()
