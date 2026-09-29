# SPS Retail Fulfillment Intelligence

**Data Join + AI/ML for Retail Supply Chain**

SPS Commerce (data provider) supplies EDI transaction data across retail partners. Each retailer (Foot Locker, Bass Pro Shops, Urban Outfitters) contributes their unique operational context. The data join creates unified fulfillment visibility. Snowflake ML predicts which orders will fail before they do.

## What's Inside

| Folder | Contents |
|--------|----------|
| `apps/` | 5 Streamlit in Snowflake dashboards |
| `data/` | All CSV datasets (13 tables, ~2.9M activity rows) |
| `setup/` | SQL scripts and shell script to replicate from scratch |
| `*.md` | Data models per company, setup guide, demo talk track |

## Dashboards

1. **SPS Fulfillment Intelligence** — Cross-retailer OTIF, order-to-cash journey, ML risk predictions
2. **SPS + Foot Locker** — Multi-banner performance, size availability, ML risk by banner
3. **SPS + Bass Pro Shops** — Seasonal demand, regional sales, weeks of supply
4. **SPS + Urban Outfitters** — Replacement POs, SKU crosswalk health, pre-ship readiness
5. **SPS Partner Value Lab** — ML accuracy comparison, feature importance, data value proof

## Snowflake ML Features Used

- `SNOWFLAKE.ML.CLASSIFICATION` — Fulfillment risk prediction (91.3% accuracy)
- `SHOW_FEATURE_IMPORTANCE()` — Which SPS + retailer data points drive predictions
- Native Streamlit in Snowflake — No external dependencies

## Quick Start

See [SETUP.md](SETUP.md) for full replication instructions. Summary:

```bash
# 1. Create environment
snow sql -f setup/01_environment.sql --connection coco_conn

# 2. Upload data
bash setup/upload_data.sh coco_conn

# 3. Load tables and views
snow sql -f setup/02_load_data.sql --connection coco_conn
snow sql -f setup/03_views.sql --connection coco_conn

# 4. Train ML model and deploy apps
snow sql -f setup/04_ml_model.sql --connection coco_conn
snow sql -f setup/05_streamlit_apps.sql --connection coco_conn
```

## Documentation

- [SETUP.md](SETUP.md) — Full setup and replication guide
- [DEMO_TALK_TRACK.md](DEMO_TALK_TRACK.md) — Presenter walk-through for each dashboard
- [SPS_DATAMODEL.md](SPS_DATAMODEL.md) — SPS Commerce provider data model
- [FOOTLOCKER_DATAMODEL.md](FOOTLOCKER_DATAMODEL.md) — Foot Locker consumer data model
- [BASSPRO_DATAMODEL.md](BASSPRO_DATAMODEL.md) — Bass Pro Shops consumer data model
- [URBANOUTFITTERS_DATAMODEL.md](URBANOUTFITTERS_DATAMODEL.md) — Urban Outfitters consumer data model
