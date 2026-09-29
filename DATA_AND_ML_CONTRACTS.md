# Proposed synthetic data contracts and ML design

Status: design for review, 2026-09-25. No data generated and no SQL deployed.

Every uppercase table and lowercase field name below is OUR PROPOSED CANONICAL SCHEMA, not a claim about an SPS API payload. Published source fields are separately preserved in `RESEARCH.md` and `PUBLISHED_ACTIVITY_SCHEMA.csv`. Source IDs refer to RESEARCH.md.

## 1. Three source families

| Family | Data | Evidence / design boundary |
|---|---|---|
| SPS fulfillment | 850 PO, applicable 855 acknowledgment, 856 ASN, 810 invoice; optional 860/846/852/997 by program; API processing history; label descriptors | Business document families are grounded in SPS/retailer documentation. Complete RSX/X12 schemas and qualifiers are not yet acquired. Generated canonical JSON is demo data, not certified production RSX/X12. |
| SPS sales/inventory | ACTIVITY-compatible observations, product and location mappings | ACTIVITY columns are published. Complete dimension contracts and feed cadence remain unverified. Synthetic ITEM/LOCATION extensions must be labeled proposed. |
| Retailer / operational extensions | Actual receipts, appointments, product/style/size, campaigns, launch dates, available inventory, fulfillment capacity, costs, disputes and payment events | Necessary to answer business questions EDI alone cannot. Entirely synthetic initially. |

Do not count the same 852-derived activity twice if both the raw 852 feed and SPS analytics feed represent the same underlying source observation. Store origin and observation identity and pick an authoritative source per measure.

## 2. Common conventions

- `tenant_id`, `retailer_id`, `brand_id`, `source_system`, `source_record_id`, `observed_at`, `ingested_at`, `record_version`, `is_synthetic`, `generator_version`, `scenario_id` accompany relevant rows.
- Source business identifiers: VARCHAR, never numeric even if they contain digits. Preserve leading zeros, qualifiers, original casing and raw values.
- Canonical surrogate IDs: VARCHAR. All business keys include retailer, supplier/program and version scope where relevant; a PO number alone is not globally unique.
- Timestamps: TIMESTAMP_TZ normalized to UTC, while retaining `source_timezone` and raw timestamp. Business deadlines also retain location-local DATE and cutoff rule. TIMESTAMP_NTZ sources require a documented timezone assumption before conversion.
- Currency: ISO code VARCHAR(3); monetary amounts NUMBER(18,4), rates NUMBER(12,6); no automatic sum across currencies.
- Quantities: NUMBER(18,4), separate source UOM, canonical unit UOM, and effective-dated conversion. Footwear pairs, eaches, cartons and packs cannot be added without conversion.
- Snapshot dates: DATE plus reporting-period start/end and cadence. Missing coverage is not zero activity.
- Revisions use effective-from/to and `known_at`/`observed_at`, enabling point-in-time joins. Preserve originals; never overwrite history used for training.
- `scenario_id` and hidden simulator variables are NEVER predictive features. Synthetic source-record IDs and entity IDs must not encode outcomes.
- No real names, consumer addresses, email addresses or purchased customer records. Fictional store/DC/supplier identities; approximate regions are sufficient for maps.

## 3. Canonical entities: grain, fields and relationships

Abbreviations: S=VARCHAR, N=NUMBER, D=DATE, T=TIMESTAMP_TZ, B=BOOLEAN, V=VARIANT. Fields listed in addition to common provenance columns.

