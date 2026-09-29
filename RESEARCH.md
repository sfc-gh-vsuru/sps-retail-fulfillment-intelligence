# SPS Commerce retail intelligence: research and evidence

Research date: 2026-09-25. Status: public-source research, planning only.

## Evidence policy

- VERIFIED: observed in an official public source, with source ID below.
- INFERRED: reasonable interpretation, not a published data contract.
- PROPOSED: our demo design, not an SPS or retailer capability/requirement.
- UNVERIFIED: needs current documentation, data entitlement, or partner confirmation.
- All retailer records and outcomes in the proposed demos will be synthetic. Public brand names and program rules do not imply an endorsement, an entitlement to retailer data, or a commercial implementation by this project.
- No SPS login, production API invocation, Marketplace subscription, account query, or Snowflake object creation was performed. Documentation endpoints described below are references, not integrations implemented or exercised.

## 1. SPS portfolio and implications

| Solution | Publicly supported scope | Demo opportunity | Boundary |
|---|---|---|---|
| Fulfillment / EDI [S01, S07, S21] | Trading-partner order, shipment, invoice and related document exchange; ERP/WMS integration | Predict fulfillment exceptions before shipment; trace order-to-invoice evidence | Document transmission is not proof of physical receipt or payment |
| Decision Intelligence [S02] | Normalized sales, inventory and item performance; SKU/location analysis, days of supply, distribution gaps, allocation and retailer collaboration | Add fulfillment leading indicators to downstream availability and margin decisions | Data availability differs by retailer; do not adopt marketing outcome percentages as demo results |
| Assortment [S03] | Consolidation, validation, taxonomy mapping and delivery of item attributes via API, EDI 832, flat files or spreadsheets | SKU crosswalk quality, pack/UOM consistency, item readiness | Product-content management is not itself a predictive assortment optimizer |
| E-invoicing [S04] | Inbound/outbound B2B/B2G invoices, legal and commercial compliance, reporting and archiving; advertised coverage 50+ countries | Invoice mismatch detection, dispute prioritization, cash-cycle visibility | X12 810 alone is not statutory e-invoicing compliance; jurisdiction-specific rules need separate evidence |
| Relationship Management [S05] | Supplier onboarding, requirements, communications and training | Later supplier onboarding/readiness analytics | No public transactional schema acquired |
| Performance Management [S06] | Supplier scorecards including OTIF, fill rate and ASN accuracy | Explainable supplier performance and risk | Requires agreed denominators, delivery/receipt truth and effective-dated rules |
| Shipping Documentation [S11-S14] | Retailer-specific GS1-128/UCC-128 labels and packing slips; PDF/ZPL output | Carton-to-ASN consistency and exception drilldowns | Do not fabricate certification or live label-service outputs |
| Trading Partner Submission [S15] | Automates supplier submission to buying-organization programs | Later onboarding workflow | Not an order-history, retailer-directory, or sales-data API |

The official analytics URL currently resolves to a page titled Decision Intelligence [S02]. A September 15, 2026 SPS article found during research describes the transition from Analytics [S22]. The public Marketplace listing still uses the older Analytics wording. Treat this as product naming evolution, not two independent copies of the same data.

SPS's September 15 product announcement describes MAX availability and future expansion [S23]. The public Dev Center banner separately identifies Max Connect MCP as beta [S07]. Neither MAX nor MCP is required for the proposed Snowflake ML demos; do not imply our work implements SPS's proprietary AI product.

## 2. Snowflake Marketplace: what is actually documented

**Verified listing:** Sales and Inventory Data for Retail Business Intelligence.

- Provider: SPS Commerce, Inc.
- Listing ID: `GZSOZ8SOC`.
- URL: [S16]. Provider page: [S17].
- Public labels: Free; Unlimited Access; Secure share.
- Advertised refresh: daily.
- Advertised time coverage: last three years, by day.
- Advertised geography: global, by address.
- Listed objects: `ACTIVITY`, `ITEM`, `LOCATION`, `RETAILER_METADATA`.
- `ACTIVITY` public preview exposes 42 column names and broad Snowflake types; captured in `PUBLISHED_ACTIVITY_SCHEMA.csv`.
- The public example joins activity to item on `(SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_ITEM_KEY)` and to location on `(SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_LOCATION_KEY)`.
- The location example explicitly names `STATE` and `SPS_LOCATION_TYPE`. These are observed references, not a complete dimension schema.

