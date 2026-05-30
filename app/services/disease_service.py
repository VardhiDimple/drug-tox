"""Disease prediction from symptoms and keywords using dynamic text similarity."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REFERENCE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "disease_reference.csv"


def _load_reference() -> pd.DataFrame:
    if not REFERENCE_PATH.exists():
        raise ValueError("Disease reference database not found.")
    df = pd.read_csv(REFERENCE_PATH)
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"disease", "symptoms", "description"}
    if not required.issubset(set(df.columns)):
        raise ValueError("Disease reference must include disease, symptoms, and description columns.")
    df["search_text"] = (
        df["disease"].astype(str)
        + " "
        + df["symptoms"].astype(str)
        + " "
        + df["description"].astype(str)
    ).str.lower()
    return df


def predict_disease(query: str, top_k: int = 3) -> dict[str, Any]:
    query = query.strip()
    if len(query) < 3:
        raise ValueError("Enter a disease name, condition, symptoms, or keywords (min 3 characters).")

    df = _load_reference()
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    corpus = df["search_text"].tolist()
    X = vectorizer.fit_transform(corpus)
    q_vec = vectorizer.transform([query.lower()])
    scores = cosine_similarity(q_vec, X).flatten()

    top_idx = scores.argsort()[::-1][:top_k]
    predictions = []
    for idx in top_idx:
        row = df.iloc[idx]
        disease_name = str(row["disease"])
        score = round(float(scores[idx]), 4)
        google_url = f"https://www.google.com/search?q={quote_plus(disease_name + ' disease symptoms treatment')}"
        predictions.append(
            {
                "disease": disease_name,
                "description": str(row["description"]),
                "symptoms": str(row["symptoms"]),
                "category": str(row.get("category", "General")),
                "confidence_score": score,
                "google_search_url": google_url,
            }
        )

    best = predictions[0]
    return {
        "query": query,
        "primary_prediction": best,
        "alternatives": predictions[1:],
        "google_search_url": best["google_search_url"],
    }
