import json
from datetime import UTC, datetime
from pathlib import Path

from entities import ModelSummary, Thresholds


def write_report(
    report_dir: Path,
    results: list[ModelSummary],
    winner: ModelSummary | None,
    thresholds: Thresholds,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"eval_report_{ts}.json"

    all_failed = winner is None
    report_data: dict[str, object] = {
        "generated_at_utc": ts,
        "thresholds": {
            "accuracy_threshold": thresholds.accuracy_min,
            "latency_threshold_seconds": thresholds.latency_max_seconds,
            "cost_threshold_usd": thresholds.cost_max_usd,
            "error_rate_threshold": thresholds.error_rate_max,
        },
        "all_failed": all_failed,
        "winner": None,
        "results": [result.to_dict() for result in results],
    }

    if winner is not None:
        report_data["winner"] = {
            "model": winner.model,
            "avg_accuracy": winner.avg_accuracy,
            "avg_latency_seconds": winner.avg_latency_seconds,
            "avg_cost_usd": winner.avg_cost_usd,
            "error_rate": winner.error_rate,
            "passed": winner.passed,
        }

    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    return report_path