**Important observations from the public preview:**

- Retailer labels shown in sample rows are generic, such as Sports Retailer and Outdoor Retailer. They are NOT evidence identifying Foot Locker or Bass Pro.
- `PERIOD_ENDING_DATE` is published as NUMBER. Sample values look like `20240427`; this supports a candidate YYYYMMDD interpretation but does not establish reporting-period duration.
- Sample period endings include dates spaced one week apart. Daily refresh and 'by day' listing labels do not prove every retailer supplies daily-grain POS. Preserve reporting cadence and source methodology; never manufacture daily observations by treating weekly totals as daily totals.
- Many financial fields are VARCHAR; many sample values are null. Numeric null, zero and unavailable are distinct states.
- One sample has negative `INVENTORY_UNITS`. Preserve raw observations and flag quality conditions; do not silently clamp all upstream inventory to zero.
- `INSERT_TIMESTAMP` is TIMESTAMP_NTZ, not a timezone-qualified business event timestamp.

**Not established:**

- Full schemas, uniqueness and cardinality contracts of ITEM, LOCATION and RETAILER_METADATA. Attempts to select other objects in the public browser preview continued displaying ACTIVITY; no claim is made that dimensional metadata was recovered.
- Exact currency, valuation, retail calendar, UOM, correction/restatement and coverage semantics.
- Whether the three named retailers are present in an entitled consumer feed.
- Whether listing access includes all network data, samples, customer-specific data, or further commercial arrangements.
- Any public raw Fulfillment/EDI transaction listing. The discovered listing is sales/inventory data, NOT documented 850/856/810 raw events.

SPS separately describes customer delivery via Snowflake private listings [S18]. Network-size and metric-count claims are product/network descriptors, not consumer data entitlements or verified schema columns.

**Design implication:** build distinct source adapters for SPS EDI/RSX and SPS sales/inventory. Keep the synthetic demo independent of live access, but make replacing either adapter possible without rebuilding the apps.

## 3. Transaction API: transport, not a universal JSON order schema

The official overview says the API is an HTTPS alternative to FTP/AS2, usually carrying Retail Standard XML (RSX), with other formats supported. Sandbox keys can exercise basic functionality; production data needs an SPS agreement and implementation-team access [S07].

RSX supports financial documents, bulk import, dropship, cross-dock, multi-store fulfillment, product/inventory and warehouse documents [S08]. Public unauthenticated RSX navigation exposed an overview, not complete retailer-specific XSDs or mapping guides.

### Published API v5 paths and controls

Base URL shown in documentation examples: `https://api.spscommerce.com`.

| Operation | Published path | Metadata / semantics | Source |
|---|---|---|---|
| Create file | `POST /transactions/v5/data/{file-path}` | Case-sensitive path; `application/octet-stream`; optional `sps-meta-{key}` string headers; body max 2 GB; same path overwrites existing transaction | S09 |
| List files | `GET /transactions/v5/data/{directory-path}` | Directory ends with `/`; `limit` 1-1000, default 1000; `cursor`; case-sensitive `entryNamePrefix` | S10 |
| Retrieve file | `GET /transactions/v5/data/{file-path}` | Retrieves file payload; do not assume a business JSON object | S24 |
| Processing history | `GET /transactions/v5/history` | `limit` default 100, `offset` default 0, `after`, `until`; report may take up to five minutes | S25 |

The overview describes outbound files in `out`, deletion after successful consumption, and SPS deleting incoming files after processing [S07]. A future live integration must land durable raw copies and commit processing before acknowledgement/deletion. This planning exercise does not authorize deletion or any live integration.

### Exact public list-response field paths

Observed in the documentation's JSON examples through browser DOM extraction:

| Field path | JSON type observed | Meaning |
|---|---|---|
| `results` | array | Directory entries |
| `results[].path` | string | File or directory path |
| `results[].type` | string | Example values `file`, `directory` |
| `results[].url` | string | Resource URL |
| `paging.limit` | number | Page limit |
| `paging.next.cursor` | string | Next-page cursor, when more results exist |
| `paging.next.url` | string | Next-page URL |

These response types are inferred from the published JSON sample, not a complete OpenAPI contract. One example pairs an `/out/` path with an `/in/` URL: treat examples as illustrative, validate production contracts, and do not hard-code example identifiers.

