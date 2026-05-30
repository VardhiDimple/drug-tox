"""Dataset visualization with matplotlib and plotly."""

from __future__ import annotations

import base64
import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120, facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def generate_plot(
    df: pd.DataFrame,
    plot_type: str,
    x_column: str | None = None,
    y_column: str | None = None,
    color_column: str | None = None,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    plot_type = plot_type.lower().strip().replace(" ", "_")

    if plot_type in ("correlation_matrix", "correlation"):
        plot_type = "correlation_matrix"
    if plot_type == "heatmap" and not columns:
        plot_type = "correlation_matrix"

    handlers = {
        "scatter": _plot_scatter,
        "heatmap": _plot_heatmap,
        "correlation_matrix": _plot_correlation_matrix,
        "boxplot": _plot_boxplot,
        "histogram": _plot_histogram,
        "bar": _plot_bar,
        "bar_chart": _plot_bar,
        "line": _plot_line,
        "line_plot": _plot_line,
    }
    handler = handlers.get(plot_type)
    if not handler:
        raise ValueError(
            f"Unsupported plot_type: {plot_type}. "
            "Use scatter, heatmap, boxplot, histogram, bar, line, or correlation_matrix."
        )
    return handler(df, x_column, y_column, color_column, columns)


def _plot_scatter(df, x_column, y_column, color_column, columns):
    if not x_column or not y_column:
        raise ValueError("Scatter plot requires x_column and y_column.")
    if x_column not in df.columns or y_column not in df.columns:
        raise ValueError("Selected columns not found in dataset.")
    fig = px.scatter(
        df,
        x=x_column,
        y=y_column,
        color=color_column if color_column in df.columns else None,
        title=f"{y_column} vs {x_column}",
        template="plotly_white",
    )
    return {
        "plot_type": "scatter",
        "plotly_json": fig.to_json(),
        "matplotlib_png": _scatter_mpl(df, x_column, y_column, color_column),
    }


def _plot_heatmap(df, x_column, y_column, color_column, columns):
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
    if len(cols) < 2:
        raise ValueError("Heatmap requires at least 2 numeric columns.")
    pivot = df[cols].corr()
    fig = go.Figure(
        data=go.Heatmap(z=pivot.values, x=list(pivot.columns), y=list(pivot.index), colorscale="Viridis")
    )
    fig.update_layout(title="Heatmap (correlation values)", template="plotly_white")
    return {"plot_type": "heatmap", "plotly_json": fig.to_json(), "matplotlib_png": _heatmap_mpl(pivot, "Heatmap")}


def _plot_correlation_matrix(df, x_column, y_column, color_column, columns):
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
    if len(cols) < 2:
        raise ValueError("Correlation matrix requires at least 2 numeric columns.")
    corr = df[cols].corr()
    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=list(corr.columns),
            y=list(corr.index),
            colorscale="RdBu",
            zmid=0,
            text=np.round(corr.values, 2),
            texttemplate="%{text}",
        )
    )
    fig.update_layout(title="Correlation Matrix", template="plotly_white")
    return {
        "plot_type": "correlation_matrix",
        "plotly_json": fig.to_json(),
        "matplotlib_png": _heatmap_mpl(corr, "Correlation Matrix"),
    }


def _plot_boxplot(df, x_column, y_column, color_column, columns):
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()[:8]
    if not cols:
        raise ValueError("Boxplot requires numeric columns.")
    fig = px.box(df, y=cols[0] if len(cols) == 1 else None, template="plotly_white", title="Box Plot")
    if len(cols) > 1:
        melted = df[cols].melt(var_name="variable", value_name="value")
        fig = px.box(melted, x="variable", y="value", title="Box Plot", template="plotly_white")
    fig_mpl, ax = plt.subplots(figsize=(8, 5))
    data = [df[c].dropna().values for c in cols]
    ax.boxplot(data, tick_labels=cols)
    ax.set_title("Box Plot")
    ax.set_ylabel("Value")
    plt.xticks(rotation=30, ha="right")
    return {"plot_type": "boxplot", "plotly_json": fig.to_json(), "matplotlib_png": _fig_to_base64(fig_mpl)}


