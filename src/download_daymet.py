
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import earthaccess
import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
DATES_FILE = ROOT / "data" / "processed" / "daymet_required_dates.csv"
OUTPUT_DIR = ROOT / "data" / "processed" / "daymet_rasters"
SUMMARY_FILE = OUTPUT_DIR / "extraction_summary.csv"

COLLECTION = "C2532426483-ORNL_CLOUD"
DOI = "10.3334/ORNLDAAC/2129"

X_SLICE = slice(6432, 6456)
Y_SLICE = slice(5092, 5119)
EXPECTED_SHAPE = (27, 24)

GRID_KEYS = ("x", "y", "lat", "lon")
NPZ_KEYS = set(GRID_KEYS) | {"precipitation", "metadata_json"}


def granule_url(year: int) -> str:
    return (
        "dap4://opendap.earthdata.nasa.gov/"
        f"collections/{COLLECTION}/granules/"
        f"Daymet_Daily_V4R1.daymet_v4_daily_na_prcp_{year}.nc"
    )


def load_dates(limit: int | None) -> list[pd.Timestamp]:
    if not DATES_FILE.is_file():
        raise FileNotFoundError(DATES_FILE)

    table = pd.read_csv(DATES_FILE)

    if "date" not in table.columns:
        raise ValueError("Date file must contain a 'date' column")

    dates = pd.to_datetime(
        table["date"], errors="raise"
    ).dt.normalize()

    if dates.isna().any():
        raise ValueError("Missing dates in date file")

    result = sorted(set(dates.tolist()))

    if limit is not None:
        result = result[:limit]

    return result


def get_grid(ds: xr.Dataset) -> dict:
    grid = {
        "x": np.asarray(
            ds["x"].isel(x=X_SLICE).values
        ).copy(),
        "y": np.asarray(
            ds["y"].isel(y=Y_SLICE).values
        ).copy(),
        "lat": np.asarray(
            ds["lat"].isel(
                y=Y_SLICE, x=X_SLICE
            ).values
        ).copy(),
        "lon": np.asarray(
            ds["lon"].isel(
                y=Y_SLICE, x=X_SLICE
            ).values
        ).copy(),
    }

    if grid["x"].shape != (24,):
        raise ValueError("Unexpected Daymet x shape")

    if grid["y"].shape != (27,):
        raise ValueError("Unexpected Daymet y shape")

    for key in ("lat", "lon"):
        if grid[key].shape != EXPECTED_SHAPE:
            raise ValueError(f"Unexpected {key} shape")

        if not np.isfinite(grid[key]).all():
            raise ValueError(f"Nonfinite {key} coordinates")

    return grid


def validate_grid(current: dict, reference: dict) -> None:
    for key in ("x", "y"):
        if not np.array_equal(
            current[key], reference[key]
        ):
            raise ValueError(
                f"Projected grid mismatch: {key}"
            )

    for key in ("lat", "lon"):
        if not np.allclose(
            current[key],
            reference[key],
            rtol=0,
            atol=1e-5,
            equal_nan=False,
        ):
            raise ValueError(
                f"Geographic grid mismatch: {key}"
            )


def validate_precipitation(values: np.ndarray) -> None:
    if values.shape != EXPECTED_SHAPE:
        raise ValueError(
            f"Unexpected precipitation shape: {values.shape}"
        )

    if np.isinf(values).any():
        raise ValueError("Infinite precipitation values")

    valid = np.isfinite(values)

    if not valid.any():
        raise ValueError("No valid precipitation cells")

    if (values[valid] < 0).any():
        raise ValueError("Negative precipitation values")


def verify_existing_file(
    path: Path,
    date: pd.Timestamp,
    expected_grid: dict | None = None,
) -> dict:
    with np.load(path, allow_pickle=False) as stored:
        if not NPZ_KEYS.issubset(stored.files):
            raise ValueError(
                f"Missing NPZ fields in {path.name}"
            )

        values = np.asarray(
            stored["precipitation"]
        )

        validate_precipitation(values)

        grid = {
            key: np.asarray(stored[key])
            for key in GRID_KEYS
        }

        if grid["x"].shape != (24,):
            raise ValueError("Invalid saved x shape")

        if grid["y"].shape != (27,):
            raise ValueError("Invalid saved y shape")

        for key in ("lat", "lon"):
            if grid[key].shape != EXPECTED_SHAPE:
                raise ValueError(
                    f"Invalid saved {key} shape"
                )

        if expected_grid is not None:
            validate_grid(grid, expected_grid)

        metadata = json.loads(
            str(stored["metadata_json"].item())
        )

        if metadata.get("date") != date.strftime(
            "%Y-%m-%d"
        ):
            raise ValueError(
                f"Saved date mismatch: {path.name}"
            )

        return grid


