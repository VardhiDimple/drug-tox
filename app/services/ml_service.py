"""Machine learning training from uploaded CSV datasets."""

from __future__ import annotations

import base64
import io
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from rdkit import Chem
from rdkit.Chem import AllChem
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    auc,
    classification_report,
    confusion_matrix,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from app.services.model_store import set_trained_classifier


def _is_smiles_series(series: pd.Series, sample_size: int = 20) -> bool:
    sample = series.dropna().astype(str).head(sample_size)
    if sample.empty:
        return False
    ok = sum(1 for v in sample if Chem.MolFromSmiles(v.strip()) is not None)
    return ok / len(sample) >= 0.6


def _fp_from_smiles(smiles: str, radius: int = 2, n_bits: int = 2048) -> np.ndarray | None:
    mol = Chem.MolFromSmiles(str(smiles).strip())
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return np.array(list(fp))


def _build_feature_matrix(
    df: pd.DataFrame, feature_columns: list[str]
) -> tuple[np.ndarray, list[str], int, dict[str, Any]]:
    """Build X from selected columns. SMILES columns use Morgan fingerprints."""
    parts: list[np.ndarray] = []
    names: list[str] = []
    invalid_smiles = 0
    smiles_mode = False

    for col in feature_columns:
        if col not in df.columns:
            raise ValueError(f"Feature column '{col}' not found.")
        series = df[col]
        if _is_smiles_series(series):
            smiles_mode = True
            fps = []
            for val in series:
                fp = _fp_from_smiles(val)
                if fp is None:
                    fps.append(None)
                    invalid_smiles += 1
                else:
                    fps.append(fp)
            valid_idx = [i for i, fp in enumerate(fps) if fp is not None]
            if not valid_idx:
                raise ValueError(f"Column '{col}' appears to be SMILES but no valid molecules found.")
            parts.append(np.vstack([fps[i] for i in valid_idx]))
            names.extend([f"{col}_fp_{i}" for i in range(parts[-1].shape[1])])
            meta = {"valid_indices": valid_idx, "smiles_column": col}
            return np.hstack(parts) if len(parts) > 1 else parts[0], names, invalid_smiles, meta

    # Tabular features
    block = df[feature_columns].copy()
    for col in feature_columns:
        if block[col].dtype == object or str(block[col].dtype) == "string":
            le = LabelEncoder()
            block[col] = le.fit_transform(block[col].astype(str))
        block[col] = pd.to_numeric(block[col], errors="coerce")
    block = block.fillna(block.median(numeric_only=True))
    X = block.values.astype(float)
    names = list(feature_columns)
    return X, names, invalid_smiles, {"smiles_mode": smiles_mode}


