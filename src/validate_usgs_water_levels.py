
from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = (
    ROOT / "data" / "processed" / "usgs_water_levels"
)

OUTPUT_FILE = (
    ROOT / "data" / "processed"
    / "usgs_water_levels_validation.csv"
)

rows = []

csv_files = sorted(DATA_DIR.glob("event_*.csv"))

print("\nUSGS WATER-LEVEL VALIDATION")
print("-" * 55)
print("CSV files found:", len(csv_files))

for csv_path in csv_files:

    json_path = csv_path.with_suffix(".json")

    result = {
        "file": csv_path.name,
        "readings": 0,
        "missing_values": 0,
        "invalid_timestamps": 0,
        "negative_values": 0,
        "sentinel_values": 0,
        "duplicate_timestamps": 0,
        "event_flag_mismatches": 0,
        "outside_window": 0,
        "metadata_mismatch": 0,
        "metadata_missing": 0,
        "event_readings": 0,
        "status": "PASS",
    }

    try:
        df = pd.read_csv(csv_path)

        result["readings"] = len(df)

        required = {
            "timestamp_utc",
            "gage_height_ft",
            "qualifiers",
            "series_index",
            "within_event",
        }

        if not required.issubset(df.columns):
            raise ValueError("Missing required columns")

        if not json_path.exists():
            result["metadata_missing"] = 1
            raise ValueError("Missing metadata JSON")

        with open(
            json_path,
            "r",
            encoding="utf-8",
        ) as f:
            metadata = json.load(f)

        timestamps = pd.to_datetime(
            df["timestamp_utc"],
            utc=True,
            errors="coerce",
        )

        values = pd.to_numeric(
            df["gage_height_ft"],
            errors="coerce",
        )

        start = pd.to_datetime(
            metadata["event_start_utc"],
            utc=True,
        )

        end = pd.to_datetime(
            metadata["event_end_utc"],
            utc=True,
        )

        window_start = pd.to_datetime(
            metadata["window_start_utc"],
            utc=True,
        )

        window_end = pd.to_datetime(
            metadata["window_end_utc"],
            utc=True,
        )

        result["missing_values"] = int(
            values.isna().sum()
        )

        result["invalid_timestamps"] = int(
            timestamps.isna().sum()
        )

        result["negative_values"] = int(
            (values < 0).sum()
        )

        result["sentinel_values"] = int(
            (values <= -99999).sum()
        )

        result["duplicate_timestamps"] = int(
            df.duplicated(
                ["timestamp_utc", "series_index"]
            ).sum()
        )

        expected_flags = timestamps.between(
            start,
            end,
            inclusive="both",
        )

        actual_flags = (
            df["within_event"]
            .astype(str)
            .str.lower()
            .map({"true": True, "false": False})
        )

        result["event_flag_mismatches"] = int(
            (
                actual_flags.isna()
                | (actual_flags != expected_flags)
            ).sum()
        )

        result["outside_window"] = int(
            (
                ~timestamps.between(
                    window_start,
                    window_end,
                    inclusive="both",
                )
            ).sum()
        )

        result["event_readings"] = int(
            expected_flags.sum()
        )

        result["metadata_mismatch"] = int(
            metadata.get("reading_count") != len(df)
            or metadata.get("event_reading_count")
            != result["event_readings"]
        )

        critical_checks = [
            "missing_values",
            "invalid_timestamps",
            "sentinel_values",
            "duplicate_timestamps",
            "event_flag_mismatches",
            "outside_window",
            "metadata_mismatch",
        ]

        if any(
            result[key] > 0
            for key in critical_checks
        ):
            result["status"] = "REVIEW"

        if result["negative_values"] > 0:
            result["status"] = "REVIEW"

    except Exception as error:
        result["status"] = "ERROR"
        result["error"] = str(error)

    rows.append(result)


report = pd.DataFrame(rows)

report.to_csv(
    OUTPUT_FILE,
    index=False,
)

print("\nVALIDATION SUMMARY")
print("-" * 55)

print("Files checked:", len(report))

if not report.empty:

    print(
        "PASS:",
        int((report["status"] == "PASS").sum()),
    )

    print(
        "REVIEW:",
        int((report["status"] == "REVIEW").sum()),
    )

    print(
        "ERROR:",
        int((report["status"] == "ERROR").sum()),
    )

    print(
        "Total readings:",
        int(report["readings"].sum()),
    )

    print(
        "Readings during events:",
        int(report["event_readings"].sum()),
    )

    for field in [
        "missing_values",
        "invalid_timestamps",
        "negative_values",
        "sentinel_values",
        "duplicate_timestamps",
        "event_flag_mismatches",
        "outside_window",
        "metadata_mismatch",
    ]:
        print(
            f"{field}:",
            int(report[field].sum()),
        )

    flagged = report[
        report["status"] != "PASS"
    ]

    if not flagged.empty:
        print("\nFILES REQUIRING ATTENTION")
        print(
            flagged[
                ["file", "status"]
            ].to_string(index=False)
        )

print("\nValidation report:", OUTPUT_FILE)
