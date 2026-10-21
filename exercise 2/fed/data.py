"""Load a World Bank snapshot and prepare a complete country-year GDP table."""

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from . import settings
from .settings import COUNTRIES as COUNTRIES
from .settings import INDICATOR as INDICATOR
from .settings import PathInput


def source_url(
    start_year: int | None = None,
    end_year: int | None = None,
    *,
    countries: Mapping[str, str] | None = None,
) -> str:
    """Return the configured World Bank annual GDP query; reject invalid settings."""
    start, end, chosen = settings.selection(start_year, end_year, countries)
    query = urlencode({"date": f"{start}:{end}", "format": "json", "per_page": 10000})
    return (
        f"https://api.worldbank.org/v2/country/{';'.join(chosen)}"
        f"/indicator/{settings.INDICATOR}?{query}"
    )


def load_gdp(
    path: PathInput | None = None,
    *,
    refresh: bool = False,
    start_year: int | None = None,
    end_year: int | None = None,
    countries: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Return selected raw rows with country_code, country, year, and gdp_usd.

    Years and GDP retain their source representation until clean_gdp is called.
    Relative paths start at the project, not the working folder. Normally this
    reads the saved snapshot offline; refresh=True explicitly downloads and
    replaces it, along with retrieval metadata. GDP uses settings.UNITS.

    Raise FileNotFoundError with download instructions if the snapshot is absent,
    or ValueError if the response is invalid or does not cover the selection.
    Network failures propagate without replacing the saved snapshot.
    """
    start, end, chosen = settings.selection(start_year, end_year, countries)
    target = settings.project_path(settings.RAW_PATH if path is None else path)
    if refresh:
        url = source_url(start, end, countries=chosen)
        with urlopen(url, timeout=60) as response:
            payload = json.load(response)
        _validate_payload(payload)
        clean_gdp(_records_frame(payload[1]), start, end, countries=chosen)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        provenance = {
            "url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "indicator": settings.INDICATOR,
            "units": settings.UNITS,
            "frequency": "annual",
            "source_last_updated": payload[0].get("lastupdated"),
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
        }
        target.with_suffix(".metadata.json").write_text(
            json.dumps(provenance, indent=2), encoding="utf-8"
        )
    if not target.is_file():
        raise FileNotFoundError(
            f"GDP snapshot not found: {target}. With internet access, call "
            "load_gdp(refresh=True, ...) using the same path and selection."
        )
    payload = json.loads(target.read_text(encoding="utf-8"))
    _validate_payload(payload)
    frame = _records_frame(payload[1])
    try:
        clean_gdp(frame, start, end, countries=chosen)
    except ValueError as error:
        if str(error).startswith("Missing "):
            raise ValueError(
                f"{error}. The saved snapshot does not cover this selection. "
                "Call load_gdp(refresh=True, ...) explicitly with the same "
                "path, countries, and years to download it."
            ) from error
        raise
    years = pd.to_numeric(frame["year"], errors="coerce")
    return frame[frame["country_code"].isin(chosen) & years.between(start, end)].reset_index(
        drop=True
    )


def _validate_payload(payload: Any) -> None:
    """Reject empty, incomplete, or wrong-indicator API responses."""
    if (
        not isinstance(payload, list)
        or len(payload) != 2
        or not isinstance(payload[0], dict)
        or not isinstance(payload[1], list)
    ):
        raise ValueError("Unexpected World Bank response; expected metadata and records")
    metadata, records = payload
    if int(metadata.get("pages", 0)) != 1 or int(metadata.get("total", -1)) != len(records):
        raise ValueError("Incomplete World Bank response")
    if not records or any(r.get("indicator", {}).get("id") != settings.INDICATOR for r in records):
        raise ValueError("Unexpected or empty GDP indicator")


def _records_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Translate API records into the four raw GDP columns."""
    return pd.DataFrame(
        [
            {
                "country_code": r.get("countryiso3code"),
                "country": r.get("country", {}).get("value"),
                "year": r.get("date"),
                "gdp_usd": r.get("value"),
            }
            for r in records
        ]
    )


def clean_gdp(
    raw: pd.DataFrame,
    start_year: int | None = None,
    end_year: int | None = None,
    *,
    countries: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Return a sorted, complete GDP panel without modifying raw.

    Input requires country_code, year, and gdp_usd. Output adds normalized country
    names and contains integer years and numeric GDP in settings.UNITS, one row
    per selected country-year. Extra countries/years are filtered; identical
    duplicates are removed. Conflicts, invalid values/years, and missing pairs
    raise ValueError. No interpolation or replacement with zero is performed.
    """
    start, end, chosen = settings.selection(start_year, end_year, countries)
    required = {"country_code", "year", "gdp_usd"}
    if not required.issubset(raw.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(raw.columns))}")
    df = raw[list(sorted(required))].copy()
    df["country_code"] = df["country_code"].astype("string").str.strip().str.upper()
    df = df[df["country_code"].isin(chosen)].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    if (df["year"].isna() | (df["year"] % 1 != 0)).any():
        raise ValueError("Years must be finite integers")
    df = df[df["year"].between(start, end)].copy()
    df["year"] = df["year"].astype(int)
    df["gdp_usd"] = pd.to_numeric(df["gdp_usd"], errors="coerce")
    df = df.drop_duplicates()
    if df.duplicated(["country_code", "year"]).any():
        raise ValueError("Conflicting GDP values for the same country and year")
    if (df["gdp_usd"].isna() | (df["gdp_usd"] <= 0) | (df["gdp_usd"] == float("inf"))).any():
        raise ValueError("GDP must be finite, positive, and non-missing")
    expected = pd.MultiIndex.from_product([chosen, range(start, end + 1)])
    actual = pd.MultiIndex.from_frame(df[["country_code", "year"]])
    missing = expected.difference(actual)
    if len(missing):
        raise ValueError(f"Missing {len(missing)} country-year observations: {list(missing[:5])}")
    df["country"] = df["country_code"].map(chosen)
    return (
        df[["country_code", "country", "year", "gdp_usd"]]
        .sort_values(["country", "year"])
        .reset_index(drop=True)
    )
