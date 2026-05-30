"""In-memory store for user-trained ML models."""

from __future__ import annotations

from typing import Any

_trained_classifier: Any = None
_model_metadata: dict[str, Any] = {}
_label_encoder: Any = None
_model_bundle: dict[str, Any] | None = None


def set_trained_classifier(
    model: Any,
    metadata: dict[str, Any],
    label_encoder: Any = None,
    model_bundle: dict[str, Any] | None = None,
) -> None:
    global _trained_classifier, _model_metadata, _label_encoder, _model_bundle
    _trained_classifier = model
    _model_metadata = metadata
    _label_encoder = label_encoder
    _model_bundle = model_bundle


def get_trained_classifier() -> Any:
    return _trained_classifier


def get_model_metadata() -> dict[str, Any]:
    return dict(_model_metadata)


def get_model_bundle() -> dict[str, Any] | None:
    return _model_bundle


def clear_model() -> None:
    global _trained_classifier, _model_metadata, _label_encoder, _model_bundle
    _trained_classifier = None
    _model_metadata = {}
    _label_encoder = None
    _model_bundle = None
