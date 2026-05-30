"""RDKit molecular descriptor calculations."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors


@dataclass
class MolecularDescriptors:
    molecular_weight: float
    logp: float
    tpsa: float
    h_bond_donors: int
    h_bond_acceptors: int
    rotatable_bonds: int
    aromatic_rings: int
    heavy_atoms: int
    fraction_csp3: float
    qed: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def mol_from_smiles(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError("Invalid SMILES string. Could not parse molecule.")
    Chem.SanitizeMol(mol)
    return mol


def calculate_descriptors(mol: Chem.Mol) -> MolecularDescriptors:
    return MolecularDescriptors(
        molecular_weight=round(Descriptors.MolWt(mol), 2),
        logp=round(Descriptors.MolLogP(mol), 2),
        tpsa=round(Descriptors.TPSA(mol), 2),
        h_bond_donors=Lipinski.NumHDonors(mol),
        h_bond_acceptors=Lipinski.NumHAcceptors(mol),
        rotatable_bonds=Lipinski.NumRotatableBonds(mol),
        aromatic_rings=rdMolDescriptors.CalcNumAromaticRings(mol),
        heavy_atoms=mol.GetNumHeavyAtoms(),
        fraction_csp3=round(Lipinski.FractionCSP3(mol), 3),
        qed=round(Descriptors.qed(mol), 3),
    )


def morgan_fingerprint_vector(mol: Chem.Mol, radius: int = 2, n_bits: int = 2048) -> list[int]:
    from rdkit.Chem import AllChem

    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return list(fp)
