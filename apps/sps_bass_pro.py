"""
SPS + Bass Pro Shops: Seasonal Availability Dashboard
Tracks seasonal demand patterns, inventory positioning, and supplier reliability
for outdoor recreation categories. SPS Commerce data joined with Bass Pro store/category data, powered by Snowflake ML.
"""
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import altair as alt

st.set_page_config(page_title="SPS + Bass Pro Shops", layout="wide")
session = get_active_session()

st.title("SPS + Bass Pro Shops")
st.markdown("**Seasonal Availability & Inventory Intelligence**")
st.caption("SPS Commerce EDI + Activity Data  |  Bass Pro Shops Store & Category Data  |  Snowflake ML")

st.info(
    "**SPS Commerce** provides weekly sell-through and inventory data plus EDI fulfillment tracking. "
    "**Bass Pro Shops** contributes its regional store network, seasonal product categories, and climate zones. "
    "**Joined together**, this enables seasonal demand planning by region and category. "
    "**Snowflake ML** adds supplier reliability scoring to flag at-risk orders during peak seasons."
)

# ── KPIs ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Key Metrics")
st.markdown("SPS shipment data joined with Bass Pro's PO and receipt data — overall delivery performance.")

kpi = session.sql("""
    SELECT
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS OTIF_PCT,
        COUNT(DISTINCT po.PO_ID) AS TOTAL_POS,
        SUM(sh.TOTAL_UNITS) AS TOTAL_SHIPPED,
        ROUND(AVG(rcp.DAYS_LATE), 1) AS AVG_DAYS_LATE
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
    LEFT JOIN SPS_RETAIL_AI.SHARED.SHIPMENT sh ON po.PO_ID = sh.PO_ID
    LEFT JOIN SPS_RETAIL_AI.SHARED.RECEIPT rcp ON sh.SHIPMENT_ID = rcp.SHIPMENT_ID
    WHERE po.RETAILER_ID = 'BP'
""").to_pandas()

if not kpi.empty:
    r = kpi.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OTIF Rate", f"{r['OTIF_PCT']}%")
    c2.metric("Total POs", f"{int(r['TOTAL_POS']):,}")
    shipped = int(r["TOTAL_SHIPPED"]) if pd.notna(r["TOTAL_SHIPPED"]) else 0
    c3.metric("Units Shipped", f"{shipped:,}")
    c4.metric("Avg Days Late", f"{r['AVG_DAYS_LATE']}")

# ── Seasonal Demand by Category ──────────────────────────────
st.markdown("---")
st.subheader("Seasonal Demand by Product Category")
st.markdown(
    "SPS weekly activity data (sales velocity) cross-referenced with Bass Pro's seasonal product classification. "
    "Darker cells = higher demand. Inventory must be positioned before peak seasons or sales are lost."
)

seasonal_df = session.sql("""
    SELECT
        CATEGORY_NAME AS CATEGORY,
        SEASON,
        ROUND(AVG(NET_SALES_UNITS), 1) AS AVG_WEEKLY_SALES
    FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY
    WHERE RETAILER_ID = 'BP' AND SEASON IS NOT NULL
    GROUP BY 1, 2
""").to_pandas()

if not seasonal_df.empty:
    season_order = ["Spring", "Summer", "Fall", "Winter"]
    seasonal_df["SEASON"] = pd.Categorical(seasonal_df["SEASON"],
                                            categories=[s for s in season_order if s in seasonal_df["SEASON"].values],
                                            ordered=True)
    heat = (
        alt.Chart(seasonal_df)
        .mark_rect()
        .encode(
            x=alt.X("SEASON:O", title="Season", sort=season_order),
            y=alt.Y("CATEGORY:N", title="Category"),
            color=alt.Color("AVG_WEEKLY_SALES:Q", title="Avg Weekly Sales",
                            scale=alt.Scale(scheme="orangered")),
            tooltip=["CATEGORY", "SEASON", "AVG_WEEKLY_SALES"],
        )
        .properties(height=250)
    )
    text = heat.mark_text(baseline="middle").encode(
        text=alt.Text("AVG_WEEKLY_SALES:Q", format=".1f"),
        color=alt.condition(alt.datum.AVG_WEEKLY_SALES > 10,
                            alt.value("white"), alt.value("black")),
    )
    st.altair_chart(heat + text, use_container_width=True)

# ── Regional Sales ───────────────────────────────────────────
st.markdown("---")
st.subheader("Regional Sales Patterns")
st.markdown(
    "SPS activity data joined with Bass Pro's store-region dimension. "
    "Different regions peak at different times — useful for planning inventory transfers between DCs and stores."
)

region_df = session.sql("""
    SELECT
        v.STORE_REGION AS REGION,
        v.SEASON,
        SUM(v.NET_SALES_UNITS) AS TOTAL_SALES
    FROM SPS_RETAIL_AI.BASS_PRO.V_WEEKLY_ACTIVITY v
    WHERE v.STORE_REGION IS NOT NULL AND v.SEASON IS NOT NULL
    GROUP BY 1, 2
    ORDER BY TOTAL_SALES DESC
""").to_pandas()

if not region_df.empty:
    reg_chart = (
        alt.Chart(region_df)
        .mark_bar()
        .encode(
            x=alt.X("SEASON:N", title="Season"),
            y=alt.Y("TOTAL_SALES:Q", title="Total Units Sold"),
            color=alt.Color("SEASON:N", title="Season"),
            column=alt.Column("REGION:N", title="Store Region"),
            tooltip=["REGION", "SEASON", "TOTAL_SALES"],
        )
        .properties(width=120, height=340)
    )
    st.altair_chart(reg_chart)