### Exact public history-response field paths

| Field path | JSON type observed | Meaning |
|---|---|---|
| `results[].id` | string | Report/transaction identifier, UUID-shaped example |
| `results[].path` | string | File path |
| `results[].direction` | string | Example `out`; complete enum not established |
| `results[].status_log` | array | Processing-event history |
| `results[].status_log[].status` | string | Examples `uploaded`, `downloaded`, `deleted`; not necessarily exhaustive |
| `results[].status_log[].timestamp` | string | ISO timestamp, example includes fractional seconds and Z |
| `results[].status_log[].message` | string | Optional event detail shown for deletion |
| `paging.offset`, `paging.limit`, `paging.total_count` | number | Pagination metadata |
| `paging.next.url`, `paging.previous.url` | string | Navigation URLs |

History query dates are documented as `YYYY-MM-DDTHH:mm:ss` without an explicit timezone in that section. The offset description conflicts with its default and example progression; confirm pagination and timezone behavior before implementing a client. File uploaded/downloaded/deleted states must never be relabeled as shipped/delivered/paid business states.

## 4. Shipping documentation: useful public schema evidence

Shipping label overview [S11] names ship-from, ship-to and SSCC-18, plus possible PO, postal code, carrier, PRO/BOL/tracking number, carton/pallet counts, item identifiers/descriptions, mark-for location, ship date and lot/batch data.

- Endpoint-specific schema path: `GET /label/v1/{label-id}/schema` [S12].
- Query flags: `download`, `pretty`, `pendingChange` (all Boolean, default false). `pendingChange=true` requests upcoming retailer requirement changes.
- The sample schema declares JSON Schema draft-07; it does not publish all properties in that example.
- Sample-data path: `GET /label/v1/{label-id}/sample-json` [S13].
- Endpoint documentation uses `/label/v1`, while overview prose mentions `/labels/...`; prefer endpoint-specific documentation and confirm with SPS.
- The full Shipping Label API Schema navigation [S14] redirected to authentication. No attempt was made to bypass it.

**Exact field paths in the public label sample [S13]:**

| Field | Sample JSON type | Proposed normalized interpretation |
|---|---|---|
| `Header.Address[]` | array of objects | One address record per role |
| `Header.Address[].Address1`, `Address2`, `AddressName` | string | Address lines and name |
| `Header.Address[].AddressTypeCode` | string | Role code; sample SF |
| `Header.Address[].City`, `Country`, `PostalCode`, `State` | string | Geography; preserve original country coding |
| `Header.BillOfLadingNumber` | string | BOL reference |
| `Pack[]` | array of objects | Package/carton structure |
| `Pack[].ShippingSerialID` | string | Barcode/shipping serial identifier; preserve leading zeros |
| `Pack[].Item[]` | array of objects | Contents |
| `Pack[].Item[].UPCCaseCode` | string | Case-level identifier; preserve qualifier and leading zeros |

Do not assume ShippingSerialID length must equal 18 from its name: the published sample is 20 characters long, while the overview discusses SSCC-18. Store the raw barcode separately from any parsed application identifier/SSCC and validate using an approved specification.

Packing-slip overview [S26] lists origin, order date, bill-to, ship-to, order number, quantity, item number/description, unit price and shipping method. Optional data includes returns, payment method, logos and marketing content. Package hierarchies explicitly supported: Pallet/Pack/Item, Pallet/Item, Pack/Item, Item. Do not flatten hierarchy without parent keys. The overview mentions `packing-slip/{slip-id}/schema`; versioned endpoint and full schema were not verified here.

## 5. Retailer-specific evidence and scope

### Foot Locker

Verified: official vendor manual portal has US/Canada, Europe and Asia Pacific scopes, plus shipping-label, packing and ticketing requirements [S19].

A public Section 8 PDF was reachable, but text was not extracted during this pass; its filename references Eastbay and must not be treated as a current all-banner contract. Third-party directories enumerate 810/816/850/852/855/856/860/997; these remain leads, NOT verified current retailer requirements in our contract.

Recommended demo: footwear launch readiness, style/color/size availability and inbound shortfall risk. Product launch dates, size curves, customer demand, store inventory and receipt evidence are synthetic retailer extensions, not fields guaranteed by SPS EDI.

