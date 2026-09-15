import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import app  # noqa: E402


def cases() -> list[dict]:
    data = json.loads((ROOT / "evaluation" / "dataset.json").read_text(encoding="utf-8"))
    result = []
    for index in range(data["expansion"]["count"]):
        template = dict(data["templates"][index % len(data["templates"])])
        result.append(template)
    return result


def run() -> dict:
    totals = {"success": 0, "action_correct": 0, "tool_selection_correct": 0, "sla_detection_correct": 0, "verification_success": 0, "retries": 0, "tools": 0, "latency_ms": 0.0}
    with TestClient(app) as client:
        for case in cases():
            payload = {key: value for key, value in case.items() if key not in {"category", "expected_action"}}
            started = time.perf_counter()
            created = client.post("/api/incidents", json=payload)
            incident_id = created.json()["id"]
            resolution = client.post(f"/api/incidents/{incident_id}/resolve").json()
            details = client.get(f"/api/incidents/{incident_id}").json()
            tools = client.get(f"/api/incidents/{incident_id}/tools").json()
            elapsed = (time.perf_counter() - started) * 1000
            decision = resolution.get("decision") or {}
            totals["success"] += resolution.get("status") == "resolved"
            totals["action_correct"] += decision.get("action") == case["expected_action"]
            totals["tool_selection_correct"] += {item["tool_name"] for item in tools} >= {"get_order_details", "calculate_sla_risk"}
            totals["sla_detection_correct"] += (case["category"] == "SLA risk") == any(item.get("output", {}).get("likely_violation") for item in tools)
            totals["verification_success"] += bool(resolution.get("verification", {}).get("resolved"))
            totals["retries"] += details.get("retry_count", 0)
            totals["tools"] += len(tools)
            totals["latency_ms"] += elapsed
    count = len(cases())
    results = {"case_count": count, "resolution_success_rate": totals["success"] / count,
               "action_selection_accuracy": totals["action_correct"] / count,
               "tool_selection_accuracy": totals["tool_selection_correct"] / count,
               "sla_risk_detection_accuracy": totals["sla_detection_correct"] / count,
               "verification_success_rate": totals["verification_success"] / count,
               "average_tool_calls": totals["tools"] / count,
               "average_latency_ms": totals["latency_ms"] / count,
               "retry_rate": totals["retries"] / count}
    results_path = ROOT / "evaluation" / "results" / "latest.json"
    results_path.parent.mkdir(exist_ok=True)
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print("\nMetric                         Value")
    print("-----------------------------  ------")
    for key, value in results.items():
        print(f"{key:29}  {value}")
    return results


if __name__ == "__main__":
    run()
