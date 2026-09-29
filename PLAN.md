# SPS Retail Fulfillment Intelligence: project plan

Date: 2026-09-25. Updated same day after Marketplace share inspection. Implementation NOT started.

Project folder: `SPSCommerce/sps_footlocker_basspro_urbanoutfitters`.

**Demo account:** `sfsenorthamerica-demo_vsuru` via connection `coco_conn`.
**SPS Marketplace share:** database `SALES_AND_INVENTORY_DATA_FOR_RETAIL_BUSINESS_INTELLIGENCE` (schema `PUBLIC`).

### Live Marketplace data assessment (2026-09-25)

The shared database contains four views matching the public listing: `ACTIVITY` (42 cols), `ITEM` (57 cols), `LOCATION` (34 cols), `RETAILER_METADATA` (2 cols). All are views over a secure share. Key findings from direct inspection:

**Volume:** 720 ACTIVITY rows, 12 generic retailer labels (Shoe Retailer, Outdoor Retailer, Sports Retailer, etc.), 86 items per retailer (identical catalog), 13 total locations (mostly 1 per retailer), 6 weekly periods (2024-04-06 through 2024-05-11). All inserted on a single day (2024-05-08). This is a **demonstration sample**, not production-scale data.

**RETAILER_METADATA** reveals all 12 retailers use `WEEKLY` activity grain — confirming the research finding that daily refresh does not mean daily POS.

**ITEM dimension (57 cols):** Rich product hierarchy: CATEGORY → PRODUCT_GROUP → GENDER → STYLE → COLOR → SIZE, plus UPC, SKU, MSRP, COST, VENDOR_CODE/NAME, VENDOR_STYLE_NUMBER, REPLENISHMENT/MARKDOWN indicators, FIRST/LAST_RECEIPT_DATE, PRODUCT_SEASON, AGE, UNIT_OF_MEASURE, FEDAS_CODE, SPS_ITEM_STATUS. However, many enrichment fields (VENDOR_NAME, VENDOR_CODE, VENDOR_STYLE_NUMBER, REPLENISHMENT_INDICATOR, MARKDOWN_INDICATOR, FIRST/LAST_RECEIPT_DATE, PRODUCT_SEASON, BRAND_NAME, DIVISION fields, DEPARTMENT hierarchy) are entirely NULL in this sample.

**LOCATION dimension (34 cols):** STORE_NUMBER, STORE_NAME, ADDRESS, CITY, STATE, POSTAL_CODE, LAT/LONG, SPS_LOCATION_TYPE (STORE/INTERNET), SPS_COUNTRY, OPEN/CLOSE_DATE, MALL, STORE_RANK, STORE_CLASSIFICATION, LOCATION_TYPE, DEMOGRAPHIC, REGION, CLIMATE, COMP_STORE_INDICATOR, STORE_SIZE, RETAILER_DIVISION, BANNER, GLN, CURRENCY_CODE. Most enrichment fields are NULL; one location per retailer (except Department Store with 2). Retailer labels are generic.

**ACTIVITY population:** NET_SALES_UNITS, NET_SALES_RETAIL, INVENTORY_UNITS, ON_ORDER_UNITS, RECEIPT_UNITS, IN_TRANSIT_UNITS, and CORPORATE_UNIT costs are populated. GROSS_SALES, CUSTOMER_RETURN, RETURN_TO_VENDOR, INVENTORY_ADJUSTMENT, and MARKDOWN fields are entirely NULL across all 720 rows. Sales and inventory grow in perfectly linear increments (10 units per period), indicating synthetic/demonstration data.

**Assessment:** This share is valuable as **schema evidence and a structural template**, but cannot power production-quality ML demos at its current scale (720 rows, 6 periods, identical catalog across retailers, linear patterns, sparse dimensions). We should:

1. **Use the live share as our authoritative schema reference** — all 57 ITEM columns, 34 LOCATION columns, and the RETAILER_METADATA grain field are now verified, replacing the incomplete public-preview inference.
2. **Generate synthetic data that matches this verified schema** — our simulator output tables should be joinable with these exact column names and types.
3. **Generate at realistic scale** — our proposed 24 months, 90 stores, 1,500 SKUs, 60K POs fills the gap between this thin sample and a credible demo.
4. **Populate the NULL-but-schema-present fields** — VENDOR, BRAND, DEPARTMENT hierarchy, SEASON, MARKDOWN, RETURN, RTV, and ADJUSTMENT fields are all defined; we generate plausible values.
5. **Keep the live share mounted** — for structural validation, join-pattern testing, and showing a "real SPS data" tab alongside our enriched synthetic data.

## 1. Recommended outcome

Build one Snowflake-native data and ML foundation with five Streamlit in Snowflake (SiS) demo experiences:

1. SPS Fulfillment Intelligence: order-to-cash operational risk across the synthetic portfolio.
2. SPS Partner Value Lab: normalized multi-retailer comparisons and measured incremental value of adding SPS signals.
3. SPS + Foot Locker: footwear launch and size-level fulfillment readiness.
4. SPS + Bass Pro Shops: seasonal availability and supply-aware inventory planning.
5. SPS + Urban Outfitters: replacement-PO and SKU readiness, connected to fashion-window exposure.

These should be decision applications, not five copies of a KPI dashboard. Every experience follows: **what is at risk -> what evidence explains it -> what actions are feasible -> what the simulated tradeoff is -> who reviews it**.

Recommendation: five separately launchable SiS apps with shared query/model/UI modules and retailer configuration. Separate retailer entry points keep demos focused; shared code prevents drift. The two SPS-wide experiences can be combined into one two-page app if four deployments are preferable. No deployment choice has been applied yet.

## 2. Research findings that change the design

- SPS's public Marketplace listing documents sales/inventory, with ACTIVITY, ITEM, LOCATION and RETAILER_METADATA. It is not a verified raw EDI feed. Keep EDI and analytics source families distinct. [Research S16]
- Actual public schema evidence includes 42 ACTIVITY columns, API v5 file/history metadata and label sample fields. Complete retailer RSX/X12 maps and full dimensional schemas remain outstanding. [S07-S16, S24-S25]
- Daily refresh does not establish daily observation grain. Public period-ending samples include weekly-spaced dates. Preserve source cadence rather than silently treating all reports as daily POS. [S16]
- URBN explicitly documents SPS as its EDI partner, replacement 850s instead of 860s, proprietary short-SKU crosswalks and pre-ship PO acceptance. This is the strongest verified retailer-specific workflow for a first implementation. [S28]
- Bass Pro's SPS page verifies supplier connectivity support, not unrestricted access to Bass Pro data. Foot Locker's direct SPS relationship was not established. Label all three datasets and business outcomes synthetic. [S19-S20]
- Retail receipts, inventory availability, promotional/launch calendars, capacity and AP/AR events are necessary extensions. EDI alone cannot establish actual delivery, consumer demand, profit impact or payment settlement.
- E-invoicing commercial reconciliation belongs in the shared story. Country-specific tax clearance/compliance should be a later, separately sourced module, not inferred from X12 810s. [S04]

See `RESEARCH.md` for sources and limitations; `DATA_AND_ML_CONTRACTS.md` for proposed field-level entities, relationships, simulation, models and metrics.

## 3. Demo experiences

### A. SPS Fulfillment Intelligence

**Audience:** SPS solution leadership, supplier operations, retail supply-chain leaders.

**Hero question:** Which commitments are most likely to fail, how early can we know, and what should be reviewed first?

**Views:**

- Overview: due-line OTIF, unit fill rate, active exposure, ASN mismatch and invoice exceptions, with denominators and as-of time.
- Order-to-cash journey: 850 -> applicable acknowledgment/acceptance -> 856/package -> actual receipt -> 810 -> financial event. Transport receipt is shown separately from physical receipt.
- Risk workbench: calibrated shortfall probability, supplier/lane drivers, days remaining, linked source documents and data freshness.
- Invoice reconciliation: exact quantity/price/receipt differences; optional phase-2 ML ranking of unresolved disputes.
- Review queue: propose expedite, supplier follow-up, correction or transfer; actions remain simulated and reviewable.

