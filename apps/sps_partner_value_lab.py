"""
SPS Partner Value Lab Dashboard
Compares fulfillment performance across all retail partners and measures
the value of SPS Commerce data signals and ML predictions.
SPS Commerce as provider, retailers as consumers — the data join and AI/ML value story.
"""
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import altair as alt

st.set_page_config(page_title="SPS Partner Value Lab", layout="wide")
session = get_active_session()

st.title("SPS Partner Value Lab")
st.markdown("**Multi-Retailer Comparison & SPS Data Value Assessment**")
st.caption("SPS Commerce (Provider)  +  Foot Locker / Bass Pro / Urban Outfitters (Consumers)  +  Snowflake ML")

st.info(
    "**SPS Commerce** (data provider) supplies standardized EDI transaction data across all retailers. "
    "**Each retailer** (data consumer) contributes their unique operational context — banners, seasonal categories, "
    "SKU crosswalks. **The data join** creates a unified fulfillment picture that neither side has alone. "
    "**Snowflake ML** trained on this joined dataset reveals which SPS signals drive the most predictive value."
)

# ── Cross-Retailer KPI Table ────────────────────────────────
st.markdown("---")
st.subheader("Fulfillment Performance Comparison")
st.markdown(
    "SPS EDI data (POs, shipments, invoices) joined with each retailer's dimension data, using the same "
    "metric definitions. Differences reflect actual performance, not measurement inconsistencies."
)

compare_df = session.sql("""
    SELECT
        RETAILER_NAME, TOTAL_POS, ON_TIME_PCT, IN_FULL_PCT, OTIF_PCT,
        AVG_DAYS_LATE, INVOICE_MISMATCHES, MISMATCH_RATE_PCT
    FROM SPS_RETAIL_AI.SHARED.V_FULFILLMENT_KPI
    ORDER BY OTIF_PCT DESC
""").to_pandas()

if not compare_df.empty:
    display = compare_df.copy()
    display.columns = ["Retailer", "Total POs", "On-Time %", "In-Full %", "OTIF %",
                        "Avg Days Late", "Invoice Mismatches", "Invoice Mismatch %"]
    st.dataframe(display, use_container_width=True)

    st.markdown(
        "Taller bars = better. The same SPS EDI metrics, applied consistently across retailers."
    )
    melted = compare_df.melt(
        id_vars=["RETAILER_NAME"],
        value_vars=["ON_TIME_PCT", "IN_FULL_PCT", "OTIF_PCT"],
        var_name="Metric", value_name="Rate"
    )
    melted["Metric"] = melted["Metric"].map({
        "ON_TIME_PCT": "On-Time %", "IN_FULL_PCT": "In-Full %", "OTIF_PCT": "OTIF %"
    })
    bar = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("Metric:N", title=""),
            y=alt.Y("Rate:Q", title="Rate (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("Metric:N", title="",
                            scale=alt.Scale(range=["#3498db", "#27ae60", "#2c3e50"])),
            column=alt.Column("RETAILER_NAME:N", title="Retailer"),
            tooltip=["RETAILER_NAME", "Metric", "Rate"],
        )
        .properties(width=150, height=320)
    )
    st.altair_chart(bar)

# ── ML Model Accuracy by Retailer ────────────────────────────
st.markdown("---")
st.subheader("ML Model Accuracy by Retailer")
st.markdown(
    "Snowflake ML classification model trained on SPS + retailer joined data, evaluated per retailer. "
    "Accuracy = correct predictions. Precision = when it flags risk, is it real? Recall = of all problems, how many caught?"
)

acc_df = session.sql("""
    SELECT
        RETAILER_ID,
        COUNT(*) AS TOTAL,
        ROUND(SUM(CASE WHEN PREDICTION:"class"::INT = IS_LATE_OR_SHORT THEN 1 ELSE 0 END)::FLOAT
              / COUNT(*) * 100, 1) AS ACCURACY,
        ROUND(SUM(CASE WHEN PREDICTION:"class"::INT = 1 AND IS_LATE_OR_SHORT = 1 THEN 1 ELSE 0 END)::FLOAT /
              NULLIF(SUM(CASE WHEN PREDICTION:"class"::INT = 1 THEN 1 ELSE 0 END), 0) * 100, 1) AS PRECISION_PCT,
        ROUND(SUM(CASE WHEN PREDICTION:"class"::INT = 1 AND IS_LATE_OR_SHORT = 1 THEN 1 ELSE 0 END)::FLOAT /
              NULLIF(SUM(CASE WHEN IS_LATE_OR_SHORT = 1 THEN 1 ELSE 0 END), 0) * 100, 1) AS RECALL_PCT
    FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS
    GROUP BY 1
""").to_pandas()

