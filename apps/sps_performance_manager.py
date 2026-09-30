import streamlit as st
import altair as alt
import pandas as pd
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.set_page_config(layout="wide")

# ─── Header ─────────────────────────────────────────────────────────────────
st.title("SPS Performance Manager")
st.caption("Powered by Snowflake ML Forecast, Anomaly Detection, Classification, and Cortex AI")

# ─── Filters ────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
retailers = session.sql(
    "SELECT DISTINCT RETAILER_NAME FROM SPS_RETAIL_AI.SHARED.V_MONTHLY_PERFORMANCE ORDER BY RETAILER_NAME"
).to_pandas()["RETAILER_NAME"].tolist()
with col_f1:
    selected_retailer = st.selectbox("Retailer", ["All Retailers"] + retailers)
with col_f2:
    months_df = session.sql(
        "SELECT DISTINCT MONTH_DATE FROM SPS_RETAIL_AI.SHARED.V_MONTHLY_PERFORMANCE WHERE MONTH_DATE < '2024-08-01' ORDER BY MONTH_DATE DESC"
    ).to_pandas()
    months_df["MONTH_DATE"] = pd.to_datetime(months_df["MONTH_DATE"])
    month_options = months_df["MONTH_DATE"].dt.strftime("%B %Y").tolist()
    selected_month_label = st.selectbox("Month", month_options)

# Parse selection
selected_month_date = months_df.iloc[month_options.index(selected_month_label)]["MONTH_DATE"]
month_str = selected_month_date.strftime("%Y-%m-%d")

retailer_filter = ""
if selected_retailer != "All Retailers":
    retailer_filter = f"AND RETAILER_NAME = '{selected_retailer}'"

# ─── Current & Previous Month Data ─────────────────────────────────────────
current = session.sql(f"""
    SELECT
        ROUND(AVG(ON_TIME_RATE), 1) AS ON_TIME_RATE,
        ROUND(AVG(FILL_RATE), 1) AS FILL_RATE,
        ROUND(AVG(ORDER_ACK_RATE), 1) AS ORDER_ACK_RATE,
        ROUND(AVG(SHIPMENT_RATE), 1) AS SHIPMENT_RATE,
        ROUND(AVG(OVERALL_SCORE), 1) AS OVERALL_SCORE,
        SUM(NOT_RECEIVED_COST) AS NOT_RECEIVED_COST,
        SUM(LATE_RECEIPT_COST) AS LATE_RECEIPT_COST,
        SUM(EARLY_RECEIPT_COST) AS EARLY_RECEIPT_COST,
        SUM(ORDER_CHANGE_COST) AS ORDER_CHANGE_COST,
        SUM(UNACKNOWLEDGED_COST) AS UNACKNOWLEDGED_COST,
        SUM(DELAYED_SALES_IMPACT) AS DELAYED_SALES_IMPACT,
        SUM(MISMATCH_DOLLAR_VALUE) AS MISMATCH_DOLLAR_VALUE,
        ROUND(AVG(ON_TIME_DELTA), 1) AS ON_TIME_DELTA,
        ROUND(AVG(FILL_RATE_DELTA), 1) AS FILL_RATE_DELTA,
        ROUND(AVG(ACK_RATE_DELTA), 1) AS ACK_RATE_DELTA,
        ROUND(AVG(SHIPMENT_RATE_DELTA), 1) AS SHIPMENT_RATE_DELTA
    FROM SPS_RETAIL_AI.SHARED.V_MONTHLY_PERFORMANCE
    WHERE MONTH_DATE = '{month_str}' {retailer_filter}
""").to_pandas()

if current.empty or current["ON_TIME_RATE"].iloc[0] is None:
    st.warning("No data for selected month/retailer.")
    st.stop()

c = current.iloc[0]

# ─── Helper: Letter Grade ──────────────────────────────────────────────────
def letter_grade(score):
    if score >= 95: return "A+"
    if score >= 90: return "A"
    if score >= 85: return "B+"
    if score >= 80: return "B"
    if score >= 75: return "C+"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"