**ML:** M1 fulfillment risk; phase-2 M4 invoice escalation. Rules handle exact mismatches.

**Demo moment:** a seemingly healthy order shows latent receipt risk from changed commitments and lane congestion; inspect the evidence and simulate a bounded intervention.

### B. SPS Partner Value Lab

**Audience:** SPS executives, partner teams and technical buyers evaluating the combined solution.

**Hero question:** What does combining SPS signals with retailer data add beyond retailer data alone?

**Views:**

- Side-by-side matched test results: rules vs retailer-only ML vs retailer-plus-SPS ML.
- Retailer comparisons normalized by period, service type, category and coverage, not raw revenue leaderboards.
- Risk concentration and performance by supplier archetype, geography and category.
- Intervention simulator: allocate a fixed review/expedite budget; show tradeoff curves and sensitivity.
- Model/data confidence: baseline, calibration, forecast interval coverage, unknown mappings, source age and drift.

**ML:** reuse M1-M3; no separate vanity model solely for this dashboard.

**Demo moment:** enable SPS leading indicators and see the actually measured synthetic holdout delta. If there is no improvement, show it honestly and investigate; do not prefill an uplift percentage.

**Boundary:** cross-retailer views contain synthetic data only. Any later real-data version needs explicit rights and reviewed aggregation rules.

### C. SPS + Foot Locker: Launch & Size Readiness

**Audience:** footwear merchandising, allocation and inbound operations.

**Hero question:** Will the right style/color/size mix arrive before a launch window?

**Views:** launch calendar; size/store availability heatmap; inbound commitment timeline; store/DC transfer candidates; constrained expedite comparison.

**Inputs:** proposed 850/856/810 normalized chain, receipts, style/color/size catalog, launch calendar, sales/availability, margin and transfer constraints. Optional acknowledgment/change maps only after confirming the current program.

**ML:** M1 fulfillment risk plus M2 forecast/availability. Size-curve and launch features are retailer extensions.

**Demo moment:** aggregate inventory appears adequate, but key sizes at selected stores are exposed. The app prioritizes the actionable gap instead of treating every missing unit equally.

**Scope caution:** this is a footwear scenario, not a claim about actual Foot Locker launches, supplier performance or SPS contract status.

### D. SPS + Bass Pro: Seasonal Availability

**Audience:** outdoor-category planners, replenishment and distribution teams.

**Hero question:** Where should inventory be positioned when regional demand and inbound reliability change together?

**Views:** region/category seasonality; 7/14/28-day demand intervals; days-of-supply bands; supplier/lane reliability; capacity-constrained transfer/replenishment plan.

**Inputs:** proposed order/ASN/invoice chain, applicable 852 activity or separately identified analytics feed, inventory, geography, synthetic seasonal calendar, lead times and volume/capacity measures.

**ML:** M2 forecasts and availability, informed by M1 supply risk.

**Demo moment:** a fictional regional demand surge creates a choice between expedite and transfer, but a bulky-item constraint changes which plan is feasible.

**Scope caution:** non-regulated categories initially; no exact hunting-rule/weather feed dependency. Cabela's is an optional extension rather than part of the initial commitment.

### E. SPS + Urban Outfitters: PO & Launch Readiness

**Audience:** domestic vendor operations, buying operations and assortment teams.

**Hero question:** Which replacement orders and SKU inconsistencies put the next delivery window at risk?

**Views:** original-versus-replacement 850 diff; effective-dated short-SKU crosswalk; Tradestone acceptance timeline; carton-to-ASN check; readiness risk queue; optional sell-through/markdown exposure overlay.

**Inputs:** versioned 850s, 856/810, synthetic Tradestone events, short-SKU/vendor-SKU mapping, labels/packages, receipts, launch/exit calendar and sales/inventory.

**ML:** M3 future readiness risk; M1 downstream shortfall; M2 margin-window context after the first slice.

**Demo moment:** identify an exact replacement-PO difference using rules, then use ML to rank its likely operational consequences before the ship deadline.