| Entity | Grain / key | Required fields and descriptors | Origin |
|---|---|---|---|
| RETAILER | One retailer or enterprise identifier | `retailer_id:S`, `retailer_name:S`, `enterprise_id:S`, `default_currency:S`, `default_timezone:S` | Proposed master |
| BRAND | One brand within enterprise | `brand_id:S`, `retailer_id:S`, `brand_name:S` | Proposed master; Urban Outfitters != all URBN |
| SUPPLIER | One synthetic supplier | `supplier_id:S`, `supplier_name:S`, `region:S`, `category_group:S`, `onboarded_date:D` | Proposed master |
| LOCATION | One effective-dated store/DC/ship-from location | `location_id:S`, `retailer_id:S`, `location_type:S`, `region:S`, `state:S`, `country:S`, `timezone:S`, `active_from:D`, `active_to:D` | S16 key concepts plus proposed enrichment |
| ITEM | One effective-dated sellable style/color/size SKU | `item_id:S`, `brand_id:S`, `category:S`, `style_id:S`, `color:S`, `size:S`, `size_system:S`, `base_uom:S`, `pack_size:N`, `unit_cost:N`, `unit_retail:N`, `currency:S`, `launch_date:D`, `exit_date:D` | Assortment concepts S03; proposed retailer attributes |
| ITEM_XREF | One identifier mapping per retailer/supplier/program and effective interval | `xref_id:S`, `retailer_id:S`, `supplier_id:S`, `identifier_type:S`, `source_item_id:S`, `canonical_item_id:S`, `valid_from:T`, `valid_to:T`, `known_at:T`, `mapping_status:S` | S28 short SKU rule; S16 mapping key |
| PROGRAM_RULE | One effective-dated demo rule | `rule_id:S`, `retailer_id:S`, `program_id:S`, `document_type:S`, `rule_type:S`, `parameters:V`, `effective_from:T`, `effective_to:T`, `evidence_status:S`, `source_id:S` | Verified constraints only where sourced; other rules explicitly synthetic |
| DOCUMENT | One immutable received document version | `document_id:S`, `file_path:S`, `content_hash:S`, `document_type:S`, `format:S`, `schema_version:S`, `sender_id:S`, `receiver_id:S`, `business_document_number:S`, `business_created_at:T`, `received_at:T`, `supersedes_document_id:S`, `payload:V`, `parse_status:S` | S07-S10, S24; canonical envelope proposed |
| TRANSPORT_EVENT | One file processing event | `transport_event_id:S`, `document_id:S`, `report_id:S`, `path:S`, `direction:S`, `transport_status:S`, `event_at:T`, `message:S` | Published history fields S25 |
| PO_HEADER_VERSION | One PO version per retailer/supplier/PO | `po_id:S`, `po_version:N`, `document_id:S`, `supplier_id:S`, `ship_to_location_id:S`, `order_date:D`, `requested_ship_start:T`, `requested_ship_end:T`, `requested_delivery_by:T`, `revision_type:S`, `currency:S` | Proposed normalized 850/860 semantics |
| PO_LINE_VERSION | One stable PO line within PO version | `po_line_id:S`, `po_id:S`, `po_version:N`, `source_line_number:S`, `source_item_id:S`, `item_id:S`, `ordered_qty:N`, `cancelled_qty:N`, `uom:S`, `unit_price:N`, `line_status:S` | Proposed normalized document fields |
| PO_ACCEPTANCE_EVENT | One acceptance/re-acceptance attempt | `acceptance_event_id:S`, `po_id:S`, `po_version:N`, `attempted_at:T`, `accepted_at:T`, `status:S`, `reason_code:S` | S28 workflow, NOT a field presumed in 850 |
| ACK_LINE | One acknowledged line/version | `ack_line_id:S`, `document_id:S`, `po_line_id:S`, `po_version:N`, `ack_status:S`, `accepted_qty:N`, `backorder_qty:N`, `promised_ship_at:T` | Proposed 855 contract, only enabled programs |
| SHIPMENT | One shipment | `shipment_id:S`, `asn_document_id:S`, `supplier_id:S`, `origin_location_id:S`, `destination_location_id:S`, `carrier_id:S`, `transport_mode:S`, `bol_number:S`, `planned_ship_at:T`, `actual_ship_at:T`, `estimated_arrival_at:T` | 856 + synthetic WMS/TMS; estimated != actual |
| SHIPMENT_LINE | One allocation of PO line to shipment | `shipment_line_id:S`, `shipment_id:S`, `po_line_id:S`, `po_version:N`, `item_id:S`, `shipped_qty:N`, `uom:S` | Proposed bridge permits split shipments and many POs per shipment |
| PACKAGE | One pallet/carton/package | `package_id:S`, `shipment_id:S`, `parent_package_id:S`, `package_type:S`, `shipping_serial_raw:S`, `sscc:S`, `label_template_id:S`, `label_schema_version:S`, `label_validation_status:S` | S11-S14; parent hierarchy S26 |
| PACKAGE_ITEM | One item/PO-line allocation within package | `package_item_id:S`, `package_id:S`, `shipment_line_id:S`, `item_id:S`, `packed_qty:N`, `uom:S`, `case_code:S` | S13 Pack/Item concept; proposed bridge |
| RECEIPT_LINE | One physical receiving event for shipment line | `receipt_line_id:S`, `shipment_line_id:S`, `location_id:S`, `received_at:T`, `received_qty:N`, `damaged_qty:N`, `accepted_qty:N`, `receipt_status:S` | Synthetic WMS truth; not inferred from ASN transmission |
| INVOICE_HEADER | One supplier invoice version | `invoice_id:S`, `document_id:S`, `supplier_id:S`, `invoice_number:S`, `invoice_date:D`, `due_date:D`, `currency:S`, `tax_amount:N`, `freight_amount:N`, `allowance_amount:N`, `invoice_total:N` | Proposed normalized 810 plus terms |
| INVOICE_LINE | One invoice line | `invoice_line_id:S`, `invoice_id:S`, `po_line_id:S`, `shipment_line_id:S`, `item_id:S`, `invoiced_qty:N`, `unit_price:N`, `line_amount:N` | Proposed 810; use allocation bridge if line covers multiple shipments |
| FINANCIAL_EVENT | One payment/deduction/dispute/credit event | `financial_event_id:S`, `invoice_id:S`, `invoice_line_id:S`, `event_type:S`, `event_at:T`, `amount:N`, `currency:S`, `reason_code:S`, `resolution_status:S`, `resolved_at:T` | Synthetic AP/AR truth, not invented SPS schema |
| RETAIL_ACTIVITY | One authoritative item/location/period observation and version | `activity_id:S`, `retailer_id:S`, `item_id:S`, `location_id:S`, `period_start:D`, `period_end:D`, `cadence:S`, `gross_sales_units:N`, `return_units:N`, `net_sales_units:N`, `net_sales_retail:N`, `inventory_units:N`, `on_order_units:N`, `receipt_units:N`, `in_transit_units:N`, `currency:S`, `coverage_status:S` | Canonical projection of S16 with explicit proposed period metadata |
| RETAIL_CALENDAR | One retailer/location/date | `calendar_date:D`, `location_id:S`, `fiscal_week:S`, `season:S`, `promo_flag:B`, `launch_flag:B`, `event_type:S`, `event_known_at:T` | Synthetic planning data; known-future vs observed features separated |
| CAPACITY_COST | One location/lane/service/effective date | `capacity_id:S`, `location_id:S`, `lane_id:S`, `capacity_units:N`, `capacity_volume:N`, `transfer_lead_days:N`, `expedite_cost:N`, `holding_cost_rate:N`, `effective_date:D` | Synthetic operating assumptions |
| PREDICTION | One model/entity/as-of/horizon/run | `prediction_id:S`, `entity_id:S`, `as_of_at:T`, `horizon_days:N`, `model_name:S`, `model_version:S`, `feature_version:S`, `risk_probability:N`, `point_estimate:N`, `lower_bound:N`, `upper_bound:N`, `reason_codes:V`, `data_quality_status:S` | Snowflake ML output; not all outputs apply to all models |
| ACTION_SCENARIO | One user-reviewed candidate action | `action_id:S`, `prediction_id:S`, `action_type:S`, `constraints:V`, `assumptions:V`, `estimated_net_benefit:N`, `status:S`, `reviewed_at:T`, `outcome_event_id:S` | Simulation only; no external order changes |

