Output shot3_out.gif

Set Theme "Dracula"
Set FontSize 14
Set Width 1280
Set Height 760
Set Padding 24
Set TypingSpeed 20ms

Hide
Type "clear"
Enter
Show

Type "# Aggressive latency gate: 50ms — both models fail, PR is blocked"
Enter
Type "python3 src/eval_runner.py \"
Sleep 100ms
Enter
Type "  --models 'groq/llama-3.3-70b-versatile,groq/llama-3.1-8b-instant' \"
Sleep 100ms
Enter
Type "  --accuracy-threshold 0.8 \"
Sleep 100ms
Enter
Type "  --latency-threshold 0.05 \"
Sleep 100ms
Enter
Type "  --cost-threshold 0.001 \"
Sleep 100ms
Enter
Type "  --error-rate-threshold 0.0 2>/dev/null"
Sleep 200ms
Enter
Sleep 12s

Screenshot .demo/screenshots/03_failed.png
