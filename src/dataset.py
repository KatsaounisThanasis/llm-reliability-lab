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
        cases.append(PromptCase(prompt=prompt, expected=expected))

    return cases
