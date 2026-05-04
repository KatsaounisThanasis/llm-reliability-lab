# 🤖 Agent & Copilot Sync File

Αυτό το αρχείο χρησιμοποιείται για την επικοινωνία μεταξύ της ομάδας: **Χρήστης (Thanos)**, **Gemini CLI (DevOps/Orchestrator)** και **GitHub Copilot (IDE Assistant)**.

## 📌 Τρέχον Status
- **Φάση:** Advanced v2 (A/B Testing & Reports)
- **Τελευταία Ενέργεια:** Ολοκληρώθηκε το MVP, έγινε push στο GitHub (Private Repo). Όλα τα CI/CD gates λειτουργούν.
- **Επόμενο Βήμα:** Επέκταση του `eval_runner.py` για A/B Testing μεταξύ διαφορετικών μοντέλων και δημιουργία αναφορών.

## 🛠️ Tasks για το Copilot (Context - Φάση 2)
Αγαπητό Copilot, προχωράμε στην "Advanced v2" φάση του έργου! Παρακαλώ τροποποίησε το `src/eval_runner.py` με τα εξής χαρακτηριστικά:

1. **Υποστήριξη Πολλαπλών Μοντέλων (A/B Testing):**
   - Η μεταβλητή περιβάλλοντος `LITELLM_MODEL` θα μπορεί πλέον να δέχεται πολλαπλά μοντέλα χωρισμένα με κόμμα (π.χ. `gemini/gemini-2.5-flash,gemini/gemini-1.5-flash`). Αν δεν έχει κόμμα, τρέχει όπως πριν.
   - Το script πρέπει να τρέχει όλο το dataset για **κάθε** μοντέλο.

2. **Δημιουργία Regression Report:**
   - Μετά την ολοκλήρωση, αντί να τυπώνει μόνο στο terminal, να σώζει ένα JSON report στον φάκελο `reports/` (π.χ. `reports/eval_report_TIMESTAMP.json`). Ο φάκελος πρέπει να δημιουργείται αν δεν υπάρχει.
   - Το report να περιέχει τα μέση metrics (accuracy, latency, cost) για κάθε μοντέλο και να υποδεικνύει τον "Νικητή" (αυτόν με το καλύτερο accuracy, ή σε περίπτωση ισοπαλίας, το χαμηλότερο cost/latency).

3. **CI/CD Gate:**
   - Το script συνεχίζει να κάνει `exit(1)` αν **ΟΛΑ** τα μοντέλα αποτύχουν να περάσουν τα thresholds. Αν έστω και ένα μοντέλο περνάει τα thresholds (Accuracy>=0.8, Latency<=2.0, Cost<=0.001), τότε θεωρείται επιτυχία (`exit(0)`).

## 🚀 Σημείωση προς τον Thanos
Μόλις το Copilot φτιάξει τον κώδικα, πες μου να το τεστάρω με 2 διαφορετικά μοντέλα (π.χ. Gemini 2.5 Flash vs Gemini 1.5 Flash)!
