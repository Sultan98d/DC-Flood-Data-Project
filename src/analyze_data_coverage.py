
from pathlib import Path
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
EVENTS_FILE = PROCESSED / "validated_events.csv"
USGS_DIR = PROCESSED / "usgs_water_levels"
DAYMET_DIR = PROCESSED / "daymet_rasters"
OUTPUT_DIR = ROOT / "outputs" / "reports"

STATIONS = [
    "01652500",
    "01646500",
    "01648000",
    "01651800",
    "01651770",
    "01651760",
]


def local_dates(begin_date, end_date):
    return pd.date_range(
        start=begin_date,
        end=end_date,
        freq="D",
    ).strftime("%Y%m%d").tolist()


def inspect_station(event_id, station, start, end):
    path = USGS_DIR / f"{event_id}_{station}.csv"

    result = {
        "event_id": event_id,
        "station_id": station,
        "file_exists": path.exists(),
        "total_readings": 0,
        "event_readings": 0,
        "first_reading_utc": "",
        "last_reading_utc": "",
        "median_interval_minutes": np.nan,
        "largest_gap_minutes": np.nan,
        "large_gap_count": 0,
        "event_max_gap_minutes": np.nan,
        "event_boundary_gap_start_minutes": np.nan,
        "event_boundary_gap_end_minutes": np.nan,
        "coverage_status": "NO_FILE",
    }

    if not path.exists():
        return result

    try:
        df = pd.read_csv(path)

        candidates = [
            "datetime_utc",
            "timestamp_utc",
            "time_utc",
            "datetime",
            "timestamp",
        ]

        column = next(
            (c for c in candidates if c in df.columns),
            None,
        )

        if column is None:
            result["coverage_status"] = "UNKNOWN_TIME_COLUMN"
            return result

        times = pd.to_datetime(
            df[column],
            utc=True,
            errors="coerce",
        ).dropna().drop_duplicates().sort_values()

        if times.empty:
            result["coverage_status"] = "NO_VALID_TIMES"
            return result

        during = times[
            (times >= start) & (times <= end)
        ]

        result["total_readings"] = len(times)
        result["event_readings"] = len(during)
        result["first_reading_utc"] = times.iloc[0].isoformat()
        result["last_reading_utc"] = times.iloc[-1].isoformat()

        intervals = (
            times.diff().dropna().dt.total_seconds() / 60
        )

        if not intervals.empty:
            median = float(intervals.median())
            result["median_interval_minutes"] = median
            result["largest_gap_minutes"] = float(
                intervals.max()
            )

            threshold = max(30.0, 3.0 * median)
            result["large_gap_count"] = int(
                (intervals > threshold).sum()
            )

        if during.empty:
            result["coverage_status"] = "NO_EVENT_READINGS"
            return result

        result["event_boundary_gap_start_minutes"] = (
            during.iloc[0] - start
        ).total_seconds() / 60

        result["event_boundary_gap_end_minutes"] = (
            end - during.iloc[-1]
        ).total_seconds() / 60

        event_intervals = (
            during.diff().dropna().dt.total_seconds() / 60
        )

        if not event_intervals.empty:
            result["event_max_gap_minutes"] = float(
                event_intervals.max()
            )

        result["coverage_status"] = "HAS_EVENT_READINGS"

    except Exception as exc:
        result["coverage_status"] = "READ_ERROR"
        result["error"] = str(exc)

    return result


def main():
    print("\nDC FLOOD DATA COVERAGE AUDIT")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    events = pd.read_csv(
        EVENTS_FILE,
        dtype={"event_id": str},
    )

    station_rows = []
    event_rows = []

    for _, event in events.iterrows():
        event_id = event["event_id"]

        start = pd.to_datetime(
            event["start_utc"],
            utc=True,
        )
        end = pd.to_datetime(
            event["end_utc"],
            utc=True,
        )

        if end < start:
            raise ValueError(
                f"Invalid event: {event_id}"
            )

        station_results = [
            inspect_station(
                event_id,
                station,
                start,
                end,
            )
            for station in STATIONS
        ]

        station_rows.extend(station_results)

        dates = local_dates(
            event["begin_date"],
            event["end_date"],
        )

        available_dates = [
            date
            for date in dates
            if (
                DAYMET_DIR /
                f"daymet_prcp_{date}.npz"
            ).exists()
        ]

        missing_dates = sorted(
            set(dates) - set(available_dates)
        )

        event_rows.append({
            "event_id": event_id,
            "begin_date_local": event["begin_date"],
            "end_date_local": event["end_date"],
            "start_utc": start.isoformat(),
            "end_utc": end.isoformat(),
            "duration_hours": (
                end - start
            ).total_seconds() / 3600,
            "stations_with_files": sum(
                r["file_exists"]
                for r in station_results
            ),
            "stations_with_event_readings": sum(
                r["event_readings"] > 0
                for r in station_results
            ),
            "total_event_readings": sum(
                r["event_readings"]
                for r in station_results
            ),
            "daymet_dates_required": len(dates),
            "daymet_dates_found": len(available_dates),
            "daymet_missing_dates": ";".join(
                missing_dates
            ),
        })

    station_df = pd.DataFrame(station_rows)
    event_df = pd.DataFrame(event_rows)

    station_df.to_csv(
        OUTPUT_DIR / "usgs_station_event_coverage.csv",
        index=False,
    )

    event_df.to_csv(
        OUTPUT_DIR / "flood_event_coverage.csv",
        index=False,
    )

    summary = {
        "total_events": int(len(event_df)),
        "station_event_combinations": int(
            len(station_df)
        ),
        "station_files_found": int(
            station_df["file_exists"].sum()
        ),
        "station_event_pairs_with_readings": int(
            (station_df["event_readings"] > 0).sum()
        ),
        "events_with_any_usgs_readings": int(
            (event_df["total_event_readings"] > 0).sum()
        ),
        "events_without_usgs_readings": int(
            (event_df["total_event_readings"] == 0).sum()
        ),
        "total_event_readings": int(
            event_df["total_event_readings"].sum()
        ),
        "daymet_local_date_checks": int(
            event_df["daymet_dates_required"].sum()
        ),
        "daymet_local_date_matches": int(
            event_df["daymet_dates_found"].sum()
        ),
        "events_with_missing_daymet_dates": int(
            (event_df["daymet_missing_dates"] != "").sum()
        ),
        "notes": [
            "Daymet is checked using event-local dates.",
            "USGS measurements are checked in UTC.",
            "Repeated Daymet dates across events are counted "
            "once per event in the coverage checks.",
            "No missing measurements are interpolated.",
            "USGS gaps are diagnostic, not proof "
            "of an expected fixed sampling schedule.",
            "Daymet daily time conventions require "
            "separate documentation.",
        ],
    }

    summary_path = (
        OUTPUT_DIR / "coverage_audit_summary.json"
    )

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nSUMMARY")
    print("-" * 60)

    for key, value in summary.items():
        if key != "notes":
            print(f"{key}: {value}")

    print("\nFILES CREATED")
    print(OUTPUT_DIR / "usgs_station_event_coverage.csv")
    print(OUTPUT_DIR / "flood_event_coverage.csv")
    print(summary_path)

    print("\nAUDIT COMPLETED")


if __name__ == "__main__":
    main()
