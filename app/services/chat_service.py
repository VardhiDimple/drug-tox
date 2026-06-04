"""AI assistant chatbot with LLM fallback to rule-based responses."""

from __future__ import annotations

import json
import os
import re
from typing import Any

PANEL_NAMES = {
    "home": "Home",
    "admet": "ADMET Predictor",
    "viewer": "Molecular Viewer",
    "ml": "ML Classifier",
    "viz": "Visualization Tool",
    "go": "GO Enrichment Analysis",
    "disease": "Disease Prediction",
    "about": "About",
}

SUGGESTED_QUESTIONS = [
    "How do I use ADMET Predictor?",
    "What is a SMILES string?",
    "How do I train an ML model?",
    "How do I perform GO Enrichment?",
    "How do I interpret toxicity predictions?",
    "How do I choose feature and target columns?",
]


def get_suggested_questions() -> list[str]:
    return list(SUGGESTED_QUESTIONS)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _recommend_target(columns: list[str], column_stats: dict | None) -> str | None:
    if not columns or not column_stats:
        return None
    for col in columns:
        stats = column_stats.get(col, {})
        if stats.get("is_continuous"):
            continue
        nunique = stats.get("unique_count", 0)
        if 2 <= nunique <= 10:
            return col
    for col in reversed(columns):
        stats = column_stats.get(col, {})
        if not stats.get("is_continuous") and stats.get("unique_count", 0) >= 2:
            return col
    return None


def _recommend_features(columns: list[str], target: str | None, column_stats: dict | None) -> list[str]:
    if not columns:
        return []
    stats = column_stats or {}
    features = []
    for col in columns:
        if col == target:
            continue
        if stats.get(col, {}).get("is_continuous") or col in stats:
            features.append(col)
        else:
            features.append(col)
    return features[:8]


