# SPS Commerce — Data Model Reference

**Project:** SPS Retail Fulfillment Intelligence
**Database:** `SPS_RETAIL_AI` on `sfsenorthamerica-demo_vsuru`
**Schema:** `SHARED` (provider tables available to all retailer schemas)

---

## What SPS Commerce Provides

SPS Commerce is the **data provider** in this architecture. As the EDI network operator, SPS captures the full lifecycle of retail fulfillment transactions and makes two categories of data available:

1. **EDI Fulfillment Documents** — Structured representations of the four core EDI transaction sets that move a purchase order from placement through payment:
   - **850 Purchase Order** — Retailer sends to supplier (what to ship, where, when)
   - **856 ASN (Advance Ship Notice)** — Supplier confirms shipment details
   - **810 Invoice** — Supplier bills the retailer
   - **861 Receipt** — Retailer confirms what arrived at the dock

2. **Weekly Sales/Inventory Activity Feed** — A point-of-sale and inventory snapshot delivered weekly, mirroring the real SPS Commerce Marketplace share schema. This feed provides sell-through and stock-level visibility that EDI documents alone cannot.

---

## Tables Contributed by SPS Commerce

### SPS_ACTIVITY

Weekly sales and inventory activity feed. 2,888,606 rows covering 106 weekly periods from September 2022 through September 2024. This table mirrors the schema of the actual SPS Commerce Analytics share on Snowflake Marketplace.

| Column | Type | Description |
|--------|------|-------------|
| `SPS_CUSTOMER_ITEM_KEY` | VARCHAR | SPS-assigned composite key identifying the item within a retailer's catalog |
| `SPS_RETAILER_NAME_KEY` | VARCHAR | SPS-assigned key identifying the retailer (e.g., `FOOT_LOCKER`, `BASS_PRO`, `URBAN_OUTFITTERS`) |
| `SPS_CUSTOMER_LOCATION_KEY` | VARCHAR | SPS-assigned key identifying the store/location within a retailer's network |
| `SPS_ITEM_MAPPING_KEY` | VARCHAR | SPS-assigned key linking retailer item identifiers to a canonical product reference |
| `PERIOD_ENDING_DATE` | NUMBER | Week-ending date in `YYYYMMDD` format (e.g., `20240915`); activity is aggregated at the weekly grain |
| `NET_SALES_UNITS` | NUMBER | Units sold at the register during the period (net of returns) |
| `NET_SALES_RETAIL` | NUMBER | Retail dollar value of net sales |
| `INVENTORY_UNITS` | NUMBER | On-hand inventory units at period end |
| `ON_ORDER_UNITS` | NUMBER | Units on open purchase orders not yet received |
| `RECEIPT_UNITS` | NUMBER | Units received at the store/DC during the period |
| `IN_TRANSIT_UNITS` | NUMBER | Units shipped but not yet received |
| `CUSTOMER_RETURN_UNITS` | NUMBER | Units returned by customers during the period |
| `TOTAL_MARKDOWN_VALUES` | NUMBER | Dollar value of markdowns applied during the period |
| `CORPORATE_UNIT_ADJUSTED_COST` | NUMBER | Adjusted cost per unit (corporate-level) |
| `CORPORATE_UNIT_ACQUIRED_COST` | NUMBER | Original acquisition cost per unit |
| `CORPORATE_UNIT_OWNED_RETAIL_PRICE` | NUMBER | Retail price per unit (corporate-owned inventory) |
| `RETAILER_ID` | NUMBER | Foreign key to `RETAILER` table |
| `ITEM_ID` | NUMBER | Foreign key to `ITEM` table |
| `LOCATION_ID` | NUMBER | Foreign key to `LOCATION` table |
| `CATEGORY_NAME` | VARCHAR | Product category (e.g., `FOOTWEAR`, `APPAREL`, `OUTDOOR`) |
| `PRODUCT_GROUP_NAME` | VARCHAR | Product sub-group within the category |
| `SEASON` | VARCHAR | Product season designation |
| `FISCAL_YEAR` | NUMBER | Fiscal year of the period |
| `IS_HOLIDAY_WEEK` | BOOLEAN | Whether the period falls in a designated holiday sales week |

### PURCHASE_ORDER

