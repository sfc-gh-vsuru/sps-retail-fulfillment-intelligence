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

RETAILERS = {"FL": "Foot Locker", "BP": "Bass Pro Shops", "UO": "Urban Outfitters"}
NETWORK_FAILURE_RATE = 0.183  # share of historical POs that arrived late or short (TRAINING_DATA)
EDITABLE = ["RETAILER_ID", "TOTAL_UNITS", "TOTAL_COST", "DAYS_TO_SHIP", "DAYS_TO_DELIVER", "HIST_OTIF_RATE"]

# Risk bands: (min probability, label, color, what to do)
BANDS = [
    (0.5, "HIGH RISK", "red", "Act now: contact the supplier, confirm the ship date, and plan for a shortfall at the store."),
    (0.2, "WATCH", "orange", "Keep an eye on it: check the ship notice (ASN) and carrier tracking before the due date."),
    (0.0, "LOW RISK", "green", "No action needed: this order looks on track to arrive on time and in full."),
]


def band(p: float):
    return next(b for b in BANDS if p >= b[0])


st.set_page_config(page_title="SPS PO Risk Checker", layout="centered")

# ─── Intro ──────────────────────────────────────────────────────────────────
st.title("SPS PO Risk Checker")
st.markdown(
    "When a retailer orders goods from a supplier, the order should arrive **on time and in full** (OTIF). "
    "About **1 in 5** orders in this network don't. This tool estimates the chance that a specific order "
    "will arrive **late or short**, and explains why in plain English, so teams can act before the store is affected."
)

h1, h2, h3 = st.columns(3)
h1.markdown("**1. Pick an order**  \nStart from a real historical order, or change the numbers to try a what-if.")
h2.markdown("**2. Score it**  \nA machine-learning model trained on 9,919 past orders returns a risk %.")
h3.markdown("**3. Understand it**  \nAn AI assistant explains what drives the score and what to do.")
st.caption(
    "This app runs on a laptop, outside Snowflake. It sends the order details over a secure connection; "
    "the data, the model, and the AI all stay in Snowflake."
)
st.divider()

# ─── Step 1: choose / edit an order ────────────────────────────────────────
st.subheader("1. Choose an order")
samples = load_samples()
labels = [f"{RETAILERS[s['RETAILER_ID']]} · {s['PO_ID']} · {s['SAMPLE_LABEL'].lower()} example" for s in samples]
choice = st.selectbox(
    "Sample purchase order",
    labels,
    help="Six real orders from history: three that arrived on time and in full, and three that were late or short.",
)
original = samples[labels.index(choice)]
base = dict(original)

st.info(
    f"**{RETAILERS[base['RETAILER_ID']]}** ordered **{int(base['TOTAL_UNITS']):,} units** "
    f"(${base['TOTAL_COST']:,.0f}) for a {base['DESTINATION_SIZE'].lower()} {base['LOCATION_TYPE'].lower()} in the "
    f"{base['DESTINATION_REGION']}, from a supplier in the {base['SUPPLIER_REGION']}.  \n"
    f"This supplier has handled **{int(base['HIST_PO_COUNT']):,} orders** for this retailer and usually needs "
    f"**{base['SUPPLIER_AVG_LEAD']:.0f} days** to deliver.  \n"
    f"**What actually happened:** {base['ACTUAL_OUTCOME'].replace('OTIF', 'on time and in full')}."
)

st.markdown("**Adjust the order (optional)**: change a value to see how the risk responds.")
c1, c2, c3 = st.columns(3)
with c1:
    base["RETAILER_ID"] = st.selectbox(
        "Retailer", list(RETAILERS), index=list(RETAILERS).index(base["RETAILER_ID"]),
        format_func=RETAILERS.get, help="The retailer that placed the order.",
    )
    base["TOTAL_UNITS"] = st.number_input(
        "Units ordered", min_value=1, value=int(base["TOTAL_UNITS"]), step=10,
        help="Total number of items on the purchase order.",
    )
with c2:
    base["TOTAL_COST"] = st.number_input(
        "Order value ($)", min_value=0.0, value=float(base["TOTAL_COST"]), step=100.0,
        help="Wholesale cost of the order.",
    )
    base["DAYS_TO_SHIP"] = st.number_input(
        "Days until shipped", min_value=0, value=int(base["DAYS_TO_SHIP"]),
        help="Days from when the order was placed until the supplier shipped it (from the EDI 856 ship notice).",
    )
