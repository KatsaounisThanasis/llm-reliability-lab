# 🤖 Agent & Copilot Sync File

Αυτό το αρχείο χρησιμοποιείται για την επικοινωνία μεταξύ της ομάδας: **Χρήστης (Thanos)**, **Gemini CLI (DevOps/Orchestrator)** και **GitHub Copilot (IDE Assistant)**.

## 📌 Τρέχον Status
- **Φάση:** Υλοποίηση CI/CD & Run Instructions
- **Τελευταία Ενέργεια:** Το Copilot υλοποίησε το MVP (`eval_runner.py` & `dataset.json`). Το Gemini CLI προσάρμοσε το script για να μην κρασάρει το PC, άλλαξε το default μοντέλο σε API (Gemini/LiteLLM) και πρόσθεσε το GitHub Action.

## ⚠️ Αποφυγή CPU Load (Σημείωση για τον Thanos)
Την προηγούμενη φορά που χρησιμοποιήσαμε `litellm`, το PC κράσαρε με 100% CPU επειδή το default μοντέλο ήταν **τοπικό (Ollama)**. 
Το LiteLLM από μόνο του είναι μια πανάλαφρη βιβλιοθήκη Python (δεν τρώει πόρους). Το πρόβλημα ήταν ότι καλούσε τοπικό AI Engine (Ollama). 
**Λύση:** Άλλαξα το default μοντέλο στο `eval_runner.py` σε `gemini/gemini-1.5-flash`. Έτσι τα requests θα γίνονται μέσω API, η CPU σου θα μείνει στο 0% και όλα θα είναι αστραπιαία!

## 🚀 Πώς να τρέξεις το Evaluation (Run Instructions)

1. **Δημιούργησε Virtual Environment & Κάνε Install:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Τρέξε το Script με API Key (Ασφαλής τρόπος):**
   ```bash
   export GEMINI_API_KEY="το_api_key_σου_εδω"
   python src/eval_runner.py
   ```
   *(Σημείωση: Αν δεν έχεις Gemini API Key, μπορείς να βάλεις `export OPENAI_API_KEY="key"` και να τρέξεις με `export LITELLM_MODEL="gpt-3.5-turbo"`)*

## 🚦 Baseline Thresholds & Fail Conditions
Το pipeline (και το τοπικό σου τρέξιμο) θα γίνει `FAILED` αν το `Average Accuracy` πέσει κάτω από `0.8` (80%).
Τα cost/latency metrics τυπώνονται για observability, αλλά στο επόμενο βήμα μπορούμε να προσθέσουμε fail conditions και για αυτά (π.χ. `max_latency=2.0s`).

## 🛠️ Tasks για το Copilot (Next Steps)
Αγαπητό Copilot, όταν ο Thanos ζητήσει το επόμενο feature, παρακαλώ:
1. Πρόσθεσε thresholds για **Latency** και **Cost** στο `eval_runner.py` (π.χ. `LATENCY_THRESHOLD=2.0` seconds).
2. Αν το μέσο latency είναι πάνω από 2.0s, το script να κάνει επίσης `exit(1)`.
