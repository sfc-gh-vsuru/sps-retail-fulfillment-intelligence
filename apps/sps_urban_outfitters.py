"""
SPS + Urban Outfitters: PO & SKU Readiness Dashboard
Tracks replacement PO synchronization, URBN short-SKU crosswalk quality,
and pre-ship readiness risk for Urban Outfitters' domestic vendor program.
SPS Commerce EDI joined with URBN's SKU crosswalk and store data, powered by Snowflake ML.
"""
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import altair as alt

st.set_page_config(page_title="SPS + Urban Outfitters", layout="wide")
session = get_active_session()

st.title("SPS + Urban Outfitters")
st.markdown("**PO Revision & SKU Readiness Intelligence**")
st.caption("SPS Commerce EDI  +  URBN SKU Crosswalk & Store Data  +  Snowflake ML")

st.info(
    "**SPS Commerce** provides EDI PO version tracking (replacement 850s) and shipment data. "
    "**Urban Outfitters** contributes its proprietary URBN short SKU crosswalk and store/location data. "
    "**Joined together**, this enables PO reconciliation, SKU mapping validation, and fulfillment tracking. "
    "**Snowflake ML** predicts which orders are at risk of missing ship deadlines based on PO revision "
    "patterns, SKU mapping gaps, and supplier history."
)

# ── KPI Row ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("Key Metrics")
st.markdown("SPS EDI data joined with URBN's SKU crosswalk and PO acceptance rules — fulfillment health and PO revision metrics.")

kpi = session.sql("""
    SELECT
        COUNT(DISTINCT po.PO_ID) AS TOTAL_POS,
        SUM(CASE WHEN po.IS_REPLACEMENT_850 THEN 1 ELSE 0 END) AS REPLACEMENT_POS,
        ROUND(SUM(CASE WHEN po.IS_REPLACEMENT_850 THEN 1 ELSE 0 END)::FLOAT
              / NULLIF(COUNT(DISTINCT po.PO_ID), 0) * 100, 1) AS REPLACEMENT_PCT,
        SUM(CASE WHEN po.ACCEPTANCE_STATUS = 'LATE' THEN 1 ELSE 0 END) AS LATE_ACCEPTANCES,
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS OTIF_PCT,
        (SELECT COUNT(*) FROM SPS_RETAIL_AI.URBAN_OUTFITTERS.SKU_CROSSWALK
         WHERE MAPPING_STATUS != 'ACTIVE') AS UNRESOLVED_SKUS,
        (SELECT ROUND(COUNT(CASE WHEN MAPPING_STATUS = 'ACTIVE' THEN 1 END)::FLOAT
                / NULLIF(COUNT(*), 0) * 100, 1)
         FROM SPS_RETAIL_AI.URBAN_OUTFITTERS.SKU_CROSSWALK) AS SKU_HEALTH_PCT
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
    LEFT JOIN SPS_RETAIL_AI.SHARED.SHIPMENT sh ON po.PO_ID = sh.PO_ID
    WHERE po.RETAILER_ID = 'UO'
""").to_pandas()

if not kpi.empty:
    r = kpi.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total POs", f"{int(r['TOTAL_POS']):,}")
    c2.metric("Replacement 850s", f"{int(r['REPLACEMENT_POS'])} ({r['REPLACEMENT_PCT']}%)")
    c3.metric("Late Acceptances", f"{int(r['LATE_ACCEPTANCES'])}")
    c4.metric("OTIF Rate", f"{r['OTIF_PCT']}%")
    c5.metric("SKU Mapping Health", f"{r['SKU_HEALTH_PCT']}%")

# ── Replacement PO Analysis ──────────────────────────────────
st.markdown("---")
st.subheader("Replacement PO Tracking")
st.markdown(
    "SPS PO version tracking shows replacement 850s over time. "
    "URBN sends new POs (not change requests) when modifying orders — vendors must diff against the original."
)

