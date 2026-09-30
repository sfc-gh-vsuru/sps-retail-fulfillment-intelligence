# SPS Retail Fulfillment Intelligence — Demo Talk Track

**Data Join + AI/ML for Retail Supply Chain**

---

## Demo Information

| Field | Value |
|-------|-------|
| **Event** | *(fill in before presenting)* |
| **Presenter** | *(fill in before presenting)* |
| **Duration** | ~30 min full run; each retailer section 5-6 min standalone |
| **Database** | `SPS_RETAIL_AI` on `sfsenorthamerica-demo_vsuru` |
| **Audience** | Retail data leaders, supply chain teams, SPS Commerce partners |

---

## Key Terms

| Term | Definition |
|------|-----------|
| **OTIF** | On-Time, In-Full. The gold-standard delivery metric: did the right quantity arrive by the requested date? Our dataset: 81.7% OTIF overall. |
| **EDI** | Electronic Data Interchange. The standard format for B2B retail transactions (orders, shipments, invoices). SPS Commerce is the EDI network. |
| **PO** | Purchase Order. The retailer's instruction to a supplier: what to ship, where, and when. |
| **ASN** | Advance Ship Notice (EDI 856). The supplier's confirmation of what was shipped and how to receive it. |
| **Replacement 850** | Urban Outfitters' method for revising a PO: cancel the original and issue a new 850 instead of sending an EDI 860 change order. |
| **URBN Short SKU** | Urban Outfitters' internal product identifier, shorter than a standard UPC. Requires a crosswalk table to map to vendor products. |
| **Fill Rate** | Percentage of ordered quantity that was actually shipped. Our PO line fill rate: 98.8%. |
| **Weeks of Supply** | Inventory on hand divided by average weekly sales. Measures how long current stock will last. |
| **Feature Importance** | Which input variables the ML model relies on most to make predictions. Reveals what drives fulfillment risk. |
| **ML Classification** | A Snowflake ML model (`SNOWFLAKE.ML.CLASSIFICATION`) trained to predict a binary outcome: will this order be late or short (1) or not (0)? |

---

## Executive Opening (2 min)

> "SPS Commerce sees the order. The retailer sees the shelf. Neither side alone can predict what will go wrong between them."
>
> "By joining SPS EDI transaction data with retailer operational data inside Snowflake, we create a unified fulfillment picture — and train a machine learning model that predicts delivery problems before they happen."
>
> "Today I'll walk you through what this data join looks like across three very different retailers — Foot Locker, Bass Pro Shops, and Urban Outfitters — show you the AI value that only exists when both sides of the supply chain come together, and close with an executive performance dashboard powered by four Snowflake ML/AI features."

---

## Demo Flow — Recommended Order

| # | Dashboard | Duration | Focus |
|---|-----------|----------|-------|
| 1 | SPS Fulfillment Intelligence | 8 min | The full cross-retailer story |
| 2 | SPS + Foot Locker | 5 min | Size and banner readiness |
| 3 | SPS + Bass Pro Shops | 5 min | Seasonal availability |
| 4 | SPS + Urban Outfitters | 5 min | PO revision and SKU readiness |
| 5 | SPS Partner Value Lab | 4 min | The value proof |
| 6 | SPS Performance Manager | 5 min | Executive KPIs + Snowflake ML/AI showcase |

---

## Dashboard 1: SPS Fulfillment Intelligence (8 min)

### What you see
- Cross-retailer OTIF scorecards (on-time %, in-full %, combined OTIF %)
- Order-to-cash journey timeline (order to ship to delivery to receipt to invoice)
- ML risk predictions with confidence scores
- Supplier performance rankings by reliability tier
- Invoice reconciliation status (paid, pending, disputed, mismatch flags)

### The story to tell

> "This is the unified view that neither SPS nor any single retailer has on their own. We're looking at 10,476 purchase orders across three retailers, tracked from the moment the order was placed through shipment, receipt, and invoice payment."
>
> "Our ML model flags orders at risk of being late or short before they ship. It's 91% accurate, and when it flags something, it's right 99.6% of the time. That's a supplier's early warning system."
>
> "Notice the invoice mismatch rate — these are the disputes that cost both sides time and money. The joined data lets us trace a mismatch all the way back to the PO line to see exactly where the discrepancy started."

### Point out
- The 81.7% overall OTIF rate — realistic, not idealized. 18.3% of orders had a problem.
- The spread between on-time (88.1%) and in-full (92.9%) — lateness is a bigger problem than quantity shorts.
- The supplier reliability tier distribution — Gold/Silver/Bronze is SPS-assigned based on historical performance.

