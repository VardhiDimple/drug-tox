"""Machine learning classifier training from uploaded datasets."""

from __future__ import annotations

import base64
import io
import logging
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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_curve,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from app.services.model_store import set_trained_classifier

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {
    "random_forest": "Random Forest Classifier",
    "logistic_regression": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "svm": "Support Vector Machine (SVM)",
}

try:
    from xgboost import XGBClassifier

    SUPPORTED_MODELS["xgboost"] = "XGBoost"
    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False

CONTINUOUS_UNIQUE_THRESHOLD = 20
MIN_SAMPLES_PER_CLASS = 2


def get_available_models() -> dict[str, str]:
    return dict(SUPPORTED_MODELS)


def _safe_cv_folds(y: np.ndarray, cv_folds: int) -> int:
    """Pick a valid number of CV folds (at least 2, at most class min count)."""
    counts = pd.Series(y).value_counts()
    min_class = int(counts.min()) if len(counts) else 2
    n = min(cv_folds, len(y), min_class)
    return max(2, n)


def _run_cross_validation(clf, X: np.ndarray, y: np.ndarray, cv_folds: int, model_type: str) -> np.ndarray:
    # SVM cross-validation on hundreds of rows can take many minutes
    if model_type == "svm" and len(y) > 150:
        logger.info("Skipping CV for SVM on n=%d (slow); model will still train.", len(y))
        return np.array([])
    n_splits = _safe_cv_folds(y, cv_folds)
    try:
        scores = cross_val_score(clf, X, y, cv=n_splits, scoring="accuracy")
        logger.info("CV accuracy scores (%d folds): %s", n_splits, scores)
        return scores
    except Exception as exc:
        logger.warning("Cross-validation skipped: %s", exc)
        return np.array([])


def get_training_preview(
    df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    test_size: float = 0.2,
) -> dict[str, Any]:
    """Return pre-training debug info without fitting a model."""
    warnings: list[str] = []

    if not feature_columns:
        raise ValueError("Select at least one feature column.")
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")
    if target_column in feature_columns:
        raise ValueError("Target column cannot be included in feature columns.")

    target_info = validate_target_column(df, target_column)
    if not target_info["valid"]:
        raise ValueError(target_info["message"])

    if len(feature_columns) == 1 and _is_smiles_series(df[feature_columns[0]]):
        work = df.dropna(subset=[target_column])
        valid = sum(1 for v in work[feature_columns[0]] if _fp_from_smiles(v) is not None)
        y_raw = work[target_column].astype(str)
        le = LabelEncoder()
        y = le.fit_transform(y_raw)
        return {
            "training_mode": "fingerprints",
            "feature_columns": feature_columns,
            "target_column": target_column,
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "x_shape": [valid, 2048],
            "y_shape": [valid],
            "unique_classes": [str(c) for c in le.classes_],
            "class_distribution": target_info["class_distribution"],
            "test_size": test_size,
            "warnings": warnings,
        }

    work = df.dropna(subset=[target_column]).copy()
    if work.empty:
        raise ValueError("No rows remain after removing missing target values.")

    X, feat_names, _ = _prepare_tabular_features(work, feature_columns)
    y_raw = work[target_column].values
    le = LabelEncoder()
    y = le.fit_transform(y_raw.astype(str))

    missing_in_features = int(work[feature_columns].isna().sum().sum())
    if missing_in_features > 0:
        warnings.append(
            f"{missing_in_features} missing feature value(s) will be imputed (median/0) before training."
        )

    return {
        "training_mode": "tabular",
        "feature_columns": feature_columns,
        "target_column": target_column,
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "x_shape": [int(X.shape[0]), int(X.shape[1])],
        "y_shape": [int(len(y))],
        "unique_classes": [str(c) for c in le.classes_],
        "class_distribution": target_info["class_distribution"],
        "feature_names": feat_names,
        "test_size": test_size,
        "warnings": warnings,
    }


