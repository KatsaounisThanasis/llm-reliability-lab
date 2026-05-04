import os
import sys

from entities import EvalConfig, ModelSummary


class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"

    def __init__(self, no_color: bool) -> None:
        self.enabled = (
            (not no_color)
            and sys.stdout.isatty()
            and os.getenv("NO_COLOR") is None
        )

    def _style(self, text: str, color: str) -> str:
        if not self.enabled:
            return text
        return f"{color}{text}{self.RESET}"

    def info(self, text: str) -> str:
        return self._style(text, self.CYAN)

    def success(self, text: str) -> str:
        return self._style(text, self.GREEN)

    def error(self, text: str) -> str:
        return self._style(text, self.RED)

    def warning(self, text: str) -> str:
        return self._style(text, self.YELLOW)

    def emph(self, text: str) -> str:
        return self._style(text, self.BOLD)


def print_run_header(config: EvalConfig, ansi: Ansi) -> None:
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


def print_model_summary(summary: ModelSummary, ansi: Ansi) -> None:
    print(f"\nRunning evaluation with model={ansi.info(summary.model)}")
    print("-" * 72)
    for result in summary.cases:
        cost_text = f"${result.cost_usd:.6f}" if result.cost_usd is not None else "n/a"
        latency_text = f"{result.latency_seconds:.3f}s" if result.latency_seconds is not None else "n/a"
        row = (
            f"[{result.index}] latency={latency_text} | cost={cost_text} | "
            f"accuracy={result.accuracy:.0f} | expected='{result.expected}'"
        )
        if result.error:
            print(ansi.warning(f"{row} | error={result.error}"))
        else:
            print(row)

    avg_latency_text = (
        f"{summary.avg_latency_seconds:.3f}s"
        if summary.avg_latency_seconds is not None
        else "n/a"
    )
    avg_cost_text = (
        f"${summary.avg_cost_usd:.6f}" if summary.avg_cost_usd is not None else "n/a"
    )
    status = ansi.success("PASSED") if summary.passed else ansi.error("FAILED")

    print("-" * 72)
    print(f"Average Latency : {avg_latency_text}")
    print(f"Average Cost    : {avg_cost_text}")
    print(f"Average Accuracy: {summary.avg_accuracy:.3f}")
    print(f"Error Rate      : {summary.error_rate:.3f}")
    print(f"Result          : {status}")
    for reason in summary.failure_reasons:
        print(f"- {reason}")


def print_final_summary(
    summaries: list[ModelSummary], winner: ModelSummary | None, report_path: str, ansi: Ansi
) -> None:
    print("\n" + "=" * 72)
    if winner is None:
        print(f"Winner: {ansi.error('none (all models failed)')}")
    else:
        print(f"Winner: {ansi.info(winner.model)}")
    print(f"Report: {report_path}")

    if winner is None:
        print(ansi.error("FAILED: all models failed thresholds."))
        return

    passed_count = len([summary for summary in summaries if summary.passed])
    print(ansi.success(f"PASSED: {passed_count}/{len(summaries)} model(s) passed thresholds."))
