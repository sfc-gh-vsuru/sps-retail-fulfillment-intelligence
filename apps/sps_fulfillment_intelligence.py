"""
SPS Fulfillment Intelligence Dashboard
Cross-retailer fulfillment health, ML risk predictions, and supplier performance.
SPS Commerce EDI data joined with retailer operations data, powered by Snowflake ML.
"""
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import altair as alt

st.set_page_config(page_title="SPS Fulfillment Intelligence", layout="wide")
session = get_active_session()

# ── Header ───────────────────────────────────────────────────
st.title("SPS Fulfillment Intelligence")
st.caption("SPS Commerce EDI  +  Retailer Operations  +  Snowflake ML")

st.info(
    "**SPS Commerce** provides EDI transaction data (purchase orders, shipment notices, invoices, receipts) "
    "across all retail partners. **Each retailer** contributes store locations, product catalogs, and banner structures. "
    "**Joined together**, this creates end-to-end fulfillment visibility from order placement to delivery. "
    "**Snowflake ML** adds a classification model trained on 2 years of this joined history to predict "
    "which open orders are most likely to arrive late or incomplete — enabling proactive intervention."
)

# ── Sidebar filters ──────────────────────────────────────────
st.sidebar.header("Filters")
retailers = session.sql(
    "SELECT DISTINCT RETAILER_ID, RETAILER_NAME "
    "FROM SPS_RETAIL_AI.SHARED.RETAILER ORDER BY 2"
).to_pandas()

selected_retailers = st.sidebar.multiselect(
    "Retail Partners",
    options=retailers["RETAILER_NAME"].tolist(),
    default=retailers["RETAILER_NAME"].tolist(),
)
retailer_ids = retailers[retailers["RETAILER_NAME"].isin(selected_retailers)]["RETAILER_ID"].tolist()
retailer_filter = ",".join([f"'{r}'" for r in retailer_ids]) if retailer_ids else "'NONE'"

# ── KPI from pre-built view ──────────────────────────────────
st.markdown("---")
st.subheader("Fulfillment Health at a Glance")
st.markdown(
    "Computed by joining SPS shipment data (on-time/in-full flags) with retailer PO data (requested dates, quantities). "
    "**OTIF** (On-Time, In-Full) is the industry standard for measuring whether the right products arrived "
    "by the agreed date in the correct quantities."
)

kpi_df = session.sql(f"""
    SELECT RETAILER_NAME, TOTAL_POS, ON_TIME_PCT, IN_FULL_PCT, OTIF_PCT,
           AVG_DAYS_LATE, INVOICE_MISMATCHES, MISMATCH_RATE_PCT
    FROM SPS_RETAIL_AI.SHARED.V_FULFILLMENT_KPI
    WHERE RETAILER_ID IN ({retailer_filter})
    ORDER BY OTIF_PCT DESC
""").to_pandas()

if not kpi_df.empty:
    cols = st.columns(len(kpi_df))
    for idx, row in kpi_df.iterrows():
        with cols[idx]:
            st.metric(row["RETAILER_NAME"], f'{row["OTIF_PCT"]}% OTIF')
            c1, c2 = st.columns(2)
            c1.metric("On-Time", f'{row["ON_TIME_PCT"]}%')
            c2.metric("In-Full", f'{row["IN_FULL_PCT"]}%')
            st.metric("Avg Days Late", f'{row["AVG_DAYS_LATE"]}')
            mm = row["INVOICE_MISMATCHES"]
            mp = row["MISMATCH_RATE_PCT"]
            st.metric("Invoice Mismatches", f"{int(mm)} ({mp}%)")

# ── Order-to-Cash Journey ────────────────────────────────────
st.markdown("---")
st.subheader("Order-to-Cash Journey: The Data Join in Action")
st.markdown(
    "Each stage below represents a different EDI document joining together to form the complete picture. "
    "**SPS Commerce** tracks POs (850), shipments (856), and invoices (810). **Retailers** contribute "
    "receipt confirmation. The join across all four stages is what makes OTIF measurement and ML risk prediction possible."
)

