from types import SimpleNamespace

from entities import EvalConfig, ModelSummary, PromptCase, Thresholds
from runner import evaluate_model, extract_text, pick_winner


def _summary(model: str, passed: bool, accuracy: float, cost: float | None, latency: float | None) -> ModelSummary:
    return ModelSummary(
        model=model,
        avg_latency_seconds=latency,
        avg_cost_usd=cost,
        avg_accuracy=accuracy,
        error_rate=0.0,
        passed=passed,
        failure_reasons=[],
        successful_requests=5,
        total_requests=5,
        cases=[],
    )


def _config(tmp_path) -> EvalConfig:
    return EvalConfig(
        dataset_path=tmp_path / "dataset.json",
        models=["test-model"],
        api_base=None,
        api_key=None,
        thresholds=Thresholds(
            accuracy_min=0.5,
            latency_max_seconds=5.0,
            cost_max_usd=1.0,
            error_rate_max=0.0,
        ),
        report_dir=tmp_path,
    )


def test_pick_winner_uses_only_passed_models():
    failed_high_accuracy = _summary("model-failed", passed=False, accuracy=0.99, cost=0.01, latency=0.3)
    passed_model = _summary("model-passed", passed=True, accuracy=0.85, cost=0.001, latency=0.2)

    winner = pick_winner([failed_high_accuracy, passed_model])
    assert winner is not None
    assert winner.model == "model-passed"


def test_pick_winner_returns_none_when_all_failed():
    result = pick_winner(
        [
            _summary("m1", passed=False, accuracy=0.8, cost=0.002, latency=1.0),
            _summary("m2", passed=False, accuracy=0.7, cost=0.003, latency=1.1),
        ]
    )
    assert result is None


def test_extract_text_from_object_response():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=" hello "))]
    )
    assert extract_text(response) == "hello"


def test_extract_text_from_dict_response():
    response = {"choices": [{"message": {"content": " world "}}]}
    assert extract_text(response) == "world"


def test_evaluate_model_handles_request_errors(monkeypatch, tmp_path):
    config = _config(tmp_path)
    dataset = [PromptCase(prompt="p1", expected="ok"), PromptCase(prompt="p2", expected="ok")]

    def fail_completion(**kwargs):
        raise RuntimeError("429 Too Many Requests")

    monkeypatch.setattr("runner.completion", fail_completion)
    summary = evaluate_model("test-model", dataset, config)

    assert summary.passed is False
    assert summary.error_rate == 1.0
    assert summary.avg_latency_seconds is None
    assert summary.avg_cost_usd is None
    assert any("error rate" in reason for reason in summary.failure_reasons)
    assert all(case.error is not None for case in summary.cases)


def test_evaluate_model_supports_contains_match_mode(monkeypatch, tmp_path):
    config = _config(tmp_path)
    dataset = [PromptCase(prompt="p1", expected="devops", match_mode="contains")]

    def success_completion(**kwargs):
        return {"choices": [{"message": {"content": "hello devops team"}}]}

    monkeypatch.setattr("runner.completion", success_completion)
    summary = evaluate_model("test-model", dataset, config)

    assert summary.avg_accuracy == 1.0
