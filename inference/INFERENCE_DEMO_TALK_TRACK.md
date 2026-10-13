# Inference Add-On: Demo Talk Track

**Using the fulfillment risk model from outside Snowflake.** This is a stand-alone segment that can follow the main demo (`../DEMO_TALK_TRACK.md`, unchanged) or run on its own.

> Setup: [INFERENCE_SETUP.md](INFERENCE_SETUP.md) · Overview and API reference: [INFERENCE_README.md](INFERENCE_README.md)

---

## Demo Information

| Field | Value |
|---|---|
| **Duration** | ~5 min (2-min short version below) |
| **What runs where** | Local Next.js web app on the presenter's laptop (`localhost:3000`). Model and LLM run in Snowflake |
| **Snowflake objects** | Model `SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_XGB` V2 · Service `ML_INFERENCE.FULFILLMENT_RISK_SVC` |
| **APIs shown** | Snowflake ML real-time inference REST API (`/predict-proba`) · Cortex REST API (`/api/v2/cortex/v1/chat/completions`, `claude-sonnet-4-5`) |
| **Audience** | Developers, architects, SPS product teams, partners building on SPS data |

---

## Key Terms

| Term | Definition |
|---|---|
| **Model Registry** | Snowflake's versioned store for ML models. Models logged here can be served from SQL or as REST endpoints |
| **Real-time inference endpoint** | A Model Registry model deployed on Snowpark Container Services with a public HTTPS URL. Snowflake manages the container, scaling, and auth |
| **Cortex REST API** | OpenAI/Anthropic-compatible HTTPS endpoints for LLMs running inside Snowflake |
| **PAT** | Programmatic Access Token. A Snowflake-issued token scoped to a user and role, sent in the `Authorization` header |
| **`dataframe_split`** | The JSON request format for the endpoint: `index`, `columns`, `data`, mirroring a pandas DataFrame |

---

## Pre-Demo Checklist (5 min before)

- [ ] On VPN (the account network policy applies)
- [ ] Resume and warm the service, so the first call isn't slow:
  ```sql
  ALTER SERVICE SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC RESUME;
  SELECT SYSTEM$GET_SERVICE_STATUS('SPS_RETAIL_AI.ML_INFERENCE.FULFILLMENT_RISK_SVC');  -- all READY
  ```
  ```bash
  cd inference && .venv/bin/python test_inference.py
  ```
- [ ] Start the app: `cd web && npm run dev` → open `http://localhost:3000` (fallback: `.venv/bin/streamlit run app_streamlit.py` → `http://localhost:8501`)
- [ ] In Snowsight, open **AI & ML → Models → FULFILLMENT_RISK_XGB** in a tab
- [ ] Terminal open in `inference/`, font enlarged

---

## Opening (30 s)

> "Everything you've seen so far runs inside Snowflake: the data, the models, the dashboards. But SPS and its partners also have their own apps: supplier portals, ops tools, alerting systems. Can those apps use the same intelligence without copying data out of Snowflake?"
>
> "Let's call the model from my laptop. Two HTTPS calls, one token, no Snowflake driver."

---

## Step 1: The Model in the Registry (45 s)

**Show:** Snowsight → AI & ML → Models → `FULFILLMENT_RISK_XGB`

> "This is a fulfillment risk model in the Snowflake Model Registry, trained on the same joined SPS + retailer features as the dashboards. It's versioned: V1 and V2. It has its evaluation metrics attached: 88% accuracy and 90% precision on held-out data."
>
> "V2 is deployed as a real-time inference service. Snowflake built the container, runs it on a managed compute pool, and gives it a public HTTPS endpoint. We didn't write a Dockerfile or manage a Kubernetes cluster."

**Point out:** the Inference Services tab shows `FULFILLMENT_RISK_SVC` as running.

---

## Step 2: It's Just HTTPS (1 min)

**Show:** terminal

```bash
.venv/bin/python test_inference.py
```

> "This script uses plain Python `requests`. First call: six purchase orders go to the model endpoint and come back scored in about a second. The three Bass Pro orders are around 1% risk. The three Foot Locker orders are 99.9%, and in history all three were in fact late or short."
>
> "Second call: the Cortex REST API. Same token, OpenAI-style chat endpoint, with Claude running inside Snowflake's perimeter. It explains the riskiest order in plain English."

**Point out:**
- The two URLs: `…snowflakecomputing.app/predict-proba` and `…snowflakecomputing.com/api/v2/cortex/v1/chat/completions`
- Latency is printed for each call

---

## Step 3: An App Outside Snowflake (2–3 min)

**Show:** `http://localhost:3000` (SPS PO Risk Checker)

> "This app is running on my laptop, not in Snowflake. It's a standard React web app, the kind a product team would build for a supplier portal. It's written for a business user: the top explains the problem and the three steps, every input has a hover tip, and the results are color-coded and say what to do."