journey_df = session.sql(f"""
    SELECT
        r.RETAILER_NAME,
        COUNT(DISTINCT po.PO_ID) AS TOTAL_POS,
        COUNT(DISTINCT sh.PO_ID) AS SHIPPED,
        SUM(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END) AS OTIF_PASS,
        COUNT(DISTINCT rcp.PO_ID) AS RECEIVED,
        COUNT(DISTINCT inv.PO_ID) AS INVOICED,
        SUM(CASE WHEN inv.MISMATCH_FLAG THEN 1 ELSE 0 END) AS INVOICE_ISSUES,
        ROUND(AVG(DATEDIFF('day', po.ORDER_DATE, sh.SHIP_DATE)),1) AS AVG_ORDER_TO_SHIP,
        ROUND(AVG(DATEDIFF('day', sh.SHIP_DATE, sh.ACTUAL_DELIVERY_DATE)),1) AS AVG_TRANSIT
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
    JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON po.RETAILER_ID = r.RETAILER_ID
    LEFT JOIN SPS_RETAIL_AI.SHARED.SHIPMENT sh ON po.PO_ID = sh.PO_ID
    LEFT JOIN SPS_RETAIL_AI.SHARED.RECEIPT rcp ON sh.SHIPMENT_ID = rcp.SHIPMENT_ID
    LEFT JOIN SPS_RETAIL_AI.SHARED.INVOICE inv ON sh.SHIPMENT_ID = inv.SHIPMENT_ID
    WHERE po.RETAILER_ID IN ({retailer_filter})
    GROUP BY r.RETAILER_NAME
    ORDER BY TOTAL_POS DESC
""").to_pandas()

if not journey_df.empty:
    # Funnel bar chart: POs -> Shipped -> OTIF Pass -> Invoiced Clean
    funnel_rows = []
    for _, row in journey_df.iterrows():
        name = row["RETAILER_NAME"]
        clean_inv = int(row["INVOICED"]) - int(row["INVOICE_ISSUES"])
        funnel_rows.append({"Retailer": name, "Stage": "1. PO Placed (EDI 850)", "Count": int(row["TOTAL_POS"])})
        funnel_rows.append({"Retailer": name, "Stage": "2. Shipped (EDI 856)", "Count": int(row["SHIPPED"])})
        funnel_rows.append({"Retailer": name, "Stage": "3. OTIF Delivered", "Count": int(row["OTIF_PASS"])})
        funnel_rows.append({"Retailer": name, "Stage": "4. Invoice Clean (EDI 810)", "Count": clean_inv})
    funnel = pd.DataFrame(funnel_rows)

    funnel_chart = (
        alt.Chart(funnel)
        .mark_bar()
        .encode(
            x=alt.X("Count:Q", title="Number of Orders"),
            y=alt.Y("Stage:N", title="", sort=["1. PO Placed (EDI 850)", "2. Shipped (EDI 856)",
                                                  "3. OTIF Delivered", "4. Invoice Clean (EDI 810)"]),
            color=alt.Color("Retailer:N"),
            tooltip=["Retailer", "Stage", "Count"],
        )
        .properties(height=280)
    )
    st.altair_chart(funnel_chart, use_container_width=True)

    # Timing metrics table
    st.markdown(
        "**Cycle time between stages** — how long each step takes on average. "
        "Faster cycles mean less working capital tied up and fewer at-risk orders."
    )
    timing = journey_df[["RETAILER_NAME", "AVG_ORDER_TO_SHIP", "AVG_TRANSIT",
                          "TOTAL_POS", "SHIPPED", "INVOICE_ISSUES"]].copy()
    timing.columns = ["Retailer", "Avg Days: Order→Ship", "Avg Days: Ship→Deliver",
                       "POs Placed", "POs Shipped", "Invoice Issues"]
    st.dataframe(timing, use_container_width=True)

# ── OTIF Trend ───────────────────────────────────────────────
st.markdown("---")
st.subheader("OTIF Trend Over Time")
st.markdown(
    "SPS shipment timestamps joined with retailer delivery windows, aggregated weekly. "
    "A declining trend may signal supplier capacity issues or seasonal strain."
)

trend_df = session.sql(f"""
    SELECT
        DATE_TRUNC('week', sh.ACTUAL_DELIVERY_DATE)::DATE AS WEEK,
        r.RETAILER_NAME,
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS OTIF_PCT
    FROM SPS_RETAIL_AI.SHARED.SHIPMENT sh
    JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON sh.RETAILER_ID = r.RETAILER_ID
    WHERE sh.RETAILER_ID IN ({retailer_filter})
    GROUP BY 1, 2
    ORDER BY 1
""").to_pandas()

if not trend_df.empty:
    chart = (
        alt.Chart(trend_df)
        .mark_line(point=False, strokeWidth=2)
        .encode(
            x=alt.X("WEEK:T", title="Week"),
            y=alt.Y("OTIF_PCT:Q", title="OTIF Rate (%)", scale=alt.Scale(zero=False)),
            color=alt.Color("RETAILER_NAME:N", title="Retailer"),
            tooltip=["WEEK:T", "RETAILER_NAME:N", "OTIF_PCT:Q"],
        )
        .properties(height=450, width="container")
    )
    st.altair_chart(chart, use_container_width=True)

