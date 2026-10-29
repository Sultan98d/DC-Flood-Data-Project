
from pathlib import Path
from io import StringIO
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "data" / "processed"
    / "usgs_station_candidates.csv"
)

OUTPUT = (
    ROOT / "data" / "processed"
    / "usgs_station_coverage.csv"
)

URL = "https://waterservices.usgs.gov/nwis/dv/"

START_DATE = "1996-01-01"
END_DATE = "2025-12-31"

stations = pd.read_csv(
    INPUT,
    dtype={"site_no": str},
)

session = requests.Session()

records = []

print("\nUSGS HISTORICAL COVERAGE CHECK")
print("-" * 55)
print("Stations:", len(stations))
print("Parameter: 00065 (Gage Height)")
print("Period:", START_DATE, "to", END_DATE)

for index, station in stations.iterrows():

    site = station["site_no"]
    name = station["station_nm"]

    print(
        f"\n[{index + 1}/{len(stations)}] "
        f"{site} - {name}",
        flush=True,
    )

    record = {
        "site_no": site,
        "station_nm": name,
        "has_daily_gage_height": False,
        "first_observation": None,
        "last_observation": None,
        "observation_count": 0,
        "status": None,
    }

    try:
        response = session.get(
            URL,
            params={
                "format": "rdb",
                "sites": site,
                "parameterCd": "00065",
                "startDT": START_DATE,
                "endDT": END_DATE,
                "siteStatus": "all",
            },
            timeout=90,
        )

        response.raise_for_status()

        lines = [
            line
            for line in response.text.splitlines()
            if line.strip()
            and not line.startswith("#")
        ]

        if len(lines) < 3:
            record["status"] = "no_daily_data"

        else:
            content = "\n".join(
                [lines[0]] + lines[2:]
            )

            data = pd.read_csv(
                StringIO(content),
                sep="\t",
                dtype=str,
            )

            if "datetime" not in data.columns:
                record["status"] = "no_datetime_column"

            else:
                dates = pd.to_datetime(
                    data["datetime"],
                    errors="coerce",
                ).dropna()

                if dates.empty:
                    record["status"] = "no_valid_dates"

                else:
                    record["has_daily_gage_height"] = True
                    record["first_observation"] = (
                        dates.min().date().isoformat()
                    )
                    record["last_observation"] = (
                        dates.max().date().isoformat()
                    )
                    record["observation_count"] = len(dates)
                    record["status"] = "daily_data_found"

        print(
            "Status:", record["status"],
            "| Observations:",
            record["observation_count"],
        )

    except Exception as error:
        record["status"] = "request_error"
        record["error"] = str(error)
        print("ERROR:", error)

    records.append(record)

results = pd.DataFrame(records)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

results.to_csv(
    OUTPUT,
    index=False,
)

print("\nCOVERAGE SUMMARY")
print("-" * 55)

print(
    "Stations with daily gage height:",
    int(results["has_daily_gage_height"].sum()),
)

print(
    "\n",
    results[
        [
            "site_no",
            "first_observation",
            "last_observation",
            "observation_count",
            "status",
        ]
    ].to_string(index=False),
)

print("\nSaved to:", OUTPUT)
