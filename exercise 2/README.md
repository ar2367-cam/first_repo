# GDP analysis, 2000–2022

This exercise loads, cleans, compares, and plots annual GDP for the United Kingdom,
United States, Brazil, Japan, China, Germany, and Switzerland. Its notebook calls
small reusable functions rather than keeping all the work in one long notebook.

## Install and open the notebook

The verified setup is **Python 3.12 on Windows** (tested with 3.12.14).
First open a terminal in this folder. If you are in the parent repository:

    cd "exercise 2"

Create a private environment, install the exact dependency versions, then install
this project:

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.lock
    .venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .

The final command uses the build tools already pinned in requirements.lock.
It makes the project's functions importable from other working folders.

Register the environment for interactive notebook use and open Jupyter:

    .venv\Scripts\python -m ipykernel install --user --name gdp-analysis --display-name "Python (gdp-analysis)"
    .venv\Scripts\python -m jupyterlab gdp_analysis.ipynb

Choose **Python (gdp-analysis)** and run all cells from the beginning.

On macOS/Linux use .venv/bin/python in place of .venv\Scripts\python.
The dependency list includes operating-system conditions; execution on those
systems has not been verified here. The broad package metadata supports Python
3.10+, but the exact dependency list is specifically for Python 3.12.

### Conda option

From this folder:

    conda env create -f environment.yml
    conda activate gdp-analysis
    python -m pip install --no-deps --no-build-isolation -e .
    python -m ipykernel install --user --name gdp-analysis --display-name "Python (gdp-analysis)"
    python -m jupyterlab gdp_analysis.ipynb

Conda supplies Python 3.12 and uses the **same requirements.lock** for the Python
packages, so the two setup routes do not maintain conflicting package lists.
The pip route has been tested in a fresh environment; the Conda commands have not
been executed on this computer because Conda is not installed.

## Run everything without opening Jupyter

From this folder:

    .venv\Scripts\python scripts/run_notebook.py

This executes the notebook in a fresh kernel, saves its visible results, and
regenerates the cleaned CSV, three chart images, summary table, and findings.
It does not need a separately registered notebook kernel.

After installation, you can also run it from another folder by specifying its
full path, using PowerShell's & when the path contains spaces:

    & "C:\path to project\exercise 2\.venv\Scripts\python.exe" "C:\path to project\exercise 2\scripts\run_notebook.py"

Data loading and output locations are anchored to the installed project rather
than the folder you happen to be in.

## Change the analysis

Edit **fed/settings.py**, then restart the notebook kernel and rerun all cells.

- COUNTRIES maps three-letter country codes to the names displayed in results.
- START_YEAR and END_YEAR select the inclusive period.
- BASE_YEAR defines the year used as 100 in the indexed chart. It follows
  START_YEAR by default and must remain within the selected period.
- Project locations, the World Bank indicator, and units are defined there too.

Use at least two years for the notebook's growth comparisons. For example, choose
2005–2007 and keep only GBR and JPN to compare the UK and Japan. Expected row
counts, filenames, chart panels, labels, and calculated findings follow the
selection. Output filenames include the selected years; rerunning the same period
replaces those outputs. Different country selections for the same years therefore
replace that period's results.

Functions also accept explicit selections without editing settings:

    from fed.data import load_gdp, clean_gdp
    countries = {"GBR": "United Kingdom", "JPN": "Japan"}
    raw = load_gdp(start_year=2005, end_year=2007, countries=countries)
    data = clean_gdp(raw, 2005, 2007, countries=countries)

Relative data paths supplied to load_gdp are relative to this project. Absolute
paths are accepted as well. Existing function names and table columns are retained.
Type hints label expected inputs and outputs; runtime checks still validate data.

## Source and cleaning policy

Source: [World Bank World Development Indicators, NY.GDP.MKTP.KD](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD),
annual GDP in **constant 2015 US dollars**. The original snapshot contains 161
observations (seven countries × 23 years). Its retrieval metadata records the
exact query, timestamp, source update date, units, and [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/).

The original data works offline after installation. Selecting countries or dates
outside its coverage raises an explanation; it never downloads silently.
To explicitly replace a snapshot, with internet access:

    from fed.data import load_gdp
    raw = load_gdp(refresh=True)

That uses the selection in settings. Explicit path, countries, and year arguments
can be supplied too; use the same arguments when subsequently reading that file.
Refreshing replaces both the selected snapshot and its metadata. Historical
World Bank estimates can change.

Cleaning normalizes codes and names, converts years and GDP to numbers, filters
the selection, removes identical duplicates, and sorts observations. Conflicting
records, invalid numbers/years, and missing country-year pairs raise errors.
Nothing is interpolated or replaced with zero; inputs are not modified.

GDP here is total output, not GDP per person, purchasing-power-parity GDP, or
living standards. See the [World Bank methodology](https://datahelpdesk.worldbank.org/knowledgebase/articles/114943-how-do-you-derive-constant-price-series-in-usd).
Findings describe the selected observations and do not establish their causes.

## What the folders contain

    fed/                 Reusable loading, cleaning, calculations, plotting, settings
    data/raw/            Original World Bank response and retrieval receipt
    data/processed/      Cleaned table: gdp_START_END.csv
    outputs/             Dated chart images, summary tables, and written findings
    scripts/             One helper to execute the notebook
    tests/               Data, calculation, selection, and portability checks
    gdp_analysis.ipynb   The analysis workbook, maintained directly
    requirements.lock   Exact software versions for the verified Python 3.12 setup
    environment.yml     Conda setup using that same dependency list
    pyproject.toml      Project metadata and code-checking settings

The parent repository's original starter files are separate from this exercise.

## Check the work

From this folder:

    .venv\Scripts\python -m pip check
    .venv\Scripts\python -m pytest
    .venv\Scripts\python -m ruff check fed scripts tests
    .venv\Scripts\python -m ruff format --check fed scripts tests

Tests include missing/invalid data, duplicate records, growth arithmetic, loading
from different working folders, and executing a relocated notebook with a smaller
selection. Notebook execution uses temporary files and a local Python kernel.

### Automatic checks before a commit

This exercise lives inside the parent Git repository. From this folder, install
its hook:

    $env:PRE_COMMIT_HOME = Join-Path (Get-Location) ".pre-commit-cache"
    .venv\Scripts\python -m pre_commit install --config .pre-commit-config.yaml

Pre-commit records the configuration's path within the parent Git repository.
The hook checks only Python files inside exercise 2. It uses an isolated copy of the same pinned
Ruff version; its first run needs internet access. Formatting checks report changes
needed; apply formatting with the Ruff command without --check, then review.

To check specific files manually, including files not yet added to Git:

    .venv\Scripts\python -m pre_commit run --config .pre-commit-config.yaml --files fed/data.py

To check all files already tracked by Git, replace --files ... with --all-files.
The environment, installation caches, and verification artifacts are ignored.

## Updating dependencies later

For everyday use, install requirements.lock with pip; no extra package manager is
needed. Keep its exact versions until deliberately updating and retesting.

For maintenance, the pinned list was resolved from pyproject.toml using the
available uv tool, with current versions as constraints and universal platform
markers. To update intentionally:

    uv pip compile pyproject.toml --all-extras --python-version 3.12 --universal --output-file requirements.lock

Rerun installation in a clean Python 3.12 environment, all tests, code checks,
and the notebook before accepting an updated list. If Ruff changes, update its
pinned version in .pre-commit-config.yaml as well.
