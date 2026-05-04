import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from litellm import completion, completion_cost


class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"


def colorize(text: str, color: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{color}{text}{Ansi.RESET}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM reliability evaluation.")
    parser.add_argument("--dataset", help="Path to dataset JSON file.")
    parser.add_argument("--models", help="Comma-separated model list.")
    parser.add_argument("--api-base", help="LiteLLM api_base override.")
    parser.add_argument("--api-key", help="LiteLLM/OpenAI/Gemini API key.")
    parser.add_argument("--accuracy-threshold", type=float, help="Minimum average accuracy.")
    parser.add_argument("--latency-threshold", type=float, help="Maximum average latency in seconds.")
    parser.add_argument("--cost-threshold", type=float, help="Maximum average cost in USD.")
    parser.add_argument("--report-dir", help="Directory to write JSON reports.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colored output.")
    return parser.parse_args()


def supports_color(no_color: bool) -> bool:
    return (not no_color) and sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def pick_value(cli_value: Any, env_key: str, default: Any) -> Any:
    return cli_value if cli_value is not None else os.getenv(env_key, default)


def parse_models(raw_models: str) -> list[str]:
    models = [m.strip() for m in raw_models.split(",") if m.strip()]
    if not models:
        raise ValueError("No models were provided. Use --models or LITELLM_MODEL.")
    return models


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
    except (AttributeError, IndexError, TypeError):
        pass

    try:
        content = response["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content.strip()
    except (KeyError, IndexError, TypeError):
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
    except (TypeError, ValueError, AttributeError, KeyError):
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


def evaluate_model(
    model: str,
    dataset: list[dict[str, str]],
    api_base: str | None,
    api_key: str | None,
    accuracy_threshold: float,
    latency_threshold: float,
    cost_threshold: float,
    use_color: bool,
) -> dict[str, Any]:
    latencies: list[float] = []
    costs: list[float] = []
    accuracies: list[float] = []
    per_case: list[dict[str, Any]] = []
    error_count = 0

    print(f"\nRunning evaluation with model={colorize(model, Ansi.CYAN, use_color)}")
    print("-" * 72)

    for idx, item in enumerate(dataset, start=1):
        prompt = item["prompt"]
        expected = item["expected"]
        case_error = None

        try:
            latency, cost, accuracy = evaluate_prompt(
                prompt=prompt,
                expected=expected,
                model=model,
                api_base=api_base,
                api_key=api_key,
            )
        except Exception as exc:
            latency = latency_threshold + 1.0
            cost = cost_threshold + 0.001
            accuracy = 0.0
            case_error = str(exc)
            error_count += 1

        latencies.append(latency)
        costs.append(cost)
        accuracies.append(accuracy)

        row = {
            "index": idx,
            "prompt": prompt,
            "expected": expected,
            "latency_seconds": latency,
            "cost_usd": cost,
            "accuracy": accuracy,
        }
        if case_error:
            row["error"] = case_error
        per_case.append(row)

        line = (
            f"[{idx}] latency={latency:.3f}s | cost=${cost:.6f} | "
            f"accuracy={accuracy:.0f} | expected='{expected}'"
        )
        if case_error:
            line += f" | error={case_error}"
            print(colorize(line, Ansi.YELLOW, use_color))
        else:
            print(line)

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
    if error_count > 0:
        failures.append(f"{error_count} request(s) failed during model evaluation")

    passed = len(failures) == 0
    status = colorize("PASSED", Ansi.GREEN, use_color) if passed else colorize("FAILED", Ansi.RED, use_color)

    print("-" * 72)
    print(f"Average Latency : {avg_latency:.3f}s")
    print(f"Average Cost    : ${avg_cost:.6f}")
    print(f"Average Accuracy: {avg_accuracy:.3f}")
    print(f"Result          : {status}")
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
            -r["avg_accuracy"],
            r["avg_cost_usd"],
            r["avg_latency_seconds"],
        ),
    )[0]


def write_report(
    report_dir: Path,
    results: list[dict[str, Any]],
    winner: dict[str, Any],
    thresholds: dict[str, float],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"eval_report_{ts}.json"

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
    args = parse_args()
    use_color = supports_color(args.no_color)
    project_root = Path(__file__).resolve().parents[1]

    dataset_raw = pick_value(args.dataset, "DATASET_PATH", str(project_root / "data" / "dataset.json"))
    models_raw = pick_value(args.models, "LITELLM_MODEL", "gemini/gemini-2.5-flash")
    api_base = pick_value(args.api_base, "LITELLM_API_BASE", None)
    api_key = (
        args.api_key
        or os.getenv("LITELLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    accuracy_threshold = float(pick_value(args.accuracy_threshold, "ACCURACY_THRESHOLD", "0.8"))
    latency_threshold = float(pick_value(args.latency_threshold, "LATENCY_THRESHOLD", "2.0"))
    cost_threshold = float(pick_value(args.cost_threshold, "COST_THRESHOLD", "0.001"))
    report_dir = Path(pick_value(args.report_dir, "REPORT_DIR", str(project_root / "reports")))

    dataset_path = Path(dataset_raw)
    dataset = load_dataset(dataset_path)
    models = parse_models(models_raw)

    print(colorize("LLM Reliability Benchmark Runner", Ansi.BOLD, use_color))
    print(f"Dataset   : {dataset_path}")
    print(f"Models    : {', '.join(models)}")
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
            use_color=use_color,
        )
        for model in models
    ]

    winner = pick_winner(results)
    report_path = write_report(
        report_dir=report_dir,
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
    print(f"Winner: {colorize(winner['model'], Ansi.CYAN, use_color)}")
    print(f"Report: {report_path}")

    if not passed_models:
        print(colorize("FAILED: all models failed thresholds.", Ansi.RED, use_color))
        sys.exit(1)

    print(
        colorize(
            f"PASSED: {len(passed_models)}/{len(results)} model(s) passed thresholds.",
            Ansi.GREEN,
            use_color,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