# ── ML Risk Predictions ─────────────────────────────────────
st.markdown("---")
st.subheader("ML-Predicted Fulfillment Risk")
st.markdown(
    "A Snowflake ML classification model trained on SPS EDI history + retailer order data. "
    "It scores each PO on how likely it is to arrive late or incomplete, using supplier track record "
    "(from SPS), order size and complexity (from retailer POs), and lead time patterns (from joined shipment data)."
)

risk_df = session.sql(f"""
    SELECT
        PO_ID, RETAILER_ID, SUPPLIER_ID, TOTAL_UNITS, DAYS_TO_DELIVER,
        HIST_OTIF_RATE,
        PREDICTION:"class"::INT AS PREDICTED_RISK,
        IS_LATE_OR_SHORT AS ACTUAL_OUTCOME
    FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS
    WHERE RETAILER_ID IN ({retailer_filter})
    ORDER BY PREDICTED_RISK DESC, TOTAL_UNITS DESC
    LIMIT 500
""").to_pandas()

if not risk_df.empty:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(
            "**Risk distribution:** Each bar shows how many orders the model "
            "flagged as on-time (0) vs. at-risk (1) for each retailer."
        )
        risk_summary = risk_df.groupby(["RETAILER_ID", "PREDICTED_RISK"]).size().reset_index(name="COUNT")
        risk_summary["PREDICTED_RISK"] = risk_summary["PREDICTED_RISK"].map({0: "On-Time (low risk)", 1: "At-Risk (high risk)"})
        bar = (
            alt.Chart(risk_summary)
            .mark_bar()
            .encode(
                x=alt.X("RETAILER_ID:N", title="Retailer"),
                y=alt.Y("COUNT:Q", title="Number of POs"),
                color=alt.Color("PREDICTED_RISK:N", title="ML Prediction",
                                scale=alt.Scale(domain=["On-Time (low risk)", "At-Risk (high risk)"],
                                                range=["#27ae60", "#e74c3c"])),
                tooltip=["RETAILER_ID", "PREDICTED_RISK", "COUNT"],
            )
            .properties(height=300)
        )
        st.altair_chart(bar, use_container_width=True)

    with col2:
        st.markdown("**Model Accuracy**")
        accuracy = session.sql("""
            SELECT
                ROUND(SUM(CASE WHEN PREDICTION:"class"::INT = IS_LATE_OR_SHORT THEN 1 ELSE 0 END)::FLOAT
                    / COUNT(*) * 100, 1) AS ACCURACY_PCT,
                COUNT(*) AS TOTAL_POS
            FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS
        """).to_pandas()
        if not accuracy.empty:
            st.metric("Overall Accuracy", f"{accuracy['ACCURACY_PCT'].iloc[0]}%")
            st.metric("POs Evaluated", f"{int(accuracy['TOTAL_POS'].iloc[0]):,}")

        st.markdown("**Top Risk Factors**")
        st.markdown("_What the model weighs most when making predictions:_")
        session.sql(
            "CALL SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_RISK_MODEL!SHOW_FEATURE_IMPORTANCE()"
        ).collect()
        importance_df = session.sql(
            "SELECT \"FEATURE\" AS FEATURE, \"SCORE\" AS SCORE FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) ORDER BY \"SCORE\" DESC"
        ).to_pandas()
        if not importance_df.empty:
            importance_df.columns = [c.upper() for c in importance_df.columns]
            labels = {
                "TOTAL_COST": "Order Value ($)",
                "TOTAL_LINE_QTY": "Total Units Ordered",
                "TOTAL_UNITS": "PO Unit Count",
                "ORDER_MONTH": "Month of Year",
                "ORDER_DOW": "Day of Week",
                "LINE_COUNT": "# of Line Items",
                "HIST_ON_TIME_RATE": "Supplier On-Time History",
                "HIST_OTIF_RATE": "Supplier OTIF History",
                "SUPPLIER_AVG_LEAD": "Supplier Lead Time",
                "DAYS_TO_SHIP": "Days to Ship",
                "DAYS_TO_DELIVER": "Days to Deliver",
            }
            top = importance_df.head(7).copy()
            top["LABEL"] = top["FEATURE"].map(labels).fillna(top["FEATURE"])
            for _, r in top.iterrows():
                st.progress(min(float(r["SCORE"]), 1.0), text=f'{r["LABEL"]}: {r["SCORE"]:.1%}')

    st.markdown("**Highest Risk Purchase Orders** — review these first")
    high_risk = risk_df[risk_df["PREDICTED_RISK"] == 1].head(20)
    if not high_risk.empty:
        display = high_risk[["PO_ID", "RETAILER_ID", "SUPPLIER_ID", "TOTAL_UNITS",
                             "DAYS_TO_DELIVER", "HIST_OTIF_RATE", "ACTUAL_OUTCOME"]].copy()
        display.columns = ["PO #", "Retailer", "Supplier", "Units", "Lead Days",
                           "Supplier OTIF History", "Actual (1=late/short)"]
        st.dataframe(display, use_container_width=True)
    else:
        st.success("No high-risk orders detected in the current selection.")

