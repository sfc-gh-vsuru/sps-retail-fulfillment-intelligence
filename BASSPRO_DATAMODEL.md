# Bass Pro Shops — Data Model Reference

**Project:** SPS Retail Fulfillment Intelligence
**Database:** `SPS_RETAIL_AI` on `sfsenorthamerica-demo_vsuru`
**Schema:** `BASS_PRO`

---

## What Bass Pro Shops Contributes

Bass Pro Shops is a **data consumer** in this architecture. As the retailer, Bass Pro contributes operational context specific to the outdoor and sporting goods vertical:

1. **Seasonal Product Categories** — Bass Pro's product assortment is organized around three core categories (`OUTDOOR`, `APPAREL`, `FOOTWEAR`) with strong seasonal demand patterns. The `CATEGORY_NAME` column on `ITEM` combined with `PRODUCT_SEASON` drives seasonal planning.

2. **Regional Store Network with Climate Zones** — Bass Pro operates across diverse geographies where climate directly influences product demand. The `REGION` and `CLIMATE` columns on `LOCATION` enable weather-correlated demand analysis that is unique to outdoor retail.

3. **Store Classification** — Bass Pro classifies locations as `FLAGSHIP`, `STANDARD`, or `OUTPOST`, with different inventory depth expectations for each tier.

---

## Retailer-Specific Columns

### On LOCATION

| Column | Type | Description |
|--------|------|-------------|
| `REGION` | VARCHAR | Geographic region (e.g., `SOUTHEAST`, `MIDWEST`, `MOUNTAIN_WEST`, `PACIFIC`, `NORTHEAST`) |
| `CLIMATE` | VARCHAR | Climate zone classification: `WARM`, `TEMPERATE`, `COLD`, or `ALPINE` |
| `STORE_CLASSIFICATION` | VARCHAR | Store format: `FLAGSHIP`, `STANDARD`, or `OUTPOST` |
| `STORE_SIZE` | VARCHAR | Physical store size: `LARGE`, `MEDIUM`, or `SMALL` |

### On ITEM

| Column | Type | Description |
|--------|------|-------------|
| `CATEGORY_NAME` | VARCHAR | Product category: `OUTDOOR`, `APPAREL`, or `FOOTWEAR` |
| `PRODUCT_GROUP_NAME` | VARCHAR | Sub-category (e.g., `CAMPING`, `FISHING`, `HIKING`, `HUNTING`, `OUTERWEAR`) |
| `PRODUCT_SEASON` | VARCHAR | Primary selling season: `SPRING`, `SUMMER`, `FALL`, `WINTER`, or `ALL_SEASON` |
| `SIZE_NAME` | VARCHAR | Product size |
| `COLOR_NAME` | VARCHAR | Product color |
| `DEPARTMENT_NAME` | VARCHAR | Department (e.g., `CAMPING_GEAR`, `FISHING_TACKLE`, `HUNTING`, `LODGE_WEAR`) |

---

## Retailer-Specific Views

### BASS_PRO.V_PURCHASE_ORDERS

Joins `PURCHASE_ORDER` with `LOCATION` to surface regional and climate context on every order. Climate-aware fulfillment is critical because a late shipment of winter jackets to a `COLD` or `ALPINE` location has far more business impact than the same delay to a `WARM` region.

```sql
-- Key columns added by the join:
-- REGION, CLIMATE, STORE_CLASSIFICATION, STORE_SIZE
-- from LOCATION via SHIP_TO_LOCATION_ID
```

| Source Table | Columns Contributed |
|-------------|-------------------|
| `SHARED.PURCHASE_ORDER` | `PO_ID`, `PO_NUMBER`, `ORDER_DATE`, `REQUESTED_SHIP_DATE`, `REQUESTED_DELIVERY_DATE`, `PO_STATUS`, `TOTAL_UNITS`, `TOTAL_COST` |
| `SHARED.LOCATION` | `STORE_NAME`, `REGION`, `CLIMATE`, `STORE_CLASSIFICATION`, `STORE_SIZE`, `STATE`, `CITY` |
| `SHARED.SUPPLIER` | `SUPPLIER_NAME`, `RELIABILITY_TIER`, `CATEGORY_SPECIALTY` |
| `SHARED.SHIPMENT` | `SHIP_DATE`, `ACTUAL_DELIVERY_DATE`, `ON_TIME_FLAG`, `IN_FULL_FLAG` |

### BASS_PRO.V_WEEKLY_ACTIVITY

Joins `SPS_ACTIVITY` with `LOCATION` and `ITEM` to enable seasonal and climate-correlated demand analysis. This view powers the seasonal demand heatmap and weeks-of-supply calculations in the dashboard.

```sql
-- Key columns added by the join:
-- CATEGORY_NAME, PRODUCT_GROUP_NAME, PRODUCT_SEASON from ITEM
-- REGION, CLIMATE, STORE_CLASSIFICATION from LOCATION
```

| Source Table | Columns Contributed |
|-------------|-------------------|
| `SHARED.SPS_ACTIVITY` | `PERIOD_ENDING_DATE`, `NET_SALES_UNITS`, `NET_SALES_RETAIL`, `INVENTORY_UNITS`, `ON_ORDER_UNITS`, `RECEIPT_UNITS`, `IN_TRANSIT_UNITS`, `IS_HOLIDAY_WEEK` |
| `SHARED.ITEM` | `CATEGORY_NAME`, `PRODUCT_GROUP_NAME`, `PRODUCT_SEASON`, `BRAND_NAME`, `MSRP`, `COST` |
| `SHARED.LOCATION` | `STORE_NAME`, `REGION`, `CLIMATE`, `STORE_CLASSIFICATION`, `STORE_SIZE` |

---

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| OTIF Rate | 82.8% | Highest among the three retailers |
| Avg Sales (units/week) | 10.0 | Per item-location-week; highest volume |
| Outdoor Avg Sales | 13.9 units/week | Dominant category by a wide margin |
| Apparel Avg Sales | 7.3 units/week | Moderate velocity |
| Footwear Avg Sales | 4.7 units/week | Lowest category; niche assortment |
| Total Locations | 20 | Across multiple climate zones |
| Total Items | ~1,200 | Outdoor-heavy catalog |

---

## Seasonal Demand Patterns

Bass Pro's demand is heavily seasonal, which makes climate-zone analysis valuable:

- **Winter peaks** in `COLD` and `ALPINE` locations for outdoor categories (hunting, outerwear)
- **Summer peaks** in `WARM` and `TEMPERATE` locations for fishing and camping
- **Holiday week** spikes are pronounced across all regions (flagged by `IS_HOLIDAY_WEEK`)
- **Weeks of Supply** calculations (`INVENTORY_UNITS / AVG_WEEKLY_SALES`) vary significantly by climate zone and season

---

## The Data Join Value

Without Bass Pro's climate and seasonal attributes joined to SPS fulfillment data, a supplier cannot answer questions like:

- "Are my winter jacket shipments reaching Alpine stores before first snowfall?"
- "Which product groups have the lowest weeks of supply heading into hunting season?"
- "Should I pre-ship camping gear to Southern flagships or wait for order pull?"

The join of SPS EDI data (order-to-delivery visibility) with Bass Pro operational data (climate zones, seasonal categories, store formats) creates the analysis surface that drives the **SPS + Bass Pro Shops** Streamlit dashboard.
