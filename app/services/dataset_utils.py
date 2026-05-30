"""Shared dataset preview and upload parsing utilities."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd

SUPPORTED_DATASET_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls"}


def dataset_preview(df: pd.DataFrame, head: int = 8) -> dict[str, Any]:
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = [c for c in df.columns if c not in numeric]
    return {
        "shape": {"rows": int(len(df)), "columns": int(len(df.columns))},
        "columns": list(df.columns),
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "preview": df.head(head).astype(str).to_dict(orient="records"),
        "preview_rows": min(head, len(df)),
    }


def _extension(filename: str | None) -> str:
    if not filename:
        return ""
    return ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""


def load_uploaded_dataset(content: bytes, filename: str | None = None) -> pd.DataFrame:
    """Load CSV, TSV, or Excel uploads into a DataFrame."""
    if not content:
        raise ValueError("Uploaded file is empty.")

    ext = _extension(filename)
    buffer = io.BytesIO(content)

    if ext in (".xlsx", ".xls"):
        engine = "openpyxl" if ext == ".xlsx" else None
        try:
            df = pd.read_excel(buffer, engine=engine)
        except ImportError as e:
            raise ValueError(
                "Excel support requires openpyxl. Install with: pip install openpyxl"
            ) from e
        except Exception as e:
            raise ValueError(f"Could not read Excel file: {e}") from e
    elif ext in (".csv", ".tsv", ".txt", "") or not ext:
        sep = "\t" if ext == ".tsv" else ","
        last_error: Exception | None = None
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                buffer.seek(0)
                df = pd.read_csv(buffer, sep=sep, encoding=encoding)
                last_error = None
                break
            except UnicodeDecodeError as e:
                last_error = e
                continue
            except pd.errors.ParserError as e:
                raise ValueError(f"Could not parse file as CSV/TSV: {e}") from e
        if last_error is not None:
            raise ValueError(
                "Could not decode text file. Save as UTF-8 CSV or upload .xlsx instead."
            ) from last_error
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Upload CSV (.csv), TSV (.tsv), or Excel (.xlsx, .xls)."
        )

    if df.empty:
        raise ValueError("Dataset has no rows.")
    if len(df.columns) == 0:
        raise ValueError("Dataset has no columns.")

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]
    return df


def validate_dataset_filename(filename: str | None) -> None:
    ext = _extension(filename)
    if ext and ext not in SUPPORTED_DATASET_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DATASET_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{ext}'. Supported formats: {supported}")
