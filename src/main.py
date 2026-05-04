import sys
from pathlib import Path

from cli import make_ansi, parse_args, resolve_config
from dataset import load_dataset
from presentation import print_final_summary, print_model_summary, print_run_header
from report import write_report
from runner import evaluate_model, pick_winner


def main() -> None:
    args = parse_args()
    ansi = make_ansi(args)
    project_root = Path(__file__).resolve().parents[1]
    config = resolve_config(args, project_root)
    dataset = load_dataset(config.dataset_path)

    print_run_header(config, ansi)

    summaries = [
        evaluate_model(
            model=model,
            dataset=dataset,
            config=config,
        )
        for model in config.models
    ]
    for summary in summaries:
        print_model_summary(summary, ansi)

    winner = pick_winner(summaries)
    report_path = write_report(
        report_dir=config.report_dir,
        results=summaries,
        winner=winner,
        thresholds=config.thresholds,
    )

    print_final_summary(summaries, winner, str(report_path), ansi)
    if winner is None:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
