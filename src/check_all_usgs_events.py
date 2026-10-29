
from pathlib import Path
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "validated_events.csv"
OUTPUT = ROOT / "data" / "processed" / "usgs_all_event_coverage.csv"

STATIONS = {
    "01652500": "Fourmile Run Alexandria",
    "01651800": "Watts Branch DC",
    "01646500": "Potomac Little Falls",
    "01648000": "Rock Creek DC",
    "01651760": "Anacostia Kenilworth",
    "01651770": "Hickey Run DC",
}

URL = "https://waterservices.usgs.gov/nwis/iv/"
PARAMETER = "00065"
CONTEXT_HOURS = 12
MAX_WORKERS = 4

events = pd.read_csv(INPUT)
events["start_utc"] = pd.to_datetime(events["start_utc"], utc=True)
events["end_utc"] = pd.to_datetime(events["end_utc"], utc=True)

if len(events) != 125:
    raise ValueError(f"Expected 125 events, found {len(events)}")

if events["event_id"].duplicated().any():
    raise ValueError("Duplicate event IDs")

if (events["end_utc"] < events["start_utc"]).any():
    raise ValueError("Event end occurs before start")

tasks = []

for _, event in events.iterrows():
    for site, name in STATIONS.items():
        tasks.append((
            str(event["event_id"]),
            event["start_utc"],
            event["end_utc"],
            site,
            name,
        ))


def inspect_task(task):
    event_id, start, end, site, name = task

    window_start = start - timedelta(hours=CONTEXT_HOURS)
    window_end = end + timedelta(hours=CONTEXT_HOURS)

    record = {
        "event_id": event_id,
        "event_start_utc": start.isoformat(),
        "event_end_utc": end.isoformat(),
        "site_no": site,
        "station_name": name,
        "parameter_code": PARAMETER,
        "unit": "ft",
        "context_hours": CONTEXT_HOURS,
        "valid_context_readings": 0,
        "valid_event_readings": 0,
        "first_valid_utc": None,
        "last_valid_utc": None,
        "status": "unknown",
        "error": "",
    }

    params = {
        "format": "json",
        "sites": site,
        "parameterCd": PARAMETER,
        "startDT": window_start.strftime("%Y-%m-%d"),
        "endDT": window_end.strftime("%Y-%m-%d"),
        "siteStatus": "all",
    }

    for attempt in range(3):
        try:
            response = requests.get(
                URL, params=params, timeout=90
            )
            response.raise_for_status()
            payload = response.json()

            valid = []

            for series in payload.get(
                "value", {}
            ).get("timeSeries", []):

                variable = series.get("variable", {})
                codes = [
                    str(x.get("value", ""))
                    for x in variable.get("variableCode", [])
                ]

                if PARAMETER not in codes:
                    continue

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

                        if (
                            pd.notna(stamp)
                            and pd.notna(value)
                            and np.isfinite(value)
                            and window_start <= stamp <= window_end
                        ):
                            valid.append((stamp, float(value)))

            # Avoid counting duplicate timestamps twice.
            unique = {}
            for stamp, value in valid:
                unique[stamp] = value

            dates = sorted(unique)

            record["valid_context_readings"] = len(dates)
            record["valid_event_readings"] = sum(
                start <= stamp <= end for stamp in dates
            )

            if dates:
                record["first_valid_utc"] = dates[0].isoformat()
                record["last_valid_utc"] = dates[-1].isoformat()
                record["status"] = "valid_data_found"
            else:
                record["status"] = "no_valid_data"

            return record

        except (
            requests.RequestException,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            record["error"] = str(exc)
            record["status"] = "request_error"

            if attempt < 2:
                time.sleep(2 * (attempt + 1))

    return record


print("\nUSGS ALL-EVENT COVERAGE CHECK")
print("-" * 55)
print("Events:", len(events))
print("Stations:", len(STATIONS))
print("Total requests:", len(tasks))
print("Parameter: 00065 (gage height, feet)")
print("Context: +/- 12 hours")
print("This may take several minutes.\n", flush=True)

records = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [
        executor.submit(inspect_task, task)
        for task in tasks
    ]

    for i, future in enumerate(as_completed(futures), start=1):
        record = future.result()
        records.append(record)

        if i % 25 == 0 or i == len(tasks):
            print(
                f"Completed {i}/{len(tasks)} requests",
                flush=True,
            )

results = pd.DataFrame(records)
results = results.sort_values(
    ["event_id", "site_no"]
).reset_index(drop=True)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
results.to_csv(OUTPUT, index=False)

summary = (
    results.groupby(["site_no", "station_name"], as_index=False)
    .agg(
        events_with_context_data=(
            "valid_context_readings",
            lambda x: int((x > 0).sum()),
        ),
        events_with_in_event_data=(
            "valid_event_readings",
            lambda x: int((x > 0).sum()),
        ),
        total_valid_readings=(
            "valid_context_readings", "sum"
        ),
        request_errors=(
            "status",
            lambda x: int((x == "request_error").sum()),
        ),
    )
    .sort_values(
        "events_with_context_data",
        ascending=False,
    )
)

event_summary = results.groupby("event_id").agg(
    stations_with_data=(
        "valid_context_readings",
        lambda x: int((x > 0).sum()),
    ),
    stations_during_event=(
        "valid_event_readings",
        lambda x: int((x > 0).sum()),
    ),
)

print("\nALL-EVENT COVERAGE SUMMARY")
print("-" * 55)
print(summary.to_string(index=False))

print("\nEVENT-LEVEL SUMMARY")
print("-" * 55)
print(
    "Events with at least one station (context):",
    int((event_summary["stations_with_data"] > 0).sum()),
)
print(
    "Events with at least one station (during event):",
    int((event_summary["stations_during_event"] > 0).sum()),
)
print(
    "Events with no station data (context):",
    int((event_summary["stations_with_data"] == 0).sum()),
)
print(
    "Total request errors:",
    int((results["status"] == "request_error").sum()),
)

print("\nSaved to:", OUTPUT)
print("Coverage check completed.")