A current direct Foot Locker-SPS commercial relationship was not established. Do not claim one. Avoid relying on stale standalone public-company descriptions or historical store counts.

### Bass Pro Shops

Verified: SPS offers connections and supplier compliance support for Bass Pro and names common 810, 852, 856, 850 and 855 documents [S20]. This is evidence of supplier connectivity support, NOT proof Bass Pro purchases every SPS product or that data is included in the Marketplace listing.

The SPS-hosted Domestic Vendor Guide landing page describes vendor setup, EDI, POs, packaging, shipping, dropship, invoicing and payment. The guide is sign-in gated [S27]. Do not invent required transaction versions, penalty schedules, delivery tolerances or routing rules.

Recommended demo: region/category seasonal readiness with inbound reliability, bulky-item capacity constraints and inventory balancing. Initially focus on non-regulated fishing, camping, boating accessories, apparel and footwear. Cabela's can be an optional later banner, not an implicit expansion of scope. Seasonal/geographic scenario settings are proposed synthetic assumptions, not a reproduction of actual Bass Pro demand or hunting regulations.

### Urban Outfitters brand within URBN

The URBN official vendor program explicitly states [S28]:

1. SPS Commerce is its only EDI partner for the described program; registration, testing and certification are required.
2. Vendor EDI includes 850 POs, 856 ASNs and 810 invoices.
3. PO revisions use replacement 850s, not 860s.
4. URBN short SKU must be cross-referenced to the vendor SKU/UPC; URBN does not transmit UPCs via EDI.
5. PO acceptance must precede the PO ship date for successful transmission.
6. Country of Origin, PO acceptance/re-acceptance and style customs descriptions still require Tradestone.
7. EDI packing lists/ASNs and invoices cannot be mixed with Tradestone equivalents for EDI vendors.
8. EDI UCC-128 labels must correspond with the ASN; a packing list accompanies the first carton.
9. The described option excludes import vendors where URBN is importer of record.

Our demo should focus on the Urban Outfitters brand, US domestic-vendor workflow, with an enterprise/brand distinction in dimensions. Do not add Nuuly, Anthropologie or Free People without a scope decision. The retailer portal is evidence of program behavior, not evidence those other brands share every operational rule or dataset.

Recommended demo: replacement-PO synchronization, SKU crosswalk quality, pre-ship readiness risk and fashion-window margin exposure. Exact revision diffs and known compliance rules are deterministic checks. ML predicts future risk and prioritizes unresolved exceptions; it must not be used to rediscover an exact PO diff.

## 6. Snowflake implementation evidence

Snowflake supports ML training in its Container Runtime using ML Jobs submitted from an external IDE, with data and execution inside Snowflake [S29, S30]. Model Registry supports versioned Python models and warehouse inference where dependencies/model types are compatible [S31].

Recommended interpretation of '100% SnowML': generation, transformations, feature engineering, model training, scoring, evaluation and serving all run inside Snowflake; local files are source code and deployment orchestration only. XGBoost/scikit-learn used inside Snowflake ML runtime do not imply external model hosting. No external AI endpoints, SaaS training, or local data training are required.

SQL ML function objects such as FORECAST do not automatically appear in Python Model Registry [S31]. Prefer a unified Registry-managed training path for the core demos; keep SQL ML functions as an explicitly separate optional implementation choice.

## 7. Partner information to request before a live-data phase

- Current RSX/XSD and X12 implementation guides, versions, qualifiers, required/conditional fields, code lists and synthetic sample payloads for applicable 850/855/856/810/860/846/852/997 documents.
- The actual enabled retailer/program/document matrix; never send a synthetic URBN 860 in the primary program.
- Entitled ITEM, LOCATION and RETAILER_METADATA dictionaries; source cadence, key uniqueness, currency/UOM conventions, date encoding and restatement semantics.
- Current label/packing-slip schemas and templates for each target program, including pending changes and effective dates.
- Exact crosswalk from EDI buyer/vendor/item/location IDs to SPS analytics keys.
- Receipt/appointment/carrier events; AP deduction, dispute and payment history; catalog and launch/promotion data needed beyond EDI.
- Written permission for any real retailer data, cross-retailer aggregation, logos or co-marketing claims. No outreach sent during research.

## Sources

All URLs reviewed or discovered on 2026-09-25; most pages are undated. Publication date is stated only when explicitly supported.

