
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
    / "usgs_iv_coverage.csv"
)

URL = "https://waterservices.usgs.gov/nwis/iv/"

stations = pd.read_csv(
    INPUT,
    dtype={"site_no": str},
)

session = requests.Session()
records = []

print("\nUSGS INSTANTANEOUS COVERAGE CHECK")
print("-" * 55)
print("Stations:", len(stations))
print("Parameter: 00065 (Gage Height)")

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
        "has_iv_data": False,
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
                "startDT": "2025-01-01",
                "endDT": "2025-01-07",
                "siteStatus": "all",
            },
            timeout=90,
        )

        response.raise_for_status()

        lines = [
            line for line in response.text.splitlines()
            if line.strip()
            and not line.startswith("#")
        ]

        if len(lines) < 3:
            record["status"] = "no_data_in_sample"

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
                    utc=True,
                ).dropna()

                if dates.empty:
                    record["status"] = "no_valid_dates"

                else:
                    record["has_iv_data"] = True
                    record["first_observation"] = (
                        dates.min().isoformat()
                    )
                    record["last_observation"] = (
                        dates.max().isoformat()
                    )
                    record["observation_count"] = len(dates)
                    record["status"] = "sample_data_found"

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

print("\nIV SAMPLE SUMMARY")
print("-" * 55)

print(
    "Stations with sample data:",
    int(results["has_iv_data"].sum()),
)

print(
    results[
        [
            "site_no",
            "observation_count",
            "status",
        ]
    ].to_string(index=False)
)

print("\nSaved to:", OUTPUT)
