// Shared (client + server) constants for the FULFILLMENT_RISK_XGB V2 model. Mirrors ../../score_client.py.

export type OrderRecord = Record<string, string | number>;

export const CATEGORICAL = ["RETAILER_ID", "SUPPLIER_REGION", "DESTINATION_REGION", "DESTINATION_SIZE", "LOCATION_TYPE"];
export const NUMERIC = [
  "IS_REPLACEMENT_850", "PO_VERSION", "TOTAL_UNITS", "TOTAL_COST", "LINE_COUNT", "TOTAL_LINE_QTY",
  "DISTINCT_ITEMS", "ORDER_DOW", "ORDER_MONTH", "SUPPLIER_AVG_LEAD", "SUPPLIER_LEAD_VAR",
  "HIST_ON_TIME_RATE", "HIST_IN_FULL_RATE", "HIST_OTIF_RATE", "HIST_AVG_DAYS_LATE", "HIST_PO_COUNT",
  "DAYS_TO_SHIP", "DAYS_TO_DELIVER",
];
export const FEATURES = [...CATEGORICAL, ...NUMERIC];

export const CORTEX_MODEL = "claude-sonnet-4-5";

export const RETAILERS: Record<string, string> = { FL: "Foot Locker", BP: "Bass Pro Shops", UO: "Urban Outfitters" };

// Share of historical POs that arrived late or short (TRAINING_DATA)
export const NETWORK_FAILURE_RATE = 0.183;

export const EDITABLE = ["RETAILER_ID", "TOTAL_UNITS", "TOTAL_COST", "DAYS_TO_SHIP", "DAYS_TO_DELIVER", "HIST_OTIF_RATE"];

export type BandKey = "high" | "watch" | "low";

export const BANDS: { min: number; key: BandKey; label: string; action: string }[] = [
  { min: 0.5, key: "high", label: "High risk", action: "Act now: contact the supplier, confirm the ship date, and plan for a shortfall at the store." },
  { min: 0.2, key: "watch", label: "Watch", action: "Keep an eye on it: check the ship notice (ASN) and carrier tracking before the due date." },
  { min: 0.0, key: "low", label: "Low risk", action: "No action needed: this order looks on track to arrive on time and in full." },
];

export function band(p: number) {
  return BANDS.find((b) => p >= b.min) ?? BANDS[BANDS.length - 1];
}