EDI 850 purchase orders. 10,476 orders across all three retailers.

| Column | Type | Description |
|--------|------|-------------|
| `PO_ID` | NUMBER | Primary key |
| `PO_NUMBER` | VARCHAR | Retailer-assigned purchase order number |
| `PO_VERSION` | NUMBER | Version number; >1 indicates the PO has been revised |
| `RETAILER_ID` | NUMBER | Foreign key to `RETAILER` |
| `SUPPLIER_ID` | NUMBER | Foreign key to `SUPPLIER` |
| `SHIP_TO_LOCATION_ID` | NUMBER | Foreign key to `LOCATION`; destination store or DC |
| `ORDER_DATE` | DATE | Date the PO was issued |
| `REQUESTED_SHIP_DATE` | DATE | Date the retailer wants the supplier to ship |
| `REQUESTED_DELIVERY_DATE` | DATE | Date the retailer needs the goods at the dock |
| `PO_STATUS` | VARCHAR | Current status (`OPEN`, `SHIPPED`, `RECEIVED`, `CLOSED`, `CANCELLED`) |
| `REVISION_TYPE` | VARCHAR | Type of revision if PO was modified (`QUANTITY_CHANGE`, `DATE_CHANGE`, `CANCEL_REORDER`, `REPLACEMENT`, `NONE`) |
| `IS_REPLACEMENT_850` | BOOLEAN | Whether this PO is a replacement for a cancelled order (Urban Outfitters workflow) |
| `ORIGINAL_PO_ID` | NUMBER | Self-referencing FK to the original PO if this is a replacement |
| `TOTAL_UNITS` | NUMBER | Sum of all line item quantities |
| `TOTAL_COST` | NUMBER | Sum of all line item costs |
| `TOTAL_RETAIL` | NUMBER | Sum of all line item retail values |
| `ACCEPTANCE_STATUS` | VARCHAR | Supplier acceptance (`ACCEPTED`, `REJECTED`, `PENDING`) |

### PO_LINE

Line-level detail for purchase orders. 51,143 lines; fill rate is 98.8% on closed lines.

| Column | Type | Description |
|--------|------|-------------|
| `PO_LINE_ID` | NUMBER | Primary key |
| `PO_ID` | NUMBER | Foreign key to `PURCHASE_ORDER` |
| `LINE_NUMBER` | NUMBER | Sequential line number within the PO |
| `ITEM_ID` | NUMBER | Foreign key to `ITEM` |
| `ORDERED_QTY` | NUMBER | Quantity ordered on this line |
| `UNIT_PRICE` | NUMBER | Cost per unit |
| `LINE_TOTAL` | NUMBER | `ORDERED_QTY * UNIT_PRICE` |
| `LINE_STATUS` | VARCHAR | Line status (`OPEN`, `SHIPPED`, `RECEIVED`, `CLOSED`, `CANCELLED`) |
| `SHIPPED_QTY` | NUMBER | Units shipped against this line |
| `RECEIVED_QTY` | NUMBER | Units received against this line |
| `INVOICED_QTY` | NUMBER | Units invoiced against this line |

### SHIPMENT

EDI 856 Advance Ship Notices. 9,919 shipments.

| Column | Type | Description |
|--------|------|-------------|
| `SHIPMENT_ID` | NUMBER | Primary key |
| `ASN_NUMBER` | VARCHAR | Advance Ship Notice number |
| `PO_ID` | NUMBER | Foreign key to `PURCHASE_ORDER` |
| `SUPPLIER_ID` | NUMBER | Foreign key to `SUPPLIER` |
| `RETAILER_ID` | NUMBER | Foreign key to `RETAILER` |
| `CARRIER` | VARCHAR | Freight carrier name |
| `SHIP_DATE` | DATE | Date the shipment left the supplier |
| `ESTIMATED_DELIVERY_DATE` | DATE | Carrier-estimated arrival date |
| `ACTUAL_DELIVERY_DATE` | DATE | Actual arrival date at the destination |
| `SHIPMENT_STATUS` | VARCHAR | Status (`IN_TRANSIT`, `DELIVERED`, `DELAYED`, `CANCELLED`) |
| `TOTAL_UNITS` | NUMBER | Total units in the shipment |
| `TOTAL_CARTONS` | NUMBER | Number of cartons/packages |
| `ON_TIME_FLAG` | BOOLEAN | Whether the shipment arrived on or before the requested delivery date |
| `IN_FULL_FLAG` | BOOLEAN | Whether the shipment contained the full ordered quantity |