def delta_str(val):
    if val is None or pd.isna(val):
        return ""
    direction = "increase" if val > 0 else "decrease"
    return f"{'▲' if val > 0 else '▼'} {abs(val)}% {direction}"

def delta_color(val):
    if val is None or pd.isna(val) or val == 0:
        return "off"
    return "normal" if val > 0 else "inverse"

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Section 1: Sales/Margin Impact & Operating Expense Impact
# ═══════════════════════════════════════════════════════════════════════════
col_s, col_o = st.columns(2)

with col_s:
    st.subheader("Sales / Margin Impact")
    s1, s2, s3 = st.columns(3)
    s1.metric("Not-Received Product Costs", f"${c['NOT_RECEIVED_COST']:,.0f}")
    s2.metric("Mismatch Invoice Costs", f"${c['MISMATCH_DOLLAR_VALUE']:,.0f}")
    s3.metric("Delayed Sales Impact (7+ days)", f"${c['DELAYED_SALES_IMPACT']:,.0f}")

with col_o:
    st.subheader("Operating Expense Impact")
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Late Receipt Costs", f"${c['LATE_RECEIPT_COST']:,.0f}")
    o2.metric("Early Receipt Costs", f"${c['EARLY_RECEIPT_COST']:,.0f}")
    o3.metric("Order Change Costs", f"${c['ORDER_CHANGE_COST']:,.0f}")
    o4.metric("Unacknowledged Costs", f"${c['UNACKNOWLEDGED_COST']:,.0f}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Section 2: Overall Performance — Score + 4 KPI Cards
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("Overall Performance")

score = float(c["OVERALL_SCORE"])
grade = letter_grade(score)

col_g, col_k1, col_k2, col_k3, col_k4 = st.columns([1.2, 1, 1, 1, 1])

with col_g:
    # Score gauge using Altair donut
    gauge_val = min(score, 100)
    gauge_data = pd.DataFrame({
        "category": ["Score", "Remaining"],
        "value": [gauge_val, 100 - gauge_val]
    })
    gauge_colors = ["#2E8B57", "#E8E8E8"]
    if score < 70:
        gauge_colors[0] = "#DC3545"
    elif score < 80:
        gauge_colors[0] = "#FFA500"

    donut = alt.Chart(gauge_data).mark_arc(innerRadius=50, outerRadius=75).encode(
        theta=alt.Theta("value:Q", stack=True),
        color=alt.Color("category:N", scale=alt.Scale(range=gauge_colors), legend=None),
        order=alt.Order("category:N", sort="descending")
    ).properties(width=180, height=180)

    text_layer = alt.Chart(pd.DataFrame({"text": [f"{grade}\n{score}%"]})).mark_text(
        size=20, fontWeight="bold", color="#333", lineBreak="\n"
    ).encode(text="text:N")

    st.altair_chart(donut + text_layer, use_container_width=False)

with col_k1:
    st.metric(
        "On-Time in Full Rate",
        f"{c['ON_TIME_RATE']}%",
        delta=delta_str(c["ON_TIME_DELTA"]),
        delta_color=delta_color(c["ON_TIME_DELTA"])
    )
with col_k2:
    st.metric(
        "Fill Rate",
        f"{c['FILL_RATE']}%",
        delta=delta_str(c["FILL_RATE_DELTA"]),
        delta_color=delta_color(c["FILL_RATE_DELTA"])
    )
with col_k3:
    st.metric(
        "Order Acknowledgement Rate",
        f"{c['ORDER_ACK_RATE']}%",
        delta=delta_str(c["ACK_RATE_DELTA"]),
        delta_color=delta_color(c["ACK_RATE_DELTA"])
    )
with col_k4:
    st.metric(
        "Shipment Rate",
        f"{c['SHIPMENT_RATE']}%",
        delta=delta_str(c["SHIPMENT_RATE_DELTA"]),
        delta_color=delta_color(c["SHIPMENT_RATE_DELTA"])
    )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Section 3: Trend Chart — Historical + ML Forecast
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("Performance Trends — Historical + ML Forecast")
st.caption("Forecast generated by SNOWFLAKE.ML.FORECAST | Anomalies detected by SNOWFLAKE.ML.ANOMALY_DETECTION")

# Historical data
hist_df = session.sql(f"""
    SELECT
        MONTH_DATE,
        ROUND(AVG(ON_TIME_RATE), 1) AS ON_TIME_RATE,
        ROUND(AVG(FILL_RATE), 1) AS FILL_RATE,
        ROUND(AVG(SHIPMENT_RATE), 1) AS SHIPMENT_RATE,
        ROUND(AVG(ORDER_ACK_RATE), 1) AS ORDER_ACK_RATE
    FROM SPS_RETAIL_AI.SHARED.V_MONTHLY_PERFORMANCE
    WHERE MONTH_DATE < '2024-08-01' {retailer_filter}
    GROUP BY MONTH_DATE
    ORDER BY MONTH_DATE
""").to_pandas()

# Forecast data (6 months ahead)
try:
    session.sql("CALL SPS_RETAIL_AI.ML_MODELS.OTIF_FORECAST_MODEL!FORECAST(FORECASTING_PERIODS => 6)").collect()
    forecast_df = session.sql("""
        SELECT TS::DATE AS MONTH_DATE, ROUND(FORECAST, 1) AS FORECAST,
               ROUND(LOWER_BOUND, 1) AS LOWER_BOUND, ROUND(UPPER_BOUND, 1) AS UPPER_BOUND
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
    """).to_pandas()
    has_forecast = True
except Exception:
    has_forecast = False
    forecast_df = pd.DataFrame()

# Anomaly data
try:
    session.sql("""
        CALL SPS_RETAIL_AI.ML_MODELS.PERFORMANCE_ANOMALY_MODEL!DETECT_ANOMALIES(
            INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'SPS_RETAIL_AI.ML_MODELS.V_ANOMALY_DETECT'),
            TIMESTAMP_COLNAME => 'DS', TARGET_COLNAME => 'ON_TIME_RATE')
    """).collect()
    anomaly_df = session.sql("""
        SELECT TS::DATE AS MONTH_DATE, Y AS ON_TIME_RATE, IS_ANOMALY, ROUND(DISTANCE, 2) AS DISTANCE
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
    """).to_pandas()
    has_anomaly = True
except Exception:
    has_anomaly = False
    anomaly_df = pd.DataFrame()

# Build trend chart
tab_all, tab_otif, tab_fill, tab_ship = st.tabs(["All Metrics", "On-Time Rate", "Fill Rate", "Shipment Rate"])

with tab_all:
    melted = hist_df.melt(id_vars=["MONTH_DATE"],
                          value_vars=["ON_TIME_RATE", "FILL_RATE", "SHIPMENT_RATE", "ORDER_ACK_RATE"],
                          var_name="Metric", value_name="Rate")
    melted["Metric"] = melted["Metric"].map({
        "ON_TIME_RATE": "On-Time in Full",
        "FILL_RATE": "Fill Rate",
        "SHIPMENT_RATE": "Shipment Rate",
        "ORDER_ACK_RATE": "Order Acknowledgement"
    })
    chart = alt.Chart(melted).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("MONTH_DATE:T", title="Month"),
        y=alt.Y("Rate:Q", title="Rate (%)", scale=alt.Scale(domain=[50, 105])),
        color=alt.Color("Metric:N"),
        tooltip=["MONTH_DATE:T", "Metric:N", "Rate:Q"]
    ).properties(height=400)

    layers = [chart]

    if has_forecast and not forecast_df.empty:
        fc_line = alt.Chart(forecast_df).mark_line(
            strokeDash=[5, 5], strokeWidth=2, color="#FF6B35"
        ).encode(
            x="MONTH_DATE:T",
            y=alt.Y("FORECAST:Q"),
            tooltip=["MONTH_DATE:T", "FORECAST:Q", "LOWER_BOUND:Q", "UPPER_BOUND:Q"]
        )
        fc_band = alt.Chart(forecast_df).mark_area(opacity=0.15, color="#FF6B35").encode(
            x="MONTH_DATE:T",
            y="LOWER_BOUND:Q",
            y2="UPPER_BOUND:Q"
        )
        layers.extend([fc_band, fc_line])

    st.altair_chart(alt.layer(*layers), use_container_width=True)

