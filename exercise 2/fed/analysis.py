"""Calculate growth and describe the selected data without fixed historical claims."""

import pandas as pd

from . import settings


def add_growth_measures(data: pd.DataFrame, base_year: int | None = None) -> pd.DataFrame:
    """Return a copy with gdp_index (base = 100) and annual growth_pct.

    Input must contain unique country_code/year pairs and positive gdp_usd.
    Every country needs an observation in base_year (default: settings.BASE_YEAR).
    Missing or invalid base values raise ValueError. The first year and changes
    across gaps have undefined (NaN) annual growth.
    """
    base_year = settings.BASE_YEAR if base_year is None else base_year
    if isinstance(base_year, bool) or not isinstance(base_year, int):
        raise ValueError("Base year must be an integer")
    df = data.sort_values(["country_code", "year"]).copy()
    if df.empty:
        raise ValueError("Select at least one GDP observation")
    if df.duplicated(["country_code", "year"]).any():
        raise ValueError("Country-year observations must be unique")
    base = df.loc[df["year"].eq(base_year)].set_index("country_code")["gdp_usd"]
    if not set(df["country_code"]).issubset(base.index):
        raise ValueError(
            f"Every country must have a base-year observation for {base_year}; "
            "choose BASE_YEAR within the selected period in fed/settings.py"
        )
    if base.isna().any() or (base <= 0).any() or (base == float("inf")).any():
        raise ValueError("Base-year GDP must be finite and positive")
    df["gdp_index"] = df["gdp_usd"] / df["country_code"].map(base) * 100
    grouped = df.groupby("country_code", sort=False)
    df["growth_pct"] = grouped["gdp_usd"].pct_change(fill_method=None) * 100
    df.loc[grouped["year"].diff().ne(1), "growth_pct"] = float("nan")
    return df


def summarize_gdp(
    data: pd.DataFrame,
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """Return endpoint GDP, cumulative change (%), and compound annual growth (%).

    Input is a clean table with country, year, and gdp_usd in settings.UNITS.
    Output is indexed by country and sorted by cumulative change. Years default
    to settings; missing endpoints or a nonpositive time span raise ValueError.
    """
    start, end, _ = settings.selection(start_year, end_year)
    if end <= start:
        raise ValueError("end_year must be after start_year for growth comparisons")
    levels = data.pivot(index="country", columns="year", values="gdp_usd")
    ends = levels.reindex(columns=[start, end])
    if ends.empty or ends.isna().any().any():
        raise ValueError("Missing endpoint GDP")
    result = ends.rename(columns={start: "start_gdp_usd", end: "end_gdp_usd"}).copy()
    ratio = result["end_gdp_usd"] / result["start_gdp_usd"]
    result["total_change_pct"] = (ratio - 1) * 100
    result["cagr_pct"] = (ratio ** (1 / (end - start)) - 1) * 100
    return result.sort_values("total_change_pct", ascending=False).rename_axis(columns=None)


def describe_gdp(
    data: pd.DataFrame,
    start_year: int | None = None,
    end_year: int | None = None,
) -> str:
    """Return Markdown findings calculated from the selected clean GDP table.

    Include each country's endpoint change and CAGR, observed contraction years,
    and rankings within the selected group. This is descriptive, not causal.
    Missing endpoints raise ValueError via summarize_gdp.
    """
    start, end, _ = settings.selection(start_year, end_year)
    summary = summarize_gdp(data, start, end)
    selected = data[data["year"].between(start, end)]
    measures = add_growth_measures(selected, base_year=start)
    lines = [f"# GDP development, {start}–{end}", ""]
    for country, row in summary.iterrows():
        negative = measures[measures["country"].eq(country) & measures["growth_pct"].lt(0)]
        years = ", ".join(str(int(y)) for y in negative["year"])
        detail = (
            f"Output contracted in {years}."
            if years
            else "No annual contractions were observed within this period."
        )
        lines.append(
            f"- **{country}:** real GDP changed by **{row.total_change_pct:.1f}%** "
            f"from {start} to {end} (CAGR **{row.cagr_pct:.2f}%**). {detail}"
        )
    lines.append("")
    for column, label in (
        ("total_change_pct", "Largest proportional change over the period"),
        ("start_gdp_usd", f"Largest total GDP in {start}"),
        ("end_gdp_usd", f"Largest total GDP in {end}"),
    ):
        leaders = summary.index[summary[column].eq(summary[column].max())]
        lines.append(f"{label} in this selected group: **{', '.join(leaders)}**.")
    lines.extend(
        [
            "",
            f"Source: World Bank WDI, {settings.INDICATOR}; {settings.UNITS}.",
            "Descriptive comparisons of total output, not causal estimates or living standards.",
        ]
    )
    return "\n".join(lines) + "\n"
