# Inference Add-On Plan: Calling the Model from Outside Snowflake

**Status:** Built and verified. See [INFERENCE_README.md](INFERENCE_README.md) for instructions.

> **Changes from this plan during the build:**
> - **Features (decision 2):** a pre-ship-only model (V1) scored ROC AUC 0.50. In this dataset late/short is driven by actual delivery timing, so V2 uses the same inputs as the dashboard model. V1 is kept in the registry and not deployed.
> - **Client (decision 3):** Python `requests` via a shared `score_client.py` (used by `test_inference.py` and the Streamlit app) instead of a curl script. A curl example is in the README.
> - **Sample POs** ship as `sample_requests.json`, so the external app needs no database access.

**Goal:** A short, simple demo where an app running *outside* Snowflake sends a purchase order and gets back:
1. a fulfillment risk score, from a **Snowflake ML real-time inference REST endpoint**, and
2. a plain-English explanation of that score, from the **Cortex REST API**.

Both use official Snowflake REST APIs. There are no UDF or stored-procedure workarounds.

---

## 0. Guiding Criteria

| # | Criterion | How the plan meets it |
|---|---|---|
| 1 | **Use the official APIs** | [Real-time inference REST API](https://docs.snowflake.com/en/developer-guide/snowflake-ml/inference/real-time-inference-rest-api) for the model, and the [Cortex REST API](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-rest-api) for the explanation |
| 2 | **Keep it simple** | A `curl` example and one local Streamlit file. No React, no backend server |
| 3 | **Don't break the existing demo** | Everything new is **additive and isolated** in a new schema. The current model, tables, views, and 6 dashboards are **read-only** to this work (see section 2) |

---

## 1. Environment Check Results

| Check | Result |
|---|---|
| Existing model | `ML_MODELS.FULFILLMENT_RISK_MODEL` (`SNOWFLAKE.ML.CLASSIFICATION`). It can't be served by the real-time inference API because that API only accepts **Model Registry** models. **It stays untouched** |
| Model Registry | Empty in `SPS_RETAIL_AI`. The role owns the database, so `CREATE MODEL` works |
| `BIND SERVICE ENDPOINT` | Granted to `CORTEXCODECLIROLE` (needed for a public HTTPS endpoint) |
| `SNOWFLAKE.CORTEX_USER` | Granted (needed for the Cortex REST API) |
| Compute pool | `SYSTEM_COMPUTE_POOL_CPU` (CPU_X64_S, ACTIVE, 1 other service already running) |
| PAT | 2 active PATs (role-restricted to `CORTEXCODECLIROLE`) |
| Network policy | `ACCOUNT_VPN_POLICY_SE` at the account level. The demo machine must be on VPN |
| Local Python | Anaconda 3.10.9 has Streamlit and the connector, but **not** `snowflake-ml-python` or `xgboost`. We'll use a **separate venv** so the Anaconda env isn't changed |

---

## 2. How We Avoid Breaking the Existing Demo

### What we will NOT touch

| Existing object | Used by | Status |
|---|---|---|
| `ML_MODELS.FULFILLMENT_RISK_MODEL` | Dashboards 1–6 | No changes |
| `ML_MODELS.FULFILLMENT_PREDICTIONS`, `FULFILLMENT_FEATURES`, `TRAINING_DATA` | Dashboards, semantic view | **Read-only** (`TRAINING_DATA` is only SELECTed to train the new model) |
| `ML_MODELS.OTIF_FORECAST_MODEL`, `PERFORMANCE_ANOMALY_MODEL`, and their views | Dashboard 6 | No changes |
| All `SHARED.*`, `FOOT_LOCKER.*`, `BASS_PRO.*`, `URBAN_OUTFITTERS.*` tables and views | Dashboards | No changes |
| `PUBLIC.SPS_FULFILLMENT_INTELLIGENCE` semantic view | Cortex Analyst | No changes |
| 6 Streamlit apps and `STREAMLIT_STAGE` | Demo | No changes |
| `apps/`, `setup/`, `cowork/` folders in the repo | Replication | No changes |
| Anaconda Python env | Local tooling | No changes (we use a separate `inference/.venv`) |

### What we WILL create, all new and isolated

| New object | Purpose |
|---|---|
| Schema `SPS_RETAIL_AI.ML_INFERENCE` | Holds everything below, so nothing mixes with `ML_MODELS` |
| Model `ML_INFERENCE.FULFILLMENT_RISK_XGB` (version `V1`) | XGBoost model in the Model Registry |
| Table `ML_INFERENCE.SAMPLE_REQUESTS` | A few ready-made POs for the demo form (copied from `TRAINING_DATA`) |
| Service `ML_INFERENCE.FULFILLMENT_RISK_SVC` | Real-time inference service on `SYSTEM_COMPUTE_POOL_CPU`, ingress enabled |
| Repo folder `inference/` | All new code and docs |

### Safety checks

- **Before building:** take a baseline by recording row counts of `FULFILLMENT_PREDICTIONS`, `TRAINING_DATA`, and the `SHOW STREAMLITS` list.
- **After building:** re-run the baseline. Counts must match, all 6 dashboards must still open, and the classification model must still `!PREDICT`.
- **Rollback is two statements and leaves the demo exactly as it was today:**
  ```sql
  DROP SERVICE IF EXISTS SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC;
  DROP SCHEMA  IF EXISTS SPS_RETAIL_AI.ML_INFERENCE CASCADE;
  ```

---

## 3. Architecture

```
                       ┌──────────────────────── Snowflake ───────────────────────┐
                       │                                                           │
 Local Streamlit app ──┼──HTTPS + PAT──▶ FULFILLMENT_RISK_SVC  /predict-proba       │
 (localhost:8501)      │                 (SPCS, Model Registry: FULFILLMENT_RISK_XGB)│
   or curl             │                                                           │
                       │                                                           │
                  ─────┼──HTTPS + PAT──▶ Cortex REST API                           │
                       │                 /api/v2/cortex/v1/chat/completions          │
                       │                 "Explain this risk score for an ops lead"   │
                       └───────────────────────────────────────────────────────────┘
```

The existing classification model and dashboards are not part of this flow.

---

## 4. The New Model (FULFILLMENT_RISK_XGB)

- **Source:** `ML_MODELS.TRAINING_DATA`, the same 9,919 POs (read-only).
- **Algorithm:** XGBoost classifier, trained locally with `snowflake-ml-python` in a venv, then logged to the Model Registry.
- **Features:** pre-ship signals only. Dropping the post-shipment columns makes this an honest "predict before it ships" model:

| Kept (known at order time) | Dropped |
|---|---|
| RETAILER_ID, SUPPLIER_REGION, DESTINATION_REGION, DESTINATION_SIZE, LOCATION_TYPE, IS_REPLACEMENT_850, PO_VERSION, TOTAL_UNITS, TOTAL_COST, LINE_COUNT, TOTAL_LINE_QTY, DISTINCT_ITEMS, ORDER_DOW, ORDER_MONTH, SUPPLIER_AVG_LEAD, SUPPLIER_LEAD_VAR, HIST_ON_TIME_RATE, HIST_IN_FULL_RATE, HIST_OTIF_RATE, HIST_AVG_DAYS_LATE, HIST_PO_COUNT | `DAYS_TO_DELIVER`, `DAYS_TO_SHIP` (only known after shipment), `PO_ID`, `SUPPLIER_ID` (identifiers) |

- **Outputs:** `predict` (0/1) and `predict_proba` (probability of late or short).
- **Expected accuracy:** likely **lower** than the classification model's 91.3%, because the leaky features are gone. That's the honest number, and I'll report both side by side. Talk-track line: *"The dashboard model explains what happened. The endpoint model predicts before it ships."*

---

## 5. Client Options

| Option | What it shows | Recommendation |
|---|---|---|
| **`test_inference.sh` (curl)** | A raw REST call, so the audience sees there's no SDK and no Snowflake driver | **Yes**, as the opener |
| **`app_streamlit.py` (local Streamlit)** | A simple "PO Risk Checker" form with a risk gauge and an AI explanation | **Yes**, as the main demo |
| Basic HTML page | Same story, but the PAT can't live in browser JS, so it needs a proxy server | Skip (adds a server, not more story) |
| React app | Same as HTML with more setup | Skip |

### Local Streamlit app (single file, ~120 lines)

```
┌─────────────────────────────────────────────────────────┐
│  SPS PO Risk Checker   (running outside Snowflake)      │
├─────────────────────────────────────────────────────────┤
│  Sample PO: [ FL – Large order – Low-reliability ▼ ]    │
│  Retailer [FL▼]  Units [ 2,400 ]  Cost [$48,000]        │
│  Supplier hist. OTIF [0.72]  Avg lead days [ 18 ]       │
│                                    [ Score this PO ]    │
├─────────────────────────────────────────────────────────┤
│  Risk of late/short:  78%   HIGH RISK                   │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░                                   │
│                                                         │
│  AI explanation (Cortex REST API):                      │
│  "This order is high risk mainly because the supplier's │
│   historical OTIF is 72% and the order is 3x the usual  │
│   size. Consider splitting the shipment or …"           │
│                                                         │
│  ▸ Raw request / response JSON   (expander)             │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Folder Layout (all new)

```
inference/
├── inference_plan.md            ← this file
├── README.md                    ← how to run the demo
├── .env.example                 ← SNOWFLAKE_PAT, INFERENCE_URL, CORTEX_URL
├── requirements.txt             ← snowflake-ml-python, xgboost, streamlit, requests
├── 00_setup.sql                 ← CREATE SCHEMA ML_INFERENCE, sample table, baseline checks
├── 01_train_register.py         ← train XGBoost and log to Model Registry
├── 02_create_service.py         ← mv.create_service(ingress_enabled=True), run in background
├── test_inference.sh            ← curl /predict-proba and Cortex chat/completions
├── app_streamlit.py             ← local PO Risk Checker
└── 99_teardown.sql              ← rollback (drop service + schema)
```

`.gitignore` additions: `inference/.venv/` and `inference/.env`.

---

## 7. Security

- The PAT lives in `inference/.env`, which is gitignored. It never goes in the repo or the browser.
- Model endpoint auth: `Authorization: Snowflake Token="<PAT>"`. Cortex REST auth: `Authorization: Bearer <PAT>`. Both will be verified with `curl` during the build.
- The endpoint is only usable by the service owner role unless we explicitly `GRANT SERVICE ROLE ... ALL_ENDPOINTS_USAGE`. We won't grant it to any other role.
- The account network policy stays as is, so only VPN/allowed IPs can reach either endpoint.
- *Optional:* a dedicated least-privilege role and PAT. This may need `SECURITYADMIN`. Otherwise we use the existing `CORTEXCODECLIROLE` PAT and note that for the audience.

---

## 8. Cost

| Item | Cost driver | Control |
|---|---|---|
| Training | Warehouse `COCOWH` for data pull plus local training | One-time, a few minutes |
| Inference service | 1 CPU_X64_S node while the service runs | Set auto-suspend (15 min, the minimum for public endpoints). `ALTER SERVICE ... SUSPEND` after the demo |
| Cortex REST | Tokens per explanation (`claude-sonnet-4-5` or `mistral-large2`) | Pennies per call. Visible in `CORTEX_REST_API_USAGE_HISTORY` |

---

## 9. Demo Flow (~5 min)

1. **"Two models, two jobs."** The dashboard model explains history. A new Model Registry model is deployed as a live REST endpoint for pre-ship scoring. Show it in Snowsight under Model Registry → Inference Services (45 s).
2. **"It's just HTTPS."** Run `test_inference.sh` and show the JSON from `/predict-proba` and from the Cortex REST API (1 min).
3. **"An app outside Snowflake."** Open `localhost:8501` (2–3 min):
   - Pick a safe PO and score it to get LOW risk.
   - Switch to a large order from a low-reliability supplier and score it to get HIGH risk, plus an AI explanation.
   - Expand the raw JSON to show exactly what went over the wire.
4. **"Governed."** PAT auth, network policy, owner-only endpoint, no data stored outside Snowflake (30 s).

---

## 10. Build Steps (once approved)

1. **Baseline:** record existing object counts and the dashboard list (read-only).
2. `00_setup.sql`: create the `ML_INFERENCE` schema and the `SAMPLE_REQUESTS` table.
3. Create `inference/.venv` and install `requirements.txt` (Anaconda untouched).
4. `01_train_register.py`: train XGBoost, print accuracy/precision/recall, log `FULFILLMENT_RISK_XGB` V1.
5. `02_create_service.py`: deploy to `SYSTEM_COMPUTE_POOL_CPU` in the background (~10 min) and monitor until RUNNING.
6. `test_inference.sh`: verify both REST calls end to end with the PAT.
7. `app_streamlit.py`: run locally and verify both the LOW and HIGH sample POs.
8. **Re-run the baseline:** confirm the existing demo is unchanged and open all 6 dashboards.
9. Docs: `inference/README.md`, a short "Inference Add-On" section in the main README and DEMO_TALK_TRACK (additive only). Commit and push.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| The new model's accuracy is lower than 91.3% | Expected and explainable (no leaky features). Show both numbers |
| Service build fails (package and image issues) | Use the debug-inference workflow. The rollback leaves the demo intact |
| First call after auto-suspend is slow | Warm up the service (one `curl`) before presenting |
| Shared `SYSTEM_COMPUTE_POOL_CPU` already runs 1 other service | Our service requests modest CPU/memory. If contention appears, create a small dedicated pool instead |
| Cortex model availability in region | Fall back to another model listed in the Cortex REST API docs |

---

## 12. Decisions Needed from You

1. **Approve the approach:** XGBoost in the Model Registry, an SPCS real-time endpoint, and the Cortex REST API, all isolated in `ML_INFERENCE`.
2. **Features:** drop the post-shipment features (recommended), or keep them to match the dashboard model's accuracy?
3. **Clients:** curl plus local Streamlit (recommended)? Anything else?
4. **Auth:** reuse the existing PAT, or try to create a dedicated role and PAT?
5. **Cortex model for explanations:** `claude-sonnet-4-5` (recommended) or `mistral-large2`?