### Referential and accounting rules

- An 850 replacement supersedes a PO version, not the entire document history. URBN replacement versions preserve PO identity and require a fresh point-in-time state.
- Do not join every historical PO version to every shipment. Use the referenced version or a documented as-of reconciliation policy.
- Package-item sums reconcile to shipment-line quantities after UOM conversion; receipts may be partial or discrepant and need explicit exception reasons.
- Invoice totals reconcile to line totals plus tax/freight minus allowances using a documented rounding rule.
- Inventory movement: prior on-hand + receipts + sellable customer returns + transfers in - gross sales - transfers out - RTV + signed adjustments = ending on-hand. Net sales already accounts for returns; do not subtract returns twice.
- Physical simulator inventory stays nonnegative unless explicitly modeling backorders separately. Raw reported inventory may be negative because of injected reporting errors; keep reported and latent physical truth distinct.
- Deduction reversals and credits require signed event conventions and linkage; do not sum repeated dispute snapshots as new losses.
- Currency/UOM mismatches, unresolved SKU mappings and incomplete observations produce quarantine flags, not fabricated values.

## 4. EDI coverage matrix for the demo

| Document | Shared foundation | Foot Locker | Bass Pro | Urban Outfitters domestic |
|---|---|---|---|---|
| 850 PO | Core | Proposed; verify current map | Named on SPS page | Explicitly documented; includes replacement POs |
| 855 acknowledgment | Optional by program | Verify | Named on SPS page, mandatory status unverified | Do not assume; use separate Tradestone acceptance events |
| 856 ASN | Core | Proposed; verify map | Named on SPS page | Explicitly documented |
| 810 invoice | Core | Proposed; verify map | Named on SPS page | Explicitly documented |
| 860 buyer change | Optional | Verify program before modeling as fact | Verify | Exclude from primary workflow; replacement 850 instead |
| 846 inventory | Optional | Verify | Verify | Verify; not core EDI claim |
| 852 activity | Optional source | Verify | Named on SPS page, feed coverage unverified | Verify; retailer extension can supply synthetic POS |
| 997 functional ack | Optional technical status | Verify | Verify | Verify; never equivalent to business acceptance |
| 832 catalog | Optional Assortment extension | Verify | Verify | Verify; not a substitute for short-SKU crosswalk |