# ── Supplier Reliability ─────────────────────────────────────
st.markdown("---")
st.subheader("Supplier Reliability by Category")
st.markdown(
    "SPS shipment OTIF data joined with product category from the item catalog. "
    "An unreliable supplier during peak season has outsized impact — the 80% line marks industry target."
)

sup_cat_df = session.sql("""
    SELECT
        s.SUPPLIER_NAME,
        a.CATEGORY_NAME AS CATEGORY,
        ROUND(AVG(CASE WHEN sh.ON_TIME_FLAG AND sh.IN_FULL_FLAG THEN 1 ELSE 0 END)*100, 1) AS OTIF_PCT,
        COUNT(DISTINCT po.PO_ID) AS PO_COUNT
    FROM SPS_RETAIL_AI.SHARED.PURCHASE_ORDER po
    JOIN SPS_RETAIL_AI.SHARED.PO_LINE pl ON po.PO_ID = pl.PO_ID
    JOIN SPS_RETAIL_AI.SHARED.ITEM i ON pl.ITEM_ID = i.ITEM_ID
    JOIN SPS_RETAIL_AI.SHARED.SPS_ACTIVITY a ON i.ITEM_ID = a.ITEM_ID AND a.RETAILER_ID = 'BP'
    JOIN SPS_RETAIL_AI.SHARED.SUPPLIER s ON po.SUPPLIER_ID = s.SUPPLIER_ID
    JOIN SPS_RETAIL_AI.SHARED.SHIPMENT sh ON po.PO_ID = sh.PO_ID
    WHERE po.RETAILER_ID = 'BP'
    GROUP BY 1, 2
    HAVING COUNT(DISTINCT po.PO_ID) >= 3
""").to_pandas()

if not sup_cat_df.empty:
    sc = (
        alt.Chart(sup_cat_df)
        .mark_circle()
        .encode(
            x=alt.X("OTIF_PCT:Q", title="OTIF Rate (%)", scale=alt.Scale(domain=[50, 100])),
            y=alt.Y("CATEGORY:N", title="Product Category"),
            size=alt.Size("PO_COUNT:Q", title="Order Volume"),
            color=alt.Color("SUPPLIER_NAME:N", title="Supplier"),
            tooltip=["SUPPLIER_NAME", "CATEGORY", "OTIF_PCT", "PO_COUNT"],
        )
        .properties(height=350)
    )
    rule = alt.Chart(pd.DataFrame({"x": [80]})).mark_rule(strokeDash=[4, 4], color="grey").encode(x="x:Q")
    st.altair_chart(sc + rule, use_container_width=True)

# ── Weeks of Supply ──────────────────────────────────────────
st.markdown("---")
st.subheader("Weeks of Supply by Category")
st.markdown(
    "SPS inventory data divided by SPS sell-through rate, per category. "
    "Below 4 weeks = **stockout risk**. Above 12 weeks = **overstock**. "
    "Formula: Current Inventory / Weekly Sales Rate."
)

wos_df = session.sql("""
    SELECT
        CATEGORY_NAME AS CATEGORY,
        SUM(INVENTORY_UNITS) AS TOTAL_INVENTORY,
        ROUND(AVG(NET_SALES_UNITS), 1) AS AVG_WEEKLY_SALES,
        CASE WHEN AVG(NET_SALES_UNITS) > 0
            THEN ROUND(SUM(INVENTORY_UNITS)::FLOAT / (AVG(NET_SALES_UNITS) * COUNT(DISTINCT LOCATION_ID)), 1)
            ELSE NULL END AS WEEKS_OF_SUPPLY
    FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY
    WHERE RETAILER_ID = 'BP'
      AND PERIOD_ENDING_DATE = (SELECT MAX(PERIOD_ENDING_DATE)
                                FROM SPS_RETAIL_AI.SHARED.SPS_ACTIVITY WHERE RETAILER_ID = 'BP')
    GROUP BY 1 ORDER BY WEEKS_OF_SUPPLY
""").to_pandas()

if not wos_df.empty:
    wos_df["STATUS"] = wos_df["WEEKS_OF_SUPPLY"].apply(
        lambda w: "Stockout Risk" if w is not None and w < 4 else ("Overstock Risk" if w is not None and w > 12 else "Healthy"))
    wos_chart = (
        alt.Chart(wos_df)
        .mark_bar()
        .encode(
            x=alt.X("CATEGORY:N", title="Product Category"),
            y=alt.Y("WEEKS_OF_SUPPLY:Q", title="Weeks of Supply"),
            color=alt.Color("STATUS:N", title="Status",
                            scale=alt.Scale(domain=["Stockout Risk", "Healthy", "Overstock Risk"],
                                            range=["#e74c3c", "#27ae60", "#f39c12"])),
            tooltip=["CATEGORY", "WEEKS_OF_SUPPLY", "TOTAL_INVENTORY", "AVG_WEEKLY_SALES", "STATUS"],
        )
        .properties(height=350)
    )
    rule_low = alt.Chart(pd.DataFrame({"y": [4]})).mark_rule(strokeDash=[4, 4], color="#e74c3c").encode(y="y:Q")
    rule_high = alt.Chart(pd.DataFrame({"y": [12]})).mark_rule(strokeDash=[4, 4], color="#f39c12").encode(y="y:Q")
    st.altair_chart(wos_chart + rule_low + rule_high, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Data sources:** SPS Commerce (weekly activity, EDI 850/856) + Bass Pro Shops (stores, regions, categories, climate) + Snowflake ML.  |  "
    "**WOS** = Weeks of Supply. **OTIF** = On-Time, In-Full. "
    "**Pre-positioning** = Moving inventory to stores before the selling season."
)