rev_df = session.sql("""
    SELECT
        DATE_TRUNC('month', ORDER_DATE)::DATE AS MONTH,
        REVISION_TYPE,
        COUNT(*) AS CNT
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER
    WHERE RETAILER_ID = 'UO' AND IS_REPLACEMENT_850 = TRUE
    GROUP BY 1, 2 ORDER BY 1
""").to_pandas()

if not rev_df.empty:
    rev_chart = (
        alt.Chart(rev_df)
        .mark_bar()
        .encode(
            x=alt.X("MONTH:T", title="Month"),
            y=alt.Y("CNT:Q", title="Replacement POs", stack=True),
            color=alt.Color("REVISION_TYPE:N", title="Change Type"),
            tooltip=["MONTH:T", "REVISION_TYPE", "CNT"],
        )
        .properties(height=320)
    )
    st.altair_chart(rev_chart, use_container_width=True)

# ── SKU Crosswalk Health ─────────────────────────────────────
st.markdown("---")
st.subheader("URBN Short SKU Crosswalk Health")
st.markdown(
    "URBN's proprietary SKU-to-UPC mapping table joined with SPS order data. "
    "Without an ACTIVE mapping, ASNs and carton labels are rejected — orders cannot ship."
)

sku_df = session.sql("""
    SELECT MAPPING_STATUS, COUNT(*) AS CNT,
        ROUND(COUNT(*)::FLOAT / (SELECT COUNT(*) FROM SPS_RETAIL_AI.URBAN_OUTFITTERS.SKU_CROSSWALK) * 100, 1) AS PCT
    FROM SPS_RETAIL_AI.URBAN_OUTFITTERS.SKU_CROSSWALK
    GROUP BY 1 ORDER BY CNT DESC
""").to_pandas()

if not sku_df.empty:
    col1, col2 = st.columns([1, 2])
    with col1:
        sku_bar = (
            alt.Chart(sku_df)
            .mark_arc(innerRadius=50)
            .encode(
                theta=alt.Theta("CNT:Q"),
                color=alt.Color("MAPPING_STATUS:N", title="Status",
                                scale=alt.Scale(
                                    domain=["ACTIVE", "PENDING_REVIEW", "UNRESOLVED"],
                                    range=["#27ae60", "#f39c12", "#e74c3c"])),
                tooltip=["MAPPING_STATUS", "CNT", "PCT"],
            )
            .properties(height=280)
        )
        st.altair_chart(sku_bar, use_container_width=True)

    with col2:
        st.markdown("**Items Needing Attention**")
        unresolved = session.sql("""
            SELECT URBN_SHORT_SKU, VENDOR_UPC, STYLE_NUMBER, COLOR_NAME, SIZE_NAME, MAPPING_STATUS
            FROM SPS_RETAIL_AI.URBAN_OUTFITTERS.SKU_CROSSWALK
            WHERE MAPPING_STATUS != 'ACTIVE'
            ORDER BY MAPPING_STATUS, URBN_SHORT_SKU
            LIMIT 20
        """).to_pandas()
        if not unresolved.empty:
            unresolved.columns = ["URBN SKU", "Vendor UPC", "Style", "Color", "Size", "Status"]
            st.dataframe(unresolved, use_container_width=True)

# ── Readiness Risk ───────────────────────────────────────────
st.markdown("---")
st.subheader("Pre-Ship Readiness Risk")
st.markdown(
    "Snowflake ML risk scores using SPS EDI features (supplier OTIF history, lead time, order size) "
    "plus URBN-specific signals (replacement PO flag, PO acceptance timing). "
    "Larger dots = bigger orders. Red dots = replacement POs (higher risk)."
)

readiness_df = session.sql("""
    SELECT
        p.PO_ID, p.SUPPLIER_ID, p.TOTAL_UNITS, p.DAYS_TO_DELIVER,
        p.PREDICTION:"class"::INT AS PREDICTED_RISK,
        p.IS_REPLACEMENT_850,
        ROUND(p.HIST_OTIF_RATE, 3) AS SUPPLIER_OTIF_HISTORY,
        p.IS_LATE_OR_SHORT AS ACTUAL_OUTCOME
    FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS p
    WHERE p.RETAILER_ID = 'UO'
    ORDER BY PREDICTED_RISK DESC, TOTAL_UNITS DESC
    LIMIT 200
""").to_pandas()

