# Inference Add-On: Calling the Fulfillment Risk Model from Outside Snowflake

An app running **outside Snowflake** (your laptop) sends a purchase order over HTTPS and gets back:

1. **A risk score** from a **Snowflake ML real-time inference REST endpoint**. This is a Model Registry model served on Snowpark Container Services.
2. **A plain-English explanation** from the **Cortex REST API** (`claude-sonnet-4-5`).

Both calls are plain `requests.post(...)` with a Programmatic Access Token (PAT). There is no Snowflake driver, UDF, or stored procedure in the request path.

Official docs used:
- [Deploy models for real-time inference (REST API)](https://docs.snowflake.com/en/developer-guide/snowflake-ml/inference/real-time-inference-rest-api)
- [Cortex REST API](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-rest-api)

| Document | Contents |
|---|---|
| **INFERENCE_README.md** (this file) | Overview, isolation, files, REST API reference, model notes, operations, troubleshooting |
| [INFERENCE_SETUP.md](INFERENCE_SETUP.md) | Step-by-step setup, verification, teardown |
| [INFERENCE_DEMO_TALK_TRACK.md](INFERENCE_DEMO_TALK_TRACK.md) | Presenter script, pre-demo checklist, Q&A |
| [inference_plan.md](inference_plan.md) | Design plan and decisions |

The main project docs (`../README.md`, `../SETUP.md`, `../DEMO_TALK_TRACK.md`) are unchanged. This add-on is documented only in this folder.

---

## Architecture

```
┌──────────── Your laptop ────────────┐          ┌───────────────────── Snowflake ─────────────────────┐
│                                     │  HTTPS   │                                                     │
│  app_streamlit.py  (localhost:8501) │──+ PAT──▶│  FULFILLMENT_RISK_SVC   POST /predict-proba         │
│  test_inference.py                  │          │  (SPCS · Model Registry: FULFILLMENT_RISK_XGB V2)   │
│        │                            │          │                                                     │
│        └── score_client.py ─────────│──+ PAT──▶│  Cortex REST API  POST /api/v2/cortex/v1/           │
│                                     │          │                        chat/completions             │
└─────────────────────────────────────┘          └─────────────────────────────────────────────────────┘
```

---

## Isolation From the Main Demo

This add-on is **additive only**. The 6 dashboards, the `SNOWFLAKE.ML.CLASSIFICATION` model, the semantic view, and every existing table and view are unchanged.

| | Existing demo | This add-on |
|---|---|---|
| Schema | `ML_MODELS`, `SHARED`, retailer schemas | `ML_INFERENCE` (new) |
| Model | `ML_MODELS.FULFILLMENT_RISK_MODEL` (Cortex ML Classification) | `ML_INFERENCE.FULFILLMENT_RISK_XGB` (Model Registry, XGBoost) |
| Serving | SQL `!PREDICT` inside Streamlit in Snowflake | SPCS service `ML_INFERENCE.FULFILLMENT_RISK_SVC`, public HTTPS |
| Data access | Read/write | **Read-only** on `ML_MODELS.TRAINING_DATA` |
| Python env | Anaconda | `inference/.venv` (separate) |

The baseline was checked before and after the build: row counts, objects in `ML_MODELS`, the classification model's `!PREDICT`, and the 6 Streamlit apps were all identical.

**Rollback:** `99_teardown.sql` drops the service and the `ML_INFERENCE` schema, nothing else.

---

## Files

| File | Purpose |
|---|---|
| `inference_plan.md` | Design plan and decisions |
| `INFERENCE_SETUP.md` | Setup guide |
| `INFERENCE_DEMO_TALK_TRACK.md` | Presenter script |
| `.gitignore` | Keeps `.env` and `.venv/` out of git |
| `00_setup.sql` | Creates the `ML_INFERENCE` schema and prints baseline counts |
| `requirements.txt` | Pinned packages for `inference/.venv` |
| `snowpark_session.py` | Session helper (reads `~/.snowflake/connections.toml`). Used only for training and deploy |
| `01_train_register.py` | Trains XGBoost, logs `FULFILLMENT_RISK_XGB` to the Model Registry, writes `SAMPLE_REQUESTS` |
| `02_create_service.py` | Deploys the model with `mv.create_service(ingress_enabled=True)` |
| `score_client.py` | **Shared client**: `score()` for the inference endpoint and `explain()` for Cortex REST. Pure `requests` |
| `sample_requests.json` | 6 demo POs (3 low risk, 3 high risk), so the app needs no database access |
| `test_inference.py` | Command-line test of both REST APIs |
| `app_streamlit.py` | Local "SPS PO Risk Checker" app, written for business users: plain-language intro, order summary, input tooltips, risk bands with recommended actions, AI explanation, glossary, and a technical "behind the scenes" panel |
| `.env.example` | Config template. Copy it to `.env` (gitignored) |
| `99_teardown.sql` | Rollback |

---

## Quick Start

Full instructions: **[INFERENCE_SETUP.md](INFERENCE_SETUP.md)**

```bash
snow sql -f inference/00_setup.sql --connection coco_conn                      # isolated schema
/Users/vsuru/anaconda3/bin/python -m venv inference/.venv                      # separate env
inference/.venv/bin/pip install -r inference/requirements.txt
cd inference
SNOWFLAKE_CONNECTION_NAME=coco_conn .venv/bin/python 01_train_register.py      # Model Registry
SNOWFLAKE_CONNECTION_NAME=coco_conn .venv/bin/python 02_create_service.py      # SPCS endpoint (~7-10 min)
cp .env.example .env    # set INFERENCE_URL from SHOW ENDPOINTS IN SERVICE ...
.venv/bin/python test_inference.py                                             # verify both REST APIs
.venv/bin/streamlit run app_streamlit.py                                       # http://localhost:8501
```

---

## REST API Reference

### 1. Model inference endpoint

```
POST https://<ingress_url>/predict-proba
Authorization: Snowflake Token="<PAT>"
Content-Type: application/json
```

Request (`dataframe_split`; column order must match the model signature):

```json
{
  "dataframe_split": {
    "index": [0],
    "columns": ["RETAILER_ID","SUPPLIER_REGION","DESTINATION_REGION","DESTINATION_SIZE","LOCATION_TYPE",
                "IS_REPLACEMENT_850","PO_VERSION","TOTAL_UNITS","TOTAL_COST","LINE_COUNT","TOTAL_LINE_QTY",
                "DISTINCT_ITEMS","ORDER_DOW","ORDER_MONTH","SUPPLIER_AVG_LEAD","SUPPLIER_LEAD_VAR",
                "HIST_ON_TIME_RATE","HIST_IN_FULL_RATE","HIST_OTIF_RATE","HIST_AVG_DAYS_LATE","HIST_PO_COUNT",
                "DAYS_TO_SHIP","DAYS_TO_DELIVER"],
    "data": [["FL","…","…","…","STORE", 0, 1, 97, 5071.5, …, 11, 11]]
  }
}
```

Response:

```json
{ "data": [[0, {"output_feature_0": 0.0007, "output_feature_1": 0.9993}]] }
```

`output_feature_1` is the probability of a late or short delivery. Also available: `/predict` (returns a 0/1 class).

`curl` equivalent:

```bash
curl -X POST "$INFERENCE_URL/predict-proba" \
  -H "Authorization: Snowflake Token=\"$SNOWFLAKE_PAT\"" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

### 2. Cortex REST API

```
POST https://<account>.snowflakecomputing.com/api/v2/cortex/v1/chat/completions
Authorization: Bearer <PAT>
X-Snowflake-Authorization-Token-Type: PROGRAMMATIC_ACCESS_TOKEN
```

```json
{ "model": "claude-sonnet-4-5",
  "messages": [{"role": "user", "content": "Explain this PO risk score ..."}],
  "max_completion_tokens": 250 }
```

The account host uses hyphens (`sfsenorthamerica-demo-vsuru`), not underscores.

### Reusing the client in other apps

```python
from score_client import score, explain

result = score([po_dict])                     # list of PO dicts keyed by the column names above
risk = result["results"][0]["risk_probability"]
text = explain(po_dict, risk)["text"]
```

This could back a web form, a batch script, a webhook, or a supplier portal.

---

## About the Model

| | Dashboard model | Endpoint model |
|---|---|---|
| Object | `ML_MODELS.FULFILLMENT_RISK_MODEL` | `ML_INFERENCE.FULFILLMENT_RISK_XGB` V2 |
| Type | `SNOWFLAKE.ML.CLASSIFICATION` | XGBoost in an sklearn Pipeline (one-hot + XGBClassifier) |
| Inputs | 24 columns from `TRAINING_DATA` | Same, minus identifiers (`PO_ID`, `SUPPLIER_ID`): 23 inputs |
| Reported metrics | 91.3% accuracy (Cortex evaluation) | 88.4% accuracy, 89.8% precision, 41.1% recall, ROC AUC 0.77 (20% hold-out) |

**Use case framing:** the score is most useful once ship and transit timing are known (ASN/856 onward). Use it to flag deliveries likely to arrive late or short before the receiving dock finds out.

**Why not a pure pre-ship model?** Version **V1** was trained on pre-ship features only (no `DAYS_TO_SHIP` or `DAYS_TO_DELIVER`). It scored **ROC AUC 0.50**, no better than chance.
- In this dataset, late/short is driven almost entirely by actual delivery timing.
- Before shipment, every signal is flat: suppliers fail 16–21% of the time, and lead window and order size make no difference.
- V1 is kept in the registry for reference and is **not deployed**.

---

## Operations and Cost

| Task | Command |
|---|---|
| Status | `SELECT SYSTEM$GET_SERVICE_STATUS('SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC');` |
| Endpoint URL | `SHOW ENDPOINTS IN SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC;` |
| Pause after demo | `ALTER SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC SUSPEND;` |
| Resume before demo | `ALTER SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC RESUME;` (then wait for READY) |
| Logs | `CALL SYSTEM$GET_SERVICE_LOGS('SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC', 0, 'model-inference');` |
| Cortex usage | `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_REST_API_USAGE_HISTORY` |
| Remove everything | `snow sql -f inference/99_teardown.sql --connection coco_conn` |

- **Service:** one CPU_X64_S node on `SYSTEM_COMPUTE_POOL_CPU` bills while the service is running. Auto-suspend is set to **30 minutes**, and it auto-resumes on the next request (the first call after resume is slower).
- **Cortex REST:** billed per token, roughly a fraction of a cent per explanation.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `HTTP 404` from the endpoint | SPCS returns 404 for **auth and network** failures too. Check you're on VPN, the PAT is valid, and the URL is the `inference` ingress URL |
| `HTTP 401/403` from Cortex | The PAT's role needs `SNOWFLAKE.CORTEX_USER`. Check the token-type header |
| Slow first call | The service was auto-suspended. Warm it up with `test_inference.py` before presenting |
| `INFERENCE_URL` error | `.env` is missing. Copy `.env.example` and set the URL |
| Service `FAILED` | Check `SYSTEM$GET_SERVICE_LOGS`. Versions are pinned (`xgboost==3.2.0`, `scikit-learn==1.7.2`) to packages available in Snowflake |

---

## Demo Talk Track

See **[INFERENCE_DEMO_TALK_TRACK.md](INFERENCE_DEMO_TALK_TRACK.md)** for the presenter script, pre-demo checklist, and Q&A.
