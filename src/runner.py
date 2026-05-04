import logging
import time
from typing import Any

from litellm import completion
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

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


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    return "429" in message or "rate limit" in message or "too many requests" in message


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_random_exponential(multiplier=0.5, min=0.5, max=8.0),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _call_completion(kwargs: dict[str, Any]) -> Any:
    return completion(**kwargs)


def _compute_accuracy(case: PromptCase, output: str) -> float:
    expected = case.expected.strip().lower()
    candidate = output.strip().lower()
    if case.match_mode == "contains":
        return 1.0 if expected in candidate else 0.0
    return 1.0 if expected == candidate else 0.0


def _evaluate_prompt(
    case: PromptCase,
    model: str,
    api_base: str | None,
    api_key: str | None,
) -> tuple[str, float, float | None, float]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an evaluation assistant. Return concise answers only."},
            {"role": "user", "content": case.prompt},
        ],
        "temperature": 0,
    }

    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    start = time.perf_counter()
    response = _call_completion(kwargs)
    latency = time.perf_counter() - start

    output = extract_text(response)
    cost = get_cost_usd(response)
    accuracy = _compute_accuracy(case, output)
    return output, latency, cost, accuracy


def evaluate_model(model: str, dataset: list[PromptCase], config: EvalConfig) -> ModelSummary:
    results: list[PromptResult] = []
    error_count = 0

    for idx, case in enumerate(dataset, start=1):
        try:
            output, latency, cost, accuracy = _evaluate_prompt(
                case=case,
                model=model,
                api_base=config.api_base,
                api_key=config.api_key,
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

    return ModelSummary(
        model=model,
        avg_latency_seconds=avg_latency,
        avg_cost_usd=avg_cost,
        avg_accuracy=avg_accuracy,
        error_rate=error_rate,
        passed=not failures,
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
