
from pathlib import Path
from datetime import timedelta
import requests
import pandas as pd
import numpy as np
import time

ROOT = Path(__file__).resolve().parents[1]

EVENTS_FILE = (
    ROOT / "data" / "processed"
    / "validated_events.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "processed"
    / "usgs_event_coverage_pilot.csv"
)

STATIONS = {
    "01652500": "Fourmile Run Alexandria",
    "01651800": "Watts Branch DC",
    "01646500": "Potomac Little Falls",
    "01648000": "Rock Creek DC",
    "01651760": "Anacostia Kenilworth",
    "01651770": "Hickey Run DC",
}

URL = "https://waterservices.usgs.gov/nwis/iv/"

events = pd.read_csv(EVENTS_FILE)

events["start_utc"] = pd.to_datetime(
    events["start_utc"], utc=True
)
events["end_utc"] = pd.to_datetime(
    events["end_utc"], utc=True
)

events = events.sort_values(
    "start_utc"
).reset_index(drop=True)

# Select 10 events across the historical period.
indices = np.unique(
    np.linspace(
        0, len(events) - 1,
        num=min(10, len(events)),
        dtype=int,
    )
)

sample = events.iloc[indices]

session = requests.Session()
records = []

print("\nUSGS EVENT COVERAGE PILOT")
print("-" * 55)
print("Sampled events:", len(sample))
print("Stations:", len(STATIONS))

for _, event in sample.iterrows():

    event_id = event["event_id"]
    start = event["start_utc"]
    end = event["end_utc"]

    # Include a 12-hour context window.
    window_start = start - timedelta(hours=12)
    window_end = end + timedelta(hours=12)

    # Request calendar dates covering the window.
    request_start = window_start.strftime("%Y-%m-%d")
    request_end = window_end.strftime("%Y-%m-%d")

    print(
        f"\nEvent: {event_id} | "
        f"{start.date()}",
        flush=True,
    )

    for site, name in STATIONS.items():

        record = {
            "event_id": event_id,
            "event_start_utc": start.isoformat(),
            "event_end_utc": end.isoformat(),
            "site_no": site,
            "station_name": name,
            "observation_count": 0,
            "has_event_window_data": False,
            "first_observation_utc": None,
            "last_observation_utc": None,
            "status": None,
        }

        try:
            response = session.get(
                URL,
                params={
                    "format": "json",
                    "sites": site,
                    "parameterCd": "00065",
                    "startDT": request_start,
                    "endDT": request_end,
                    "siteStatus": "all",
                },
                timeout=90,
            )

            response.raise_for_status()

            payload = response.json()
            timestamps = []

            for series in payload.get(
                "value", {}
            ).get("timeSeries", []):

                for block in series.get("values", []):
                    for item in block.get("value", []):

                        stamp = pd.to_datetime(
                            item.get("dateTime"),
                            utc=True,
                            errors="coerce",
                        )

                        if pd.notna(stamp):
                            timestamps.append(stamp)

            if timestamps:
                dates = pd.DatetimeIndex(timestamps)

                # Only count timestamps inside
                # the actual event/context window.
                dates = dates[
                    (dates >= window_start)
                    & (dates <= window_end)
                ]

                record["observation_count"] = len(dates)

                if len(dates):
                    record["has_event_window_data"] = True
                    record["first_observation_utc"] = (
                        dates.min().isoformat()
                    )
                    record["last_observation_utc"] = (
                        dates.max().isoformat()
                    )
                    record["status"] = "data_found"
                else:
                    record["status"] = "no_data_in_window"
            else:
                record["status"] = "no_data_returned"

        except Exception as error:
            record["status"] = "request_error"
            record["error"] = str(error)

        records.append(record)

        print(
            f"  {site}: {record['status']} "
            f"({record['observation_count']})",
            flush=True,
        )

        time.sleep(0.15)

results = pd.DataFrame(records)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

results.to_csv(
    OUTPUT_FILE,
    index=False,
)

summary = (
    results.groupby(
        ["site_no", "station_name"],
        as_index=False,
    )
    .agg(
        events_with_data=(
            "has_event_window_data", "sum"
        ),
        total_timestamps=(
            "observation_count", "sum"
        ),
        errors=(
            "status",
            lambda s: int(
                (s == "request_error").sum()
            ),
        ),
    )
    .sort_values(
        "events_with_data",
        ascending=False,
    )
)

print("\nEVENT COVERAGE PILOT SUMMARY")
print("-" * 55)

print(
    summary.to_string(index=False)
)

print("\nSaved to:", OUTPUT_FILE)
