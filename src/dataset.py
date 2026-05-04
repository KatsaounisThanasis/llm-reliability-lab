import json
from pathlib import Path

from entities import PromptCase


def load_dataset(dataset_path: Path) -> list[PromptCase]:
    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        raise ValueError("Dataset must be a non-empty JSON array.")

    cases: list[PromptCase] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Dataset item at index {i} is not an object.")
        if "prompt" not in item or "expected" not in item:
            raise ValueError(f"Dataset item at index {i} must contain 'prompt' and 'expected'.")
        prompt = item["prompt"]
        expected = item["expected"]
        if not isinstance(prompt, str) or not isinstance(expected, str):
            raise ValueError(f"'prompt' and 'expected' must be strings at index {i}.")
        prompt = prompt.strip()
        expected = expected.strip()
        if not prompt or not expected:
            raise ValueError(f"'prompt' and 'expected' must be non-empty at index {i}.")

        match_mode_raw = item.get("match_mode", "exact")
        if not isinstance(match_mode_raw, str):
            raise ValueError(f"'match_mode' must be a string at index {i}.")
        match_mode = match_mode_raw.strip().lower()
        if match_mode not in {"exact", "contains"}:
            raise ValueError(f"'match_mode' must be either 'exact' or 'contains' at index {i}.")

        cases.append(PromptCase(prompt=prompt, expected=expected, match_mode=match_mode))

    return cases