with tab_otif:
    otif_chart = alt.Chart(hist_df).mark_line(point=True, strokeWidth=2, color="#1B6B3A").encode(
        x=alt.X("MONTH_DATE:T", title="Month"),
        y=alt.Y("ON_TIME_RATE:Q", title="On-Time in Full Rate (%)", scale=alt.Scale(domain=[75, 95])),
        tooltip=["MONTH_DATE:T", "ON_TIME_RATE:Q"]
    ).properties(height=400)
    layers_otif = [otif_chart]
    if has_forecast and not forecast_df.empty:
        fc_line2 = alt.Chart(forecast_df).mark_line(strokeDash=[5,5], strokeWidth=2, color="#FF6B35").encode(
            x="MONTH_DATE:T", y=alt.Y("FORECAST:Q"), tooltip=["MONTH_DATE:T", "FORECAST:Q"]
        )
        fc_band2 = alt.Chart(forecast_df).mark_area(opacity=0.15, color="#FF6B35").encode(
            x="MONTH_DATE:T", y="LOWER_BOUND:Q", y2="UPPER_BOUND:Q"
        )
        layers_otif.extend([fc_band2, fc_line2])
    if has_anomaly and not anomaly_df.empty:
        anom_points = alt.Chart(anomaly_df).mark_point(size=150, shape="diamond", filled=True).encode(
            x="MONTH_DATE:T",
            y=alt.Y("ON_TIME_RATE:Q"),
            color=alt.condition(alt.datum.IS_ANOMALY, alt.value("#DC3545"), alt.value("#2E8B57")),
            tooltip=["MONTH_DATE:T", "ON_TIME_RATE:Q", "IS_ANOMALY:N", "DISTANCE:Q"]
        )
        layers_otif.append(anom_points)
    st.altair_chart(alt.layer(*layers_otif), use_container_width=True)
    if has_anomaly:
        st.caption("🔶 Diamond markers = Anomaly Detection results (red = anomaly, green = normal)")

