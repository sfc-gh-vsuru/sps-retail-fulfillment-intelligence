"""
Shared client for the inference add-on. Plain HTTPS + PAT — no Snowflake driver needed.

  score()    -> Snowflake ML real-time inference endpoint (Model Registry model on SPCS)
  explain()  -> Cortex REST API (chat/completions) for a plain-English explanation

Config (environment variables or inference/.env):
  INFERENCE_URL     https://<id>.snowflakecomputing.app           (SHOW ENDPOINTS IN SERVICE ...)
  CORTEX_BASE_URL   https://<account>.snowflakecomputing.com      (optional, derived from connection)
  SNOWFLAKE_PAT     programmatic access token                     (optional, falls back to connections.toml)
  SNOWFLAKE_CONNECTION_NAME  connection to read the PAT/account from (default: coco_conn)
"""

import json
import os
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

CATEGORICAL = ["RETAILER_ID", "SUPPLIER_REGION", "DESTINATION_REGION", "DESTINATION_SIZE", "LOCATION_TYPE"]
NUMERIC = [
    "IS_REPLACEMENT_850", "PO_VERSION", "TOTAL_UNITS", "TOTAL_COST", "LINE_COUNT", "TOTAL_LINE_QTY",
    "DISTINCT_ITEMS", "ORDER_DOW", "ORDER_MONTH", "SUPPLIER_AVG_LEAD", "SUPPLIER_LEAD_VAR",
    "HIST_ON_TIME_RATE", "HIST_IN_FULL_RATE", "HIST_OTIF_RATE", "HIST_AVG_DAYS_LATE", "HIST_PO_COUNT",
    "DAYS_TO_SHIP", "DAYS_TO_DELIVER",
]
FEATURES = CATEGORICAL + NUMERIC

CORTEX_MODEL = "claude-sonnet-4-5"
TIMEOUT_SECS = 60


def _connection() -> dict:
    """Read the named connection from ~/.snowflake/connections.toml (only used as a PAT/account fallback)."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    path = Path(os.environ.get("SNOWFLAKE_HOME", Path.home() / ".snowflake")) / "connections.toml"
    if not path.exists():
        return {}
    name = os.environ.get("SNOWFLAKE_CONNECTION_NAME", "coco_conn")
    with open(path, "rb") as f:
        return tomllib.load(f).get(name, {})


def _pat() -> str:
    token = os.environ.get("SNOWFLAKE_PAT") or _connection().get("token")
    if not token:
        raise RuntimeError("No PAT found. Set SNOWFLAKE_PAT in inference/.env or use a PAT-based connection.")
    return token


def inference_url() -> str:
    url = os.environ.get("INFERENCE_URL", "").strip().rstrip("/")
    if not url:
        raise RuntimeError("Set INFERENCE_URL in inference/.env (see SHOW ENDPOINTS IN SERVICE ...).")
    return url if url.startswith("http") else f"https://{url}"


def cortex_base_url() -> str:
    url = os.environ.get("CORTEX_BASE_URL", "").strip().rstrip("/")
    if url:
        return url
    account = _connection().get("account", "")
    if not account:
        raise RuntimeError("Set CORTEX_BASE_URL in inference/.env.")
    # Hostnames can't contain underscores; Snowflake accepts the hyphenated account form.
    return f"https://{account.replace('_', '-').lower()}.snowflakecomputing.com"


def _normalize(record: dict) -> list:
    """Order and type one PO record to match the model signature (strings + floats)."""
    row = []
    for c in CATEGORICAL:
        row.append(str(record.get(c) or "UNKNOWN"))
    for c in NUMERIC:
        v = record.get(c)
        if isinstance(v, bool):
            v = int(v)
        row.append(None if v is None else float(v))
    return row


def build_payload(records: list[dict]) -> dict:
    return {
        "dataframe_split": {
            "index": list(range(len(records))),
            "columns": FEATURES,
            "data": [_normalize(r) for r in records],
        }
    }


def score(records: list[dict]) -> dict:
    """POST to /predict-proba. Returns probabilities plus the raw request/response for display."""
    payload = build_payload(records)
    url = f"{inference_url()}/predict-proba"
    headers = {"Authorization": f'Snowflake Token="{_pat()}"', "Content-Type": "application/json"}

    start = time.perf_counter()
    resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECS)
    latency_ms = round((time.perf_counter() - start) * 1000)
    if resp.status_code != 200:
        # SPCS returns 404 for auth/network failures as well as bad URLs.
        raise RuntimeError(f"Inference call failed: HTTP {resp.status_code} {resp.text[:300]}")
    body = resp.json()

    results = []
    for row in body.get("data", []):
        out = row[1] if len(row) > 1 and isinstance(row[1], dict) else {}
        # predict_proba of a binary classifier -> output_feature_0 = P(on-time), output_feature_1 = P(late/short)
        p_risk = float(out.get("output_feature_1", 0.0))
        results.append({"row": row[0], "risk_probability": p_risk, "risk_class": int(p_risk >= 0.5)})

    return {"url": url, "latency_ms": latency_ms, "request": payload, "response": body, "results": results}


def explain(record: dict, risk_probability: float) -> dict:
    """Ask Cortex (Claude) for a short, plain-English explanation of a single score."""
    url = f"{cortex_base_url()}/api/v2/cortex/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {_pat()}",
        "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
        "Content-Type": "application/json",
    }
    facts = {k: record.get(k) for k in FEATURES}
    prompt = (
        "You are a retail supply-chain analyst. A model scored this purchase order's risk of arriving "
        f"late or short at {risk_probability:.0%}.\n"
        f"PO attributes (JSON): {json.dumps(facts, default=str)}\n"
        "Field notes: HIST_* = this supplier/retailer pair's historical rates; DAYS_TO_SHIP / DAYS_TO_DELIVER = "
        "observed ship and transit days; SUPPLIER_AVG_LEAD = supplier's typical lead days.\n"
        "In 3 short sentences for an operations lead: what most likely drives this score, and one concrete action. "
        "No preamble, no markdown headers."
    )
    payload = {
        "model": CORTEX_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 250,
    }

    start = time.perf_counter()
    resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECS)
    latency_ms = round((time.perf_counter() - start) * 1000)
    if resp.status_code != 200:
        raise RuntimeError(f"Cortex REST call failed: HTTP {resp.status_code} {resp.text[:300]}")
    body = resp.json()
    text = body["choices"][0]["message"]["content"]
    return {"url": url, "latency_ms": latency_ms, "text": text.strip(), "response": body}


def load_samples() -> list[dict]:
    return json.loads(Path(__file__).with_name("sample_requests.json").read_text())
