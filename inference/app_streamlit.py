"""
SPS PO Risk Checker — a local Streamlit app running OUTSIDE Snowflake.

Calls two Snowflake REST APIs over HTTPS with a PAT (see score_client.py):
  1. Snowflake ML real-time inference endpoint -> fulfillment risk probability
  2. Cortex REST API (claude-sonnet-4-5)        -> plain-English explanation

Run:
    inference/.venv/bin/streamlit run inference/app_streamlit.py
"""

import json

import streamlit as st

from score_client import CORTEX_MODEL, explain, load_samples, score

st.set_page_config(page_title="SPS PO Risk Checker", layout="centered")

st.title("SPS PO Risk Checker")
st.caption(
    "Running locally, outside Snowflake. Scores come from a Snowflake ML real-time inference endpoint; "
    f"explanations come from the Cortex REST API ({CORTEX_MODEL})."
)

samples = load_samples()
labels = [f"{s['PO_ID']} · {s['SAMPLE_LABEL']} · retailer {s['RETAILER_ID']}" for s in samples]
choice = st.selectbox("Start from a sample purchase order", labels)
base = dict(samples[labels.index(choice)])

st.subheader("Purchase order")
c1, c2, c3 = st.columns(3)
with c1:
    retailers = ["FL", "BP", "UO"]
    base["RETAILER_ID"] = st.selectbox("Retailer", retailers, index=retailers.index(base["RETAILER_ID"]))
    base["TOTAL_UNITS"] = st.number_input("Total units", min_value=1, value=int(base["TOTAL_UNITS"]), step=10)
with c2:
    base["TOTAL_COST"] = st.number_input("Total cost ($)", min_value=0.0, value=float(base["TOTAL_COST"]), step=100.0)
    base["DAYS_TO_SHIP"] = st.number_input("Days to ship", min_value=0, value=int(base["DAYS_TO_SHIP"]))
with c3:
    base["DAYS_TO_DELIVER"] = st.number_input("Days in transit", min_value=0, value=int(base["DAYS_TO_DELIVER"]))
    base["HIST_OTIF_RATE"] = st.slider("Supplier historical OTIF", 0.0, 1.0, float(base["HIST_OTIF_RATE"]), 0.01)

with st.expander("All model inputs"):
    st.json({k: v for k, v in base.items() if k not in ("SAMPLE_LABEL", "ACTUAL_OUTCOME", "EXPECTED_RISK_PROB")})

explain_too = st.toggle("Explain the score with Cortex AI", value=True)

if st.button("Score this PO", type="primary", use_container_width=True):
    try:
        with st.spinner("Calling inference endpoint..."):
            result = score([base])
        risk = result["results"][0]["risk_probability"]
    except Exception as e:
        st.error(str(e))
        st.stop()

    level, color = ("HIGH RISK", "red") if risk >= 0.5 else (("WATCH", "orange") if risk >= 0.2 else ("LOW RISK", "green"))
    st.subheader("Result")
    m1, m2 = st.columns(2)
    m1.metric("Risk of late or short delivery", f"{risk:.0%}")
    m2.markdown(f"### :{color}[{level}]")
    st.progress(min(max(risk, 0.0), 1.0))
    st.caption(f"Inference endpoint responded in {result['latency_ms']} ms · historical outcome: {base['ACTUAL_OUTCOME']}")

    if explain_too:
        try:
            with st.spinner("Asking Cortex AI..."):
                exp = explain(base, risk)
            st.markdown("**Why (Cortex AI):**")
            st.info(exp["text"])
            st.caption(f"Cortex REST API responded in {exp['latency_ms']} ms")
        except Exception as e:
            st.warning(f"Explanation unavailable: {e}")

    with st.expander("What went over the wire"):
        st.markdown(f"**POST** `{result['url']}`")
        st.code(json.dumps(result["request"], indent=2), language="json")
        st.markdown("**Response**")
        st.code(json.dumps(result["response"], indent=2), language="json")