with tab_fill:
    fill_chart = alt.Chart(hist_df).mark_line(point=True, strokeWidth=2, color="#2563EB").encode(
        x=alt.X("MONTH_DATE:T", title="Month"),
        y=alt.Y("FILL_RATE:Q", title="Fill Rate (%)", scale=alt.Scale(domain=[80, 100])),
        tooltip=["MONTH_DATE:T", "FILL_RATE:Q"]
    ).properties(height=400)
    st.altair_chart(fill_chart, use_container_width=True)

with tab_ship:
    ship_chart = alt.Chart(hist_df).mark_line(point=True, strokeWidth=2, color="#7C3AED").encode(
        x=alt.X("MONTH_DATE:T", title="Month"),
        y=alt.Y("SHIPMENT_RATE:Q", title="Shipment Rate (%)", scale=alt.Scale(domain=[90, 100])),
        tooltip=["MONTH_DATE:T", "SHIPMENT_RATE:Q"]
    ).properties(height=400)
    st.altair_chart(ship_chart, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Section 4: ML Risk from Classification Model
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("ML-Predicted Fulfillment Risk")
st.caption("SNOWFLAKE.ML.CLASSIFICATION model — 91.3% accuracy on 9,919 POs")

risk_where = f"WHERE r.RETAILER_NAME = '{selected_retailer}'" if selected_retailer != "All Retailers" else ""
risk_sql = (
    'SELECT r.RETAILER_NAME, '
    'SUM(CASE WHEN fp.PREDICTION:"class"::INT = 1 THEN 1 ELSE 0 END) AS AT_RISK, '
    'SUM(CASE WHEN fp.PREDICTION:"class"::INT = 0 THEN 1 ELSE 0 END) AS ON_TRACK, '
    'COUNT(*) AS TOTAL, '
    'ROUND(SUM(CASE WHEN fp.PREDICTION:"class"::INT = 1 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100, 1) AS RISK_PCT '
    'FROM SPS_RETAIL_AI.ML_MODELS.FULFILLMENT_PREDICTIONS fp '
    'JOIN SPS_RETAIL_AI.SHARED.RETAILER r ON fp.RETAILER_ID = r.RETAILER_ID '
    f'{risk_where} '
    'GROUP BY r.RETAILER_NAME ORDER BY RISK_PCT DESC'
)
risk_df = session.sql(risk_sql).to_pandas()

rc1, rc2 = st.columns([1, 2])
with rc1:
    st.dataframe(risk_df, use_container_width=True)
with rc2:
    risk_melted = risk_df.melt(id_vars=["RETAILER_NAME"], value_vars=["AT_RISK", "ON_TRACK"],
                                var_name="Status", value_name="Count")
    risk_chart = alt.Chart(risk_melted).mark_bar().encode(
        x=alt.X("RETAILER_NAME:N", title=""),
        y=alt.Y("Count:Q", title="Purchase Orders"),
        color=alt.Color("Status:N", scale=alt.Scale(
            domain=["AT_RISK", "ON_TRACK"],
            range=["#DC3545", "#2E8B57"]
        )),
        tooltip=["RETAILER_NAME:N", "Status:N", "Count:Q"]
    ).properties(height=300)
    st.altair_chart(risk_chart, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Section 5: Cortex AI Executive Summary
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("AI Executive Summary")
st.caption("Generated by Snowflake Cortex LLM (COMPLETE)")

month_label = pd.Timestamp(selected_month_date).strftime("%B %Y")
retailer_context = selected_retailer if selected_retailer != "All Retailers" else "all retailers combined"
on_time_d = f", {c['ON_TIME_DELTA']:+.1f} pts from prior month" if c["ON_TIME_DELTA"] and not pd.isna(c["ON_TIME_DELTA"]) else ""
fill_d = f", {c['FILL_RATE_DELTA']:+.1f} pts from prior month" if c["FILL_RATE_DELTA"] and not pd.isna(c["FILL_RATE_DELTA"]) else ""

prompt = f"""You are a retail supply chain analyst writing for a VP of Operations.
Given these {month_label} performance metrics for {retailer_context}:
- On-Time in Full Rate: {c['ON_TIME_RATE']}%{on_time_d}
- Fill Rate: {c['FILL_RATE']}%{fill_d}
- Shipment Rate: {c['SHIPMENT_RATE']}%
- Order Acknowledgement Rate: {c['ORDER_ACK_RATE']}%
- Overall Score: {c['OVERALL_SCORE']}% (Grade: {grade})
- Not-Received Product Costs: ${c['NOT_RECEIVED_COST']:,.0f}
- Invoice Mismatches: ${c['MISMATCH_DOLLAR_VALUE']:,.0f}
- Late Receipt Penalty Costs: ${c['LATE_RECEIPT_COST']:,.0f}

Write a 3-4 sentence executive summary. Be specific with numbers. Highlight the most important trend or concern. End with one actionable recommendation."""

try:
    ai_summary = session.sql(f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${prompt}$$) AS SUMMARY
    """).to_pandas()["SUMMARY"].iloc[0]
    st.markdown(ai_summary)
except Exception as e:
    st.info(f"AI summary unavailable: {e}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Footer: Snowflake ML/AI Features Used
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("##### Snowflake ML & AI Features Used")
f1, f2, f3, f4 = st.columns(4)
f1.markdown("**ML.CLASSIFICATION**\nFulfillment risk prediction (91.3% accuracy)")
f2.markdown("**ML.FORECAST**\nOn-time rate trend prediction with confidence intervals")
f3.markdown("**ML.ANOMALY_DETECTION**\nUnusual performance month detection")
f4.markdown("**CORTEX.COMPLETE**\nAI-generated executive narrative summary")
