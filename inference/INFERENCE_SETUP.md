# Inference Add-On: Setup Guide

Step-by-step setup for the inference add-on. It is fully separate from the main demo setup (`../SETUP.md`), which stays unchanged. Everything here creates objects only in `SPS_RETAIL_AI.ML_INFERENCE`.

> Overview and API reference: [INFERENCE_README.md](INFERENCE_README.md) · Presenter script: [INFERENCE_DEMO_TALK_TRACK.md](INFERENCE_DEMO_TALK_TRACK.md)

---

## Prerequisites

| Requirement | Check | Notes |
|---|---|---|
| Main demo already set up | `SELECT COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.TRAINING_DATA;` returns 9,919 | Training data is read-only input |
| `BIND SERVICE ENDPOINT` | `SHOW GRANTS TO ROLE CORTEXCODECLIROLE;` | Needed for a public HTTPS endpoint |
| `SNOWFLAKE.CORTEX_USER` | same | Needed for the Cortex REST API |
| CPU compute pool | `SHOW COMPUTE POOLS;` lists `SYSTEM_COMPUTE_POOL_CPU` | |
| PAT | `SHOW USER PROGRAMMATIC ACCESS TOKENS FOR USER CORTEXCODEUSER;` | The demo reuses the PAT in the `coco_conn` connection |
| Network | On VPN / allowed IP | The account network policy `ACCOUNT_VPN_POLICY_SE` applies to both REST APIs |
| Python 3.10 | `/Users/vsuru/anaconda3/bin/python --version` | Used only to create a separate venv |
| Snowflake CLI | `snow --version` | For running the SQL files |
| Node.js 20+ | `node --version` | For the web app in `web/` (optional if you use the Streamlit alternative) |

All commands below are run from the **project root** unless noted.

---

## Step 1: Create the Isolated Schema

```bash
snow sql -f inference/00_setup.sql --connection coco_conn
```

This creates `SPS_RETAIL_AI.ML_INFERENCE` and prints **baseline row counts**. Save them; you'll compare against them in Step 7.

Expected baseline: TRAINING_DATA 9,919 · FULFILLMENT_PREDICTIONS 9,919 · FULFILLMENT_FEATURES 9,919 · PURCHASE_ORDER 10,476 · SHIPMENT 9,919.

---

## Step 2: Create the Python Environment

A dedicated venv keeps Anaconda untouched.

```bash
/Users/vsuru/anaconda3/bin/python -m venv inference/.venv
inference/.venv/bin/pip install --upgrade pip
inference/.venv/bin/pip install -r inference/requirements.txt
```

`xgboost==3.2.0` and `scikit-learn==1.7.2` are pinned to versions in the Snowflake package channel, so the model image builds cleanly.

Test the connection:

```bash
cd inference
SNOWFLAKE_CONNECTION_NAME=coco_conn .venv/bin/python snowpark_session.py --test
```

---

## Step 3: Train and Register the Model (~1 min)

```bash
SNOWFLAKE_CONNECTION_NAME=coco_conn .venv/bin/python 01_train_register.py
```

What it does:
1. Reads `ML_MODELS.TRAINING_DATA` (read-only).
2. Trains an sklearn Pipeline (one-hot encoding + XGBoost) on 80% and evaluates on the 20% hold-out.
3. Logs `ML_INFERENCE.FULFILLMENT_RISK_XGB` version `V2` to the Model Registry, with metrics.
4. Writes `ML_INFERENCE.SAMPLE_REQUESTS`: the 3 clearest low-risk and 3 clearest high-risk hold-out POs.

Expected output:

```
Hold-out metrics (20% test set): {'accuracy': 0.8836, 'precision': 0.8976, 'recall': 0.4105, 'roc_auc': 0.7667}
Registered SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_XGB version V2
  function: PREDICT
  function: PREDICT_PROBA
```

The script refuses to overwrite an existing version. Bump `VERSION` in the script to create a new one.

Then export the demo samples to JSON, so the external app needs no database access:

```bash
SNOWFLAKE_CONNECTION_NAME=coco_conn .venv/bin/python -c "
import json; from snowpark_session import create_snowpark_session
df = create_snowpark_session().sql('SELECT * FROM SPS_RETAIL_AI.ML_INFERENCE.SAMPLE_REQUESTS ORDER BY EXPECTED_RISK_PROB').to_pandas()
open('sample_requests.json','w').write(json.dumps(json.loads(df.to_json(orient='records')), indent=2))"
```

(`sample_requests.json` is already committed. Re-run this only if you retrain.)

---

## Step 4: Deploy the Real-Time Inference Service (~7–10 min)

```bash
SNOWFLAKE_CONNECTION_NAME=coco_conn .venv/bin/python 02_create_service.py
```

This calls `mv.create_service(service_name="FULFILLMENT_RISK_SVC", service_compute_pool="SYSTEM_COMPUTE_POOL_CPU", ingress_enabled=True, max_instances=1)`.

Monitor in another terminal or in Snowsight:

```sql
SHOW SERVICES IN SCHEMA SPS_RETAIL_AI.ML_INFERENCE;     -- a MODEL_BUILD_* job runs first, then FULFILLMENT_RISK_SVC
SELECT SYSTEM$GET_SERVICE_STATUS('SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC');  -- wait for all "READY"
```

Set auto-suspend to control cost:

```sql
ALTER SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC SET AUTO_SUSPEND_SECS = 900;
```

900 s (15 min) is the minimum Snowflake allows for a service with a public endpoint.

---

## Step 5: Configure the Client

Get the public endpoint:

```sql
SHOW ENDPOINTS IN SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC;
-- copy ingress_url of the "inference" endpoint (port 5000)
```

```bash
cp .env.example .env
```

Edit `inference/.env`:

```
INFERENCE_URL=https://<ingress_url>
SNOWFLAKE_CONNECTION_NAME=coco_conn
```

**PAT:** if `SNOWFLAKE_PAT` is not set in `.env`, the client reads the `token` of `coco_conn` from `~/.snowflake/connections.toml`. `.env` is gitignored by `inference/.gitignore`, so the token is never committed.

**Cortex URL:** derived automatically from the connection's account (`https://sfsenorthamerica-demo-vsuru.snowflakecomputing.com`). Override it with `CORTEX_BASE_URL` if needed.

---

## Step 6: Verify Both REST APIs

```bash
.venv/bin/python test_inference.py          # --raw to print full JSON
```

Pass criteria:
- 6 rows scored. The low-risk samples come back around 1–2% and the high-risk samples around 99.9%, matching `EXPECTED_RISK_PROB`.
- A Cortex explanation is printed for the highest-risk PO.

Verified output (also a fallback to show if a live call fails):

```
1) Snowflake ML real-time inference endpoint  (/predict-proba)
   https://n6a4a2jo-sfsenorthamerica-demo-vsuru.snowflakecomputing.app/predict-proba  ->  1160 ms for 6 rows
   PO_007447  Low risk   actual=Delivered OTIF  risk=1.2%
   PO_006430  Low risk   actual=Delivered OTIF  risk=1.3%
   PO_002260  Low risk   actual=Delivered OTIF  risk=2.4%
   PO_009932  High risk  actual=Late/short      risk=99.9%
   PO_005406  High risk  actual=Late/short      risk=99.9%
   PO_008398  High risk  actual=Late/short      risk=99.9%

2) Cortex REST API  (chat/completions, claude-sonnet-4-5)
   https://sfsenorthamerica-demo-vsuru.snowflakecomputing.com/api/v2/cortex/v1/chat/completions  ->  5965 ms
   PO_008398: The 100% risk score is driven by the 11-day delivery window falling short of the supplier's
   typical 13.4-day lead time ... Immediately contact the supplier to expedite production and shipping, or
   negotiate a revised delivery date ...
```

Then run the web app (Node.js 20+):

```bash
cd web
npm install          # first time only
npm run dev          # http://localhost:3000
```

No extra configuration is needed: the app's server routes read `inference/.env` and the `coco_conn` connection, the same as the Python client. The page loads the 6 sample orders live from `ML_INFERENCE.SAMPLE_REQUESTS` (SQL REST API).

Score one low-risk and one high-risk sample. You should see:
- the order summary tiles and a green or red "what actually happened" banner;
- the risk gauge and a colored Low/Watch/High badge;
- an up or down arrow showing the points above or below a typical order (18%);
- the recommended action and "The model got it right";
- the AI explanation (step 3);
- the request and response under "Behind the scenes."

For a what-if check, set **Days in transit** to 3 on the high-risk Foot Locker sample (PO_008398) and score again. The gauge should drop to about 23% (Watch), with a `100% → 23% ↘` indicator.

Verified (headless Chrome, no console errors): PO_008398 100% High · what-if 23% Watch · PO_007447 1% Low · AI toggle off skips the Cortex call · `npm run build` passes.

Alternative without Node: `.venv/bin/streamlit run app_streamlit.py` (http://localhost:8501) shows the same flow in Streamlit.

---

## Step 7: Confirm the Main Demo Is Unchanged

```sql
SELECT
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.TRAINING_DATA)           AS TRAINING_DATA,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS) AS FULFILLMENT_PREDICTIONS,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_FEATURES)    AS FULFILLMENT_FEATURES,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER)             AS PURCHASE_ORDER,
  (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.SHIPMENT)                   AS SHIPMENT;

SHOW OBJECTS IN SCHEMA SPS_RETAIL_AI.ML_MODELS;       -- no new objects
SHOW STREAMLITS IN DATABASE SPS_RETAIL_AI;             -- same 6 apps, original created_on dates
```

The counts must match Step 1. Open any dashboard to confirm it loads.

---

## Teardown

```bash
snow sql -f inference/99_teardown.sql --connection coco_conn
```

This drops `FULFILLMENT_RISK_SVC` and the `ML_INFERENCE` schema (model + sample table). Nothing outside `ML_INFERENCE` is touched.

To keep everything but stop billing, suspend instead:

```sql
ALTER SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC SUSPEND;
```

---

## Setup Checklist

- [ ] `ML_INFERENCE` schema created, baseline counts saved
- [ ] `inference/.venv` created with pinned packages
- [ ] `FULFILLMENT_RISK_XGB` V2 registered (PREDICT, PREDICT_PROBA)
- [ ] `FULFILLMENT_RISK_SVC` all containers READY, auto-suspend 15 min
- [ ] `inference/.env` has `INFERENCE_URL`
- [ ] `test_inference.py` passes (scores + Cortex explanation)
- [ ] Web app (`web/`, localhost:3000) loads samples and scores low and high orders
- [ ] Main demo counts unchanged