## 5. Generative process, not independently randomized tables

Proposed initial scale: 24 months of history; 3 retailer scenarios; 90 fictional stores and 6 DCs total; 60 synthetic suppliers; 1,500 sellable SKUs total; 60,000 POs with approximately 300,000 lines. Generate only active assortment/location combinations. Aim for roughly 1-3 million daily activity rows, with a small weekly-cadence fixture; actual counts follow the assortment map and are validated, not promised.

Build a 2,000-PO smoke-test dataset first. Larger portfolio simulations come after the shared model and first retailer app work. These numbers are demo sizing choices, not actual retailer footprints.

### Generation order

1. Generate masters, effective-dated SKU mappings, calendars and permissible assortment/location combinations.
2. Generate latent customer demand with weekly/annual seasonality, launch lifecycle, price response, regional effects and correlated random shocks.
3. Generate replenishment decisions, orders and capacity-constrained supplier responses; include congestion and supplier/lane heterogeneity.
4. Generate document lifecycle and transport independently from physical shipping, including duplicates, retries, delayed ingestion, revisions and mapping failures.
5. Generate shipments, cartons, delivery/receipt outcomes, sales constrained by availability, returns and inventory ledger movements.
6. Generate invoices, realistic mismatches, deductions, payment timing and resolutions from business events.
7. Derive observed features and matured labels at explicit as-of times; hide latent truth from features.
8. Independently validate keys, quantities, balances, histories, coverage and retailer program rules.

