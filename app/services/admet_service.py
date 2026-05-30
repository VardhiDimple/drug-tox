"""ADMET prediction: Lipinski rules and toxicity scoring."""

from __future__ import annotations

from typing import Any

from rdkit import Chem
from rdkit.Chem import FilterCatalog

from app.services.descriptors import calculate_descriptors, mol_from_smiles
from app.services.model_store import get_trained_classifier


LIPINSKI_LIMITS = {
    "molecular_weight": 500,
    "logp": 5,
    "h_bond_donors": 5,
    "h_bond_acceptors": 10,
}

# Common toxicophore / structural alert patterns (SMARTS)
TOXICITY_ALERTS = [
    ("Nitro aromatic", "[N+](=O)[O-]c"),
    ("Epoxide", "C1OC1"),
    ("Aldehyde", "[CH]=O"),
    ("Michael acceptor", "C=CC(=O)"),
    ("Hydrazine", "NN"),
    ("Quinone", "O=C1C=CC(=O)C=C1"),
    ("Isocyanate", "N=C=O"),
    ("Azide", "N=[N+]=[N-]"),
]


def evaluate_lipinski(descriptors: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    checks = [
        ("molecular_weight", descriptors["molecular_weight"], LIPINSKI_LIMITS["molecular_weight"], "≤"),
        ("logp", descriptors["logp"], LIPINSKI_LIMITS["logp"], "≤"),
        ("h_bond_donors", descriptors["h_bond_donors"], LIPINSKI_LIMITS["h_bond_donors"], "≤"),
        ("h_bond_acceptors", descriptors["h_bond_acceptors"], LIPINSKI_LIMITS["h_bond_acceptors"], "≤"),
    ]
    for name, value, limit, op in checks:
        passed = value <= limit
        if not passed:
            violations.append(
                {
                    "property": name,
                    "value": value,
                    "limit": limit,
                    "operator": op,
                }
            )
    return {
        "passed": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations,
        "drug_like": len(violations) <= 1,
        "summary": "Passes Rule of Five"
        if len(violations) == 0
        else f"{len(violations)} violation(s) — {'still drug-like (≤1 violation)' if len(violations) <= 1 else 'poor drug-likeness'}",
    }


def _count_structural_alerts(mol: Chem.Mol) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    for name, smarts in TOXICITY_ALERTS:
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is not None and mol.HasSubstructMatch(pattern):
            alerts.append({"name": name, "smarts": smarts})
    return alerts


def _rdkit_pains_alerts(mol: Chem.Mol) -> list[str]:
    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
    catalog = FilterCatalog.FilterCatalog(params)
    entries = catalog.GetMatches(mol)
    return [e.GetDescription() for e in entries]


def rule_based_toxicity_score(mol: Chem.Mol, descriptors: dict[str, Any]) -> dict[str, Any]:
    """Heuristic toxicity risk from descriptors and substructure alerts."""
    score = 0.0
    factors: list[str] = []

    if descriptors["molecular_weight"] > 600:
        score += 0.15
        factors.append("High molecular weight (>600)")
    if descriptors["logp"] > 5:
        score += 0.2
        factors.append("High LogP (>5)")
    if descriptors["logp"] < -1:
        score += 0.1
        factors.append("Very low LogP (<-1)")
    if descriptors["tpsa"] < 20:
        score += 0.1
        factors.append("Low TPSA (<20) — possible permeability/tox issues")
    if descriptors["tpsa"] > 140:
        score += 0.1
        factors.append("High TPSA (>140) — poor absorption")
    if descriptors["rotatable_bonds"] > 10:
        score += 0.1
        factors.append("High rotatable bond count")

    alerts = _count_structural_alerts(mol)
    pains = _rdkit_pains_alerts(mol)
    score += min(0.4, 0.08 * len(alerts))
    score += min(0.3, 0.05 * len(pains))

    if alerts:
        factors.append(f"{len(alerts)} toxicophore alert(s) detected")
    if pains:
        factors.append(f"{len(pains)} PAINS filter hit(s)")

    lipinski = evaluate_lipinski(descriptors)
    score += 0.05 * lipinski["violation_count"]

    score = min(1.0, round(score, 3))
    label = "Low" if score < 0.35 else "Moderate" if score < 0.65 else "High"

    return {
        "method": "rule_based",
        "risk_score": score,
        "risk_label": label,
        "toxicity_class": "Non-toxic" if score < 0.35 else "Uncertain" if score < 0.65 else "Potentially toxic",
        "contributing_factors": factors,
        "structural_alerts": alerts,
        "pains_alerts": pains[:10],
    }


def ml_toxicity_prediction(mol: Chem.Mol) -> dict[str, Any] | None:
    clf = get_trained_classifier()
    if clf is None:
        return None
    from app.services.descriptors import morgan_fingerprint_vector

    X = [morgan_fingerprint_vector(mol)]
    proba = clf.predict_proba(X)[0]
    pred = int(clf.predict(X)[0])
    classes = list(clf.classes_)
    toxic_idx = 1 if len(classes) > 1 and max(classes) == 1 else int(pred)
    toxic_prob = float(proba[toxic_idx]) if len(proba) > toxic_idx else float(max(proba))

    return {
        "method": "ml_classifier",
        "predicted_class": int(pred),
        "class_labels": [str(c) for c in classes],
        "probabilities": {str(c): round(float(p), 4) for c, p in zip(classes, proba)},
        "toxicity_probability": round(toxic_prob, 4),
        "toxicity_class": "Potentially toxic" if toxic_prob >= 0.5 else "Non-toxic",
        "risk_score": round(toxic_prob, 3),
        "risk_label": "Low" if toxic_prob < 0.35 else "Moderate" if toxic_prob < 0.65 else "High",
    }


def predict_admet(smiles: str) -> dict[str, Any]:
    mol = mol_from_smiles(smiles)
    desc = calculate_descriptors(mol)
    desc_dict = desc.to_dict()
    lipinski = evaluate_lipinski(desc_dict)
    rule_tox = rule_based_toxicity_score(mol, desc_dict)
    ml_tox = ml_toxicity_prediction(mol)

    canonical_smiles = Chem.MolToSmiles(mol)
    return {
        "input_smiles": smiles.strip(),
        "canonical_smiles": canonical_smiles,
        "descriptors": desc_dict,
        "lipinski": lipinski,
        "toxicity": {
            "primary": ml_tox if ml_tox else rule_tox,
            "rule_based": rule_tox,
            "ml": ml_tox,
            "note": "Using trained ML model." if ml_tox else "Train a model in ML Classifier to enable ML-based toxicity.",
        },
        "admet_summary": {
            "absorption_hint": "Good" if desc_dict["tpsa"] <= 90 and desc_dict["logp"] <= 5 else "Review",
            "distribution_hint": "Favorable" if 200 <= desc_dict["molecular_weight"] <= 500 else "Review",
            "metabolism_hint": "Lower risk" if desc_dict["rotatable_bonds"] <= 7 else "Higher flexibility",
            "excretion_hint": "Polar" if desc_dict["logp"] < 2 else "Lipophilic",
            "toxicity_hint": (ml_tox or rule_tox)["risk_label"],
        },
    }
