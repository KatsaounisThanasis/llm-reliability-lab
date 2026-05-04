from entities import ModelSummary
from runner import pick_winner


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
