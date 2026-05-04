import argparse
import os
from pathlib import Path

from entities import EvalConfig, Thresholds
from presentation import Ansi


def parse_models(raw_models: str) -> list[str]:
    models = [m.strip() for m in raw_models.split(",") if m.strip()]
    if not models:
        raise ValueError("No models were provided. Use --models or LITELLM_MODEL.")
    return models


def _pick_str(cli_value: str | None, env_key: str, default: str) -> str:
    return cli_value if cli_value is not None else os.getenv(env_key, default)


def _pick_optional_str(cli_value: str | None, env_key: str) -> str | None:
    return cli_value if cli_value is not None else os.getenv(env_key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM reliability evaluation.")
    parser.add_argument("--dataset", help="Path to dataset JSON file.")
    parser.add_argument("--models", help="Comma-separated model list.")
    parser.add_argument("--api-base", help="LiteLLM api_base override.")
    parser.add_argument("--api-key", help="LiteLLM/OpenAI/Gemini API key.")
    parser.add_argument("--accuracy-threshold", type=float, help="Minimum average accuracy.")
    parser.add_argument("--latency-threshold", type=float, help="Maximum average latency in seconds.")
    parser.add_argument("--cost-threshold", type=float, help="Maximum average cost in USD.")
    parser.add_argument("--error-rate-threshold", type=float, help="Maximum failed request ratio (0-1).")
    parser.add_argument("--report-dir", help="Directory to write JSON reports.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colored output.")
    return parser.parse_args()


def resolve_config(args: argparse.Namespace, project_root: Path) -> EvalConfig:
    dataset_raw = _pick_str(args.dataset, "DATASET_PATH", str(project_root / "data" / "dataset.json"))
    models_raw = _pick_str(args.models, "LITELLM_MODEL", "gemini/gemini-2.5-flash")
    api_base = _pick_optional_str(args.api_base, "LITELLM_API_BASE")
    api_key = (
        args.api_key
        or os.getenv("LITELLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    accuracy_threshold = (
        args.accuracy_threshold
        if args.accuracy_threshold is not None
        else float(os.getenv("ACCURACY_THRESHOLD", "0.8"))
    )
    latency_threshold = (
        args.latency_threshold
        if args.latency_threshold is not None
        else float(os.getenv("LATENCY_THRESHOLD", "2.0"))
    )
    cost_threshold = (
        args.cost_threshold
        if args.cost_threshold is not None
        else float(os.getenv("COST_THRESHOLD", "0.001"))
    )
    error_rate_threshold = (
        args.error_rate_threshold
        if args.error_rate_threshold is not None
        else float(os.getenv("ERROR_RATE_THRESHOLD", "0.0"))
    )
    report_dir = Path(_pick_str(args.report_dir, "REPORT_DIR", str(project_root / "reports")))

    return EvalConfig(
        dataset_path=Path(dataset_raw),
        models=parse_models(models_raw),
        api_base=api_base,
        api_key=api_key,
        thresholds=Thresholds(
            accuracy_min=accuracy_threshold,
            latency_max_seconds=latency_threshold,
            cost_max_usd=cost_threshold,
            error_rate_max=error_rate_threshold,
        ),
        report_dir=report_dir,
    )


def make_ansi(args: argparse.Namespace) -> Ansi:
    return Ansi(no_color=args.no_color)
