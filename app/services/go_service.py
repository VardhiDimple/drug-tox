"""Gene Ontology enrichment analysis via Enrichr (gseapy)."""

from __future__ import annotations

import base64
import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


GO_LIBRARIES = [
    "GO_Biological_Process_2023",
    "GO_Molecular_Function_2023",
    "GO_Cellular_Component_2023",
]


def parse_gene_input(text: str | None = None, file_content: str | None = None) -> list[str]:
    raw = ""
    if text and text.strip():
        raw = text
    elif file_content:
        raw = file_content
    else:
        raise ValueError("Provide gene symbols via text input or file upload.")

    genes: list[str] = []
    for line in raw.replace(",", "\n").replace(";", "\n").splitlines():
        token = line.strip().upper()
        if not token or token.startswith("#"):
            continue
        if "," in token:
            genes.extend(g.strip().upper() for g in token.split(",") if g.strip())
        else:
            genes.append(token)
    genes = list(dict.fromkeys(genes))
    if len(genes) < 2:
        raise ValueError("Provide at least 2 unique gene symbols.")
    return genes


def run_go_enrichment(genes: list[str], max_terms: int = 25) -> dict[str, Any]:
    try:
        import gseapy as gp
    except ImportError as e:
        raise ValueError("gseapy is required for GO enrichment. Install with: pip install gseapy") from e

    enr = gp.enrichr(
        gene_list=genes,
        gene_sets=GO_LIBRARIES,
        organism="human",
        outdir=None,
        no_plot=True,
    )
    results = enr.results
    if results is None or results.empty:
        raise ValueError("No enrichment results returned. Check gene symbols (e.g. TP53, BRCA1).")

    df = results.copy()
    rename_map = {
        "Term": "go_term",
        "P-value": "p_value",
        "Adjusted P-value": "adjusted_p_value",
        "Odds Ratio": "odds_ratio",
        "Combined Score": "combined_score",
        "Genes": "genes",
        "Overlap": "overlap",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    for col in ("p_value", "adjusted_p_value"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "overlap" in df.columns:
        df["gene_count"] = df["overlap"].astype(str).str.split("/").str[0].astype(int, errors="ignore")
    elif "genes" in df.columns:
        df["gene_count"] = df["genes"].astype(str).str.count(";") + 1
    else:
        df["gene_count"] = 0

    df = df.head(max_terms)
    chart_png = _enrichment_barplot(df)

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "go_term": str(row.get("go_term", row.get("Term", ""))),
                "p_value": float(row["p_value"]) if pd.notna(row.get("p_value")) else None,
                "adjusted_p_value": float(row["adjusted_p_value"]) if pd.notna(row.get("adjusted_p_value")) else None,
                "gene_count": int(row.get("gene_count", 0)) if pd.notna(row.get("gene_count")) else 0,
                "genes": str(row.get("genes", "")),
                "library": str(row.get("Gene_set", "")),
            }
        )

    return {
        "input_gene_count": len(genes),
        "genes": genes,
        "results": records,
        "result_count": len(records),
        "chart_png": chart_png,
        "export_csv": df.to_csv(index=False),
    }


def _enrichment_barplot(df: pd.DataFrame) -> str:
    plot_df = df.head(15).copy()
    if plot_df.empty:
        return ""
    term_col = "go_term" if "go_term" in plot_df.columns else "Term"
    p_col = "adjusted_p_value" if "adjusted_p_value" in plot_df.columns else "P-value"
    plot_df["neg_log10_p"] = plot_df[p_col].apply(
        lambda x: 0.0 if pd.isna(x) or x <= 0 else -np.log10(float(x))
    )

    fig, ax = plt.subplots(figsize=(9, 6))
    labels = plot_df[term_col].astype(str).str[:60]
    ax.barh(range(len(plot_df)), plot_df["neg_log10_p"], color="#3b82f6", alpha=0.85)
    ax.set_yticks(range(len(plot_df)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("-log10(Adjusted P-value)")
    ax.set_title("GO Enrichment — Top Terms")
    ax.grid(True, axis="x", alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")
