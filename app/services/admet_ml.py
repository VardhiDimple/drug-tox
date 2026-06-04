"""ML inference for ADMET toxicity from a trained classifier bundle."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from rdkit import Chem

from app.services.descriptors import calculate_descriptors, morgan_fingerprint_vector
from app.services.model_store import get_model_bundle, get_model_metadata

logger = logging.getLogger(__name__)

# Map common dataset column names → keys from calculate_descriptors().to_dict()
COLUMN_TO_DESCRIPTOR: dict[str, str] = {
    "molecularweight": "molecular_weight",
    "molweight": "molecular_weight",
    "mw": "molecular_weight",
    "weight": "molecular_weight",
    "logp": "logp",
    "log_p": "logp",
    "tpsa": "tpsa",
    "hbd": "h_bond_donors",
    "h_bond_donors": "h_bond_donors",
    "donors": "h_bond_donors",
    "hba": "h_bond_acceptors",
    "h_bond_acceptors": "h_bond_acceptors",
    "acceptors": "h_bond_acceptors",
    "rotatablebonds": "rotatable_bonds",
    "rotatable_bonds": "rotatable_bonds",
    "nrotb": "rotatable_bonds",
    "aromaticrings": "aromatic_rings",
    "aromatic_rings": "aromatic_rings",
    "heavyatoms": "heavy_atoms",
    "heavy_atoms": "heavy_atoms",
    "fractioncsp3": "fraction_csp3",
    "fraction_csp3": "fraction_csp3",
    "qed": "qed",
}


def _normalize_col(name: str) -> str:
    return str(name).lower().replace(" ", "").replace("_", "")


def _descriptor_key_for_column(col: str) -> str | None:
    norm = _normalize_col(col)
    if norm in COLUMN_TO_DESCRIPTOR:
        return COLUMN_TO_DESCRIPTOR[norm]
    # direct match on descriptor dict keys
    for key in (
        "molecular_weight",
        "logp",
        "tpsa",
        "h_bond_donors",
        "h_bond_acceptors",
        "rotatable_bonds",
        "aromatic_rings",
        "heavy_atoms",
        "fraction_csp3",
        "qed",
    ):
        if _normalize_col(key) == norm:
            return key
    return None


def _build_tabular_features_from_mol(mol: Chem.Mol, bundle: dict[str, Any]) -> np.ndarray:
    feature_columns: list[str] = bundle.get("feature_columns") or []
    if not feature_columns:
        raise ValueError("Trained model has no feature columns.")

    desc = calculate_descriptors(mol).to_dict()
    encoders = bundle.get("feature_encoders") or {}
    row: list[float] = []

    for col in feature_columns:
        if _normalize_col(col) == "smiles":
            raise ValueError(
                "ADMET cannot use a tabular model trained only on SMILES strings. "
                "Train on descriptor columns (e.g. MolecularWeight, LogP, TPSA) or use a SMILES fingerprint model."
            )

        desc_key = _descriptor_key_for_column(col)
        if desc_key is None:
            raise ValueError(
                f"Feature column '{col}' cannot be computed from a SMILES structure in ADMET. "
                f"Supported: MolecularWeight, LogP, TPSA, HBD, HBA, RotatableBonds, AromaticRings, etc."
            )

        val = float(desc[desc_key])
        if col in encoders:
            le = encoders[col]
            try:
                val = float(le.transform([str(int(val)) if val == int(val) else str(val)])[0])
            except ValueError:
                val = float(le.transform([str(val)])[0])
        row.append(val)

    X = np.array([row], dtype=float)
    scaler = bundle.get("scaler")
    if scaler is not None:
        X = scaler.transform(X)
    return X


def _build_fingerprint_features(mol: Chem.Mol) -> np.ndarray:
    return np.array([morgan_fingerprint_vector(mol)], dtype=float)


def predict_toxicity_ml(mol: Chem.Mol) -> dict[str, Any] | None:
    """
    Run the in-memory trained classifier on a molecule.
    Uses fingerprint features OR RDKit descriptors depending on how the model was trained.
    """
    bundle = get_model_bundle()
    if bundle is None:
        return None

    clf = bundle.get("classifier")
    if clf is None:
        return None

    le = bundle.get("label_encoder")
    training_mode = bundle.get("training_mode", "tabular")
    meta = get_model_metadata()

    try:
        if training_mode == "fingerprints":
            X = _build_fingerprint_features(mol)
        else:
            X = _build_tabular_features_from_mol(mol, bundle)

        expected = getattr(clf, "n_features_in_", None)
        if expected is not None and X.shape[1] != expected:
            raise ValueError(
                f"Feature mismatch: model expects {expected} features, got {X.shape[1]}. "
                "Retrain the model or clear it from ML Classifier."
            )

        proba = clf.predict_proba(X)[0]
        pred_encoded = int(clf.predict(X)[0])

        if le is not None:
            class_labels = [str(c) for c in le.classes_]
            pred_label = str(le.inverse_transform([pred_encoded])[0])
        else:
            class_labels = [str(c) for c in getattr(clf, "classes_", [])]
            pred_label = class_labels[pred_encoded] if pred_encoded < len(class_labels) else str(pred_encoded)

        # Toxic probability: class "1" or highest positive label
        toxic_prob = 0.0
        if len(proba) == 2:
            idx = 1
            if le is not None and "1" in class_labels:
                idx = class_labels.index("1")
            elif "1" in class_labels:
                idx = class_labels.index("1")
            toxic_prob = float(proba[idx])
        else:
            toxic_prob = float(max(proba))

        is_toxic = toxic_prob >= 0.5
        if le is not None:
            toxic_labels = {str(c).lower() for c in class_labels if str(c).lower() in ("1", "toxic", "yes", "true")}
            if toxic_labels and pred_label.lower() in toxic_labels:
                is_toxic = True

        return {
            "method": "ml_classifier",
            "model_name": meta.get("model_name", bundle.get("model_type", "ml")),
            "training_mode": training_mode,
            "predicted_class": pred_label,
            "class_labels": class_labels,
            "probabilities": {
                str(class_labels[i] if i < len(class_labels) else i): round(float(p), 4)
                for i, p in enumerate(proba)
            },
            "toxicity_probability": round(toxic_prob, 4),
            "toxicity_class": "Potentially toxic" if is_toxic else "Non-toxic",
            "risk_score": round(toxic_prob, 3),
            "risk_label": "Low" if toxic_prob < 0.35 else "Moderate" if toxic_prob < 0.65 else "High",
        }
    except Exception as exc:
        logger.warning("ADMET ML prediction skipped: %s", exc)
        return {
            "method": "rule_based_fallback",
            "ml_error": str(exc),
        }
