import argparse
from pathlib import Path

import pytest

from cli import parse_models, resolve_config


def test_parse_models_comma_separated():
    models = parse_models("gemini/gemini-2.5-flash, gemini/gemini-1.5-flash")
    assert models == ["gemini/gemini-2.5-flash", "gemini/gemini-1.5-flash"]


def test_parse_models_empty_raises():
    with pytest.raises(ValueError, match="No models were provided"):
        parse_models(" , ")


def test_resolve_config_priority_cli_over_env_over_default(monkeypatch):
    monkeypatch.setenv("DATASET_PATH", "env-dataset.json")
    monkeypatch.setenv("LITELLM_MODEL", "env/model")
    monkeypatch.setenv("ERROR_RATE_THRESHOLD", "0.15")

    args = argparse.Namespace(
        dataset="cli-dataset.json",
        models="cli/model",
        api_base=None,
        api_key=None,
        accuracy_threshold=None,
        latency_threshold=None,
        cost_threshold=None,
        error_rate_threshold=0.05,
        report_dir=None,
        no_color=False,
    )

    config = resolve_config(args, Path("/tmp/project"))
    assert config.dataset_path == Path("cli-dataset.json")
    assert config.models == ["cli/model"]
    assert config.thresholds.error_rate_max == 0.05

    args.dataset = None
    args.models = None
    args.error_rate_threshold = None
    config_env = resolve_config(args, Path("/tmp/project"))
    assert config_env.dataset_path == Path("env-dataset.json")
    assert config_env.models == ["env/model"]
    assert config_env.thresholds.error_rate_max == 0.15

    monkeypatch.delenv("DATASET_PATH")
    monkeypatch.delenv("LITELLM_MODEL")
    monkeypatch.delenv("ERROR_RATE_THRESHOLD")
    config_default = resolve_config(args, Path("/tmp/project"))
    assert config_default.dataset_path == Path("/tmp/project/data/dataset.json")
    assert config_default.models == ["gemini/gemini-2.5-flash"]
    assert config_default.thresholds.error_rate_max == 0.0