with c3:
    base["DAYS_TO_DELIVER"] = st.number_input(
        "Days in transit", min_value=0, value=int(base["DAYS_TO_DELIVER"]),
        help="Days the shipment spends with the carrier before reaching the store or warehouse.",
    )
    base["HIST_OTIF_RATE"] = st.slider(
        "Supplier track record (OTIF)", 0.0, 1.0, float(base["HIST_OTIF_RATE"]), 0.01,
        help="Share of this supplier's past orders for this retailer that arrived on time and in full. "
             "0.80 means 8 out of 10.",
    )

edited = [k for k in EDITABLE if base[k] != original[k]]
if edited:
    st.caption("✎ What-if mode: you've changed this order, so the 'what actually happened' note no longer applies.")

with st.expander("See every detail the model uses"):
    st.caption("The model looks at 23 details about the order, the destination, and the supplier's history.")
    st.json({k: v for k, v in base.items() if k not in ("SAMPLE_LABEL", "ACTUAL_OUTCOME", "EXPECTED_RISK_PROB")})

explain_too = st.toggle("Include an AI explanation", value=True,
                        help=f"Uses Snowflake Cortex AI ({CORTEX_MODEL}) to explain the score in plain English.")

st.divider()

# ─── Step 2 + 3: score and explain ─────────────────────────────────────────
st.subheader("2. Check the risk")
if st.button("Score this order", type="primary", use_container_width=True):
    try:
        with st.spinner("Scoring the order..."):
            result = score([base])
        risk = result["results"][0]["risk_probability"]
    except Exception as e:
        st.error(f"Couldn't reach the scoring service. {e}")
        st.stop()

    _, level, color, action = band(risk)
    m1, m2 = st.columns([1, 1])
    m1.metric("Chance of arriving late or short", f"{risk:.0%}",
              delta=f"{(risk - NETWORK_FAILURE_RATE) * 100:+.0f} pts vs. typical order",
              delta_color="inverse")
    m2.markdown(f"### :{color}[{level}]")
    st.progress(min(max(risk, 0.0), 1.0))
    st.markdown(f"**What this means:** {action}")
    if not edited:
        st.caption(f"For comparison, this order was actually: {base['ACTUAL_OUTCOME'].replace('OTIF', 'delivered on time and in full')}.")

    with st.expander("How to read the score"):
        st.markdown(
            f"- The score is the model's estimate of the chance this order arrives **late, short, or both**.\n"
            f"- A typical order in this network has about a **{NETWORK_FAILURE_RATE:.0%}** chance.\n"
            "- **Low** is under 20%, **Watch** is 20–50%, and **High** is 50% or more.\n"
            "- On orders it hadn't seen before, the model was right about **88%** of the time. When it flags "
            "high risk, it's right about **9 times out of 10**."
        )

    if explain_too:
        st.subheader("3. Why?")
        exp = None
        try:
            with st.spinner("Asking the AI assistant..."):
                exp = explain(base, risk)
            st.info(exp["text"])
            st.caption("Written by Snowflake Cortex AI from the order details above. Treat it as guidance, not a guarantee.")
        except Exception as e:
            st.warning(f"The AI explanation isn't available right now. {e}")

    exp_latency = f", responded in **{exp['latency_ms']} ms**." if explain_too and exp else "."
    with st.expander("Behind the scenes (technical)"):
        st.markdown(
            f"- **Scoring:** Snowflake ML real-time inference endpoint (model `FULFILLMENT_RISK_XGB` V2, served on "
            f"Snowpark Container Services). Responded in **{result['latency_ms']} ms**.\n"
            f"- **Explanation:** Cortex REST API, `{CORTEX_MODEL}`{exp_latency}\n"
            "- **Security:** each call uses a Snowflake access token (PAT) over HTTPS and is subject to the "
            "account's network policy. The app never reads Snowflake tables."
        )
        st.markdown(f"**Request** · `POST {result['url']}`")
        st.code(json.dumps(result["request"], indent=2), language="json")
        st.markdown("**Response** (`output_feature_1` = probability of late or short)")
        st.code(json.dumps(result["response"], indent=2), language="json")

# ─── Glossary ──────────────────────────────────────────────────────────────
st.divider()
with st.expander("Glossary"):
    st.markdown(
        "- **Purchase order (PO):** a retailer's order to a supplier: what to send, how many, where, and by when.\n"
        "- **OTIF (on time, in full):** the order arrived by the requested date with the full quantity.\n"
        "- **Late or short:** the order missed the date, was missing items, or both.\n"
        "- **Ship notice (ASN / EDI 856):** the supplier's message saying what was shipped and when.\n"
        "- **SPS Commerce:** the network that carries these order, shipment, and invoice messages between "
        "retailers and suppliers. The model combines that data with each retailer's store information."
    )
