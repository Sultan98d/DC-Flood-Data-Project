
from pathlib import Path
from datetime import timedelta, datetime, timezone
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import requests


# ============================================================
# PROJECT PATHS AND SETTINGS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

EVENTS_FILE = (
    ROOT / "data" / "processed" / "validated_events.csv"
)

COVERAGE_FILE = (
    ROOT / "data" / "processed" / "usgs_all_event_coverage.csv"
)

OUTPUT_DIR = (
    ROOT / "data" / "processed" / "usgs_water_levels"
)

URL = "https://waterservices.usgs.gov/nwis/iv/"

PARAMETER = "00065"
CONTEXT_HOURS = 12
MAX_RETRIES = 3

REQUIRED_COLUMNS = {
    "timestamp_utc",
    "gage_height_ft",
    "qualifiers",
    "series_index",
    "within_event",
}


# ============================================================
# DOWNLOAD AND PARSE USGS DATA
# ============================================================

def fetch_series(site, start, end):

    window_start = start - timedelta(
        hours=CONTEXT_HOURS
    )

    window_end = end + timedelta(
        hours=CONTEXT_HOURS
    )

    params = {
        "format": "json",
        "sites": site,
        "parameterCd": PARAMETER,
        "startDT": window_start.strftime("%Y-%m-%d"),
        "endDT": window_end.strftime("%Y-%m-%d"),
        "siteStatus": "all",
    }

    response = None

    for attempt in range(MAX_RETRIES):

        try:
            response = requests.get(
                URL,
                params=params,
                timeout=90,
            )

            response.raise_for_status()
            break

        except requests.RequestException:

            if attempt == MAX_RETRIES - 1:
                raise

            time.sleep(2 * (attempt + 1))

    payload = response.json()

    records = []
    series_metadata = []

    for series_index, series in enumerate(
        payload.get("value", {}).get("timeSeries", [])
    ):

        variable = series.get("variable", {})

        codes = [
            str(code.get("value", ""))
            for code in variable.get("variableCode", [])
        ]

        if PARAMETER not in codes:
            continue

        unit = variable.get(
            "unit", {}
        ).get("unitCode", "")

        if unit.lower() not in ("ft", "feet"):
            raise ValueError(
                f"Unexpected unit for {site}: {unit}"
            )

        source = series.get("sourceInfo", {})

        series_metadata.append({
            "series_index": series_index,
            "site_name": source.get("siteName"),
            "variable_codes": codes,
            "unit": unit,
            "variable_name": variable.get("variableName"),
        })

        for block in series.get("values", []):

            for item in block.get("value", []):

                stamp = pd.to_datetime(
                    item.get("dateTime"),
                    utc=True,
                    errors="coerce",
                )

                value = pd.to_numeric(
                    item.get("value"),
                    errors="coerce",
                )

                if pd.isna(stamp) or pd.isna(value):
                    continue

                if not np.isfinite(value):
                    continue

                if not (
                    window_start <= stamp <= window_end
                ):
                    continue

                records.append({
                    "timestamp_utc": stamp.isoformat(),
                    "gage_height_ft": float(value),
                    "qualifiers": json.dumps(
                        item.get("qualifiers", []),
                        ensure_ascii=False,
                    ),
                    "series_index": series_index,
                    "within_event": bool(
                        start <= stamp <= end
                    ),
                })

    frame = pd.DataFrame(
        records,
        columns=[
            "timestamp_utc",
            "gage_height_ft",
            "qualifiers",
            "series_index",
            "within_event",
        ],
    )

    if not frame.empty:

        frame = (
            frame.sort_values(
                ["timestamp_utc", "series_index"]
            )
            .drop_duplicates(
                subset=[
                    "timestamp_utc",
                    "series_index",
                    "gage_height_ft",
                    "qualifiers",
                ]
            )
            .reset_index(drop=True)
        )

    metadata = {
        "site_no": site,
        "parameter_code": PARAMETER,
        "parameter_name": "Gage height",
        "unit": "ft",
        "event_start_utc": start.isoformat(),
        "event_end_utc": end.isoformat(),
        "window_start_utc": window_start.isoformat(),
        "window_end_utc": window_end.isoformat(),
        "source_url": response.url,
        "retrieved_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "series_metadata": series_metadata,
        "quality_note": (
            "USGS qualifiers are retained. "
            "Measurements are not independently "
            "quality-approved."
        ),
    }

    return frame, metadata


# ============================================================
# VALIDATE EXISTING FILES FOR RESUME
# ============================================================

def existing_files_valid(
    csv_path,
    json_path,
    event_id,
    site,
    start,
    end,
):

    if not csv_path.exists() or not json_path.exists():
        return False

    try:
        existing = pd.read_csv(csv_path)

        with open(
            json_path,
            "r",
            encoding="utf-8",
        ) as handle:
            metadata = json.load(handle)

        if existing.empty:
            return False

        if not REQUIRED_COLUMNS.issubset(
            existing.columns
        ):
            return False

        if metadata.get("event_id") != event_id:
            return False

        if metadata.get("site_no") != site:
            return False

        if metadata.get("parameter_code") != PARAMETER:
            return False

        if metadata.get("unit") != "ft":
            return False

        if metadata.get("event_start_utc") != start.isoformat():
            return False

        if metadata.get("event_end_utc") != end.isoformat():
            return False

        if metadata.get("reading_count") != len(existing):
            return False

        timestamps = pd.to_datetime(
            existing["timestamp_utc"],
            utc=True,
            errors="coerce",
        )

        values = pd.to_numeric(
            existing["gage_height_ft"],
            errors="coerce",
        )

        if timestamps.isna().any():
            return False

        if values.isna().any():
            return False

        if not np.isfinite(values.to_numpy()).all():
            return False

        window_start = start - timedelta(
            hours=CONTEXT_HOURS
        )

        window_end = end + timedelta(
            hours=CONTEXT_HOURS
        )

        if not timestamps.between(
            window_start,
            window_end,
            inclusive="both",
        ).all():
            return False

        event_flags = (
            timestamps.between(
                start,
                end,
                inclusive="both",
            )
        )

        if (
            metadata.get("event_reading_count")
            != int(event_flags.sum())
        ):
            return False

        return True

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ):
        return False