- S01: [SPS Fulfillment](https://www.spscommerce.com/products/fulfillment/edi/)
- S02: [Decision Intelligence](https://www.spscommerce.com/products/analytics/)
- S03: [Assortment](https://www.spscommerce.com/products/assortment/)
- S04: [E-invoicing](https://www.spscommerce.com/products/e-invoicing/)
- S05: [Relationship Management](https://www.spscommerce.com/products/relationship-management/)
- S06: [Performance Management](https://www.spscommerce.com/products/performance-management/)
- S07: [Transaction API overview](https://developercenter.spscommerce.com/#/docs/transaction-api)
- S08: [Public RSX overview](https://developercenter.spscommerce.com/#/rsx/docs/connect-to-sps-commerce)
- S09: [Create Transaction](https://developercenter.spscommerce.com/#/docs/transaction-api/v5-posting)
- S10: [Filter Transactions](https://developercenter.spscommerce.com/#/docs/transaction-api/v5-filtering)
- S11: [Shipping label overview](https://developercenter.spscommerce.com/#/docs/shipping-doc-api/labels/label_overview)
- S12: [Label schema endpoint documentation](https://developercenter.spscommerce.com/#/docs/shipping-doc-api/labels/get_label_schema)
- S13: [Public label JSON sample](https://developercenter.spscommerce.com/#/docs/shipping-doc-api/labels/get_label_sample)
- S14: [Full label schema navigation: authentication required](https://developercenter.spscommerce.com/#/docs/shipping-doc-api/labels/shipping_label_object)
- S15: [Trading Partner Submission API](https://developercenter.spscommerce.com/#/docs/trading-partner-submission-api)
- S16: [SPS Marketplace listing and data dictionary](https://app.snowflake.com/marketplace/listing/GZSOZ8SOC/sps-commerce-inc-sales-and-inventory-data-for-retail-business-intelligence)
- S17: [SPS Marketplace provider](https://app.snowflake.com/marketplace/providers/GZSOZ8SNB/SPS%20Commerce%2C%20Inc.)
- S18: [Snowflake/data warehouse integration](https://www.spscommerce.com/products/integrations/data-warehouse-integrations/)
- S19: [Foot Locker Vendor Standards Manual](https://www.footlocker-inc.com/content/flinc-aem-site/en/vendor-standards-manual.html)
- S20: [SPS Bass Pro supplier connectivity](https://www.spscommerce.com/network/find-a-partner/view/bass-pro/)
- S21: [SPS EDI document directory](https://www.spscommerce.com/resources/edi-documents-transactions/)
- S22: [Analytics becomes Decision Intelligence, September 15, 2026](https://www.spscommerce.com/community/articles/sps-analytics-is-now-decision-intelligence/) (research helper retrieved; a subsequent fetch redirected to an advertising URL, which was not followed)
- S23: [SPS product announcement, September 15, 2026](https://spscommerceinc.gcs-web.com/news-releases/news-release-details/sps-commerce-brings-network-intelligence-ai-enabling-supply)
- S24: [Get Transaction](https://developercenter.spscommerce.com/#/docs/transaction-api/v5-getting)
- S25: [Interaction history](https://developercenter.spscommerce.com/#/docs/transaction-api/v5-reporting)
- S26: [Packing slip overview](https://developercenter.spscommerce.com/#/docs/shipping-doc-api/packing_slips/packing_slip_overview)
- S27: [Bass Pro Domestic Vendor Guide landing page](https://www.spscommerce.com/community/unlock-your/bass-pro-shops-domestic-vendor-guide)
- S28: [URBN official EDI program](https://vendor.urbn.com/us/vendor-setups/urbn-edi-program)
- S29: [Snowflake ML development](https://docs.snowflake.com/en/developer-guide/snowflake-ml/modeling)
- S30: [Snowflake ML Jobs](https://docs.snowflake.com/en/developer-guide/snowflake-ml/ml-jobs/overview)
- S31: [Snowflake Model Registry](https://docs.snowflake.com/en/developer-guide/snowflake-ml/model-registry/overview)
- S32: [SPS getting started and OAuth](https://developercenter.spscommerce.com/#/docs/getting-started)
- S33: [SPS API reference landing page](https://docs.api.spscommerce.com/) (labels itself an internal-reference catalog and directs public developers to Dev Center; not treated as an approved public business API contract)