if not acc_df.empty:
    names = {"FL": "Foot Locker", "BP": "Bass Pro Shops", "UO": "Urban Outfitters"}
    acc_df["RETAILER"] = acc_df["RETAILER_ID"].map(names)

    cols = st.columns(len(acc_df))
    for idx, row in acc_df.iterrows():
        with cols[idx]:
            st.markdown(f"**{row['RETAILER']}**")
            st.metric("Accuracy", f"{row['ACCURACY']}%")
            prec = row["PRECISION_PCT"]
            st.metric("Precision", f"{prec}%" if pd.notna(prec) else "N/A")
            rec = row["RECALL_PCT"]
            st.metric("Recall", f"{rec}%" if pd.notna(rec) else "N/A")
            st.metric("POs Evaluated", f"{int(row['TOTAL']):,}")

# ── Feature Importance ───────────────────────────────────────
st.markdown("---")
st.subheader("What Drives the ML Predictions?")
st.markdown(
    "Which SPS data points give the ML model the most predictive power? "
    "This answers: what information from the data join makes the biggest difference?"
)

session.sql(
    "CALL SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_RISK_MODEL!SHOW_FEATURE_IMPORTANCE()"
).collect()
importance_df = session.sql(
    "SELECT \"FEATURE\" AS FEATURE, \"SCORE\" AS SCORE FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) ORDER BY \"SCORE\" DESC"
).to_pandas()

if not importance_df.empty:
    importance_df.columns = [c.upper() for c in importance_df.columns]
    labels = {
        "TOTAL_COST": "Order Value (total cost of the PO)",
        "TOTAL_LINE_QTY": "Total Units Ordered",
        "TOTAL_UNITS": "PO Unit Count",
        "ORDER_MONTH": "Month of Year (seasonal patterns)",
        "ORDER_DOW": "Day of Week order was placed",
        "LINE_COUNT": "Number of Line Items (order complexity)",
        "HIST_ON_TIME_RATE": "Supplier's On-Time Track Record",
        "DESTINATION_REGION": "Destination Region (shipping distance)",
        "SUPPLIER_ID": "Specific Supplier",
        "HIST_IN_FULL_RATE": "Supplier's In-Full Track Record",
        "SUPPLIER_LEAD_VAR": "Supplier Lead Time Consistency",
        "SUPPLIER_AVG_LEAD": "Supplier Average Lead Time (days)",
        "RETAILER_ID": "Which Retailer",
        "HIST_PO_COUNT": "# of Past Orders with Supplier",
        "HIST_OTIF_RATE": "Supplier's OTIF Track Record",
        "DAYS_TO_SHIP": "Days to Ship",
        "DAYS_TO_DELIVER": "Days to Deliver",
    }
    top = importance_df[importance_df["SCORE"] > 0].head(12).copy()
    top["LABEL"] = top["FEATURE"].map(labels).fillna(top["FEATURE"])

    imp_chart = (
        alt.Chart(top)
        .mark_bar(color="#3498db")
        .encode(
            x=alt.X("SCORE:Q", title="Importance Score"),
            y=alt.Y("LABEL:N", title="", sort="-x"),
            tooltip=["LABEL", "SCORE"],
        )
        .properties(height=400)
    )
    st.altair_chart(imp_chart, use_container_width=True)

# ── SPS Data Value Proposition ───────────────────────────────
st.markdown("---")
st.subheader("The SPS Commerce Data Advantage")
st.markdown("The data join story — what each party brings and what becomes possible together:")

value_data = pd.DataFrame({
    "Retailer": ["Foot Locker", "Bass Pro Shops", "Urban Outfitters"],
    "Unique Challenge": [
        "Multi-banner size/color fulfillment for footwear launches",
        "Seasonal outdoor demand with strong regional variation",
        "Replacement POs and proprietary SKU mapping complexity",
    ],
    "SPS Data Signal": [
        "EDI 850/856 tracking across banners",
        "Weekly sales/inventory activity data",
        "PO version tracking + SKU crosswalk validation",
    ],
    "ML-Enabled Action": [
        "Predict size availability gaps before launch day",
        "Pre-position inventory before seasonal peaks",
        "Flag at-risk orders before ship deadline passes",
    ],
})
st.dataframe(value_data, use_container_width=True)

st.markdown(
    "**Without the join:** Each side sees only half the picture. Retailers miss supplier-side signals; "
    "SPS data lacks store-level context. Late shipments become chargebacks and lost sales.\n\n"
    "**With the join + ML:** EDI transaction history combined with retailer operations data creates "
    "predictive features that neither dataset has alone — enabling early intervention before problems happen."
)

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Data sources:** SPS Commerce (provider: EDI transactions) + Retailers (consumers: stores, products, operations) + Snowflake ML (classification model).  |  "
    "**Accuracy** = % correct. **Precision** = Flagged risks that are real. "
    "**Recall** = Real problems caught. **Feature Importance** = Which data the model relies on most."
)