1. **Low risk.** Click the **Bass Pro Shops · PO_007447** card (green dot, "Arrived OTIF"). Read the summary tiles aloud (units, value, supplier history, usual lead time) and the green "what actually happened" banner, then click **Score this order**.
   > "The gauge settles at 1%. Green Low Risk badge, and a down arrow: 17 points below a typical order. No action needed, and the model got it right. Cortex says why: this supplier has a strong history with this retailer and the shipment is moving well ahead of schedule."
2. **High risk.** Click the **Foot Locker · PO_008398** card (red dot) and score it.
   > "Now the gauge swings to 100%. Red High Risk badge, up arrow, 82 points above typical, act now. The explanation points to the delivery window running short of the supplier's typical lead time, and suggests a concrete action: expedite or renegotiate the date. In history, this order was in fact late."
3. **What-if.** On the high-risk order, lower **Days in transit** from 11 to 3 and score again.
   > "Change one input and the indicator shows 100% → 23%, with a down arrow. It drops from High to Watch, amber. The app flags that we're in what-if mode and offers a Reset. This is what a supplier portal or a receiving-dock tool would do in real time."
4. **How to read it.** Open **How to read the score**.
   > "Plain-language bands, the typical-order baseline, and how often the model is right, so a business user knows how much to trust it."
5. **Behind the scenes.** Open **Behind the scenes (technical)**.
   > "For the technical audience: the flow is laptop, HTTPS with a token, the ML endpoint, and Cortex. Here's exactly what was sent, a small JSON payload of order details, and what came back, two probabilities, with response times. The token stays on the app's server. The browser never sees it."

---

## Step 4: Governed and Secure (30 s)

> "This is still governed by Snowflake:"
> - "**Auth:** a Programmatic Access Token tied to a user and role. Revoke it and the app stops working."
> - "**Network:** the account's network policy applies, so these endpoints only answer from approved networks."
> - "**Authorization:** only the service owner role can call the endpoint unless we explicitly grant it."
> - "**Data:** the training data never left Snowflake. The model and LLM run inside the Snowflake perimeter."

---

## Closing (30 s)

> "Same SPS + retailer data, same Snowflake governance, but now any application can use the model with an HTTPS call. That's how SPS insight gets into the tools where suppliers and retailers actually work."

---

## Short Version (2 min)

1. Run `test_inference.py` (45 s): "two HTTPS calls, a score and an explanation."
2. In the app, score the high-risk order, change days in transit to 3 and re-score (watch the 100% → 23% arrow), then open "Behind the scenes" (60 s).
3. One governance sentence (15 s).

---

## Presenter Notes and Likely Questions

**"Why a different model from the dashboards?"**
The dashboards use `SNOWFLAKE.ML.CLASSIFICATION`, which is great for SQL inside Snowflake. To get a dedicated REST endpoint, a model has to be in the Model Registry. So we trained the same features into an XGBoost model and registered it. Results are comparable: 88% hold-out accuracy here, versus 91% from the Cortex evaluation for the dashboard model.

**"Can it predict before the order ships?"**
Not with this dataset. We tried that first (V1, pre-ship features only), and it scored ROC AUC 0.50, which is chance. Late/short here is driven by actual delivery timing. So the endpoint is positioned for the ASN-onward window: once ship and transit timing are known, it flags deliveries likely to arrive late or short before the receiving dock finds out. With richer upstream signals in production data, the same pipeline would support pre-ship scoring.

**"How fast is it?"**
About a second for a batch of 6 on a warm CPU service. The first call after auto-suspend takes longer, which is why we warm it up. The Cortex explanation takes a few seconds because it's generating text.

**"What does it cost?"**
- **Endpoint:** one small CPU node while the service runs. It auto-suspends after 15 minutes idle and resumes on demand.
- **Cortex:** billed per token, a fraction of a cent per explanation.

**"Could this be a web or mobile app?"**
It already is: the demo app is a standard Next.js web app. Its server routes (`web/lib/server/snowflake.ts`, a TypeScript port of `score_client.py`) make the same HTTPS calls, and the PAT stays on the server, never in browser JavaScript. Any backend (Python, Node, Java, .NET) can do the same. For production you'd host it anywhere, or inside Snowflake on SPCS, and use OAuth instead of a personal token.

**"Can we log the predictions?"**
Yes. Recreating the service with Auto-Capture enabled logs every request and response to an inference table, for monitoring, drift checks, and retraining. It's off in this demo.

**If something fails live:**
- **HTTP 404:** usually VPN/network or the token. SPCS returns 404 for auth failures.
- **Slow or timeout:** the service was suspended. Resume it and wait for READY.
- **Fallback:** show the pre-recorded `test_inference.py` output in [INFERENCE_SETUP.md](INFERENCE_SETUP.md#step-6-verify-both-rest-apis).