def validate_target_column(df: pd.DataFrame, target_column: str) -> dict[str, Any]:
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")

    series = df[target_column].dropna()
    if series.empty:
        raise ValueError(f"Target column '{target_column}' has no non-missing values.")

    nunique = int(series.nunique())
    is_numeric = pd.api.types.is_numeric_dtype(series)
    is_continuous = is_numeric and nunique > CONTINUOUS_UNIQUE_THRESHOLD

    if is_continuous:
        return {
            "valid": False,
            "is_continuous": True,
            "unique_count": nunique,
            "message": (
            "Selected column appears continuous. Choose a categorical target column for classification."
            ),
        }

    class_counts = series.astype(str).value_counts().to_dict()
    if nunique < 2:
        raise ValueError(
            f"Target column must have at least 2 classes; found {nunique}."
        )

    small_classes = {k: v for k, v in class_counts.items() if v < MIN_SAMPLES_PER_CLASS}
    if small_classes:
        details = ", ".join(f"{k}={v}" for k, v in small_classes.items())
        raise ValueError(
            f"Each class must have at least {MIN_SAMPLES_PER_CLASS} samples. "
            f"Under-represented classes: {details}"
        )

    return {
        "valid": True,
        "is_continuous": False,
        "unique_count": nunique,
        "class_distribution": {str(k): int(v) for k, v in class_counts.items()},
        "message": "Target column is suitable for classification.",
    }


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


def _prepare_tabular_features(
    df: pd.DataFrame, feature_columns: list[str]
) -> tuple[np.ndarray, list[str], dict[str, LabelEncoder]]:
    block = df[feature_columns].copy()
    encoders: dict[str, LabelEncoder] = {}

    for col in feature_columns:
        if block[col].dtype == object or str(block[col].dtype) == "string":
            le = LabelEncoder()
            block[col] = le.fit_transform(block[col].astype(str))
            encoders[col] = le
        block[col] = pd.to_numeric(block[col], errors="coerce")
        if block[col].isna().any():
            median_val = block[col].median()
            if pd.isna(median_val):
                block[col] = block[col].fillna(0)
            else:
                block[col] = block[col].fillna(median_val)

    return block.values.astype(float), list(feature_columns), encoders


def _build_classifier(model_type: str, random_state: int):
    if model_type == "random_forest":
        return RandomForestClassifier(
            n_estimators=100, max_depth=12, random_state=random_state, class_weight="balanced"
        )
    if model_type == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=random_state, class_weight="balanced")
    if model_type == "decision_tree":
        return DecisionTreeClassifier(max_depth=12, random_state=random_state, class_weight="balanced")
    if model_type == "svm":
        return SVC(
            kernel="rbf",
            probability=True,
            random_state=random_state,
            class_weight="balanced",
        )
    if model_type == "xgboost":
        if not _XGBOOST_AVAILABLE:
            raise ValueError("XGBoost is not installed. Install with: pip install xgboost")
        return XGBClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=random_state,
            eval_metric="logloss",
        )
    raise ValueError(f"Unknown model type '{model_type}'.")


def _needs_scaling(model_type: str) -> bool:
    return model_type in ("logistic_regression", "svm")


def _supports_feature_importance(model_type: str) -> bool:
    return model_type in ("random_forest", "decision_tree")


def _extract_feature_importance(clf, model_type: str, feature_names: list[str]) -> list[dict[str, Any]] | None:
    if not _supports_feature_importance(model_type):
        return None
    if not hasattr(clf, "feature_importances_"):
        return None
    importances = clf.feature_importances_

    pairs = sorted(
        zip(feature_names, importances),
        key=lambda x: float(x[1]),
        reverse=True,
    )
    return [{"feature": name, "importance": round(float(imp), 6)} for name, imp in pairs]


