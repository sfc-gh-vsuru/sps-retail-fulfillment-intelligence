# Inference Add-On: Demo Talk Track

**Using the fulfillment risk model from outside Snowflake.** This is a stand-alone segment that can follow the main demo (`../DEMO_TALK_TRACK.md`, unchanged) or run on its own.

> Setup: [INFERENCE_SETUP.md](INFERENCE_SETUP.md) · Overview and API reference: [INFERENCE_README.md](INFERENCE_README.md)

---

## Demo Information

| Field | Value |
|---|---|
| **Duration** | ~5 min (2-min short version below) |
| **What runs where** | Local Streamlit app on the presenter's laptop (`localhost:8501`). Model and LLM run in Snowflake |
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
- [ ] Start the app: `.venv/bin/streamlit run app_streamlit.py` → open `http://localhost:8501`
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

**Show:** `http://localhost:8501` (SPS PO Risk Checker)

> "This app is running on my laptop, not in Snowflake. It's one Python file. It's written for a business user: the top explains the problem and the three steps, every input has a hover tip, and the results say what to do."

1. **Low risk.** Select `Bass Pro Shops · PO_007447 · low risk example`. Read the order summary card aloud (units, value, supplier history, what actually happened), then click **Score this order**.
   > "1% chance of arriving late or short, 17 points below a typical order. Green, no action needed. Cortex says why: this supplier has a strong history with this retailer and the shipment is moving well ahead of schedule."
2. **High risk.** Select `Foot Locker · PO_008398 · high risk example` and click **Score this order**.
   > "Near 100%, red, act now. The explanation points to the delivery window running short of the supplier's typical lead time, and suggests a concrete action: expedite or renegotiate the date. In history, this order was in fact late."
3. **What-if.** On the high-risk order, lower **Days in transit** from 11 to 3 and re-score.
   > "Change one input and the score drops from 100% to about 23%, from High to Watch. The app flags that we're now in what-if mode. This is what a supplier portal or a receiving-dock tool would do in real time."
4. **How to read it.** Open **How to read the score**.
   > "Plain-language bands, the typical-order baseline, and how often the model is right, so a business user knows how much to trust it."
5. **Behind the scenes.** Open **Behind the scenes (technical)**.
   > "For the technical audience: exactly what was sent, a small JSON payload of order details, and what came back, two probabilities. Response times are shown. The app never touched a table. It only sees the score."

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
2. In the app, score the high-risk order, change days in transit to 3 and re-score, then open "Behind the scenes" (60 s).
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
- **Endpoint:** one small CPU node while the service runs. It auto-suspends after 30 minutes idle and resumes on demand.
- **Cortex:** billed per token, a fraction of a cent per explanation.

**"Could this be a web or mobile app?"**
Yes. `score_client.py` is ~150 lines of `requests`. Any backend (Python, Node, Java, .NET) can make the same two calls. Keep the PAT on the server side, not in browser JavaScript.

**"Can we log the predictions?"**
Yes. Recreating the service with Auto-Capture enabled logs every request and response to an inference table, for monitoring, drift checks, and retraining. It's off in this demo.

**If something fails live:**
- **HTTP 404:** usually VPN/network or the token. SPCS returns 404 for auth failures.
- **Slow or timeout:** the service was suspended. Resume it and wait for READY.
- **Fallback:** show the pre-recorded `test_inference.py` output in [INFERENCE_SETUP.md](INFERENCE_SETUP.md#step-6-verify-both-rest-apis).