### Data sources

| Dashboard Element | Snowflake Tables/Views |
|-------------------|----------------------|
| OTIF scorecards | `SHARED.SHIPMENT` (`ON_TIME_FLAG`, `IN_FULL_FLAG`) joined with `SHARED.RETAILER` |
| Order-to-cash timeline | `SHARED.V_FULFILLMENT_KPI` (joins PO, Shipment, Receipt, Invoice) |
| ML risk predictions | `ML_MODELS.FULFILLMENT_PREDICTIONS` (model output) |
| Supplier performance | `SHARED.SUPPLIER` (`RELIABILITY_TIER`) joined with `SHARED.SHIPMENT` |
| Invoice reconciliation | `SHARED.INVOICE` (`MISMATCH_FLAG`, `PAYMENT_STATUS`) |

---

## Dashboard 2: SPS + Foot Locker (5 min)

### What you see
- Banner performance comparison (Foot Locker, Champs Sports, Kids Foot Locker, WSS)
- Size availability analysis (which sizes are selling out fastest)
- Weekly sales trend lines by category
- ML risk scores broken down by banner

### The story to tell

> "Foot Locker operates four different banners, and each one has different fulfillment needs. A size 10 Jordan that's late to a flagship Foot Locker store is a very different problem than the same delay to a WSS outlet."
>
> "The SPS data tells us the order shipped late. The Foot Locker data tells us which banner, which store tier, and which size was affected. Together, they tell us the business impact."
>
> "Look at Footwear averaging 9.0 units per week versus Apparel at 4.7. That velocity difference means a late footwear shipment burns through safety stock twice as fast."

