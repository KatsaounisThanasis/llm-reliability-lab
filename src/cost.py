import logging

from litellm import completion_cost
from litellm.types.utils import ModelResponse


def estimate_dummy_cost(response: ModelResponse | dict[str, object]) -> float | None:
    usage = None
    if hasattr(response, "usage"):
        usage = response.usage
    elif isinstance(response, dict):
        usage = response.get("usage")

    if not usage:
        logging.warning("Cost usage metadata missing; skipping dummy cost calculation.")
        return None

    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
    else:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)

    if prompt_tokens is None or completion_tokens is None:
        logging.warning("Token counts missing in usage metadata; skipping dummy cost calculation.")
        return None

    total_tokens = int(prompt_tokens) + int(completion_tokens)
    return total_tokens * 0.000001


def get_cost_usd(response: ModelResponse | dict[str, object]) -> float | None:
    try:
        cost = completion_cost(completion_response=response)
        if cost is not None:
            return float(cost)
    except Exception as exc:
        logging.warning(
            "litellm completion_cost unavailable for this response (%s); using fallback.",
            type(exc).__name__,
        )
    return estimate_dummy_cost(response)
