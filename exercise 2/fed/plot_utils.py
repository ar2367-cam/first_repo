"""Plotting functions return figures without displaying or saving implicitly."""

from math import ceil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from numpy.typing import NDArray

from . import settings
from .analysis import add_growth_measures

COLORS = {
    "Brazil": "#a66700",
    "China": "#d14141",
    "Germany": "#597538",
    "Japan": "#8e5eb5",
    "Switzerland": "#a14b78",
    "United Kingdom": "#157e93",
    "United States": "#305aaa",
}


def plot_gdp(
    data: pd.DataFrame, *, indexed: bool = False, base_year: int | None = None
) -> tuple[Figure, Axes]:
    """Return (figure, axes) comparing clean GDP levels or an index.

    Input columns: country_code, country, year, gdp_usd in settings.UNITS.
    Levels are displayed in trillions; indexed values use base_year = 100.
    The title follows the supplied years. An empty table or missing index base
    raises ValueError. The caller decides whether to display or save the figure.
    """
    if data.empty:
        raise ValueError("Cannot plot an empty GDP table")
    base_year = settings.BASE_YEAR if base_year is None else base_year
    frame = add_growth_measures(data, base_year) if indexed else data
    start, end = int(frame["year"].min()), int(frame["year"].max())
    fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    for country, group in frame.groupby("country", sort=True):
        group = group.sort_values("year")
        values = group["gdp_index"] if indexed else group["gdp_usd"] / 1e12
        ax.plot(
            group["year"],
            values,
            label=country,
            color=COLORS.get(country),
            linewidth=2.3,
        )
    title = (
        f"Real GDP index, {start}–{end} (base {base_year})"
        if indexed
        else f"Annual real GDP, {start}–{end}"
    )
    ax.set(
        title=title,
        xlabel="Year",
        ylabel=f"Index ({base_year} = 100)" if indexed else f"GDP (trillion {settings.UNITS})",
    )
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
    ax.grid(axis="y", alpha=0.22)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    fig.text(
        0.01,
        -0.025,
        f"Source: World Bank WDI · {settings.INDICATOR} · annual · {settings.UNITS}",
        fontsize=9,
        color="#555555",
    )
    return fig, ax


def plot_annual_growth(data: pd.DataFrame) -> tuple[Figure, NDArray[np.object_]]:
    """Return (figure, 2-D axes array) of annual changes in clean GDP.

    Input uses country_code, country, year, gdp_usd in settings.UNITS.
    Each country receives one visible panel on a shared percentage scale.
    Panel count and dates follow the data, independently of the configured index
    base. Require at least two years; hide unused panels.
    """
    if data.empty or data["year"].nunique() < 2:
        raise ValueError("Annual growth plots require at least two years")
    start, end = int(data["year"].min()), int(data["year"].max())
    frame = add_growth_measures(data, base_year=start)
    count = frame["country"].nunique()
    columns = min(2, count)
    rows = ceil(count / columns)
    fig, axes = plt.subplots(
        rows,
        columns,
        figsize=(11, max(3.5, rows * 2.75)),
        squeeze=False,
        sharex=True,
        sharey=True,
        layout="constrained",
    )
    for ax, (country, group) in zip(axes.flat, frame.groupby("country", sort=True), strict=False):
        ax.plot(
            group["year"],
            group["growth_pct"],
            color=COLORS.get(country),
            linewidth=2,
        )
        ax.axhline(0, color="#555555", linewidth=0.7)
        ax.set_title(country, loc="left", fontsize=11)
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
        # Show years on every panel, including the last panel of an odd grid.
        ax.tick_params(labelbottom=True)
    for ax in list(axes.flat)[count:]:
        ax.set_visible(False)
    fig.suptitle(f"Annual real GDP growth, {start + 1}–{end}", fontsize=16)
    fig.supylabel("Change from previous year (%)")
    fig.supxlabel(f"Year · Source: World Bank WDI, {settings.INDICATOR}")
    return fig, axes