Use separate seeds for base histories, interventions, holdout shocks and scenario fixtures. Freeze a generator version and snapshot for reproducible demos. Maintain noise and irreducible uncertainty; do not deterministically make every late acknowledgment a late shipment.

### Signature scenario fixtures

- Foot Locker: a fictional footwear launch encounters delayed inbound units concentrated in key sizes. Some suppliers recover; others miss. Prioritize size/location exposure and compare transfer versus expedite under capacity limits.
- Bass Pro: a regional seasonal demand shift overlaps with a constrained bulky-item lane. Forecast uncertainty increases; choose inventory pre-positioning with cubic-capacity and arrival-date limits. No real regulated-product workflows.
- Urban Outfitters: a replacement 850 changes quantities or dates; an old SKU crosswalk and late re-acceptance create readiness risk. Exact changes are rule-detected; ML prioritizes future deadline/receipt exposure.
- Shared financial story: a split shipment creates an invoice quantity discrepancy and a disputed deduction. Match known facts deterministically; predict which unresolved exceptions need review.
- Data reliability: a late feed, duplicated ASN or malformed numeric activity value changes confidence and disables unsafe recommendations.

## 6. Model cards to implement

| Model | Prediction moment and target | Inputs available then | Baseline / evaluation | Business decision |
|---|---|---|---|---|
| M1 Fulfillment shortfall risk | Daily active PO-line snapshot; probability receipt is late or incomplete at agreed delivery cutoff | Current PO version, available acknowledgments, elapsed times, pre-existing supplier/lane history, inventory/capacity signals | Rule score + logistic baseline vs gradient boosting; PR-AUC, Brier/calibration, recall at fixed review capacity, per-retailer slices | Expedite, request supplier update, or reallocate before cutoff |
| M2 Supply-aware demand and availability | Daily SKU/location forecast for 7/14/28 days; observed sales forecast plus separate unmet-demand scenario | Lagged sales, availability flags, known promotions/launches, seasonality, as-of inbound commitments | Seasonal naive; rolling time-series evaluation; WAPE/MASE where denominators valid, bias, pinball loss and interval coverage | Replenish or transfer with uncertainty and supply constraints |
| M3 Pre-ship readiness risk | Active PO/version snapshot before ship cutoff; probability required readiness remains unresolved at cutoff | Revision count and magnitude, mapping coverage, acceptance lag, time remaining, pre-existing vendor processing history | Deadline rules vs calibrated classifier; precision/recall at top-K, calibration, lead-time gained | Prioritize revision/mapping/acceptance exceptions |
| M4 Invoice exception escalation (phase 2) | On invoice arrival after deterministic reconciliation; probability unresolved mismatch/dispute at a defined future day | Invoice/PO/receipt differences known then, terms, supplier history, earlier dispute patterns | Rules vs calibrated classifier; PR-AUC and review-yield; aging regression MAE if added | Rank AP/AR investigation queue, not automatically pay or reject |

Algorithms: candidate XGBoost/scikit-learn models trained inside Snowflake ML Jobs, logged in Snowflake Model Registry. Select the simplest model that beats the defined baseline on held-out synthetic periods; no algorithm or performance claim is predetermined. Model-specific explanations require compatible Registry support; otherwise calculate and persist explanations inside Snowflake ML compute. Feature contribution is not causal evidence.

M2 requires special care: sales during a stockout are censored demand. Hidden simulator demand can evaluate the synthetic availability policy, but cannot become an observed production label or feature. Display observed sales forecasting and simulated unmet demand separately. Weekly feeds must be modeled at their native cadence or with an explicitly validated disaggregation method, not silently upsampled.

## 7. Point-in-time and evaluation contract

