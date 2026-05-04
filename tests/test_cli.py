import pytest

from cli import parse_models


def test_parse_models_comma_separated():
    models = parse_models("gemini/gemini-2.5-flash, gemini/gemini-1.5-flash")
    assert models == ["gemini/gemini-2.5-flash", "gemini/gemini-1.5-flash"]


def test_parse_models_empty_raises():
    with pytest.raises(ValueError, match="No models were provided"):
        parse_models(" , ")
