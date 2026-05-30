"""2D and 3D molecular structure generation."""

from __future__ import annotations

import base64
import io
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem, Draw

from app.services.descriptors import mol_from_smiles


def smiles_to_2d_png(smiles: str, size: tuple[int, int] = (400, 400)) -> bytes:
    mol = mol_from_smiles(smiles)
    AllChem.Compute2DCoords(mol)
    img = Draw.MolToImage(mol, size=size)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def smiles_to_2d_base64(smiles: str, size: tuple[int, int] = (400, 400)) -> str:
    return base64.b64encode(smiles_to_2d_png(smiles, size)).decode("ascii")


def generate_3d_structure(smiles: str, optimize: bool = True) -> dict[str, Any]:
    mol = mol_from_smiles(smiles)
    mol_h = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    status = AllChem.EmbedMolecule(mol_h, params)
    if status == -1:
        raise ValueError("Could not generate 3D coordinates for this molecule.")

    if optimize:
        AllChem.UFFOptimizeMolecule(mol_h, maxIters=500)

    conf = mol_h.GetConformer()
    atoms = []
    for i, atom in enumerate(mol_h.GetAtoms()):
        pos = conf.GetAtomPosition(i)
        atoms.append(
            {
                "index": i,
                "symbol": atom.GetSymbol(),
                "x": round(pos.x, 4),
                "y": round(pos.y, 4),
                "z": round(pos.z, 4),
            }
        )

    bonds = []
    for bond in mol_h.GetBonds():
        bonds.append(
            {
                "begin": bond.GetBeginAtomIdx(),
                "end": bond.GetEndAtomIdx(),
                "order": int(bond.GetBondTypeAsDouble()),
            }
        )

    return {
        "canonical_smiles": Chem.MolToSmiles(mol),
        "num_atoms": len(atoms),
        "atoms": atoms,
        "bonds": bonds,
        "energy_minimized": optimize,
    }


def smiles_to_3d_png(smiles: str, size: tuple[int, int] = (450, 450)) -> bytes:
    mol = mol_from_smiles(smiles)
    mol_h = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    if AllChem.EmbedMolecule(mol_h, params) == -1:
        raise ValueError("Could not embed 3D structure.")
    AllChem.UFFOptimizeMolecule(mol_h, maxIters=200)
    img = Draw.MolToImage(mol_h, size=size)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