### RECEIPT

EDI 861 Receiving Advice. 9,919 receipts (1:1 with shipments in this dataset).

| Column | Type | Description |
|--------|------|-------------|
| `RECEIPT_ID` | NUMBER | Primary key |
| `SHIPMENT_ID` | NUMBER | Foreign key to `SHIPMENT` |
| `PO_ID` | NUMBER | Foreign key to `PURCHASE_ORDER` |
| `LOCATION_ID` | NUMBER | Foreign key to `LOCATION`; receiving store or DC |
| `RETAILER_ID` | NUMBER | Foreign key to `RETAILER` |
| `RECEIPT_DATE` | DATE | Date goods were received and checked in |
| `TOTAL_RECEIVED_UNITS` | NUMBER | Units accepted |
| `TOTAL_DAMAGED_UNITS` | NUMBER | Units flagged as damaged at receiving |
| `RECEIPT_STATUS` | VARCHAR | Status (`RECEIVED`, `PARTIAL`, `REJECTED`) |
| `DAYS_LATE` | NUMBER | Number of days past the requested delivery date (0 = on time, negative = early) |

### INVOICE

EDI 810 Invoices. 9,919 invoices.

| Column | Type | Description |
|--------|------|-------------|
| `INVOICE_ID` | NUMBER | Primary key |
| `INVOICE_NUMBER` | VARCHAR | Supplier-assigned invoice number |
| `PO_ID` | NUMBER | Foreign key to `PURCHASE_ORDER` |
| `SHIPMENT_ID` | NUMBER | Foreign key to `SHIPMENT` |
| `SUPPLIER_ID` | NUMBER | Foreign key to `SUPPLIER` |
| `RETAILER_ID` | NUMBER | Foreign key to `RETAILER` |
| `INVOICE_DATE` | DATE | Date the invoice was issued |
| `DUE_DATE` | DATE | Payment due date |
| `INVOICE_TOTAL` | NUMBER | Total invoice amount |
| `PAYMENT_STATUS` | VARCHAR | Status (`PAID`, `PENDING`, `DISPUTED`, `OVERDUE`) |
| `MISMATCH_FLAG` | BOOLEAN | Whether the invoice has a discrepancy vs. PO or receipt |
| `MISMATCH_REASON` | VARCHAR | Description of the mismatch if flagged |

### SUPPLIER

Supplier master data. 20 suppliers.

| Column | Type | Description |
|--------|------|-------------|
| `SUPPLIER_ID` | NUMBER | Primary key |
| `SUPPLIER_NAME` | VARCHAR | Supplier business name |
| `REGION` | VARCHAR | Supplier's operating region |
| `COUNTRY` | VARCHAR | Supplier's country |
| `CATEGORY_SPECIALTY` | VARCHAR | Primary product category the supplier specializes in |
| `RELIABILITY_TIER` | VARCHAR | SPS-assessed reliability rating (`GOLD`, `SILVER`, `BRONZE`) |
| `AVG_LEAD_DAYS` | NUMBER | Average days from PO acceptance to shipment |
| `LEAD_VARIABILITY_DAYS` | NUMBER | Standard deviation of lead time in days |
| `ONBOARDED_DATE` | DATE | Date the supplier joined the SPS network |

### RETAILER

Retailer master data. 3 retailers.

| Column | Type | Description |
|--------|------|-------------|
| `RETAILER_ID` | NUMBER | Primary key |
| `RETAILER_NAME` | VARCHAR | Retailer display name |
| `ENTERPRISE_NAME` | VARCHAR | Parent enterprise name |
| `INDUSTRY_SEGMENT` | VARCHAR | Retail segment (e.g., `ATHLETIC`, `OUTDOOR`, `LIFESTYLE`) |
| `DEFAULT_CURRENCY` | VARCHAR | Default transaction currency |
| `EDI_PARTNER` | BOOLEAN | Whether the retailer is an active SPS EDI trading partner |
| `PO_REVISION_METHOD` | VARCHAR | How the retailer handles PO changes (`EDI_860`, `REPLACEMENT_850`, `PORTAL`) |
| `USES_UPC` | BOOLEAN | Whether the retailer uses UPC as the primary product identifier |
| `ACTIVITY_GRAIN` | VARCHAR | Granularity of the activity feed (`WEEKLY`, `DAILY`) |

