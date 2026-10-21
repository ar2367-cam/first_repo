"""Edit the analysis here; paths start at this project, not your working folder."""

from collections.abc import Mapping
from os import PathLike
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "world_bank_gdp.json"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
NOTEBOOK_PATH = PROJECT_ROOT / "gdp_analysis.ipynb"
COUNTRIES = {
    "GBR": "United Kingdom",
    "USA": "United States",
    "BRA": "Brazil",
    "JPN": "Japan",
    "CHN": "China",
    "DEU": "Germany",
    "CHE": "Switzerland",
}
START_YEAR = 2000
END_YEAR = 2022
BASE_YEAR = START_YEAR
INDICATOR = "NY.GDP.MKTP.KD"
UNITS = "constant 2015 US$"
PathInput = str | PathLike[str]


def project_path(path: PathInput) -> Path:
    """Return an absolute path; relative paths start inside this project."""
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def selection(
    start_year: int | None = None,
    end_year: int | None = None,
    countries: Mapping[str, str] | None = None,
) -> tuple[int, int, dict[str, str]]:
    """Validate settings and return (start, end, ISO3-code/name dictionary)."""
    start = START_YEAR if start_year is None else start_year
    end = END_YEAR if end_year is None else end_year
    if any(isinstance(y, bool) or not isinstance(y, int) for y in (start, end)):
        raise ValueError("Start and end years must be integers")
    if not 1 <= start <= end <= 9999:
        raise ValueError("Years must satisfy 1 <= start_year <= end_year <= 9999")
    chosen = dict(COUNTRIES if countries is None else countries)
    if not chosen:
        raise ValueError("Select at least one country")
    if any(
        not isinstance(code, str)
        or len(code) != 3
        or not code.isascii()
        or not code.isalpha()
        or code != code.upper()
        or not isinstance(name, str)
        or not name.strip()
        for code, name in chosen.items()
    ):
        raise ValueError("Countries must map uppercase ISO3 codes to nonempty names")
    if len(set(chosen.values())) != len(chosen):
        raise ValueError("Country names must be unique")
    return start, end, chosen


def output_path(stem: str, start_year: int, end_year: int, suffix: str) -> Path:
    """Return a dated output filename in OUTPUT_DIR (without creating it)."""
    return OUTPUT_DIR / f"{stem}_{start_year}_{end_year}.{suffix}"
