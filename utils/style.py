"""
Shared plotting and table style for the course.

    from utils.style import COLORS, CYCLE, apply_style
    apply_style()
"""

import html

import matplotlib.pyplot as plt
import polars as pl

# Fixed-order categorical palette (the first three hues are colour-blind safe as a set).
COLORS = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "teal": "#1baf7a",
    "grey": "#8a8984",
    "ink": "#0b0b0b",
    "ink_soft": "#52514e",
}
CYCLE = [COLORS["blue"], COLORS["orange"], COLORS["teal"]]


def _html_table(df: pl.DataFrame, decimals: int = 3, max_rows: int = 30) -> str:
    """Clean HTML table for a Polars DataFrame (no quotes, no dtypes)."""

    def cell(v):
        if v is None:
            return ""
        if isinstance(v, float):
            d = 1 if abs(v) >= 1_000 else decimals
            return f"{v:,.{d}f}"
        if isinstance(v, int) and not isinstance(v, bool) and abs(v) >= 10_000:
            return f"{v:,}"
        return html.escape(str(v))

    numeric = {c for c, t in df.schema.items() if t.is_numeric()}
    align = lambda c: ' style="text-align:right"' if c in numeric else ""  # noqa: E731
    head = "".join(f"<th{align(c)}>{html.escape(c)}</th>" for c in df.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td{align(c)}>{cell(v)}</td>" for c, v in zip(df.columns, row)) + "</tr>"
        for row in df.head(max_rows).iter_rows()
    )
    note = (
        f'<caption style="caption-side:bottom">Showing {max_rows} of {df.height} rows</caption>'
        if df.height > max_rows else ""
    )
    return (f'<table class="table table-sm" style="width:auto">{note}'
            f"<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>")


def apply_style() -> None:
    """Configure Matplotlib and the HTML display of Polars tables."""
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is not None:
            fmt = ip.display_formatter.formatters["text/html"]
            fmt.for_type(pl.DataFrame, _html_table)
            fmt.for_type(pl.Series, lambda s: _html_table(s.to_frame()))
    except ImportError:
        pass

    plt.rcParams.update({
        "figure.figsize": (7, 4),
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelcolor": COLORS["ink_soft"],
        "axes.edgecolor": COLORS["grey"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#e4e3df",
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "axes.prop_cycle": plt.cycler(color=CYCLE),
        "xtick.color": COLORS["ink_soft"],
        "ytick.color": COLORS["ink_soft"],
        "legend.frameon": False,
    })
