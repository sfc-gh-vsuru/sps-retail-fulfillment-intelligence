# Urban Outfitters — Data Model Reference

**Project:** SPS Retail Fulfillment Intelligence
**Database:** `SPS_RETAIL_AI` on `sfsenorthamerica-demo_vsuru`
**Schema:** `URBAN_OUTFITTERS`

---

## What Urban Outfitters Contributes

Urban Outfitters (URBN) is a **data consumer** in this architecture. As the retailer, Urban Outfitters contributes operational context specific to its fast-fashion, multi-category business:

1. **URBN Short SKU Crosswalk** — Urban Outfitters uses an internal short SKU system that differs from standard UPC. The `SKU_CROSSWALK` table (650 records) maps between URBN short SKUs, vendor UPCs, and style/color/size combinations. Crosswalk health directly affects order accuracy.

2. **Replacement-850 Workflow** — Unlike Foot Locker and Bass Pro, Urban Outfitters does not use EDI 860 (Purchase Order Change). Instead, when a PO needs modification, UO cancels the original and issues a new replacement 850. The `IS_REPLACEMENT_850` and `REVISION_TYPE` columns on `PURCHASE_ORDER` track this workflow.

3. **Multi-Category Assortment** — UO spans `APPAREL`, `ACCESSORIES`, and `HOME` categories with different fulfillment characteristics for each.

---

## Retailer-Specific Columns

### On PURCHASE_ORDER

| Column | Type | Relevance |
|--------|------|-----------|
| `IS_REPLACEMENT_850` | BOOLEAN | `TRUE` if this PO replaces a cancelled order; unique to UO's no-860 workflow |
| `REVISION_TYPE` | VARCHAR | Set to `REPLACEMENT` when `IS_REPLACEMENT_850` is true; also tracks `QUANTITY_CHANGE` or `CANCEL_REORDER` |
| `ORIGINAL_PO_ID` | NUMBER | Links replacement POs back to the original cancelled order |
| `PO_VERSION` | NUMBER | Incremented when a replacement is issued |

### On ITEM

| Column | Type | Description |
|--------|------|-------------|
| `URBN_SHORT_SKU` | VARCHAR | Urban Outfitters internal short SKU identifier |
| `CATEGORY_NAME` | VARCHAR | Product category: `APPAREL`, `ACCESSORIES`, or `HOME` |
| `PRODUCT_GROUP_NAME` | VARCHAR | Sub-category (e.g., `DRESSES`, `TOPS`, `JEWELRY`, `CANDLES`, `BEDDING`) |
| `STYLE_NUMBER` | VARCHAR | Vendor-assigned style number |
| `COLOR_NAME` | VARCHAR | Product color |
| `SIZE_NAME` | VARCHAR | Product size |

### On LOCATION

| Column | Type | Description |
|--------|------|-------------|
| `REGION` | VARCHAR | Geographic region |
| `STORE_CLASSIFICATION` | VARCHAR | Store tier |
| `STORE_SIZE` | VARCHAR | Physical store size |

---

## SKU_CROSSWALK Table

The `SKU_CROSSWALK` table is unique to Urban Outfitters and lives in the `URBAN_OUTFITTERS` schema. It maps between URBN's internal short SKU system and vendor product identifiers.

| Column | Type | Description |
|--------|------|-------------|
| `ITEM_ID` | NUMBER | Foreign key to `ITEM` |
| `URBN_SHORT_SKU` | VARCHAR | URBN internal short SKU |
| `VENDOR_UPC` | VARCHAR | Vendor-supplied UPC code |
| `VENDOR_STYLE_NUMBER` | VARCHAR | Vendor-supplied style number |
| `STYLE_NUMBER` | VARCHAR | Canonical style number |
| `COLOR_NAME` | VARCHAR | Color associated with this SKU mapping |
| `SIZE_NAME` | VARCHAR | Size associated with this SKU mapping |
| `MAPPING_STATUS` | VARCHAR | Health of the mapping: `ACTIVE`, `PENDING`, `EXPIRED`, or `UNMAPPED` |
| `VALID_FROM` | DATE | Start date of the mapping's validity |
| `VALID_TO` | DATE | End date of the mapping's validity (NULL = currently active) |

SKU mapping health is a leading indicator of order accuracy. An `UNMAPPED` or `EXPIRED` status means the system cannot reliably match vendor products to URBN's internal catalog, increasing the risk of fulfillment errors.

---

## Retailer-Specific Views

### URBAN_OUTFITTERS.V_PURCHASE_ORDERS

Joins `PURCHASE_ORDER` with `LOCATION` and adds a computed `PO_TYPE_LABEL` column that classifies each order as either `ORIGINAL` or `REPLACEMENT`. This is the key differentiator for UO's fulfillment analysis — replacement POs inflate order counts and distort OTIF calculations if not identified.

