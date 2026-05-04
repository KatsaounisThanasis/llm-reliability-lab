# Contributing

Thanks for your interest. Contributions, ideas, and bug reports are welcome.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run tests

```bash
pytest -q
```

All tests should pass. Add a test for any new behavior.

## Run the evaluator locally

```bash
export GROQ_API_KEY="gsk_..."   # or GEMINI_API_KEY, OPENAI_API_KEY, etc.
python3 src/eval_runner.py --models "groq/llama-3.3-70b-versatile"
```

## Pull request guidelines

- One change per PR. Keep diffs reviewable.
- Update or add tests for any behavior change.
- Update the README if you add a CLI flag, env var, or dataset schema field.
- The CI gate must stay green. If you intentionally tighten thresholds, mention it in the PR description.

## Reporting issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- A minimal reproduction (dataset entry + command)
