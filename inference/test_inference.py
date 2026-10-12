"""
Inference Add-On — command-line test of both REST APIs (Python requests, no Snowflake driver).

    inference/.venv/bin/python inference/test_inference.py            # score all 6 samples + explain one
    inference/.venv/bin/python inference/test_inference.py --raw      # also print raw JSON
"""

import json
import sys

from score_client import explain, load_samples, score


def main() -> None:
    raw = "--raw" in sys.argv
    samples = load_samples()

    print("1) Snowflake ML real-time inference endpoint  (/predict-proba)")
    result = score(samples)
    print(f"   {result['url']}  ->  {result['latency_ms']} ms for {len(samples)} rows")
    for s, r in zip(samples, result["results"]):
        print(f"   {s['PO_ID']:<10} {s['SAMPLE_LABEL']:<10} actual={s['ACTUAL_OUTCOME']:<15} "
              f"risk={r['risk_probability']:.1%}  (training-time expectation {s['EXPECTED_RISK_PROB']:.1%})")
    if raw:
        print(json.dumps(result["response"], indent=2))

    high = max(zip(samples, result["results"]), key=lambda x: x[1]["risk_probability"])
    print("\n2) Cortex REST API  (chat/completions, claude-sonnet-4-5)")
    exp = explain(high[0], high[1]["risk_probability"])
    print(f"   {exp['url']}  ->  {exp['latency_ms']} ms")
    print(f"   {high[0]['PO_ID']}: {exp['text']}")


if __name__ == "__main__":
    main()