```sql
-- Key columns added:
-- PO_TYPE_LABEL: 'REPLACEMENT' when IS_REPLACEMENT_850 = TRUE, else 'ORIGINAL'
-- REGION, STORE_CLASSIFICATION from LOCATION
```

| Source Table | Columns Contributed |
|-------------|-------------------|
| `SHARED.PURCHASE_ORDER` | `PO_ID`, `PO_NUMBER`, `ORDER_DATE`, `PO_STATUS`, `IS_REPLACEMENT_850`, `REVISION_TYPE`, `ORIGINAL_PO_ID`, `TOTAL_UNITS`, `TOTAL_COST` |
| `SHARED.LOCATION` | `STORE_NAME`, `REGION`, `STORE_CLASSIFICATION`, `STORE_SIZE` |
| `SHARED.SUPPLIER` | `SUPPLIER_NAME`, `RELIABILITY_TIER` |
| `SHARED.SHIPMENT` | `SHIP_DATE`, `ACTUAL_DELIVERY_DATE`, `ON_TIME_FLAG`, `IN_FULL_FLAG` |
| *(computed)* | `PO_TYPE_LABEL` — `CASE WHEN IS_REPLACEMENT_850 THEN 'REPLACEMENT' ELSE 'ORIGINAL' END` |

### URBAN_OUTFITTERS.V_WEEKLY_ACTIVITY

Joins `SPS_ACTIVITY` with `ITEM`, `LOCATION`, and `SKU_CROSSWALK` to surface URBN short SKU identifiers and their mapping health alongside weekly sell-through data.

```sql
-- Key columns added:
-- URBN_SHORT_SKU from ITEM
-- SKU_MAPPING_STATUS from SKU_CROSSWALK (via ITEM_ID join)
```

| Source Table | Columns Contributed |
|-------------|-------------------|
| `SHARED.SPS_ACTIVITY` | `PERIOD_ENDING_DATE`, `NET_SALES_UNITS`, `NET_SALES_RETAIL`, `INVENTORY_UNITS`, `ON_ORDER_UNITS`, `RECEIPT_UNITS` |
| `SHARED.ITEM` | `CATEGORY_NAME`, `PRODUCT_GROUP_NAME`, `URBN_SHORT_SKU`, `BRAND_NAME`, `MSRP` |
| `SHARED.LOCATION` | `STORE_NAME`, `REGION`, `STORE_CLASSIFICATION` |
| `URBAN_OUTFITTERS.SKU_CROSSWALK` | `MAPPING_STATUS` (aliased as `SKU_MAPPING_STATUS`) |

---

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| OTIF Rate | 80.8% | Lowest among the three retailers; replacement POs contribute to complexity |
| Ship Rate | 85.3% | Lower than FL/BP due to replacement PO cancellation patterns |
| Avg Sales (units/week) | 4.8 | Per item-location-week; lowest volume (fast-fashion, smaller pack sizes) |
| Apparel Avg Sales | 5.9 units/week | Strongest category |
| Accessories Avg Sales | 3.1 units/week | Moderate velocity |
| Home Avg Sales | 2.5 units/week | Lowest velocity; longer shelf life |
| SKU Crosswalk Records | 650 | URBN-specific mapping table |
| Total Locations | 20 | All Urban Outfitters branded |
| Total Items | ~1,180 | Multi-category assortment |

---

## The Replacement-850 Workflow

Urban Outfitters' PO revision process works differently from the other retailers:

1. **Standard flow (Foot Locker, Bass Pro):** Retailer sends an EDI 860 to modify the original PO in place
2. **UO flow:** Retailer cancels the original 850 and issues a new replacement 850 with a fresh PO number

This means:
- `PO_VERSION > 1` indicates a replacement PO
- `IS_REPLACEMENT_850 = TRUE` flags the new order
- `ORIGINAL_PO_ID` links back to the cancelled order
- Ship rate appears lower because cancelled POs count as "not shipped" in raw calculations
- The `PO_TYPE_LABEL` in `V_PURCHASE_ORDERS` disambiguates original vs. replacement for accurate KPI calculation

---

## The Data Join Value

Without Urban Outfitters' SKU crosswalk and replacement-850 context joined to SPS fulfillment data, a supplier cannot answer questions like:

- "How many of my open POs have unmapped SKUs that will cause receiving errors?"
- "What percentage of UO orders are replacements, and are they shipping faster than originals?"
- "Is my pre-ship readiness risk driven by SKU mapping gaps or lead-time issues?"

The join of SPS EDI data (order-to-delivery visibility) with Urban Outfitters operational data (SKU crosswalk, replacement workflow, multi-category structure) creates the analysis surface that drives the **SPS + Urban Outfitters** Streamlit dashboard.