- Provisional time split: 18 months training, 3 validation, 3 final test; rolling-origin folds within training/validation for tuning. Handle label maturity across boundaries.
- Purge PO trajectories that straddle splits, or use a documented entity-group/time split. No same-order snapshot leakage across train/test.
- For every feature use BOTH business event time and information availability: `observed_at <= as_of_at`. A historical event delivered tomorrow was not available today.
- Outcomes such as final delivery, deduction resolution, payment date and post-cutoff revisions are labels only.
- Open POs and unresolved disputes with immature outcome windows are censored, not automatically negative.
- Report per-retailer, supplier, category, volume and cold-start slices. Hold out selected suppliers/products to test generalization.
- Train a retailer-data-only baseline and an otherwise comparable retailer-plus-SPS model on identical splits, targets and tuning budgets. Remove all SPS-derived aggregates from the baseline. Report measured synthetic-data delta rather than assuming improvement.
- ML value and intervention value are distinct. Policy replay uses identical starting state and common random demand/shocks; report assumptions, sensitivity and downside, not causal real-world uplift.
- Stable model versions, feature versions, dataset snapshot, generation seed and as-of time are visible in technical drilldowns.

## 8. Shared KPI contract

All formulas below are proposed DEMO definitions. Actual retailer business rules can differ and require effective-dated agreement.

- **Line OTIF:** due, non-cancelled PO lines whose cumulative accepted receipts reach required quantity by delivery cutoff / all eligible due lines. Not-yet-due lines excluded. Quantity changes are resolved using the contracted version as known at the cutoff; retain a frozen-original-commitment comparison to reveal goalpost changes.
- **Unit fill rate at cutoff:** sum(min(accepted units by cutoff, required units)) / sum(required units), after UOM conversion. Overdeliveries cannot conceal other shortfalls.
- **ASN accuracy:** eligible ASN lines with matched item, quantity and package references within configured tolerance / eligible reconciled ASN lines. Show unreconciled population separately.
- **Expected late lines:** sum of calibrated late probabilities across eligible lines; not a measured count of late lines.
- **Observed stockout rate:** covered active item-location periods with nonpositive reported availability / covered active periods. Report frequency and negative-inventory quality separately; this is not automatically customer lost demand.
- **Forecast WAPE:** sum(abs(actual-predicted)) / sum(abs(actual)); show N/A when denominator is zero, plus volume and bias.
- **Retail value exposed:** distinct at-risk units x retail price. Not recognized revenue, profit or guaranteed lost sales; avoid repeating units across linked PO/shipment/invoice alerts.
- **Estimated intervention net benefit:** simulated incremental contribution margin + avoided distinct deduction/handling costs - expedite/transfer/holding costs. Keep wholesale invoice value and retail sell-through value separate; no double counting.
- **Invoice mismatch rate:** invoices with at least one defined reconciliation failure / eligible invoices received in the cohort.
- **Comparison:** denominators, windows, currency, UOM and cadence always visible. Cross-retailer comparison uses matched categories/service types or separately reported strata and each retailer's baseline; no unqualified ranking of dissimilar retailers.

## 9. Validation gates

- Unique canonical primary keys; no orphan parent/bridge references.
- No duplicated business documents counted twice; source revisions retained.
- Ledger conservation, package/shipment reconciliation, invoice reconciliation and UOM/currency checks pass for valid fixtures; intentional invalid fixtures are correctly quarantined.
- URBN workflow tests: no primary-path 860; replacement-850 changes preserved; short-SKU mapping; pre-ship acceptance gate; import program excluded.
- Transport status and physical fulfillment state are separate.
- Late-arrival and future-label leakage tests fail deliberately unsafe features.
- Baseline metrics, confidence intervals where supportable and subgroup sample counts are published even if the richer model does not improve.
- All dashboards display 'Synthetic demonstration data', as-of time and forecast uncertainty. Financial scenario outputs read 'estimated/simulated', not 'saved/recovered'.
- A drift/coverage failure routes to rule-based review or abstention rather than a confident recommendation.
