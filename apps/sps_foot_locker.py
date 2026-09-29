"""
SPS + Foot Locker: Launch & Size Readiness Dashboard
Tracks footwear launch readiness, size availability, and fulfillment risk
across Foot Locker's multi-banner portfolio (FL, Champs, Kids FL, WSS).
SPS Commerce EDI joined with Foot Locker store/banner/product data, powered by Snowflake ML.
"""
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import altair as alt

st.set_page_config(page_title="SPS + Foot Locker", layout="wide")
session = get_active_session()

st.title("SPS + Foot Locker")
st.markdown("**Launch & Size Readiness Intelligence**")
st.caption("SPS Commerce EDI  +  Foot Locker Store & Product Data  +  Snowflake ML")

st.info(
    "**SPS Commerce** provides EDI order and shipment tracking across all Foot Locker banners. "
    "**Foot Locker** contributes its multi-banner store structure (FL, Champs, Kids FL, WSS) and "
    "product catalog with size/color attributes. **Joined together**, this enables size-level readiness "
    "analysis per banner. **Snowflake ML** flags which inbound orders are at risk of missing launch dates."
)

# ── KPIs ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Key Metrics")
st.markdown("SPS shipment data joined with Foot Locker's banner/store dimension — OTIF, POs, and shipped units across all banners.")

kpi = session.sql("""
    SELECT
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS OTIF_PCT,
        COUNT(DISTINCT po.PO_ID) AS TOTAL_POS,
        COUNT(DISTINCT l.BANNER) AS BANNERS,
        SUM(sh.TOTAL_UNITS) AS TOTAL_SHIPPED
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
    JOIN SPS_RETAIL_AI.SHARED.LOCATION l ON po.SHIP_TO_LOCATION_ID = l.LOCATION_ID
    LEFT JOIN SPS_RETAIL_AI.SHARED.SHIPMENT sh ON po.PO_ID = sh.PO_ID
    WHERE po.RETAILER_ID = 'FL'
""").to_pandas()

if not kpi.empty:
    r = kpi.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OTIF Rate", f"{r['OTIF_PCT']}%")
    c2.metric("Total POs", f"{int(r['TOTAL_POS']):,}")
    c3.metric("Active Banners", f"{int(r['BANNERS'])}")
    shipped = int(r["TOTAL_SHIPPED"]) if pd.notna(r["TOTAL_SHIPPED"]) else 0
    c4.metric("Units Shipped", f"{shipped:,}")

# ── Banner Performance ───────────────────────────────────────
st.markdown("---")
st.subheader("Performance by Banner")
st.markdown(
    "SPS EDI shipment flags (on-time, in-full) joined with Foot Locker's banner dimension. "
    "Banners with lower scores may have different supplier mixes that need attention."
)

banner_df = session.sql("""
    SELECT
        l.BANNER,
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG THEN 1 ELSE 0 END)*100, 1) AS ON_TIME_PCT,
        ROUND(AVG(CASE WHEN sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS IN_FULL_PCT,
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS OTIF_PCT,
        COUNT(DISTINCT po.PO_ID) AS PO_COUNT
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
    JOIN SPS_RETAIL_AI.SHARED.LOCATION l ON po.SHIP_TO_LOCATION_ID = l.LOCATION_ID
    JOIN SPS_RETAIL_AI.SHARED.SHIPMENT sh ON po.PO_ID = sh.PO_ID
    WHERE po.RETAILER_ID = 'FL'
    GROUP BY 1 ORDER BY OTIF_PCT DESC
""").to_pandas()

if not banner_df.empty:
    melted = banner_df.melt(id_vars=["BANNER", "PO_COUNT"],
                            value_vars=["ON_TIME_PCT", "IN_FULL_PCT"],
                            var_name="Metric", value_name="Rate")
    melted["Metric"] = melted["Metric"].map({"ON_TIME_PCT": "On-Time %", "IN_FULL_PCT": "In-Full %"})
    chart = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("Metric:N", title=""),
            y=alt.Y("Rate:Q", title="Rate (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("Metric:N", scale=alt.Scale(range=["#3498db", "#27ae60"])),
            column=alt.Column("BANNER:N", title="Banner"),
            tooltip=["BANNER", "Metric", "Rate"],
        )
        .properties(width=120, height=300)
    )
    st.altair_chart(chart)

# ── Size Availability ────────────────────────────────────────
st.markdown("---")
st.subheader("Footwear Size Availability")
st.markdown(
    "SPS activity data (inventory units) joined with Foot Locker's product catalog (size/color attributes). "
    "Sizes 9-12 typically account for 50-60% of men's sales — low inventory on these sizes is a red flag."
)