# ============================================================
# MAIN DOWNLOAD WORKFLOW
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download USGS gage-height measurements "
            "for DC flood events."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help=(
            "Maximum number of events. "
            "Use 0 for all available events."
        ),
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Skip previously downloaded files "
            "that pass validation."
        ),
    )

    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be >= 0")

    events = pd.read_csv(
        EVENTS_FILE,
        dtype={"event_id": str},
    )

    coverage = pd.read_csv(
        COVERAGE_FILE,
        dtype={
            "event_id": str,
            "site_no": str,
        },
    )

    events["start_utc"] = pd.to_datetime(
        events["start_utc"],
        utc=True,
    )

    events["end_utc"] = pd.to_datetime(
        events["end_utc"],
        utc=True,
    )

    if events["event_id"].duplicated().any():
        raise ValueError("Duplicate event IDs")

    if coverage.duplicated(
        ["event_id", "site_no"]
    ).any():
        raise ValueError(
            "Duplicate event-station coverage pairs"
        )

    available = coverage.loc[
        (coverage["valid_context_readings"] > 0)
        & (coverage["status"] == "valid_data_found")
    ].copy()

    event_ids = set(available["event_id"])

    selected = (
        events[
            events["event_id"].isin(event_ids)
        ]
        .sort_values("start_utc")
    )

    if args.limit:
        selected = selected.head(args.limit)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_saved = 0
    total_skipped = 0
    total_failed = 0
    total_readings = 0
    failures = []

    print("\nUSGS WATER-LEVEL DOWNLOAD")
    print("-" * 55)
    print("Selected events:", len(selected))
    print("Parameter: 00065 (Gage height)")
    print("Units: feet")
    print("Context: +/- 12 hours")
    print("Resume enabled:", args.resume)
    print()

    for event_number, (_, event) in enumerate(
        selected.iterrows(),
        start=1,
    ):

        event_id = event["event_id"]
        start = event["start_utc"]
        end = event["end_utc"]

        matches = available[
            available["event_id"] == event_id
        ]

        print(
            f"\n[{event_number}/{len(selected)}] "
            f"{event_id}: {len(matches)} stations",
            flush=True,
        )

        for _, match in matches.iterrows():

            site = match["site_no"]

            stem = f"{event_id}_{site}"

            csv_path = OUTPUT_DIR / f"{stem}.csv"
            json_path = OUTPUT_DIR / f"{stem}.json"

            if args.resume and existing_files_valid(
                csv_path,
                json_path,
                event_id,
                site,
                start,
                end,
            ):

                total_skipped += 1

                print(
                    f"  {site}: already downloaded, skipping",
                    flush=True,
                )

                continue

            try:

                frame, metadata = fetch_series(
                    site,
                    start,
                    end,
                )

                if frame.empty:
                    raise ValueError(
                        "No valid measurements returned"
                    )

                metadata["event_id"] = event_id
                metadata["reading_count"] = len(frame)

                metadata["event_reading_count"] = int(
                    frame["within_event"].sum()
                )

                csv_tmp = csv_path.with_suffix(
                    ".csv.tmp"
                )

                json_tmp = json_path.with_suffix(
                    ".json.tmp"
                )

                frame.to_csv(
                    csv_tmp,
                    index=False,
                )

                with open(
                    json_tmp,
                    "w",
                    encoding="utf-8",
                ) as handle:

                    json.dump(
                        metadata,
                        handle,
                        indent=2,
                        ensure_ascii=False,
                    )

                os.replace(
                    csv_tmp,
                    csv_path,
                )

                os.replace(
                    json_tmp,
                    json_path,
                )

                total_saved += 1
                total_readings += len(frame)

                print(
                    f"  {site}: saved {len(frame)} readings",
                    flush=True,
                )

            except Exception as error:

                total_failed += 1

                failures.append({
                    "event_id": event_id,
                    "site_no": site,
                    "error": str(error),
                })

                print(
                    f"  {site}: ERROR - {error}",
                    flush=True,
                )

            time.sleep(0.2)

    # ========================================================
    # SAVE FAILURE LOG
    # ========================================================

    failure_file = OUTPUT_DIR / "download_failures.csv"

    pd.DataFrame(
        failures,
        columns=[
            "event_id",
            "site_no",
            "error",
        ],
    ).to_csv(
        failure_file,
        index=False,
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\nDOWNLOAD SUMMARY")
    print("-" * 55)

    print("Events selected:", len(selected))
    print("New station-event files saved:", total_saved)
    print("Existing files skipped:", total_skipped)
    print("Failed or empty:", total_failed)
    print("New readings saved:", total_readings)
    print("Output:", OUTPUT_DIR)
    print("Failure log:", failure_file)

    if total_failed == 0:
        print("\nDownload completed without errors.")
    else:
        print(
            "\nSome downloads failed. "
            "Run again with --resume to retry them."
        )


if __name__ == "__main__":
    main()
