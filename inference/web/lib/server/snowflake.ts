/**
 * Server-only client for the inference add-on (TypeScript port of ../../score_client.py).
 * Plain HTTPS + PAT, no Snowflake driver:
 *   fetchSamples() -> SQL REST API (/api/v2/statements)  -> ML_INFERENCE.SAMPLE_REQUESTS
 *   score()        -> Snowflake ML real-time inference endpoint (/predict-proba on SPCS)
 *   explain()      -> Cortex REST API (/api/v2/cortex/v1/chat/completions)
 *
 * Config is read from inference/.env (shared with the Python client) or process env:
 *   INFERENCE_URL, CORTEX_BASE_URL (optional), SNOWFLAKE_PAT (optional),
 *   SNOWFLAKE_CONNECTION_NAME (default coco_conn; PAT/account/warehouse fallback).
 * The PAT never leaves the server.
 */
import "server-only";
import fs from "fs";
import os from "os";
import path from "path";
import { parse as parseToml } from "smol-toml";
import { CATEGORICAL, CORTEX_MODEL, FEATURES, NUMERIC, type OrderRecord } from "@/lib/model";

const TIMEOUT_MS = 60_000;

let envCache: Record<string, string> | null = null;

function fileEnv(): Record<string, string> {
  if (envCache) return envCache;
  envCache = {};
  const envPath = path.resolve(process.cwd(), "..", ".env");
  if (fs.existsSync(envPath)) {
    for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (m) envCache[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  }
  return envCache;
}

function env(name: string): string {
  return (process.env[name] || fileEnv()[name] || "").trim();
}

function connection(): Record<string, string> {
  const home = process.env.SNOWFLAKE_HOME || path.join(os.homedir(), ".snowflake");
  const tomlPath = path.join(home, "connections.toml");
  if (!fs.existsSync(tomlPath)) return {};
  const name = env("SNOWFLAKE_CONNECTION_NAME") || "coco_conn";
  const parsed = parseToml(fs.readFileSync(tomlPath, "utf8")) as Record<string, Record<string, string>>;
  return parsed[name] || {};
}

function pat(): string {
  const token = env("SNOWFLAKE_PAT") || connection().token;
  if (!token) throw new Error("No PAT found. Set SNOWFLAKE_PAT in inference/.env or use a PAT-based connection.");
  return token;
}

export function inferenceUrl(): string {
  const url = env("INFERENCE_URL").replace(/\/+$/, "");
  if (!url) throw new Error("Set INFERENCE_URL in inference/.env (see SHOW ENDPOINTS IN SERVICE ...).");
  return url.startsWith("http") ? url : `https://${url}`;
}

export function accountBaseUrl(): string {
  const url = env("CORTEX_BASE_URL").replace(/\/+$/, "");
  if (url) return url;
  const account = connection().account;
  if (!account) throw new Error("Set CORTEX_BASE_URL in inference/.env.");
  // Hostnames can't contain underscores; Snowflake accepts the hyphenated account form.
  return `https://${account.replace(/_/g, "-").toLowerCase()}.snowflakecomputing.com`;
}

function bearerHeaders() {
  return {
    Authorization: `Bearer ${pat()}`,
    "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
    "Content-Type": "application/json",
    Accept: "application/json",
  };
}

async function timedPost(url: string, headers: Record<string, string>, body: unknown) {
  const start = performance.now();
  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(TIMEOUT_MS),
    cache: "no-store",
  });
  const latencyMs = Math.round(performance.now() - start);
  const text = await resp.text();
  return { resp, text, latencyMs };
}

export async function fetchSamples(): Promise<OrderRecord[]> {
  const conn = connection();
  const url = `${accountBaseUrl()}/api/v2/statements`;
  const { resp, text } = await timedPost(url, bearerHeaders(), {
    statement: "SELECT * FROM SPS_RETAIL_AI.ML_INFERENCE.SAMPLE_REQUESTS ORDER BY EXPECTED_RISK_PROB",
    timeout: 60,
    warehouse: env("SNOWFLAKE_WAREHOUSE") || conn.warehouse,
    role: env("SNOWFLAKE_ROLE") || conn.role,
  });
  if (resp.status !== 200) throw new Error(`SQL API call failed: HTTP ${resp.status} ${text.slice(0, 300)}`);
  const body = JSON.parse(text) as {
    resultSetMetaData: { rowType: { name: string; type: string }[] };
    data: (string | null)[][];
  };
  const cols = body.resultSetMetaData.rowType;
  return body.data.map((row) => {
    const rec: OrderRecord = {};
    cols.forEach((c, i) => {
      const v = row[i];
      rec[c.name] = v !== null && ["fixed", "real"].includes(c.type.toLowerCase()) ? Number(v) : (v ?? "");
    });
    return rec;
  });
}

export function buildPayload(records: OrderRecord[]) {
  return {
    dataframe_split: {
      index: records.map((_, i) => i),
      columns: FEATURES,
      data: records.map((r) => [
        ...CATEGORICAL.map((c) => String(r[c] || "UNKNOWN")),
        ...NUMERIC.map((c) => (r[c] === undefined || r[c] === null || r[c] === "" ? null : Number(r[c]))),
      ]),
    },
  };
}

export async function score(records: OrderRecord[]) {
  const payload = buildPayload(records);
  const url = `${inferenceUrl()}/predict-proba`;
  const { resp, text, latencyMs } = await timedPost(
    url,
    { Authorization: `Snowflake Token="${pat()}"`, "Content-Type": "application/json" },
    payload,
  );
  // SPCS returns 404 for auth/network failures as well as bad URLs.
  if (resp.status !== 200) throw new Error(`Inference call failed: HTTP ${resp.status} ${text.slice(0, 300)}`);
  const body = JSON.parse(text) as { data: [number, Record<string, number>][] };
  // predict_proba of a binary classifier -> output_feature_1 = P(late/short)
  const results = body.data.map((row) => {
    const p = Number(row[1]?.output_feature_1 ?? 0);
    return { row: row[0], riskProbability: p, riskClass: p >= 0.5 ? 1 : 0 };
  });
  return { url, latencyMs, request: payload, response: body, results };
}

export async function explain(record: OrderRecord, riskProbability: number) {
  const url = `${accountBaseUrl()}/api/v2/cortex/v1/chat/completions`;
  const facts = Object.fromEntries(FEATURES.map((k) => [k, record[k]]));
  const prompt =
    "You are a retail supply-chain analyst. A model scored this purchase order's risk of arriving " +
    `late or short at ${Math.round(riskProbability * 100)}%.\n` +
    `PO attributes (JSON): ${JSON.stringify(facts)}\n` +
    "Field notes: HIST_* = this supplier/retailer pair's historical rates; DAYS_TO_SHIP / DAYS_TO_DELIVER = " +
    "observed ship and transit days; SUPPLIER_AVG_LEAD = supplier's typical lead days.\n" +
    "In 3 short sentences for an operations lead: what most likely drives this score, and one concrete action. " +
    "No preamble, no markdown headers.";
  const { resp, text, latencyMs } = await timedPost(url, bearerHeaders(), {
    model: CORTEX_MODEL,
    messages: [{ role: "user", content: prompt }],
    max_completion_tokens: 250,
  });
  if (resp.status !== 200) throw new Error(`Cortex REST call failed: HTTP ${resp.status} ${text.slice(0, 300)}`);
  const body = JSON.parse(text) as { choices: { message: { content: string } }[] };
  return { url, latencyMs, model: CORTEX_MODEL, text: body.choices[0].message.content.trim() };
}
