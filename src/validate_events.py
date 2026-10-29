
from pathlib import Path
from datetime import timezone, timedelta
import pandas as pd

# ============================================================
# STAT 6289 - DC Flood Data Project
# Version 4: Daymet + DC Water-Level Gauges
# Event validation and time normalization
#
# Original event times use fixed EST (UTC-5), including summer.
# The original instructor-provided CSV is never modified.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    PROJECT_ROOT / "data" / "raw" / "DC_flood_times.csv"
)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

REQUIRED_COLUMNS = [
    "begin_date",
    "begin_time",
    "end_date",
    "end_time",
]

EST = timezone(timedelta(hours=-5))


def main():
    print("=" * 65)
    print("STAT 6289 - DC FLOOD EVENT VALIDATION")
    print("Version 4: Daymet + Water-Level Gauges")
    print("=" * 65)

    # --------------------------------------------------------
    # 1. Read original event index
    # --------------------------------------------------------
    if not CSV_PATH.is_file():
        raise FileNotFoundError(
            f"Original event CSV not found: {CSV_PATH}"
        )

    df = pd.read_csv(CSV_PATH, dtype="string")

    print("\n=== Original Dataset ===")
    print("Total events:", len(df))
    print("Columns:", df.columns.tolist())

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # 2. Preserve original records and assign event IDs
    # --------------------------------------------------------
    events = df.copy()

    events.insert(
        0,
        "event_id",
        [
            f"event_{i:03d}"
            for i in range(1, len(events) + 1)
        ],
    )

    # --------------------------------------------------------
    # 3. Identify missing fields
    # --------------------------------------------------------
    missing_fields = (
        df[REQUIRED_COLUMNS]
        .isna()
        .any(axis=1)
    )

    for column in REQUIRED_COLUMNS:
        missing_fields |= (
            df[column].str.strip().eq("").fillna(False)
        )

    # --------------------------------------------------------
    # 4. Parse original timestamps
    # --------------------------------------------------------
    start_text = (
        df["begin_date"].str.strip()
        + " "
        + df["begin_time"].str.strip()
    )

    end_text = (
        df["end_date"].str.strip()
        + " "
        + df["end_time"].str.strip()
    )

    start_local = pd.to_datetime(
        start_text,
        format="%Y-%m-%d %H:%M",
        errors="coerce",
    )

    end_local = pd.to_datetime(
        end_text,
        format="%Y-%m-%d %H:%M",
        errors="coerce",
    )

    # --------------------------------------------------------
    # 5. Convert fixed EST to UTC
    # --------------------------------------------------------
    events["start_utc"] = (
        start_local
        .dt.tz_localize(EST)
        .dt.tz_convert("UTC")
    )

    events["end_utc"] = (
        end_local
        .dt.tz_localize(EST)
        .dt.tz_convert("UTC")
    )

    events["duration_hours"] = (
        (
            events["end_utc"]
            - events["start_utc"]
        )
        .dt.total_seconds()
        / 3600
    )

    # --------------------------------------------------------
    # 6. Identify validation issues
    # --------------------------------------------------------
    invalid_dates = (
        events["start_utc"].isna()
        | events["end_utc"].isna()
    )

    negative_duration = (
        events["duration_hours"] < 0
    ).fillna(False)

    zero_duration = (
        events["duration_hours"] == 0
    ).fillna(False)

    duplicate_rows = events.duplicated(
        subset=REQUIRED_COLUMNS,
        keep=False,
    )

    # A zero-duration event is retained, not rejected.
    events["validation_status"] = "valid"

    events.loc[
        zero_duration,
        "validation_status"
    ] = "zero_duration"

    events.loc[
        duplicate_rows,
        "validation_status"
    ] = "duplicate"

    events.loc[
        negative_duration,
        "validation_status"
    ] = "negative_duration"

    events.loc[
        invalid_dates,
        "validation_status"
    ] = "invalid_datetime"

    events.loc[
        missing_fields,
        "validation_status"
    ] = "missing_fields"

    # --------------------------------------------------------
    # 7. Document the zero-duration event
    # --------------------------------------------------------
    events["validation_note"] = ""

    events.loc[
        zero_duration,
        "validation_note"
    ] = (
        "Start and end timestamps are identical. "
        "Original event retained without extending "
        "the event window. Source temporal resolution "
        "must be considered during data retrieval."
    )

    # --------------------------------------------------------
    # 8. Print validation results
    # --------------------------------------------------------
    print("\n=== Validation Summary ===")
    print("Total events:", len(events))
    print("Missing-field rows:", int(missing_fields.sum()))
    print("Invalid dates:", int(invalid_dates.sum()))
    print(
        "Negative-duration events:",
        int(negative_duration.sum())
    )
    print(
        "Zero-duration events:",
        int(zero_duration.sum())
    )
    print(
        "Duplicate rows:",
        int(duplicate_rows.sum())
    )

    print("\n=== Validation Status Counts ===")
    print(
        events["validation_status"]
        .value_counts()
        .to_string()
    )

    print("\n=== Zero-Duration Events ===")

    if zero_duration.any():
        print(
            events.loc[
                zero_duration,
                [
                    "event_id",
                    "begin_date",
                    "begin_time",
                    "end_date",
                    "end_time",
                    "start_utc",
                    "end_utc",
                    "duration_hours",
                ],
            ].to_string(index=False)
        )
    else:
        print("None found.")

    print("\n=== Temporal Coverage ===")
    print(
        "Earliest start:",
        events["start_utc"].min()
    )
    print(
        "Latest end:",
        events["end_utc"].max()
    )

    print("\n=== Duration Statistics (Hours) ===")
    print(
        events["duration_hours"]
        .describe()
        .to_string()
    )

    # --------------------------------------------------------
    # 9. Save validation report
    # --------------------------------------------------------
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        PROCESSED_DIR
        / "event_validation_report.csv"
    )

    events.to_csv(
        report_path,
        index=False
    )

    print("\nValidation report:", report_path)

    # --------------------------------------------------------
    # 10. Check whether data can be approved
    # --------------------------------------------------------
    blocking_issues = (
        missing_fields.any()
        or invalid_dates.any()
        or negative_duration.any()
        or duplicate_rows.any()
    )

    if blocking_issues:
        print("\nVALIDATION REQUIRES REVIEW")
        print(
            "Blocking issues were detected. "
            "The validated event index was not saved."
        )
        raise ValueError(
            "Resolve blocking validation issues."
        )

    # --------------------------------------------------------
    # 11. Save validated event index
    # --------------------------------------------------------
    validated_path = (
        PROCESSED_DIR / "validated_events.csv"
    )

    events.to_csv(
        validated_path,
        index=False
    )

    print("\n" + "=" * 65)
    print("VALIDATION PASSED")
    print("=" * 65)
    print("All original events were preserved.")
    print("Zero-duration events were documented.")
    print("Original CSV remains unchanged.")
    print("Validated event index:", validated_path)


if __name__ == "__main__":
    main()
