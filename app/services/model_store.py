"""In-memory store for user-trained ML models."""

from __future__ import annotations

from typing import Any

_trained_classifier: Any = None
_model_metadata: dict[str, Any] = {}
_label_encoder: Any = None
_model_bundle: dict[str, Any] | None = None
_predictions: list[dict[str, str]] | None = None


def set_trained_classifier(
    model: Any,
    metadata: dict[str, Any],
    label_encoder: Any = None,
    model_bundle: dict[str, Any] | None = None,
    predictions: list[dict[str, str]] | None = None,
) -> None:
    global _trained_classifier, _model_metadata, _label_encoder, _model_bundle, _predictions
    _trained_classifier = model
    _model_metadata = metadata
    _label_encoder = label_encoder
    _model_bundle = model_bundle
    _predictions = predictions


def get_trained_classifier() -> Any:
    return _trained_classifier


def get_label_encoder() -> Any:
    return _label_encoder


def get_model_metadata() -> dict[str, Any]:
    return dict(_model_metadata)


def is_model_usable_for_admet() -> bool:
    """True if a trained model exists and can score a single SMILES in ADMET."""
    if _model_bundle is None or _trained_classifier is None:
        return False
    mode = _model_bundle.get("training_mode", "tabular")
    if mode == "fingerprints":
        return True
    if mode == "tabular":
        return bool(_model_bundle.get("feature_columns"))
    return False


def get_model_bundle() -> dict[str, Any] | None:
    return _model_bundle


def get_predictions() -> list[dict[str, str]] | None:
    return list(_predictions) if _predictions else None


def clear_model() -> None:
    global _trained_classifier, _model_metadata, _label_encoder, _model_bundle, _predictions
    _trained_classifier = None
    _model_metadata = {}
    _label_encoder = None
    _model_bundle = None
    _predictions = None