def extract_precipitation(
    ds: xr.Dataset,
    date: pd.Timestamp,
) -> np.ndarray:
    day_of_year = int(date.day_of_year)
    index = day_of_year - 1

    if index >= ds.sizes["time"]:
        raise ValueError(
            f"Date index out of range: {date.date()}"
        )

    actual_day = int(
        ds["yearday"].isel(time=index).values
    )

    if actual_day != day_of_year:
        raise ValueError(
            f"Day-of-year mismatch: {date.date()}"
        )

    raw = np.asarray(
        ds["prcp"].isel(
            time=index,
            y=Y_SLICE,
            x=X_SLICE,
        ).values,
        dtype=np.float32,
    )

    fill_value = ds["prcp"].attrs.get(
        "_FillValue", -9999
    )

    values = raw.copy()

    values[values == -9999] = np.nan

    if fill_value is not None:
        values[values == fill_value] = np.nan

    missing_value = ds["prcp"].attrs.get(
        "missing_value"
    )

    if missing_value is not None:
        values[values == missing_value] = np.nan

    validate_precipitation(values)

    return values


def save_raster(
    path: Path,
    date: pd.Timestamp,
    values: np.ndarray,
    grid: dict,
    url: str,
) -> None:
    valid = np.isfinite(values)

    metadata = {
        "date": date.strftime("%Y-%m-%d"),
        "source_dataset": "Daymet V4 R1 daily precipitation",
        "collection": COLLECTION,
        "doi": DOI,
        "source_url": url,
        "variable": "prcp",
        "units": "mm/day",
        "spatial_resolution_m": 1000,
        "time_convention": "24-hour day based on local time",
        "missing_cells": int((~valid).sum()),
        "valid_cells": int(valid.sum()),
        "min_precipitation": float(
            np.nanmin(values)
        ),
        "max_precipitation": float(
            np.nanmax(values)
        ),
        "mean_precipitation": float(
            np.nanmean(values)
        ),
        "retrieved_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    temporary = path.with_suffix(".tmp.npz")

    np.savez_compressed(
        temporary,
        precipitation=values,
        x=grid["x"],
        y=grid["y"],
        lat=grid["lat"],
        lon=grid["lon"],
        metadata_json=json.dumps(metadata),
    )

    try:
        verify_existing_file(
            temporary, date, grid
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract DC Daymet precipitation rasters"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N required dates",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    dates = load_dates(args.limit)
    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    print("\nDAYMET EXTRACTION", flush=True)
    print("Requested dates:", len(dates), flush=True)

    auth = earthaccess.login(
        strategy="interactive"
    )

    if not auth.authenticated:
        raise RuntimeError(
            "NASA Earthdata authentication failed"
        )

    session = earthaccess.get_requests_https_session()

    new_count = 0
    existing_count = 0
    reference_grid = None
    records = []

    years = sorted({date.year for date in dates})

    for year in years:
        year_dates = [
            date for date in dates
            if date.year == year
        ]

        url = granule_url(year)

        print(
            f"\nOpening Daymet year {year}...",
            flush=True,
        )

        ds = xr.open_dataset(
            url,
            engine="pydap",
            backend_kwargs={"session": session},
            decode_cf=False,
        )

        try:
            grid = get_grid(ds)

            if reference_grid is None:
                reference_grid = grid
            else:
                validate_grid(
                    grid, reference_grid
                )

            for date in year_dates:
                name = (
                    "daymet_prcp_"
                    + date.strftime("%Y%m%d")
                    + ".npz"
                )

                path = OUTPUT_DIR / name

                if path.exists():
                    verify_existing_file(
                        path, date, grid
                    )

                    existing_count += 1
                    status = "verified_existing"

                    print(
                        f"Verified existing: {date.date()}",
                        flush=True,
                    )

                else:
                    values = extract_precipitation(
                        ds, date
                    )

                    save_raster(
                        path, date, values, grid, url
                    )

                    new_count += 1
                    status = "newly_extracted"

                    print(
                        f"Extracted: {date.date()}",
                        flush=True,
                    )

                records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "year": year,
                    "file": name,
                    "status": status,
                })

        finally:
            ds.close()

    summary = pd.DataFrame(records)
    summary.to_csv(
        SUMMARY_FILE, index=False
    )

    print("\nEXTRACTION SUMMARY")
    print("-" * 45)
    print("Requested dates:", len(dates))
    print("Newly extracted:", new_count)
    print("Verified existing:", existing_count)
    print(
        "Total processed:",
        new_count + existing_count,
    )
    print("Summary file:", SUMMARY_FILE)


if __name__ == "__main__":
    main()
