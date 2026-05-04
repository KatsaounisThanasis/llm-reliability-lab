# LLM Reliability Benchmark Lab

A production-oriented lab to test, benchmark, and enforce reliability metrics for LLM applications. 
Part of my DevOps & AI Engineering Portfolio.

## 🎯 Goal
Ensure that any changes to LLM prompts, models, or parameters do not degrade performance (Latency, Cost, Accuracy). We achieve this by introducing CI/CD gates that act as "Policy-as-Code" for AI.

## 📦 MVP Features
- Dataset with test prompts and expected outputs.
- Evaluation Runner measuring Latency, Cost, and Accuracy.
- CI/CD integration: Blocks pull requests if metrics drop below defined thresholds.

## 🚀 Usage
1. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set your API key:
```bash
export GEMINI_API_KEY="your_api_key"
```

3. Run the evaluator (single model):
```bash
python3 src/eval_runner.py --models "gemini/gemini-2.5-flash"
```

4. Run A/B testing (multi-model):
```bash
python3 src/eval_runner.py \
  --models "gemini/gemini-2.5-flash,gemini/gemini-1.5-flash" \
  --dataset data/dataset.json \
  --accuracy-threshold 0.8 \
  --latency-threshold 2.0 \
  --cost-threshold 0.001
```

## ⚙️ CLI Flags
- `--dataset`: Dataset path (fallback: `DATASET_PATH`)
- `--models`: Comma-separated model list (fallback: `LITELLM_MODEL`)
- `--api-base`: LiteLLM API base (fallback: `LITELLM_API_BASE`)
- `--api-key`: API key override (fallback order: `LITELLM_API_KEY` -> `GEMINI_API_KEY` -> `OPENAI_API_KEY`)
- `--accuracy-threshold`: Min average accuracy (fallback: `ACCURACY_THRESHOLD`)
- `--latency-threshold`: Max average latency in seconds (fallback: `LATENCY_THRESHOLD`)
- `--cost-threshold`: Max average cost in USD (fallback: `COST_THRESHOLD`)
- `--error-rate-threshold`: Max failed request ratio (fallback: `ERROR_RATE_THRESHOLD`, default: `0.0`)
- `--report-dir`: Report output directory (fallback: `REPORT_DIR`, default: `reports/`)
- `--no-color`: Disable ANSI color output

## 🧪 CI/CD Gate Behavior
- The run **fails** only when **all models** fail thresholds.
- The run **passes** when at least one model passes.
- A regression JSON report is generated under `reports/` with per-model metrics and winner selection.

## 🏗️ Architecture / Flow
1. Load dataset from JSON.
2. Parse one or more model IDs.
3. Evaluate all prompts for each model.
4. Compute average latency/cost/accuracy and threshold pass/fail.
5. Select winner (highest accuracy, then lowest cost, then lowest latency).
6. Write timestamped report to `reports/eval_report_*.json`.
7. Return CI-friendly exit code.
