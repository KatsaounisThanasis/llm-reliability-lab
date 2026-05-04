import logging
import time
from typing import Any

from litellm import completion

from cli import Ansi
from cost import get_cost_usd
from entities import EvalConfig, ModelSummary, PromptCase, PromptResult


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

    logging.warning("Could not extract response text from model output.")
    return ""


def _evaluate_prompt(
    case: PromptCase,
    model: str,
    api_base: str | None,
    api_key: str | None,
    num_retries: int,
) -> tuple[str, float, float | None, float]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an evaluation assistant. Return concise answers only."},
            {"role": "user", "content": case.prompt},
        ],
        "temperature": 0,
        "num_retries": num_retries,
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
    accuracy = 1.0 if case.expected.strip().lower() == output.strip().lower() else 0.0
    return output, latency, cost, accuracy


def evaluate_model(model: str, dataset: list[PromptCase], config: EvalConfig, ansi: Ansi) -> ModelSummary:
    print(f"\nRunning evaluation with model={ansi.info(model)}")
    print("-" * 72)

    results: list[PromptResult] = []
    error_count = 0
    for idx, case in enumerate(dataset, start=1):
        try:
            output, latency, cost, accuracy = _evaluate_prompt(
                case=case,
                model=model,
                api_base=config.api_base,
                api_key=config.api_key,
                num_retries=config.num_retries,
            )
            result = PromptResult(
                index=idx,
                prompt=case.prompt,
                expected=case.expected,
                response_text=output,
                latency_seconds=latency,
                cost_usd=cost,
                accuracy=accuracy,
            )
        except Exception as exc:
            error_count += 1
            result = PromptResult(
                index=idx,
                prompt=case.prompt,
                expected=case.expected,
                response_text="",
                latency_seconds=None,
                cost_usd=None,
                accuracy=0.0,
                error=str(exc),
            )
        results.append(result)

        cost_text = f"${result.cost_usd:.6f}" if result.cost_usd is not None else "n/a"
        latency_text = f"{result.latency_seconds:.3f}s" if result.latency_seconds is not None else "n/a"
        row = (
            f"[{result.index}] latency={latency_text} | cost={cost_text} | "
            f"accuracy={result.accuracy:.0f} | expected='{result.expected}'"
        )
        if result.error:
            print(ansi.warning(f"{row} | error={result.error}"))
        else:
            print(row)

    successful_latency = [r.latency_seconds for r in results if r.latency_seconds is not None]
    successful_cost = [r.cost_usd for r in results if r.cost_usd is not None]

    avg_latency = (
        sum(successful_latency) / len(successful_latency)
        if successful_latency
        else None
    )
    avg_cost = sum(successful_cost) / len(successful_cost) if successful_cost else None
    avg_accuracy = sum(r.accuracy for r in results) / len(results)
    error_rate = error_count / len(results)

    failures: list[str] = []
    if avg_accuracy < config.thresholds.accuracy_min:
        failures.append(
            f"average accuracy {avg_accuracy:.3f} < threshold {config.thresholds.accuracy_min:.3f}"
        )
    if avg_latency is None:
        failures.append("average latency unavailable (all requests failed)")
    elif avg_latency > config.thresholds.latency_max_seconds:
        failures.append(
            f"average latency {avg_latency:.3f}s > threshold {config.thresholds.latency_max_seconds:.3f}s"
        )
    if avg_cost is None:
        failures.append("average cost unavailable (no valid cost metadata)")
    elif avg_cost > config.thresholds.cost_max_usd:
        failures.append(
            f"average cost ${avg_cost:.6f} > threshold ${config.thresholds.cost_max_usd:.6f}"
        )
    if error_rate > config.thresholds.error_rate_max:
        failures.append(
            f"error rate {error_rate:.3f} > threshold {config.thresholds.error_rate_max:.3f}"
        )

    passed = not failures
    status = ansi.success("PASSED") if passed else ansi.error("FAILED")
    avg_latency_text = f"{avg_latency:.3f}s" if avg_latency is not None else "n/a"
    avg_cost_text = f"${avg_cost:.6f}" if avg_cost is not None else "n/a"

    print("-" * 72)
    print(f"Average Latency : {avg_latency_text}")
    print(f"Average Cost    : {avg_cost_text}")
    print(f"Average Accuracy: {avg_accuracy:.3f}")
    print(f"Error Rate      : {error_rate:.3f}")
    print(f"Result          : {status}")
    for reason in failures:
        print(f"- {reason}")

    return ModelSummary(
        model=model,
        avg_latency_seconds=avg_latency,
        avg_cost_usd=avg_cost,
        avg_accuracy=avg_accuracy,
        error_rate=error_rate,
        passed=passed,
        failure_reasons=failures,
        successful_requests=len(results) - error_count,
        total_requests=len(results),
        cases=results,
    )


def pick_winner(results: list[ModelSummary]) -> ModelSummary | None:
    passing = [result for result in results if result.passed]
    if not passing:
        return None
    return sorted(
        passing,
        key=lambda r: (
            -r.avg_accuracy,
            r.avg_cost_usd if r.avg_cost_usd is not None else float("inf"),
            r.avg_latency_seconds if r.avg_latency_seconds is not None else float("inf"),
        ),
    )[0]
