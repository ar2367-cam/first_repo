"""Verify portable paths, configurable selections, and an independent notebook run."""

import os
import shutil
import subprocess
import sys

import matplotlib.pyplot as plt
import nbformat
import pandas as pd
import pytest

from fed import settings
from fed.analysis import add_growth_measures, describe_gdp, summarize_gdp
from fed.data import clean_gdp, load_gdp, source_url
from fed.plot_utils import plot_annual_growth, plot_gdp


@pytest.mark.parametrize("location", ["project", "repository", "unrelated"])
def test_paths_are_independent_of_working_folder(monkeypatch, tmp_path, location):
    folders = {
        "project": settings.PROJECT_ROOT,
        "repository": settings.PROJECT_ROOT.parent,
        "unrelated": tmp_path,
    }
    monkeypatch.chdir(folders[location])
    assert len(load_gdp()) == 161
    assert len(load_gdp("data/raw/world_bank_gdp.json")) == 161
    assert len(load_gdp(settings.RAW_PATH)) == 161


def test_two_country_shorter_selection():
    countries = {"GBR": "United Kingdom", "JPN": "Japan"}
    raw = load_gdp(start_year=2005, end_year=2007, countries=countries)
    data = clean_gdp(raw, 2005, 2007, countries=countries)
    assert len(data) == 6
    fig, ax = plot_gdp(data, indexed=True, base_year=2005)
    assert "2005" in ax.get_title() and "2007" in ax.get_title()
    assert len(ax.lines) == 2
    assert all(line.get_ydata()[0] == pytest.approx(100) for line in ax.lines)
    plt.close(fig)
    fig, axes = plot_annual_growth(data)
    assert sum(ax.get_visible() for ax in axes.flat) == 2
    assert "2006–2007" in fig._suptitle.get_text()
    plt.close(fig)
    findings = describe_gdp(data, 2005, 2007)
    assert "2005–2007" in findings
    assert "China" not in findings and "2020" not in findings
    assert settings.output_path("summary", 2005, 2007, "csv").name == "summary_2005_2007.csv"


@pytest.mark.parametrize("count", [1, 3])
def test_small_multiple_layouts(count):
    countries = dict(list(settings.COUNTRIES.items())[:count])
    data = clean_gdp(load_gdp(), countries=countries)
    fig, axes = plot_annual_growth(data)
    assert axes.ndim == 2
    assert sum(ax.get_visible() for ax in axes.flat) == count
    plt.close(fig)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"start_year": 2023, "end_year": 2000}, "Years must satisfy"),
        ({"start_year": "2000"}, "integers"),
        ({"countries": {}}, "at least one"),
        ({"countries": {"uk": "UK"}}, "ISO3"),
        ({"countries": {"GBR": "Same", "USA": "Same"}}, "unique"),
    ],
)
def test_invalid_settings(kwargs, message):
    with pytest.raises(ValueError, match=message):
        load_gdp(**kwargs)


def test_missing_and_uncovered_data_explain_download(tmp_path):
    with pytest.raises(FileNotFoundError, match="refresh=True"):
        load_gdp(tmp_path / "not-downloaded.json")
    with pytest.raises(ValueError, match="does not cover.*selection"):
        load_gdp(start_year=1999)
    with pytest.raises(ValueError, match="refresh=True"):
        load_gdp(countries={"FRA": "France"})


def test_runtime_settings_and_base_validation(monkeypatch):
    monkeypatch.setattr(settings, "START_YEAR", 2005)
    monkeypatch.setattr(settings, "END_YEAR", 2007)
    monkeypatch.setattr(settings, "COUNTRIES", {"GBR": "United Kingdom"})
    assert len(clean_gdp(load_gdp())) == 3
    assert "date=2005%3A2007" in source_url()
    with pytest.raises(ValueError, match="base-year"):
        add_growth_measures(clean_gdp(load_gdp()), base_year=2000)


@pytest.mark.parametrize("year", ["bad", None, 2001.5, float("inf")])
def test_bad_years_are_not_silently_dropped(year):
    raw = load_gdp()
    raw.loc[0, "year"] = year
    with pytest.raises(ValueError, match="Years must be finite integers"):
        clean_gdp(raw)


def test_negative_changes_are_described_accurately():
    data = pd.DataFrame(
        {
            "country_code": ["GBR", "GBR"],
            "country": ["United Kingdom"] * 2,
            "year": [2000, 2001],
            "gdp_usd": [100.0, 90.0],
        }
    )
    findings = describe_gdp(data, 2000, 2001)
    assert "changed by **-10.0%**" in findings
    assert "contracted in 2001" in findings
    assert "rose" not in findings
    with pytest.raises(ValueError, match="after"):
        summarize_gdp(data, 2000, 2000)


def test_relocated_notebook_runs_with_new_selection(tmp_path):
    """A fresh kernel must import the relocated copy, not the installed original."""
    copied = tmp_path / "relocated exercise with spaces"
    copied.mkdir()
    for folder in ("fed", "data/raw", "scripts"):
        shutil.copytree(
            settings.PROJECT_ROOT / folder,
            copied / folder,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    shutil.copy2(settings.NOTEBOOK_PATH, copied / "gdp_analysis.ipynb")
    config = copied / "fed/settings.py"
    text = config.read_text(encoding="utf-8")
    text = text.replace("START_YEAR = 2000", "START_YEAR = 2005")
    text = text.replace("END_YEAR = 2022", "END_YEAR = 2007")
    text += '\nCOUNTRIES = {"GBR": "United Kingdom", "JPN": "Japan"}\n'
    config.write_text(text, encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(copied), "MPLBACKEND": "Agg"}
    result = subprocess.run(
        [sys.executable, str(copied / "scripts/run_notebook.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    nb = nbformat.read(copied / "gdp_analysis.ipynb", as_version=4)
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert all(c.execution_count is not None for c in code_cells)
    assert not any(o.output_type == "error" for c in code_cells for o in c.outputs)
    data = pd.read_csv(copied / "data/processed/gdp_2005_2007.csv")
    assert len(data) == 6
    assert len(list((copied / "outputs").glob("*.png"))) == 3
    findings = (copied / "outputs/findings_2005_2007.md").read_text(encoding="utf-8")
    assert "China" not in findings and "2005–2007" in findings
    assert len(pd.read_csv(copied / "outputs/summary_2005_2007.csv")) == 2
