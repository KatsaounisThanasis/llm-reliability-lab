import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from litellm import completion, completion_cost


def load_dataset(dataset_path: Path) -> list[dict[str, str]]:
    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        raise ValueError("Dataset must be a non-empty JSON array.")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Dataset item at index {i} is not an object.")
        if "prompt" not in item or "expected" not in item:
            raise ValueError(f"Dataset item at index {i} must contain 'prompt' and 'expected'.")
        if not isinstance(item["prompt"], str) or not isinstance(item["expected"], str):
            raise ValueError(f"'prompt' and 'expected' must be strings at index {i}.")

    return data


def extract_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content.strip()
    except Exception:
        pass

    try:
        content = response["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content.strip()
    except Exception:
        pass

    return ""


def estimate_dummy_cost(response: Any) -> float:
    prompt_tokens = 0
    completion_tokens = 0

    usage = None
    if hasattr(response, "usage"):
        usage = response.usage
    elif isinstance(response, dict):
        usage = response.get("usage")

    if usage:
        if isinstance(usage, dict):
            prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        else:
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

    total_tokens = prompt_tokens + completion_tokens
    return total_tokens * 0.000001


def get_cost_usd(response: Any) -> float:
    try:
        cost = completion_cost(completion_response=response)
        if cost is not None:
            return float(cost)
    except Exception:
        pass

    return estimate_dummy_cost(response)


def evaluate_prompt(
    prompt: str,
    expected: str,
    model: str,
    api_base: str | None,
    api_key: str | None,
) -> tuple[float, float, float]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an evaluation assistant. Return concise answers only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }

    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    start = time.perf_counter()
    response = completion(**kwargs)
    latency = time.perf_counter() - start

    output = extract_text(response)
    cost = get_cost_usd(response)
    accuracy = 1.0 if expected.strip().lower() in output.lower() else 0.0

    return latency, cost, accuracy


def parse_models(raw_models: str) -> list[str]:
    models = [m.strip() for m in raw_models.split(",") if m.strip()]
    if not models:
        raise ValueError("LITELLM_MODEL is empty. Provide at least one model.")
    return models


def evaluate_model(
    model: str,
    dataset: list[dict[str, str]],
    api_base: str | None,
    api_key: str | None,
    accuracy_threshold: float,
    latency_threshold: float,
    cost_threshold: float,
) -> dict[str, Any]:
    latencies: list[float] = []
    costs: list[float] = []
    accuracies: list[float] = []
    per_case: list[dict[str, Any]] = []

    print(f"\nRunning evaluation with model={model}")
    print("-" * 72)

    for idx, item in enumerate(dataset, start=1):
        prompt = item["prompt"]
        expected = item["expected"]

        latency, cost, accuracy = evaluate_prompt(
            prompt=prompt,
            expected=expected,
            model=model,
            api_base=api_base,
            api_key=api_key,
        )

        latencies.append(latency)
        costs.append(cost)
        accuracies.append(accuracy)
        per_case.append(
            {
                "index": idx,
                "prompt": prompt,
                "expected": expected,
                "latency_seconds": latency,
                "cost_usd": cost,
                "accuracy": accuracy,
            }
        )

        print(
            f"[{idx}] latency={latency:.3f}s | cost=${cost:.6f} | "
            f"accuracy={accuracy:.0f} | expected='{expected}'"
        )
        time.sleep(2)

    avg_latency = sum(latencies) / len(latencies)
    avg_cost = sum(costs) / len(costs)
    avg_accuracy = sum(accuracies) / len(accuracies)

    failures: list[str] = []
    if avg_accuracy < accuracy_threshold:
        failures.append(
            f"average accuracy {avg_accuracy:.3f} < threshold {accuracy_threshold:.3f}"
        )
    if avg_latency > latency_threshold:
        failures.append(
            f"average latency {avg_latency:.3f}s > threshold {latency_threshold:.3f}s"
        )
    if avg_cost > cost_threshold:
        failures.append(
            f"average cost ${avg_cost:.6f} > threshold ${cost_threshold:.6f}"
        )

    passed = len(failures) == 0

    print("-" * 72)
    print(f"Average Latency : {avg_latency:.3f}s")
    print(f"Average Cost    : ${avg_cost:.6f}")
    print(f"Average Accuracy: {avg_accuracy:.3f}")
    print(f"Result          : {'PASSED' if passed else 'FAILED'}")
    if failures:
        for reason in failures:
            print(f"- {reason}")

    return {
        "model": model,
        "avg_latency_seconds": avg_latency,
        "avg_cost_usd": avg_cost,
        "avg_accuracy": avg_accuracy,
        "passed": passed,
        "failure_reasons": failures,
        "cases": per_case,
    }


def pick_winner(results: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        results,
        key=lambda r: (
            -r["avg_accuracy"],     # highest accuracy first
            r["avg_cost_usd"],      # then lowest cost
            r["avg_latency_seconds"]  # then lowest latency
        ),
    )[0]


def write_report(
    project_root: Path,
    results: list[dict[str, Any]],
    winner: dict[str, Any],
    thresholds: dict[str, float],
) -> Path:
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = reports_dir / f"eval_report_{ts}.json"

    report_data = {
        "generated_at_utc": ts,
        "thresholds": thresholds,
        "winner": {
            "model": winner["model"],
            "avg_accuracy": winner["avg_accuracy"],
            "avg_latency_seconds": winner["avg_latency_seconds"],
            "avg_cost_usd": winner["avg_cost_usd"],
            "passed": winner["passed"],
        },
        "results": results,
    }

    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    return report_path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    dataset_path = Path(os.getenv("DATASET_PATH", project_root / "data" / "dataset.json"))

    raw_models = os.getenv("LITELLM_MODEL", "gemini/gemini-2.5-flash")
    api_base = os.getenv("LITELLM_API_BASE")
    api_key = (
        os.getenv("LITELLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    accuracy_threshold = float(os.getenv("ACCURACY_THRESHOLD", "0.8"))
    latency_threshold = float(os.getenv("LATENCY_THRESHOLD", "2.0"))
    cost_threshold = float(os.getenv("COST_THRESHOLD", "0.001"))

    dataset = load_dataset(dataset_path)
    models = parse_models(raw_models)

    print(f"Dataset: {dataset_path}")
    print(f"Models : {', '.join(models)}")
    print(
        "Thresholds: "
        f"accuracy>={accuracy_threshold:.3f}, "
        f"latency<={latency_threshold:.3f}s, "
        f"cost<=${cost_threshold:.6f}"
    )

    results = [
        evaluate_model(
            model=model,
            dataset=dataset,
            api_base=api_base,
            api_key=api_key,
            accuracy_threshold=accuracy_threshold,
            latency_threshold=latency_threshold,
            cost_threshold=cost_threshold,
        )
        for model in models
    ]

    winner = pick_winner(results)
    report_path = write_report(
        project_root=project_root,
        results=results,
        winner=winner,
        thresholds={
            "accuracy_threshold": accuracy_threshold,
            "latency_threshold_seconds": latency_threshold,
            "cost_threshold_usd": cost_threshold,
        },
    )

    passed_models = [r for r in results if r["passed"]]
    print("\n" + "=" * 72)
    print(f"Winner: {winner['model']}")
    print(f"Report: {report_path}")

    if not passed_models:
        print("FAILED: all models failed thresholds.")
        sys.exit(1)

    print(f"PASSED: {len(passed_models)}/{len(results)} model(s) passed thresholds.")


if __name__ == "__main__":
    main()