def _plot_histogram(df, x_column, y_column, color_column, columns):
    col = x_column or (columns[0] if columns else None)
    if not col or col not in df.columns:
        raise ValueError("Histogram requires a numeric x_column.")
    fig = px.histogram(df, x=col, color=color_column if color_column in df.columns else None, title=f"Histogram of {col}", template="plotly_white")
    fig_mpl, ax = plt.subplots(figsize=(7, 5))
    ax.hist(df[col].dropna(), bins=30, color="#2563eb", edgecolor="white", alpha=0.85)
    ax.set_xlabel(col)
    ax.set_ylabel("Frequency")
    ax.set_title(f"Histogram of {col}")
    ax.grid(True, alpha=0.3)
    return {"plot_type": "histogram", "plotly_json": fig.to_json(), "matplotlib_png": _fig_to_base64(fig_mpl)}


def _plot_bar(df, x_column, y_column, color_column, columns):
    if not x_column:
        raise ValueError("Bar chart requires x_column (category).")
    y_col = y_column
    if y_col and y_col in df.columns:
        fig = px.bar(df, x=x_column, y=y_col, color=color_column if color_column in df.columns else None, title=f"{y_col} by {x_column}", template="plotly_white")
        agg = df.groupby(x_column)[y_col].mean().reset_index()
    else:
        counts = df[x_column].value_counts().reset_index()
        counts.columns = [x_column, "count"]
        fig = px.bar(counts, x=x_column, y="count", title=f"Count by {x_column}", template="plotly_white")
        agg = counts
    fig_mpl, ax = plt.subplots(figsize=(8, 5))
    ax.bar(agg.iloc[:, 0].astype(str), agg.iloc[:, 1], color="#2563eb", alpha=0.85)
    ax.set_xlabel(x_column)
    ax.set_ylabel(agg.columns[1])
    ax.set_title(f"Bar Chart — {x_column}")
    plt.xticks(rotation=30, ha="right")
    return {"plot_type": "bar", "plotly_json": fig.to_json(), "matplotlib_png": _fig_to_base64(fig_mpl)}


def _plot_line(df, x_column, y_column, color_column, columns):
    if not x_column or not y_column:
        raise ValueError("Line plot requires x_column and y_column.")
    fig = px.line(df, x=x_column, y=y_column, color=color_column if color_column in df.columns else None, title=f"{y_column} over {x_column}", template="plotly_white")
    fig_mpl, ax = plt.subplots(figsize=(8, 5))
    if color_column and color_column in df.columns:
        for label, group in df.groupby(color_column):
            ax.plot(group[x_column], group[y_column], marker="o", label=str(label), alpha=0.8)
        ax.legend(fontsize=8)
    else:
        ax.plot(df[x_column], df[y_column], marker="o", color="#2563eb", alpha=0.85)
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)
    ax.set_title(f"Line Plot — {y_column} vs {x_column}")
    ax.grid(True, alpha=0.3)
    return {"plot_type": "line", "plotly_json": fig.to_json(), "matplotlib_png": _fig_to_base64(fig_mpl)}


def _scatter_mpl(df, x, y, color):
    fig, ax = plt.subplots(figsize=(7, 5))
    if color and color in df.columns:
        for label, group in df.groupby(color):
            ax.scatter(group[x], group[y], label=str(label), alpha=0.7, s=40)
        ax.legend(title=color, fontsize=8)
    else:
        ax.scatter(df[x], df[y], alpha=0.7, c="#2563eb", s=40)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"{y} vs {x}")
    ax.grid(True, alpha=0.3)
    return _fig_to_base64(fig)


def _heatmap_mpl(corr, title):
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.index)
    fig.colorbar(im, ax=ax)
    ax.set_title(title)
    return _fig_to_base64(fig)
