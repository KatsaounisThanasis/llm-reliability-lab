import json

import pytest

from dataset import load_dataset


def test_load_dataset_valid(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {"prompt": "p1", "expected": "e1"},
                {"prompt": "p2", "expected": "e2"},
            ]
        ),
        encoding="utf-8",
    )

    cases = load_dataset(dataset_path)
    assert len(cases) == 2
    assert cases[0].prompt == "p1"
    assert cases[0].expected == "e1"
    assert cases[0].match_mode == "exact"


def test_load_dataset_requires_prompt_and_expected(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps([{"prompt": "only"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="must contain 'prompt' and 'expected'"):
        load_dataset(dataset_path)


def test_load_dataset_rejects_empty_prompt_or_expected(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps([{"prompt": "   ", "expected": "ok"}]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be non-empty"):
        load_dataset(dataset_path)


def test_load_dataset_accepts_match_mode_contains(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps([{"prompt": "p", "expected": "e", "match_mode": "contains"}]),
        encoding="utf-8",
    )
    cases = load_dataset(dataset_path)
    assert cases[0].match_mode == "contains"