### Point out
- The banner split — show how OTIF rates differ across Foot Locker vs. Champs vs. Kids FL vs. WSS
- Size-level sell-through — highlight a specific size (e.g., Men's 10-11) that's selling out fastest
- The 81.1% OTIF rate for Foot Locker specifically — slightly below the cross-retailer average

### Data sources

| Dashboard Element | Snowflake Tables/Views |
|-------------------|----------------------|
| Banner performance | `FOOT_LOCKER.V_PURCHASE_ORDERS` (`BANNER`, `OTIF_FLAG`) |
| Size availability | `FOOT_LOCKER.V_WEEKLY_ACTIVITY` (`SIZE_NAME`, `INVENTORY_UNITS`, `NET_SALES_UNITS`) |
| Sales trend lines | `FOOT_LOCKER.V_WEEKLY_ACTIVITY` (`PERIOD_ENDING_DATE`, `NET_SALES_UNITS`, `CATEGORY_NAME`) |
| ML risk by banner | `ML_MODELS.FULFILLMENT_PREDICTIONS` joined with `SHARED.LOCATION` (`BANNER`) |

---

## Dashboard 3: SPS + Bass Pro Shops (5 min)

### What you see
- Seasonal demand heatmap (category x month, colored by sales volume)
- Regional sales comparison across climate zones
- Supplier reliability scores broken down by product category
- Weeks of supply gauge by region and category

### The story to tell

> "Bass Pro is an outdoor retailer, which means demand is driven by seasons and geography in ways that Foot Locker and Urban Outfitters are not. Hunting gear peaks in fall at Cold and Alpine stores. Fishing peaks in summer at Warm and Temperate locations."
>
> "The SPS data shows us order and shipment timing. Bass Pro's climate-zone and seasonal-category data tells us whether that timing aligns with actual demand. A shipment that arrives on time but after the season peak is on-time by the metric but late by the business."
>
> "Outdoor products average 13.9 units per week — nearly three times Footwear at 4.7. When you're moving that volume through seasonal peaks, even a small OTIF gap compounds into serious out-of-stocks."

### Point out
- The seasonal demand heatmap — show a clear peak (e.g., Outdoor in October-November)
- Weeks of supply differences by climate zone — Alpine stores may need pre-positioning
- Bass Pro's 82.8% OTIF — highest of the three retailers, but still room to improve

### Data sources

| Dashboard Element | Snowflake Tables/Views |
|-------------------|----------------------|
| Seasonal demand heatmap | `BASS_PRO.V_WEEKLY_ACTIVITY` (`CATEGORY_NAME`, `PRODUCT_SEASON`, `NET_SALES_UNITS`, `PERIOD_ENDING_DATE`) |
| Regional sales by climate | `BASS_PRO.V_WEEKLY_ACTIVITY` (`REGION`, `CLIMATE`, `NET_SALES_UNITS`) |
| Supplier reliability by category | `BASS_PRO.V_PURCHASE_ORDERS` (`SUPPLIER_NAME`, `RELIABILITY_TIER`, `CATEGORY_SPECIALTY`, `OTIF_FLAG`) |
| Weeks of supply | `BASS_PRO.V_WEEKLY_ACTIVITY` (`INVENTORY_UNITS`, `NET_SALES_UNITS` — calculated as inventory / avg weekly sales) |

---

## Dashboard 4: SPS + Urban Outfitters (5 min)

### What you see
- Replacement PO tracking (original vs. replacement 850s, with linked PO chains)
- SKU crosswalk health dashboard (ACTIVE, PENDING, EXPIRED, UNMAPPED counts)
- Pre-ship readiness risk score (combining SKU mapping + lead time + supplier history)
- Weekly activity with URBN short SKU identifiers and mapping status

### The story to tell

> "Urban Outfitters doesn't use EDI 860 change orders. When they need to revise a PO, they cancel the original and issue a brand-new replacement 850. This means our order count is inflated, and our ship rate looks lower — 85.3% — because cancelled originals count as unshipped."
>
> "The SPS data sees two separate POs. Urban Outfitters' data links them together through the replacement workflow. Without that join, you'd think fulfillment performance is worse than it actually is."
>
> "Now look at the SKU crosswalk. Urban Outfitters uses an internal short-SKU system. Every product needs a clean mapping to the vendor UPC. An unmapped or expired SKU means the receiving dock can't match the product to the PO, and the shipment stalls — even if it arrived on time."

### Point out
- The replacement PO chain — show an original PO linked to its replacement
- SKU mapping status distribution — highlight the percentage of ACTIVE vs. UNMAPPED
- The 80.8% OTIF rate — lowest of the three, but context matters (replacement PO workflow inflates the denominator)

### Data sources

| Dashboard Element | Snowflake Tables/Views |
|-------------------|----------------------|
| Replacement PO tracking | `URBAN_OUTFITTERS.V_PURCHASE_ORDERS` (`IS_REPLACEMENT_850`, `PO_TYPE_LABEL`, `ORIGINAL_PO_ID`) |
| SKU crosswalk health | `URBAN_OUTFITTERS.SKU_CROSSWALK` (`MAPPING_STATUS`) |
| Pre-ship readiness risk | `ML_MODELS.FULFILLMENT_PREDICTIONS` joined with `URBAN_OUTFITTERS.SKU_CROSSWALK` |
| Weekly activity with SKU | `URBAN_OUTFITTERS.V_WEEKLY_ACTIVITY` (`URBN_SHORT_SKU`, `SKU_MAPPING_STATUS`) |

---

## Dashboard 5: SPS Partner Value Lab (4 min)

### What you see
- Cross-retailer comparison matrix (OTIF, fill rate, avg lead time side by side)
- ML model accuracy breakdown by retailer
- Feature importance chart (which variables drive predictions)
- Data value proposition summary (what each data source contributes to ML accuracy)

### The story to tell

> "This is the proof point. The ML model achieves 91.3% accuracy — but look at where that accuracy comes from. The top features are order value, days to ship, line quantity, total units, and days to deliver. Every one of those comes from the joined dataset. SPS provides the transaction timing. The retailer provides the destination context."
>
> "No single system has all these signals. The EDI network knows the order was placed and shipped. The retailer knows which store, which banner, which climate zone, which season. The ML model needs both to predict what will go wrong."

### Point out
- Feature importance ranking — `TOTAL_COST`, `DAYS_TO_SHIP`, `TOTAL_LINE_QTY`, `TOTAL_UNITS`, `DAYS_TO_DELIVER`, `ORDER_MONTH` are the top drivers
- Cross-retailer accuracy comparison — model performance may vary by retailer based on data completeness
- The 99.6% precision on risk flags — when the model says "at risk," suppliers should act on it

### Data sources

| Dashboard Element | Snowflake Tables/Views |
|-------------------|----------------------|
| Cross-retailer comparison | `SHARED.V_FULFILLMENT_KPI` grouped by `RETAILER_NAME` |
| ML accuracy by retailer | `ML_MODELS.FULFILLMENT_PREDICTIONS` joined with `SHARED.RETAILER` |
| Feature importance | `ML_MODELS.FULFILLMENT_RISK_MODEL` (model metadata / `!EXPLAIN` output) |
| Data value proposition | Derived from feature importance — maps each feature to its source (SPS vs. retailer) |

---

## Dashboard 6: SPS Performance Manager (5 min)

### What you see
- Sales/Margin Impact KPIs: not-received product costs, invoice mismatch costs, delayed sales impact
- Operating Expense Impact KPIs: late receipt costs, early receipt costs, order change costs
- Overall Performance score with letter grade (A/B/C) gauge and 4 KPI cards with month-over-month deltas
- Performance trend chart with ML Forecast (6-month prediction with confidence bands) and Anomaly Detection markers
- ML-predicted fulfillment risk by retailer (from Classification model)
- AI-generated executive summary narrative (Cortex LLM)

### The story to tell

> "This is the executive operations view — modeled after the real SPS Commerce Performance Manager dashboard. But we've added four Snowflake ML and AI capabilities on top."
>
> "First, the ML Forecast predicts where on-time rates are heading over the next six months — the dashed line with the confidence band. Second, Anomaly Detection automatically flags months where performance deviated from the expected pattern — the diamond markers."
>
> "Third, the Classification model from Dashboard 1 scores every PO for risk. And fourth, at the bottom, Cortex AI writes a dynamic executive summary that updates every time you change the retailer or month filter. It's not a template — it's an LLM reading the actual numbers and generating insight."

### Point out
- The dollar-impact KPIs — translate delivery failures into financial terms that executives understand
- The forecast confidence band — shows the range of expected outcomes, not just a single prediction
- The AI summary changing when you switch retailers — demonstrates real-time LLM integration
- Four distinct Snowflake ML/AI features in one dashboard: FORECAST, ANOMALY_DETECTION, CLASSIFICATION, CORTEX.COMPLETE

### Data sources

| Dashboard Element | Snowflake Tables/Views |
|-------------------|----------------------|
| Sales/Margin Impact | `SHARED.V_MONTHLY_PERFORMANCE` (NOT_RECEIVED_COST, MISMATCH_DOLLAR_VALUE, DELAYED_SALES_IMPACT) |
| Operating Expense Impact | `SHARED.V_MONTHLY_PERFORMANCE` (LATE_RECEIPT_COST, EARLY_RECEIPT_COST, ORDER_CHANGE_COST) |
| Overall Score + KPI cards | `SHARED.V_MONTHLY_PERFORMANCE` (OVERALL_SCORE, ON_TIME_RATE, FILL_RATE, etc.) |
| Trend + Forecast | `ML_MODELS.OTIF_FORECAST_MODEL!FORECAST()` + `SHARED.V_MONTHLY_PERFORMANCE` |
| Anomaly Detection | `ML_MODELS.PERFORMANCE_ANOMALY_MODEL!DETECT_ANOMALIES()` |
| ML Risk | `ML_MODELS.FULFILLMENT_PREDICTIONS` |
| AI Summary | `SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', ...)` |

---

## Closing (1 min)

> "The ML model's top features — order value, lead time, supplier history — all come from the joined SPS-plus-retailer dataset. No single system has these signals alone. This is the data join creating AI value."
>
> "SPS Commerce brings the transaction network. Each retailer brings their operational context — banners, climate zones, SKU systems, revision workflows. Snowflake is where these come together, and Snowflake ML turns that joined data into predictions that help suppliers ship smarter."
>
> "The dashboards you saw today are live on the data. Every chart queries the same tables and views the model was trained on. The Performance Manager dashboard alone uses four Snowflake ML/AI capabilities — Forecast, Anomaly Detection, Classification, and Cortex LLM. This isn't a slide deck — it's a working system."

---

## Presenter Notes

**If asked about data volumes:**
- 2.9M weekly activity rows, 10K+ purchase orders, 9.9K shipments — two years of realistic synthetic data modeled on real SPS Commerce schemas.

**If asked about ML model limitations:**
- 52.5% recall means the model catches about half of actual failures. It's tuned for precision (don't cry wolf) over recall (catch everything). In production, you'd tune this threshold based on the cost of false alarms vs. missed flags.

**If asked about real vs. synthetic data:**
- The table schemas match real SPS Commerce Marketplace shares. The data is synthetic but modeled on realistic distributions, seasonal patterns, and failure rates. The 18.3% failure rate and OTIF breakdown are calibrated to industry benchmarks.

**If running a short version (10-15 min):**
- Open with Dashboard 1 (SPS Fulfillment Intelligence) for the full story
- Pick ONE retailer dashboard to show the data-join depth
- Close with Dashboard 6 (Performance Manager) for the ML/AI showcase

**If running a single-retailer spotlight (5-6 min):**
- Go directly to the retailer dashboard
- Spend 1 min on what makes that retailer's data unique (banner/climate/SKU)
- Spend 2 min on the dashboard charts
- Spend 2 min on the ML predictions for that retailer