def _feature_importance_png(importance_list: list[dict[str, Any]], top_n: int = 15) -> str | None:
    if not importance_list:
        return None
    top = importance_list[:top_n]
    names = [item["feature"] for item in top][::-1]
    values = [item["importance"] for item in top][::-1]

    fig, ax = plt.subplots(figsize=(7, max(4, len(top) * 0.35)))
    ax.barh(names, values, color="#3b82f6")
    ax.set_xlabel("Importance")
    ax.set_title("Feature Importance")
    ax.grid(True, axis="x", alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def train_from_csv(
    df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    model_type: str = "random_forest",
    test_size: float = 0.2,
    random_state: int = 42,
    cv_folds: int = 5,
) -> dict[str, Any]:
    if not feature_columns:
        raise ValueError("Select at least one feature column.")
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")
    if target_column in feature_columns:
        raise ValueError("Target column cannot be included in feature columns.")
    if model_type not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model type '{model_type}'.")
    if not 0.1 <= test_size <= 0.4:
        raise ValueError("Test size must be between 0.1 and 0.4.")
    if cv_folds < 2:
        raise ValueError("Cross validation folds must be at least 2.")

    target_info = validate_target_column(df, target_column)
    if not target_info["valid"]:
        raise ValueError(target_info["message"])

    if len(feature_columns) == 1 and _is_smiles_series(df[feature_columns[0]]):
        return _train_smiles_fingerprint(
            df,
            feature_columns[0],
            target_column,
            model_type=model_type,
            test_size=test_size,
            random_state=random_state,
            cv_folds=cv_folds,
        )

    work = df.dropna(subset=[target_column]).copy()
    X, feat_names, feature_encoders = _prepare_tabular_features(work, feature_columns)
    y_raw = work[target_column].values

    if len(X) < 10:
        raise ValueError(f"Need at least 10 rows for training; got {len(X)}.")

    le = LabelEncoder()
    y = le.fit_transform(y_raw.astype(str))
    if len(np.unique(y)) < 2:
        raise ValueError("Target column must have at least two classes.")

    class_counts = pd.Series(y).value_counts()
    if (class_counts < MIN_SAMPLES_PER_CLASS).any():
        raise ValueError(
            f"Each class must have at least {MIN_SAMPLES_PER_CLASS} samples after preprocessing."
        )

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
    except ValueError as e:
        raise ValueError(f"Could not split dataset: {e}") from e

    scaler = None
    if _needs_scaling(model_type):
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        X_cv = scaler.transform(X)
    else:
        X_cv = X

    clf = _build_classifier(model_type, random_state)
    cv_scores = _run_cross_validation(clf, X_cv, y, cv_folds, model_type)
    logger.info("Training %s on X_train shape %s", model_type, X_train.shape)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    class_names = [str(c) for c in le.classes_]
    actual_labels = [class_names[i] for i in y_test]
    predicted_labels = [class_names[i] for i in y_pred]
    predictions_table = [
        {"actual": actual_labels[i], "predicted": predicted_labels[i]}
        for i in range(len(y_test))
    ]

    importance_list = _extract_feature_importance(clf, model_type, feat_names)
    class_distribution = target_info.get("class_distribution") or {
        class_names[i]: int((y == i).sum()) for i in range(len(class_names))
    }

    return _package_results(
        clf=clf,
        le=le,
        y_test=y_test,
        y_pred=y_pred,
        y_proba=y_proba,
        feature_columns=feature_columns,
        target_column=target_column,
        training_mode="tabular",
        model_type=model_type,
        df=df,
        samples_used=len(X),
        n_features=len(feat_names),
        X_train_len=len(X_train),
        X_test_len=len(X_test),
        class_distribution=class_distribution,
        cv_scores=cv_scores,
        predictions_table=predictions_table,
        importance_list=importance_list,
        scaler=scaler,
        feature_encoders=feature_encoders,
        test_size=test_size,
    )


def _train_smiles_fingerprint(
    df: pd.DataFrame,
    smiles_column: str,
    target_column: str,
    model_type: str,
    test_size: float,
    random_state: int,
    cv_folds: int,
) -> dict[str, Any]:
    validate_target_column(df, target_column)

    valid_rows: list[tuple[np.ndarray, Any]] = []
    invalid_count = 0
    for _, row in df.iterrows():
        if pd.isna(row[target_column]):
            continue
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
    y = le.fit_transform([str(v) for v in y_raw])
    if len(np.unique(y)) < 2:
        raise ValueError("Target column must have at least two classes.")

    class_counts = pd.Series(y).value_counts()
    if (class_counts < MIN_SAMPLES_PER_CLASS).any():
        raise ValueError(
            f"Each class must have at least {MIN_SAMPLES_PER_CLASS} samples."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    clf = _build_classifier(model_type, random_state)
    cv_scores = _run_cross_validation(clf, X, y, cv_folds, model_type)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    class_names = [str(c) for c in le.classes_]
    actual_labels = [class_names[i] for i in y_test]
    predicted_labels = [class_names[i] for i in y_pred]
    predictions_table = [
        {"actual": actual_labels[i], "predicted": predicted_labels[i]}
        for i in range(len(y_test))
    ]

    class_distribution = {str(k): int(v) for k, v in pd.Series(y_raw).astype(str).value_counts().to_dict().items()}
    feat_names = [f"fp_{i}" for i in range(X.shape[1])]
    importance_list = _extract_feature_importance(clf, model_type, feat_names)

    return _package_results(
        clf=clf,
        le=le,
        y_test=y_test,
        y_pred=y_pred,
        y_proba=y_proba,
        feature_columns=[smiles_column],
        target_column=target_column,
        training_mode="fingerprints",
        model_type=model_type,
        df=df,
        samples_used=len(valid_rows),
        n_features=int(X.shape[1]),
        invalid_smiles_skipped=invalid_count,
        X_train_len=len(X_train),
        X_test_len=len(X_test),
        class_distribution=class_distribution,
        cv_scores=cv_scores,
        predictions_table=predictions_table,
        importance_list=importance_list,
        test_size=test_size,
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
    model_type: str,
    df: pd.DataFrame,
    samples_used: int,
    n_features: int,
    X_train_len: int,
    X_test_len: int,
    class_distribution: dict[str, int],
    cv_scores: np.ndarray,
    predictions_table: list[dict[str, str]],
    importance_list: list[dict[str, Any]] | None = None,
    invalid_smiles_skipped: int = 0,
    scaler=None,
    feature_encoders: dict | None = None,
    test_size: float = 0.2,
) -> dict[str, Any]:
    acc = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

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
    fi_png = _feature_importance_png(importance_list) if importance_list else None

    cv_mean = round(float(cv_scores.mean()), 4) if len(cv_scores) else None
    warnings: list[str] = []
    if invalid_smiles_skipped:
        warnings.append(f"{invalid_smiles_skipped} invalid SMILES row(s) were skipped.")
    if len(cv_scores) == 0:
        warnings.append("Cross-validation was skipped (dataset too small or CV failed).")

    debug_info = {
        "dataset_shape": [int(len(df)), int(len(df.columns))],
        "feature_columns": feature_columns,
        "target_column": target_column,
        "model_type": model_type,
        "model_name": SUPPORTED_MODELS.get(model_type, model_type),
        "train_size": int(X_train_len),
        "test_size": int(X_test_len),
        "test_split_ratio": test_size,
        "class_distribution": class_distribution,
        "x_shape": [int(samples_used), int(n_features)],
        "y_shape": [int(samples_used)],
        "unique_classes": class_names,
        "warnings": warnings,
    }

    model_bundle = {
        "classifier": clf,
        "label_encoder": le,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "training_mode": training_mode,
        "model_type": model_type,
        "scaler": scaler,
        "feature_encoders": feature_encoders or {},
    }

    metadata = {
        "feature_columns": feature_columns,
        "target_column": target_column,
        "training_mode": training_mode,
        "model_type": model_type,
        "model_name": SUPPORTED_MODELS.get(model_type, model_type),
        "classes": class_names,
        "n_train": X_train_len,
        "n_test": X_test_len,
        "accuracy": round(float(acc), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "auc": auc_score,
        "cv_mean_accuracy": cv_mean,
        "cv_folds": int(len(cv_scores)) if len(cv_scores) else 0,
    }

    set_trained_classifier(
        clf,
        metadata,
        label_encoder=le,
        model_bundle=model_bundle,
        predictions=predictions_table,
    )

    logger.info(
        "Training complete: model=%s accuracy=%.4f samples=%d",
        model_type,
        acc,
        samples_used,
    )

    return {
        "success_message": "Model trained successfully.",
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "accuracy": round(float(acc), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "auc": auc_score,
        "cv_mean_accuracy": cv_mean,
        "cv_scores": [round(float(s), 4) for s in cv_scores.tolist()],
        "classification_report": report,
        "classification_report_text": classification_report(y_test, y_pred, target_names=class_names),
        "confusion_matrix": cm,
        "confusion_matrix_labels": class_names,
        "confusion_matrix_png": cm_png,
        "class_labels": class_names,
        "class_distribution": class_distribution,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "training_mode": training_mode,
        "model_type": model_type,
        "model_name": SUPPORTED_MODELS.get(model_type, model_type),
        "samples_used": samples_used,
        "n_features": n_features,
        "invalid_smiles_skipped": invalid_smiles_skipped,
        "roc_curve_png": roc_png,
        "roc_curve": roc_points,
        "feature_importance": importance_list,
        "feature_importance_png": fi_png,
        "predictions": predictions_table,
        "debug": debug_info,
        "model_ready_for_admet": training_mode == "fingerprints" and model_type == "random_forest",
        "model_download_available": True,
        "predictions_download_available": True,
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


def get_predictions_csv() -> str | None:
    from app.services.model_store import get_predictions

    predictions = get_predictions()
    if not predictions:
        return None
    df = pd.DataFrame(predictions)
    return df.to_csv(index=False)


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