def train_from_csv(
    df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    if not feature_columns:
        raise ValueError("Select at least one feature column.")
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")
    if target_column in feature_columns:
        raise ValueError("Target column cannot be included in feature columns.")

    # SMILES fingerprint path (single SMILES feature column)
    if len(feature_columns) == 1 and _is_smiles_series(df[feature_columns[0]]):
        return _train_smiles_fingerprint(df, feature_columns[0], target_column, test_size, random_state)

    # Mixed / tabular
    work = df.dropna(subset=[target_column]).copy()
    X, feat_names, invalid_smiles, _ = _build_feature_matrix(work, feature_columns)
    y_raw = work[target_column].values

    if len(X) < 10:
        raise ValueError(f"Need at least 10 rows for training; got {len(X)}.")

    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    if len(np.unique(y)) < 2:
        raise ValueError("Target column must have at least two classes.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=100, max_depth=12, random_state=random_state, class_weight="balanced"
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    return _package_results(
        clf=clf,
        le=le,
        y_test=y_test,
        y_pred=y_pred,
        y_proba=y_proba,
        feature_columns=feature_columns,
        target_column=target_column,
        training_mode="tabular",
        samples_used=len(X),
        invalid_smiles_skipped=invalid_smiles,
        X_train_len=len(X_train),
        X_test_len=len(X_test),
    )


def _train_smiles_fingerprint(
    df: pd.DataFrame,
    smiles_column: str,
    target_column: str,
    test_size: float,
    random_state: int,
) -> dict[str, Any]:
    valid_rows = []
    invalid_count = 0
    for _, row in df.iterrows():
        fp = _fp_from_smiles(row[smiles_column])
        if fp is None:
            invalid_count += 1
            continue
        valid_rows.append((fp, row[target_column]))

    if len(valid_rows) < 10:
        raise ValueError(
            f"Need at least 10 valid SMILES rows; got {len(valid_rows)} ({invalid_count} invalid skipped)."
        )

    X = np.vstack([r[0] for r in valid_rows])
    y_raw = [r[1] for r in valid_rows]
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    if len(np.unique(y)) < 2:
        raise ValueError("Target column must have at least two classes.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=12, random_state=random_state, class_weight="balanced"
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    return _package_results(
        clf=clf,
        le=le,
        y_test=y_test,
        y_pred=y_pred,
        y_proba=y_proba,
        feature_columns=[smiles_column],
        target_column=target_column,
        training_mode="fingerprints",
        samples_used=len(valid_rows),
        invalid_smiles_skipped=invalid_count,
        X_train_len=len(X_train),
        X_test_len=len(X_test),
    )


def _package_results(
    clf,
    le: LabelEncoder,
    y_test,
    y_pred,
    y_proba,
    feature_columns: list[str],
    target_column: str,
    training_mode: str,
    samples_used: int,
    invalid_smiles_skipped: int,
    X_train_len: int,
    X_test_len: int,
) -> dict[str, Any]:
    acc = accuracy_score(y_test, y_pred)
    class_names = [str(c) for c in le.classes_]
    report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)
    cm = confusion_matrix(y_test, y_pred).tolist()

    roc_png = None
    auc_score = None
    roc_points: dict[str, Any] = {}

    if len(le.classes_) == 2:
        fpr, tpr, _ = roc_curve(y_test, y_proba[:, 1])
        auc_score = round(float(auc(fpr, tpr)), 4)
        roc_points = {"fpr": [round(float(x), 4) for x in fpr], "tpr": [round(float(x), 4) for x in tpr]}
        roc_png = _roc_curve_png(fpr, tpr, auc_score)
    else:
        from sklearn.metrics import roc_auc_score
        from sklearn.preprocessing import label_binarize

        y_bin = label_binarize(y_test, classes=range(len(le.classes_)))
        try:
            auc_score = round(float(roc_auc_score(y_bin, y_proba, multi_class="ovr", average="macro")), 4)
        except ValueError:
            auc_score = None

    cm_png = _confusion_matrix_png(cm, class_names)
    model_bundle = {
        "classifier": clf,
        "label_encoder": le,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "training_mode": training_mode,
    }

    metadata = {
        "feature_columns": feature_columns,
        "target_column": target_column,
        "training_mode": training_mode,
        "classes": class_names,
        "n_train": X_train_len,
        "n_test": X_test_len,
        "accuracy": round(float(acc), 4),
        "auc": auc_score,
    }
    set_trained_classifier(clf, metadata, label_encoder=le, model_bundle=model_bundle)

    return {
        "accuracy": round(float(acc), 4),
        "auc": auc_score,
        "classification_report": report,
        "classification_report_text": classification_report(y_test, y_pred, target_names=class_names),
        "confusion_matrix": cm,
        "confusion_matrix_png": cm_png,
        "class_labels": class_names,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "training_mode": training_mode,
        "samples_used": samples_used,
        "invalid_smiles_skipped": invalid_smiles_skipped,
        "roc_curve_png": roc_png,
        "roc_curve": roc_points,
        "model_ready_for_admet": training_mode == "fingerprints",
        "model_download_available": True,
    }


def _serialize_model_bundle(bundle: dict) -> bytes:
    buf = io.BytesIO()
    joblib.dump(bundle, buf)
    return buf.getvalue()


def get_model_bytes() -> bytes | None:
    from app.services.model_store import get_model_bundle

    bundle = get_model_bundle()
    if bundle is None:
        return None
    return _serialize_model_bundle(bundle)


def _roc_curve_png(fpr: np.ndarray, tpr: np.ndarray, auc_val: float) -> str:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#2563eb", lw=2, label=f"ROC (AUC = {auc_val:.4f})")
    ax.plot([0, 1], [0, 1], color="#94a3b8", linestyle="--", lw=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _confusion_matrix_png(cm: list, labels: list[str]) -> str:
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(np.array(cm), annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix")
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")