size_df = session.sql("""
    SELECT
        v.SIZE_NAME,
        v.PRODUCT_GROUP_NAME AS CATEGORY,
        SUM(v.INVENTORY_UNITS) AS TOTAL_INVENTORY,
        SUM(v.NET_SALES_UNITS) AS TOTAL_SALES
    FROM SPS_RETAIL_AI.FOOT_LOCKER.V_WEEKLY_ACTIVITY v
    WHERE v.CATEGORY_NAME = 'FOOTWEAR'
      AND v.PERIOD_ENDING_DATE = (SELECT MAX(PERIOD_ENDING_DATE) FROM SPS_RETAIL_AI.FOOT_LOCKER.V_WEEKLY_ACTIVITY)
      AND v.SIZE_NAME IS NOT NULL
    GROUP BY 1, 2
    ORDER BY 2, 1
""").to_pandas()

if not size_df.empty:
    size_bar = (
        alt.Chart(size_df)
        .mark_bar()
        .encode(
            x=alt.X("SIZE_NAME:N", title="Size", sort=None),
            y=alt.Y("TOTAL_INVENTORY:Q", title="Inventory Units"),
            color=alt.Color("CATEGORY:N", title="Product Group"),
            tooltip=["SIZE_NAME", "CATEGORY", "TOTAL_INVENTORY", "TOTAL_SALES"],
        )
        .properties(height=320)
    )
    st.altair_chart(size_bar, use_container_width=True)
else:
    st.warning("No size-level data available for the latest period.")

# ── Sales Trend by Category ──────────────────────────────────
st.markdown("---")
st.subheader("Weekly Sales Trend by Category")
st.markdown(
    "SPS weekly sell-through data broken out by Foot Locker's product categories. "
    "Spikes around back-to-school (Aug-Sep) and holiday (Nov-Dec) are expected; unexpected dips signal supply problems."
)

trend_df = session.sql("""
    SELECT PERIOD_ENDING_DATE, CATEGORY_NAME,
           SUM(NET_SALES_UNITS) AS TOTAL_SALES
    FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY
    WHERE RETAILER_ID = 'FL'
    GROUP BY 1, 2 ORDER BY 1
""").to_pandas()

if not trend_df.empty:
    trend_df["WEEK"] = pd.to_datetime(trend_df["PERIOD_ENDING_DATE"].astype(str), format="%Y%m%d")
    area = (
        alt.Chart(trend_df)
        .mark_area(opacity=0.6)
        .encode(
            x=alt.X("WEEK:T", title="Week"),
            y=alt.Y("TOTAL_SALES:Q", title="Units Sold", stack=True),
            color=alt.Color("CATEGORY_NAME:N", title="Category"),
            tooltip=["WEEK:T", "CATEGORY_NAME:N", "TOTAL_SALES:Q"],
        )
        .properties(height=380)
    )
    st.altair_chart(area, use_container_width=True)

# ── ML Risk by Banner ────────────────────────────────────────
st.markdown("---")
st.subheader("ML-Predicted Fulfillment Risk by Banner")
st.markdown(
    "Snowflake ML risk scores aggregated by Foot Locker's banner structure. "
    "Banners with more flagged orders need proactive supplier follow-up before ship dates."
)

risk_banner = session.sql("""
    SELECT
        l.BANNER,
        COUNT(*) AS TOTAL_POS,
        SUM(CASE WHEN p.PREDICTION:"class"::INT = 1 THEN 1 ELSE 0 END) AS HIGH_RISK_POS,
        ROUND(SUM(CASE WHEN p.PREDICTION:"class"::INT = 1 THEN 1 ELSE 0 END)::FLOAT
              / NULLIF(COUNT(*), 0) * 100, 1) AS RISK_PCT
    FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS p
    JOIN SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po ON p.PO_ID = po.PO_ID
    JOIN SPS_RETAIL_AI.SHARED.LOCATION l ON po.SHIP_TO_LOCATION_ID = l.LOCATION_ID
    WHERE p.RETAILER_ID = 'FL'
    GROUP BY 1
""").to_pandas()

if not risk_banner.empty:
    risk_chart = (
        alt.Chart(risk_banner)
        .mark_bar(color="#e74c3c")
        .encode(
            x=alt.X("BANNER:N", title="Banner"),
            y=alt.Y("HIGH_RISK_POS:Q", title="High-Risk Orders"),
            tooltip=["BANNER", "HIGH_RISK_POS", "TOTAL_POS", "RISK_PCT"],
        )
        .properties(height=300)
    )
    st.altair_chart(risk_chart, use_container_width=True)

    for _, row in risk_banner.iterrows():
        st.caption(f'{row["BANNER"]}: {int(row["HIGH_RISK_POS"])} of {int(row["TOTAL_POS"])} orders flagged ({row["RISK_PCT"]}%)')

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Data sources:** SPS Commerce (EDI 850/856, weekly activity) + Foot Locker (banners, stores, product catalog with sizes) + Snowflake ML.  |  "
    "**Banner** = Retail brand (FL, Champs, Kids FL, WSS). **Size Curve** = Distribution of sales across shoe sizes. "
    "**OTIF** = On-Time, In-Full."
)
