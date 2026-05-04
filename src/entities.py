from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class PromptCase:
    prompt: str
    expected: str
    match_mode: str = "exact"


@dataclass(frozen=True)
class Thresholds:
    accuracy_min: float
    latency_max_seconds: float
    cost_max_usd: float
    error_rate_max: float


@dataclass(frozen=True)
class EvalConfig:
    dataset_path: Path
    models: list[str]
    api_base: str | None
    api_key: str | None
    thresholds: Thresholds
    report_dir: Path


@dataclass
class PromptResult:
    index: int
    prompt: str
    expected: str
    response_text: str
    latency_seconds: float | None
    cost_usd: float | None
    accuracy: float
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], asdict(self))


@dataclass
class ModelSummary:
    model: str
    avg_latency_seconds: float | None
    avg_cost_usd: float | None
    avg_accuracy: float
    error_rate: float
    passed: bool
    failure_reasons: list[str]
    successful_requests: int
    total_requests: int
    cases: list[PromptResult]

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], asdict(self))
