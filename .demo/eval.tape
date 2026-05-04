# vhs script: records a real A/B evaluation run as an animated GIF.
# Usage:
#   export GROQ_API_KEY=...
#   PATH="$HOME/.local/bin:$PATH" vhs .demo/eval.tape
# Output:
#   .demo/eval.gif

Output .demo/eval.gif

Set Theme "Dracula"
Set FontSize 14
Set Width 1280
Set Height 760
Set Padding 20
Set TypingSpeed 30ms
Set PlaybackSpeed 1.0

# Force colors even though vhs runs non-tty
Env FORCE_COLOR "1"
Env CLICOLOR_FORCE "1"

Type "python3 src/eval_runner.py \"
Sleep 200ms
Enter
Type "  --models 'groq/llama-3.3-70b-versatile,groq/llama-3.1-8b-instant' \"
Sleep 200ms
Enter
Type "  --accuracy-threshold 0.8 \"
Sleep 200ms
Enter
Type "  --latency-threshold 3.0 \"
Sleep 200ms
Enter
Type "  --cost-threshold 0.001 \"
Sleep 200ms
Enter
Type "  --error-rate-threshold 0.0 2>/dev/null"
Sleep 400ms
Enter
Sleep 14s
