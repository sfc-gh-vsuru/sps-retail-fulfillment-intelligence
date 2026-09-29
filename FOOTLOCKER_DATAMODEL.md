# Foot Locker — Data Model Reference

**Project:** SPS Retail Fulfillment Intelligence
**Database:** `SPS_RETAIL_AI` on `sfsenorthamerica-demo_vsuru`
**Schema:** `FOOT_LOCKER`

---

## What Foot Locker Contributes

Foot Locker is a **data consumer** in this architecture. As the retailer, Foot Locker contributes operational context that SPS Commerce EDI data alone cannot provide:

1. **Multi-Banner Store Structure** — Foot Locker operates four distinct retail banners (`FOOT_LOCKER`, `CHAMPS_SPORTS`, `KIDS_FOOT_LOCKER`, `WSS`), each with different customer profiles, assortments, and fulfillment expectations. The `BANNER` column on `LOCATION` is the key attribute.

2. **Product Catalog with Size/Color Attributes** — Athletic footwear and apparel are size- and color-intensive categories. Foot Locker's `ITEM` records include `SIZE_NAME`, `COLOR_NAME`, `GENDER`, and `STYLE_NUMBER` columns that are essential for size-curve analysis and availability planning.

3. **Store Classification** — Foot Locker classifies stores by tier (`A`, `B`, `C`, `OUTLET`) and size (`LARGE`, `MEDIUM`, `SMALL`), which directly affects replenishment priority and allocation logic.

---

## Retailer-Specific Columns

### On LOCATION

| Column | Type | Description |
|--------|------|-------------|
| `BANNER` | VARCHAR | Retail banner: `FOOT_LOCKER`, `CHAMPS_SPORTS`, `KIDS_FOOT_LOCKER`, or `WSS` |
| `STORE_CLASSIFICATION` | VARCHAR | Store tier: `A`, `B`, `C`, or `OUTLET` |
| `STORE_SIZE` | VARCHAR | Physical store size: `LARGE`, `MEDIUM`, or `SMALL` |
| `REGION` | VARCHAR | Geographic region (e.g., `NORTHEAST`, `SOUTHEAST`, `MIDWEST`, `WEST`) |

### On ITEM

| Column | Type | Description |
|--------|------|-------------|
| `SIZE_NAME` | VARCHAR | Product size (e.g., `10`, `10.5`, `M`, `L`, `XL`) |
| `COLOR_NAME` | VARCHAR | Product color (e.g., `BLACK/WHITE`, `UNIVERSITY RED`) |
| `GENDER` | VARCHAR | Target gender: `MENS`, `WOMENS`, `KIDS`, `UNISEX` |
| `STYLE_NUMBER` | VARCHAR | Manufacturer style number |
| `DEPARTMENT_NAME` | VARCHAR | Department within the banner (e.g., `BASKETBALL`, `RUNNING`, `CASUAL`) |

---

## Retailer-Specific Views

### FOOT_LOCKER.V_PURCHASE_ORDERS

Joins `PURCHASE_ORDER` with `LOCATION` to surface banner context on every order. This view allows analysis of fulfillment performance by banner, which is critical because Champs Sports and Kids Foot Locker have different OTIF expectations than the flagship banner.

```sql
-- Key columns added by the join:
-- BANNER, STORE_CLASSIFICATION, STORE_SIZE, REGION
-- from LOCATION via SHIP_TO_LOCATION_ID
```

| Source Table | Columns Contributed |
|-------------|-------------------|
| `SHARED.PURCHASE_ORDER` | `PO_ID`, `PO_NUMBER`, `ORDER_DATE`, `REQUESTED_SHIP_DATE`, `REQUESTED_DELIVERY_DATE`, `PO_STATUS`, `TOTAL_UNITS`, `TOTAL_COST` |
| `SHARED.LOCATION` | `STORE_NAME`, `BANNER`, `STORE_CLASSIFICATION`, `STORE_SIZE`, `REGION`, `STATE`, `CITY` |
| `SHARED.SUPPLIER` | `SUPPLIER_NAME`, `RELIABILITY_TIER` |
| `SHARED.SHIPMENT` | `SHIP_DATE`, `ACTUAL_DELIVERY_DATE`, `ON_TIME_FLAG`, `IN_FULL_FLAG` |

### FOOT_LOCKER.V_WEEKLY_ACTIVITY

Joins `SPS_ACTIVITY` with `LOCATION` and `ITEM` to enable size-level and banner-level sell-through analysis. This is the primary view for understanding which sizes are selling out and which banners need replenishment.

```sql
-- Key columns added by the join:
-- SIZE_NAME, COLOR_NAME, GENDER, STYLE_NUMBER from ITEM
-- BANNER, STORE_CLASSIFICATION from LOCATION
```

| Source Table | Columns Contributed |
|-------------|-------------------|
| `SHARED.SPS_ACTIVITY` | `PERIOD_ENDING_DATE`, `NET_SALES_UNITS`, `NET_SALES_RETAIL`, `INVENTORY_UNITS`, `ON_ORDER_UNITS`, `RECEIPT_UNITS` |
| `SHARED.ITEM` | `CATEGORY_NAME`, `PRODUCT_GROUP_NAME`, `SIZE_NAME`, `COLOR_NAME`, `GENDER`, `BRAND_NAME`, `MSRP` |
| `SHARED.LOCATION` | `STORE_NAME`, `BANNER`, `STORE_CLASSIFICATION`, `STORE_SIZE`, `REGION` |

---

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| OTIF Rate | 81.1% | Slightly below the 81.7% cross-retailer average |
| Avg Sales (units/week) | 6.8 | Per item-location-week |
| Footwear Avg Sales | 9.0 units/week | Strongest category by volume |
| Apparel Avg Sales | 4.7 units/week | Lower velocity; seasonal patterns |
| Total Locations | 20 | Across all four banners |
| Total Items | ~1,200 | Footwear-heavy catalog |

---

## The Data Join Value

Without Foot Locker's banner and size attributes joined to SPS fulfillment data, a supplier cannot answer questions like:

- "Are Champs Sports stores getting their Jordan shipments on time?"
- "Which sizes are selling out fastest at Kids Foot Locker?"
- "Should I prioritize Class-A Foot Locker stores or Class-B Champs for the next allocation?"

The join of SPS EDI data (order-to-delivery visibility) with Foot Locker operational data (banner, size, store tier) creates the analysis surface that drives the **SPS + Foot Locker** Streamlit dashboard.