**Scope caution:** Urban Outfitters brand, US domestic vendor workflow. Do not expand silently to all URBN brands or import programs.

## 4. All-Snowflake architecture

```text
Synthetic source generation inside Snowflake
  |-- SPS EDI/RSX-shaped canonical fixtures + transport history
  |-- SPS ACTIVITY-compatible sales/inventory observations
  `-- Retailer product, receipt, calendar, capacity and finance extensions
           |
     RAW: immutable payloads, source versions, availability timestamps
           |
     CORE: typed entities, identifier/UOM mappings, PO versions,
           package hierarchy, receipts, invoice reconciliation
           |
     FEATURES: point-in-time feature snapshots + mature outcome labels
           |
     Snowflake ML Jobs (CPU Container Runtime)
       training / evaluation / optional constrained policy simulation
           |
     Snowflake Model Registry -> warehouse batch scoring where compatible
           |
     MARTS: predictions, explanations, KPI aggregates, action scenarios
           |
     Five SiS entry points sharing modules and retailer-specific configuration
```

- Local IDE is used for source editing and submitting work, not local data training.
- Training and data generation run on Snowflake compute. Pin package/runtime versions after environment capability checks.
- Use Snowflake ML Jobs for custom training, Snowpark/SQL for transformations and Model Registry for versioned models. Keep model artifacts/data in Snowflake.
- Batch scoring is sufficient for this demo. Persist scores and explanations; SiS reads small filtered/aggregated results rather than retraining on reruns.
- Recommended SiS container runtime, subject to target-account support. Query workloads use a warehouse; ML training uses a separate CPU compute pool. No GPU or external inference service is required initially.
- Scheduled refresh/scoring can use Snowflake Tasks after the pipeline is proven; source cadence and score age are visible. No scheduler is created during planning.
- Use native Streamlit/Plotly controls with clear selection, empty, stale, loading and error states. Avoid external CDN assets or third-party telemetry requirements.
- Retailer separation must be enforced in database access and tested, not only a UI filter. Deployment roles and data access design are a later approval gate.
- No need for an LLM/chat layer in v1. Add evidence-grounded narration only if it improves the demo and is explicitly approved as an additional Snowflake AI feature.
- Rule-based checks, constrained optimization and ML predictions must be visibly distinguished. Optimization chooses among feasible actions; prediction alone does not identify the best intervention.

The connected Snowhouse context is not assumed to be the deployment account. Account, database, schemas, warehouses, compute pool, roles and execution permissions must be confirmed before any implementation creates objects.

## 5. Phased delivery and gates

Effort ranges below are planning estimates for one focused implementer with prompt review and a ready Snowflake environment; not calendar commitments.

| Phase | Deliverable | Exit gate | Indicative effort |
|---|---|---|---|
| 0: Research and design | This plan, evidence register, public schema capture, proposed contracts | Agree scope and first retailer; document remaining source gaps | Current phase |
| 1: Data foundation | Canonical schema, deterministic simulator, 2,000-PO smoke dataset, source adapters and quality tests | Referential/accounting checks pass; intentional errors quarantined; no label leakage | 3-5 days |
| 2: First vertical slice | Urban Outfitters 850 revision/short-SKU/acceptance workbench + M1/M3 risk and linked receipts | Trace one complete exception; compare rule baseline; show synthetic labeling and source lineage | 3-5 days |
| 3: Forecast and retail adaptation | M2 forecast; Foot Locker launch/size app and Bass Pro seasonal app | Native-cadence evaluation; different workflows; feasible action simulation | 4-6 days |
| 4: Portfolio intelligence | SPS operations app, Value Lab, controlled ablation and optional M4 | Comparable cohorts; no double-counted impact; honest holdout results | 3-5 days |
| 5: Hardening and storytelling | Five deployed apps, access checks, test report, reproducible reset and five-minute demo scripts | Performance/access acceptance; versioned artifacts; no external-data dependency | 2-4 days |

Provisional implementation effort: 15-25 focused working days after design approval. Time can shrink with reused components or expand with live API/data access, current implementation-guide validation, additional retailer brands or compliance scope.

Recommended sequence: **prove the shared foundation through Urban Outfitters first**, then extend to Foot Locker and Bass Pro, then assemble the portfolio comparisons from tested components. If the immediate sales audience is footwear, Foot Locker can be the first slice, but its current EDI map needs more validation.

## 6. What will make this stronger

1. **Show added information value, not just AI labels.** Run retailer-only versus retailer-plus-SPS comparisons on the same held-out population.
2. **Make SPS visible in every decision.** Trace a prediction to the contributing 850/855/856 or analytics observation, alongside retailer extension fields.
3. **Three genuinely different retailer stories.** Size/launch, seasonal/capacity, and PO-revision/SKU readiness are distinct operational problems.
4. **Use consistent synthetic business histories.** Generate linked orders, shipments, receipts, invoices and stock movements from a simulator rather than unrelated random rows.
5. **Make action constraints tangible.** Compare feasible transfers/expedites with capacity, lead time and contribution-margin assumptions; retain human review.
6. **Put trust in the main experience.** Show source freshness, model confidence, known data gaps and why a recommendation was withheld.
7. **Use precise value language.** Estimated contribution-margin protection, invoice mismatch exposure and observed OTIF are different measures; no invented savings claims.
8. **Design a live-data replacement path without making it a dependency.** Source adapters and crosswalks can later consume entitled SPS data while demos stay reproducible offline from SPS APIs.
9. **Keep tax e-invoicing and extra brands out of v1.** They add legal and data-contract complexity without strengthening the initial fulfillment proof.
10. **Do not confuse a model with a rule.** PO diffs, matching and known document requirements are deterministic. Predict uncertainty and prioritize attention where ML adds value.

## 7. Acceptance criteria

- Three independently launchable retailer-specific demos and two SPS-wide experiences, with shared tested definitions.
- All generation, training, scoring and serving inside Snowflake; no external model/API dependency for demo playback.
- Every prediction has as-of time, model/feature version, source lineage and a meaningful uncertainty or abstention state.
- Temporal holdout results and baseline comparisons published; no hard-coded favorable accuracy or business outcome.
- Valid fixtures reconcile across PO/ASN/package/receipt/invoice/inventory; invalid fixtures are intentionally labeled and caught.
- No claim that synthetic data is actual retailer data, or that the project has verified every retailer relationship/schema.
- No cross-retailer leakage through queries, caches or app state. Provider views use explicitly synthetic portfolio data.
- Provisional UI goal: common interactions under 3 seconds after warmup on the agreed demo size; cold start measured separately, not hidden. Final threshold depends on chosen runtime and warehouse.
- Reproducible dataset/model version plus a controlled demo reset; real-world model utility is not claimed from synthetic validation.

## 8. Review decisions and deferred approvals

Decisions that materially affect the next phase:

- Start with the recommended five experiences and Urban Outfitters vertical slice, or change priority.
- Treat additional retailer inventory, sales, receipts, catalog and finance records as clearly labeled synthetic extensions alongside SPS transaction-shaped data.
- Use the US domestic, USD-first scope; Urban Outfitters brand rather than all URBN; Bass Pro rather than automatically adding Cabela's.

Before any build/deployment: confirm target Snowflake account/database/schema and compute/access resources. Before any live SPS access: obtain approved sandbox credentials, current schemas, data rights and retailer/program maps. Before public co-branding: confirm brand/claim permissions.

## Artifacts from this planning phase

- `PLAN.md`: this proposal, architecture, demo experiences and delivery gates.
- `RESEARCH.md`: sourced product/API/retailer findings, provenance and unresolved gaps.
- `PUBLISHED_ACTIVITY_SCHEMA.csv`: 42 public ACTIVITY columns and types; interpretations explicitly separated.
- `DATA_AND_ML_CONTRACTS.md`: proposed entity grains and fields, relationships, simulator behavior, model cards, KPI definitions and test gates.

No implementation, data generation, model training, deployment, external outreach, git initialization or commit has been performed.
