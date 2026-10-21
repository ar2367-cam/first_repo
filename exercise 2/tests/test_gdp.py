"""Check cleaning decisions, calculations, and the committed source snapshot."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from fed.analysis import add_growth_measures, summarize_gdp
from fed.data import COUNTRIES, clean_gdp, load_gdp
from fed.plot_utils import plot_annual_growth, plot_gdp


@pytest.fixture
def raw():
    return load_gdp()


def test_snapshot_is_complete_and_cleaning_is_idempotent(raw):
    original = raw.copy(deep=True)
    clean = clean_gdp(raw)
    assert len(clean) == 161
    assert set(clean.country_code) == set(COUNTRIES)
    assert clean.groupby("country_code").size().eq(23).all()
    pd.testing.assert_frame_equal(clean_gdp(clean), clean)
    pd.testing.assert_frame_equal(raw, original)


def test_identical_duplicates_removed_but_conflicts_rejected(raw):
    assert len(clean_gdp(pd.concat([raw, raw.iloc[:1]]))) == 161
    conflict = raw.iloc[:1].copy()
    conflict["gdp_usd"] *= 2
    with pytest.raises(ValueError, match="Conflicting"):
        clean_gdp(pd.concat([raw, conflict]))


@pytest.mark.parametrize("value", [None, "bad", 0, -1, float("inf")])
def test_invalid_gdp_rejected(raw, value):
    raw["gdp_usd"] = raw.gdp_usd.astype(object)
    raw.loc[0, "gdp_usd"] = value
    with pytest.raises(ValueError, match="finite"):
        clean_gdp(raw)


def test_missing_observation_rejected(raw):
    with pytest.raises(ValueError, match="Missing 1"):
        clean_gdp(raw.iloc[1:])


def test_numeric_coercion_and_scope(raw):
    raw["year"] = raw.year.astype(str)
    raw["gdp_usd"] = raw.gdp_usd.astype(str)
    raw["country_code"] = " " + raw.country_code.str.lower() + " "
    clean = clean_gdp(raw, 2005, 2010)
    assert len(clean) == 42
    assert clean.year.min() == 2005
    assert clean.year.max() == 2010


def test_growth_math_and_gaps():
    frame = pd.DataFrame(
        {
            "country_code": ["GBR"] * 3,
            "country": ["United Kingdom"] * 3,
            "year": [2000, 2001, 2003],
            "gdp_usd": [100.0, 110.0, 133.1],
        }
    )
    result = add_growth_measures(frame)
    assert result.gdp_index.tolist() == pytest.approx([100, 110, 133.1])
    assert result.growth_pct.iloc[1] == pytest.approx(10)
    assert pd.isna(result.growth_pct.iloc[2])
    summary = summarize_gdp(frame, 2000, 2003).iloc[0]
    assert summary.total_change_pct == pytest.approx(33.1)
    assert summary.cagr_pct == pytest.approx(10)


def test_plots_cover_all_countries(raw):
    data = clean_gdp(raw)
    fig, ax = plot_gdp(data)
    assert len(ax.lines) == 7
    plt.close(fig)
    fig, ax = plot_gdp(data, indexed=True)
    assert all(line.get_ydata()[0] == pytest.approx(100) for line in ax.lines)
    plt.close(fig)
    fig, axes = plot_annual_growth(data)
    assert sum(ax.get_visible() for ax in axes.flat) == 7
    plt.close(fig)