### RETAIL_CALENDAR

Fiscal/retail calendar reference. 106 weeks.

| Column | Type | Description |
|--------|------|-------------|
| `PERIOD_ENDING_DATE` | NUMBER | Week-ending date in `YYYYMMDD` format (join key to `SPS_ACTIVITY`) |
| `FISCAL_YEAR` | NUMBER | Fiscal year |
| `FISCAL_QUARTER` | NUMBER | Fiscal quarter (1-4) |
| `FISCAL_MONTH` | NUMBER | Fiscal month (1-12) |
| `FISCAL_WEEK` | NUMBER | Fiscal week number |
| `IS_HOLIDAY_WEEK` | BOOLEAN | Whether this week is a designated holiday sales period |
| `SEASON` | VARCHAR | Season label (`SPRING`, `SUMMER`, `FALL`, `WINTER`) |

### ITEM (partial contribution)

SPS contributes mapping keys and category attributes. 3,580 products. Retailer-specific columns (e.g., `SIZE_NAME`, `URBN_SHORT_SKU`) come from the retailers.

| Column | Type | Description |
|--------|------|-------------|
| `ITEM_ID` | NUMBER | Primary key |
| `RETAILER_ID` | NUMBER | Foreign key to `RETAILER` |
| `SPS_RETAILER_NAME_KEY` | VARCHAR | SPS mapping key linking this item to activity data |
| `CATEGORY_NAME` | VARCHAR | Product category |
| `PRODUCT_GROUP_NAME` | VARCHAR | Product sub-group |
| `UPC` | VARCHAR | Universal Product Code |
| `SKU` | VARCHAR | Stock Keeping Unit |
| `BRAND_NAME` | VARCHAR | Brand name |
| `MSRP` | NUMBER | Manufacturer's suggested retail price |
| `COST` | NUMBER | Wholesale cost |
| `SUPPLIER_ID` | NUMBER | Foreign key to `SUPPLIER` |
| `PRODUCT_SEASON` | VARCHAR | Season the product is designated for |
| `LAUNCH_DATE` | DATE | Date the product became available |
| `EXIT_DATE` | DATE | Date the product was discontinued |

### LOCATION (partial contribution)

SPS contributes base location identifiers. 60 stores. Retailer-specific attributes (e.g., `BANNER`, `CLIMATE`) come from the retailers.

| Column | Type | Description |
|--------|------|-------------|
| `LOCATION_ID` | NUMBER | Primary key |
| `RETAILER_ID` | NUMBER | Foreign key to `RETAILER` |
| `STORE_NUMBER` | VARCHAR | Retailer-assigned store number |
| `STORE_NAME` | VARCHAR | Store display name |
| `LOCATION_TYPE` | VARCHAR | Type of location (`STORE`, `DC`, `OUTLET`) |
| `ADDRESS` | VARCHAR | Street address |
| `CITY` | VARCHAR | City |
| `STATE` | VARCHAR | State/province |
| `POSTAL_CODE` | VARCHAR | Postal/ZIP code |
| `COUNTRY` | VARCHAR | Country |

---

## The SPS Activity Schema

The `SPS_ACTIVITY` table mirrors the real SPS Commerce Analytics Marketplace share. In production, this data is delivered as a Snowflake Secure Share with weekly refreshes. Key characteristics:

- **Grain:** One row per item per location per week
- **Period format:** `PERIOD_ENDING_DATE` is a `NUMBER` in `YYYYMMDD` format (not a `DATE`), matching the actual share schema
- **SPS keys:** The `SPS_CUSTOMER_ITEM_KEY`, `SPS_RETAILER_NAME_KEY`, `SPS_CUSTOMER_LOCATION_KEY`, and `SPS_ITEM_MAPPING_KEY` columns are SPS-assigned identifiers that must be joined to retailer reference data to resolve to human-readable product and store names
- **Coverage:** 106 weekly periods, 3 retailers, ~27,250 rows per period on average