if not readiness_df.empty:
    readiness_df["PO_TYPE"] = readiness_df["IS_REPLACEMENT_850"].map({True: "Replacement PO", False: "Original PO"})
    scatter = (
        alt.Chart(readiness_df)
        .mark_circle(opacity=0.7)
        .encode(
            x=alt.X("DAYS_TO_DELIVER:Q", title="Lead Time (days from order to delivery)"),
            y=alt.Y("PREDICTED_RISK:Q", title="ML Predicted Risk (0=safe, 1=at-risk)"),
            size=alt.Size("TOTAL_UNITS:Q", title="Order Size (units)"),
            color=alt.Color("PO_TYPE:N", title="PO Type",
                            scale=alt.Scale(domain=["Original PO", "Replacement PO"],
                                            range=["#3498db", "#e74c3c"])),
            tooltip=["PO_ID", "SUPPLIER_ID", "TOTAL_UNITS", "DAYS_TO_DELIVER",
                      "PO_TYPE", "SUPPLIER_OTIF_HISTORY", "ACTUAL_OUTCOME"],
        )
        .properties(height=380)
    )
    st.altair_chart(scatter, use_container_width=True)

    st.markdown("**Highest Risk Orders — Review Queue**")
    top_risk = readiness_df[readiness_df["PREDICTED_RISK"] == 1].head(15)
    if not top_risk.empty:
        display = top_risk[["PO_ID", "SUPPLIER_ID", "TOTAL_UNITS", "DAYS_TO_DELIVER",
                            "PO_TYPE", "SUPPLIER_OTIF_HISTORY", "ACTUAL_OUTCOME"]].copy()
        display.columns = ["PO #", "Supplier", "Units", "Lead Days", "PO Type",
                           "Supplier OTIF History", "Actual (1=late/short)"]
        st.dataframe(display, use_container_width=True)
    else:
        st.success("No high-risk orders detected for Urban Outfitters.")

# ── Weekly Activity ──────────────────────────────────────────
st.markdown("---")
st.subheader("Weekly Sales & Inventory Trend")
st.markdown(
    "SPS weekly sell-through and inventory data for Urban Outfitters — tracking whether products are "
    "selling as expected or inventory is building up."
)

activity_df = session.sql("""
    SELECT PERIOD_ENDING_DATE,
           SUM(NET_SALES_UNITS) AS SALES,
           SUM(INVENTORY_UNITS) AS INVENTORY,
           SUM(ON_ORDER_UNITS) AS ON_ORDER
    FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY
    WHERE RETAILER_ID = 'UO'
    GROUP BY 1 ORDER BY 1
""").to_pandas()

if not activity_df.empty:
    activity_df["WEEK"] = pd.to_datetime(activity_df["PERIOD_ENDING_DATE"].astype(str), format="%Y%m%d")
    melted = activity_df.melt(id_vars=["WEEK"], value_vars=["SALES", "INVENTORY", "ON_ORDER"],
                              var_name="Metric", value_name="Units")
    line = (
        alt.Chart(melted)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("WEEK:T", title="Week"),
            y=alt.Y("Units:Q", title="Units"),
            color=alt.Color("Metric:N", title="",
                            scale=alt.Scale(domain=["SALES", "INVENTORY", "ON_ORDER"],
                                            range=["#3498db", "#27ae60", "#f39c12"])),
            strokeDash=alt.condition(alt.datum.Metric == "ON_ORDER",
                                     alt.value([5, 5]), alt.value([0])),
            tooltip=["WEEK:T", "Metric:N", "Units:Q"],
        )
        .properties(height=380)
    )
    st.altair_chart(line, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Data sources:** SPS Commerce (EDI 850 versions, 856, weekly activity) + Urban Outfitters (URBN short SKU crosswalk, stores) + Snowflake ML.  |  "
    "**Replacement 850** = New PO replacing a previous version. "
    "**URBN Short SKU** = UO's proprietary product identifier. "
    "**ASN** = Advance Ship Notice."
)