# ── Supplier Performance ─────────────────────────────────────
st.markdown("---")
st.subheader("Supplier Performance Comparison")
st.markdown(
    "SPS shipment and receipt data joined with the supplier dimension. "
    "Suppliers in the top-right (above 80% on both axes) are meeting industry standards. "
    "Those below need review — the ML model's supplier history features are derived from this same data."
)

supplier_df = session.sql(f"""
    SELECT
        s.SUPPLIER_NAME,
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG THEN 1 ELSE 0 END)*100, 1) AS ON_TIME_PCT,
        ROUND(AVG(CASE WHEN sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS IN_FULL_PCT,
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS OTIF_PCT,
        COUNT(DISTINCT po.PO_ID) AS PO_COUNT,
        ROUND(AVG(rcp.DAYS_LATE), 1) AS AVG_DAYS_LATE
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
    JOIN SPS_RETAIL_AI.SHARED.SUPPLIER s ON po.SUPPLIER_ID = s.SUPPLIER_ID
    JOIN SPS_RETAIL_AI.SHARED.SHIPMENT sh ON po.PO_ID = sh.PO_ID
    LEFT JOIN SPS_RETAIL_AI.SHARED.RECEIPT rcp ON sh.SHIPMENT_ID = rcp.SHIPMENT_ID
    WHERE po.RETAILER_ID IN ({retailer_filter})
    GROUP BY 1
    HAVING COUNT(*) >= 5
    ORDER BY OTIF_PCT
""").to_pandas()

if not supplier_df.empty:
    scatter = (
        alt.Chart(supplier_df)
        .mark_circle(size=120)
        .encode(
            x=alt.X("ON_TIME_PCT:Q", title="On-Time Rate (%)", scale=alt.Scale(domain=[50, 100])),
            y=alt.Y("IN_FULL_PCT:Q", title="In-Full Rate (%)", scale=alt.Scale(domain=[50, 100])),
            color=alt.Color("AVG_DAYS_LATE:Q", title="Avg Days Late",
                            scale=alt.Scale(scheme="redyellowgreen", reverse=True)),
            size=alt.Size("PO_COUNT:Q", title="Order Count"),
            tooltip=["SUPPLIER_NAME", "ON_TIME_PCT", "IN_FULL_PCT", "OTIF_PCT", "PO_COUNT", "AVG_DAYS_LATE"],
        )
        .properties(height=420)
    )
    rule_h = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(strokeDash=[4, 4], color="grey").encode(y="y:Q")
    rule_v = alt.Chart(pd.DataFrame({"x": [80]})).mark_rule(strokeDash=[4, 4], color="grey").encode(x="x:Q")
    st.altair_chart(scatter + rule_h + rule_v, use_container_width=True)

# ── Invoice Health ───────────────────────────────────────────
st.markdown("---")
st.subheader("Invoice Reconciliation")
st.markdown(
    "SPS invoice data (EDI 810) cross-referenced against the original PO and shipment. "
    "Mismatches — wrong quantities, price differences, missing lines — cause payment delays and disputes."
)

inv_df = session.sql(f"""
    SELECT MISMATCH_REASON, COUNT(*) AS CNT
    FROM SPS_RETAIL_AI.SHARED.INVOICE
    WHERE MISMATCH_FLAG = TRUE AND RETAILER_ID IN ({retailer_filter})
    GROUP BY 1 ORDER BY CNT DESC
""").to_pandas()

if not inv_df.empty:
    inv_bar = (
        alt.Chart(inv_df)
        .mark_bar(color="#e74c3c")
        .encode(
            x=alt.X("CNT:Q", title="Number of Mismatches"),
            y=alt.Y("MISMATCH_REASON:N", title="Reason", sort="-x"),
            tooltip=["MISMATCH_REASON", "CNT"],
        )
        .properties(height=250)
    )
    st.altair_chart(inv_bar, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Data sources:** SPS Commerce (EDI 850/856/810/861) + Retailer (stores, products, banners) + Snowflake ML (classification model).  |  "
    "**EDI** = Electronic Data Interchange. **PO** = Purchase Order. **ASN** = Advance Ship Notice. "
    "**OTIF** = On-Time, In-Full. **Chargeback** = Financial penalty for non-compliant deliveries."
)
