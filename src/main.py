import logging
import sys
from pathlib import Path

from cli import make_ansi, parse_args, resolve_config
from dataset import load_dataset
from report import write_report
from runner import evaluate_model, pick_winner


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = parse_args()
    ansi = make_ansi(args)
    project_root = Path(__file__).resolve().parents[1]
    config = resolve_config(args, project_root)
    dataset = load_dataset(config.dataset_path)

    print(ansi.emph("LLM Reliability Benchmark Runner"))
    print(f"Dataset   : {config.dataset_path}")
    print(f"Models    : {', '.join(config.models)}")
    print(
        "Thresholds: "
        f"accuracy>={config.thresholds.accuracy_min:.3f}, "
        f"latency<={config.thresholds.latency_max_seconds:.3f}s, "
        f"cost<=${config.thresholds.cost_max_usd:.6f}, "
        f"error_rate<={config.thresholds.error_rate_max:.3f}"
    )
    print(f"Retries   : {config.num_retries}")

    summaries = [
        evaluate_model(
            model=model,
            dataset=dataset,
            config=config,
            ansi=ansi,
        )
        for model in config.models
    ]

    winner = pick_winner(summaries)
    report_path = write_report(
        report_dir=config.report_dir,
        results=summaries,
        winner=winner,
        thresholds=config.thresholds,
    )

    print("\n" + "=" * 72)
    if winner is None:
        print(f"Winner: {ansi.error('none (all models failed)')}")
    else:
        print(f"Winner: {ansi.info(winner.model)}")
    print(f"Report: {report_path}")

    if winner is None:
        print(ansi.error("FAILED: all models failed thresholds."))
        sys.exit(1)

    passed_count = len([summary for summary in summaries if summary.passed])
    print(ansi.success(f"PASSED: {passed_count}/{len(summaries)} model(s) passed thresholds."))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