def _rule_based_response(message: str, context: dict[str, Any]) -> str:
    q = _normalize(message)
    panel = context.get("panel", "home")
    columns = context.get("columns") or []
    column_stats = context.get("column_stats") or {}
    target = context.get("target_column")
    error = context.get("last_error")

    if error:
        err_lower = error.lower()
        if "smiles" in err_lower or "invalid" in err_lower:
            return (
                f"**Error:** {error}\n\n"
                "Invalid SMILES strings cannot be parsed by RDKit. Check for typos, unbalanced "
                "parentheses, or unsupported atoms. Use the Molecular Viewer to validate your structure."
            )
        if "continuous" in err_lower or "regression" in err_lower:
            return (
                f"**Error:** {error}\n\n"
                "Your target column has too many unique numeric values for classification. "
                "Choose a categorical/binary column (e.g., Toxicity with 0/1 labels) or use a regression module."
            )
        if "class" in err_lower and "sample" in err_lower:
            return (
                f"**Error:** {error}\n\n"
                "Each class needs at least 2 samples. Remove rare classes, collect more data, "
                "or merge similar categories before training."
            )
        if "missing" in err_lower or "empty" in err_lower:
            return (
                f"**Error:** {error}\n\n"
                "Ensure your CSV/XLSX is not empty, uses UTF-8 encoding, and has a header row. "
                "Fill or remove rows with missing target values."
            )
        return f"**Error:** {error}\n\nReview your inputs and try again. I can help explain any step in the {PANEL_NAMES.get(panel, panel)} module."

    if any(k in q for k in ("target column", "choose target", "which target", "what target")):
        rec = target or _recommend_target(columns, column_stats)
        if rec and columns:
            feats = _recommend_features(columns, rec, column_stats)
            feat_text = ", ".join(feats[:6]) if feats else "numeric or descriptor columns"
            return (
                "A **target column** is the variable you want to predict.\n\n"
                f"For your uploaded dataset, **'{rec}'** is the recommended target because it "
                "contains categorical labels suitable for classification. "
                f"Columns such as {feat_text} are better used as **feature columns**."
            )
        return (
            "A **target column** is the outcome you want to predict (e.g., Toxicity with 0/1 labels). "
            "It should be categorical or binary—not a continuous numeric measurement. "
            "Upload a dataset in ML Classifier, then select one target column in Step 2."
        )

    if any(k in q for k in ("feature column", "choose feature", "which feature", "what feature")):
        feats = _recommend_features(columns, target, column_stats)
        if feats:
            return (
                "**Feature columns** are the input variables used to predict the target.\n\n"
                f"For your dataset, consider: {', '.join(feats)}. "
                "Never include the target column as a feature. Select one or more columns in Step 3 of ML Classifier."
            )
        return (
            "**Feature columns** are predictors (e.g., MolecularWeight, LogP, TPSA). "
            "Select all relevant numeric or categorical columns except the target. "
            "The target column is automatically excluded from feature selection."
        )

    if "admet" in q or ("predictor" in q and panel == "admet"):
        return (
            "**ADMET Predictor** evaluates drug-likeness from a SMILES string.\n\n"
            "1. Enter or paste a valid SMILES in the input field.\n"
            "2. Click **Predict** to compute RDKit molecular descriptors.\n"
            "3. Review Lipinski Rule of Five, ADMET properties, and toxicity predictions.\n\n"
            "**Descriptors** include MW, LogP, TPSA, HBD/HBA, rotatable bonds, and aromatic rings. "
            "**Lipinski Rule of Five** checks oral bioavailability (MW ≤ 500, LogP ≤ 5, HBD ≤ 5, HBA ≤ 10). "
            "Train an ML model on SMILES in ML Classifier to enable ML-based toxicity in ADMET."
        )

    if "smiles" in q:
        return (
            "A **SMILES string** (Simplified Molecular Input Line Entry System) encodes a molecule as text, "
            "e.g., `CCO` for ethanol or `c1ccccc1` for benzene.\n\n"
            "Use the **Molecular Viewer** to visualize 2D/3D structures from SMILES. "
            "ADMET Predictor and ML Classifier (SMILES mode) also accept SMILES input."
        )

    if any(k in q for k in ("train", "ml model", "classifier", "machine learning")):
        return (
            "**ML Classifier workflow:**\n\n"
            "1. **Upload** CSV/XLSX dataset\n"
            "2. **Select target** — categorical column to predict (e.g., Toxicity)\n"
            "3. **Select features** — input columns (exclude target)\n"
            "4. **Choose model** — Random Forest, Logistic Regression, Decision Tree, SVM, or XGBoost\n"
            "5. **Configure** test size (0.1–0.4), random state, CV folds\n"
            "6. **Train** and review accuracy, precision, recall, F1, AUC, confusion matrix, ROC curve\n"
            "7. **Download** model (.pkl) and predictions (.csv)\n\n"
            "**Metrics:** Accuracy = overall correctness; Precision = true positives / predicted positives; "
            "Recall = true positives / actual positives; F1 = harmonic mean of precision & recall; "
            "AUC = area under ROC curve (1.0 = perfect, 0.5 = random)."
        )

    if "go enrichment" in q or "go term" in q or ("enrichment" in q and "go" in q):
        return (
            "**GO Enrichment Analysis** finds over-represented Gene Ontology terms in your gene list.\n\n"
            "1. Paste gene symbols or upload a text/CSV file.\n"
            "2. Run enrichment to get GO terms with p-values and adjusted p-values.\n\n"
            "**GO terms** describe gene functions (biological process, molecular function, cellular component). "
            "**P-value** = probability of seeing a term by chance; **adjusted p-value** (FDR) corrects for multiple testing. "
            "Lower adjusted p-values indicate stronger enrichment."
        )

    if "toxicity" in q or "toxic" in q:
        return (
            "**Toxicity prediction** in ADMET combines rule-based heuristics and optional ML models.\n\n"
            "Results show Low/Moderate/High risk based on structural alerts and descriptors. "
            "To use ML-based toxicity, train a Random Forest on SMILES fingerprints in ML Classifier. "
            "Interpret results alongside experimental data—predictions are computational estimates."
        )

    if any(k in q for k in ("accuracy", "precision", "recall", "f1", "auc", "roc")):
        return (
            "**Classification metrics explained:**\n\n"
            "• **Accuracy** — fraction of correct predictions\n"
            "• **Precision** — of predicted positives, how many are truly positive\n"
            "• **Recall** — of actual positives, how many were found\n"
            "• **F1 Score** — balance between precision and recall\n"
            "• **ROC Curve** — true positive rate vs false positive rate at various thresholds\n"
            "• **AUC** — area under ROC; 1.0 = perfect, 0.5 = random guessing"
        )

    if "plot" in q or "visualization" in q or "chart" in q:
        numeric = context.get("numeric_columns") or []
        categorical = context.get("categorical_columns") or []
        tips = []
        if numeric:
            tips.append(f"**Scatter/Line/Bar/Histogram** — use numeric columns like {', '.join(numeric[:3])}")
        if len(numeric) >= 2:
            tips.append("**Correlation matrix** — compare relationships between numeric columns")
        if categorical and numeric:
            tips.append(f"**Boxplot** — compare {numeric[0]} across {categorical[0]} groups")
        body = "\n".join(f"• {t}" for t in tips) if tips else (
            "• **Scatter** — two numeric variables\n"
            "• **Histogram** — distribution of one variable\n"
            "• **Bar** — counts or means by category\n"
            "• **Heatmap/Correlation** — patterns across multiple numeric columns"
        )
        return f"**Visualization Tool plot guide:**\n\n{body}\n\nUpload your dataset, pick columns, and select a plot type."

    if "disease" in q:
        return (
            "**Disease Prediction** matches symptoms or keywords to diseases in the reference database.\n\n"
            "Enter symptoms (e.g., fever, cough, fatigue) and review the primary prediction with "
            "**confidence score** (higher = stronger match). Alternative matches show related conditions. "
            "This is for educational purposes—not a clinical diagnosis tool."
        )

    if "lipinski" in q or "rule of five" in q:
        return (
            "**Lipinski Rule of Five** predicts oral drug-likeness:\n\n"
            "• Molecular Weight ≤ 500 Da\n"
            "• LogP ≤ 5\n"
            "• H-bond donors ≤ 5\n"
            "• H-bond acceptors ≤ 10\n\n"
            "Violations suggest poor absorption. ADMET Predictor shows pass/fail for each rule."
        )

    if "upload" in q and "dataset" in q:
        return (
            "To **upload a dataset**:\n\n"
            "1. Go to ML Classifier or Visualization.\n"
            "2. Click **Choose file** and select `.csv`, `.tsv`, or `.xlsx`.\n"
            "3. Preview shows first 10 rows, row/column counts, and missing value summary.\n\n"
            "Ensure UTF-8 encoding and a header row with column names."
        )

    if "hello" in q or "hi" in q or "help" in q:
        panel_name = PANEL_NAMES.get(panel, "DRUG TOX PRO")
        return (
            f"Hello! I'm the DRUG TOX PRO assistant. You're on **{panel_name}**.\n\n"
            "I can help with ADMET, molecular structures, ML classification, visualization, "
            "GO enrichment, and disease prediction. Ask a question or use the quick-action buttons below."
        )

    panel_hints = {
        "admet": "Try entering a SMILES string like `CCO` and click Predict to see descriptors and toxicity.",
        "viewer": "Paste a SMILES to view 2D and interactive 3D structures.",
        "ml": "Upload a CSV, pick a target column (e.g., Toxicity), select features, choose a model, and train.",
        "viz": "Upload data and pick plot types based on your column types.",
        "go": "Paste gene symbols (e.g., TP53, BRCA1) or upload a gene list file.",
        "disease": "Enter symptoms separated by commas to get disease predictions.",
    }
    hint = panel_hints.get(panel, "Explore the modules from the sidebar or ask me about any feature.")
    return (
        f"I'm not sure about that specific question, but here's a tip for **{PANEL_NAMES.get(panel, 'this page')}**:\n\n"
        f"{hint}\n\n"
        "Try asking about target columns, SMILES, classification metrics, GO terms, or toxicity interpretation."
    )


def _call_openai(message: str, context: dict[str, Any], history: list[dict]) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        import urllib.request

        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        system = (
            "You are the DRUG TOX PRO in-app assistant for drug discovery, ADMET, toxicity, "
            "machine learning, and bioinformatics. Be concise, helpful, and accurate. "
            f"Current page: {PANEL_NAMES.get(context.get('panel', ''), context.get('panel', 'unknown'))}. "
            f"Context: {json.dumps({k: v for k, v in context.items() if k != 'history'})}"
        )
        messages = [{"role": "system", "content": system}]
        for h in history[-6:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        payload = json.dumps({"model": model, "messages": messages, "max_tokens": 600}).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def chat(message: str, context: dict[str, Any] | None = None, history: list[dict] | None = None) -> dict[str, Any]:
    context = context or {}
    history = history or []
    message = (message or "").strip()
    if not message:
        raise ValueError("Message cannot be empty.")

    llm_response = _call_openai(message, context, history)
    if llm_response:
        return {"reply": llm_response, "source": "openai", "suggested_questions": get_suggested_questions()}

    return {
        "reply": _rule_based_response(message, context),
        "source": "rule_based",
        "suggested_questions": get_suggested_questions(),
    }
