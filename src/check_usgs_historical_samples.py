
from pathlib import Path
from io import StringIO
import time
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "data" / "processed"
    / "usgs_station_candidates.csv"
)

OUTPUT = (
    ROOT / "data" / "processed"
    / "usgs_historical_samples.csv"
)

URL = "https://waterservices.usgs.gov/nwis/iv/"

YEARS = [1996, 2000, 2005, 2010, 2015, 2020, 2025]

stations = pd.read_csv(
    INPUT, dtype={"site_no": str}
)

session = requests.Session()
records = []

print("\nUSGS HISTORICAL SAMPLE CHECK")
print("-" * 55)
print("Stations:", len(stations))
print("Sample years:", YEARS)

for index, station in stations.iterrows():

    site = station["site_no"]
    name = station["station_nm"]

    print(
        f"\n[{index + 1}/{len(stations)}] "
        f"{site} - {name}",
        flush=True,
    )

    for year in YEARS:

        record = {
            "site_no": site,
            "station_nm": name,
            "year": year,
            "sample_start": f"{year}-06-01",
            "sample_end": f"{year}-06-03",
            "has_data": False,
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
                    "startDT": record["sample_start"],
                    "endDT": record["sample_end"],
                    "siteStatus": "all",
                },
                timeout=60,
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

                if "datetime" in data.columns:
                    dates = pd.to_datetime(
                        data["datetime"],
                        errors="coerce",
                        utc=True,
                    ).dropna()

                    record["observation_count"] = len(dates)

                    if len(dates) > 0:
                        record["has_data"] = True
                        record["status"] = "data_found"
                    else:
                        record["status"] = "no_valid_dates"
                else:
                    record["status"] = "no_datetime_column"

        except Exception as error:
            record["status"] = "request_error"
            record["error"] = str(error)

        records.append(record)

        print(
            f"  {year}: {record['status']} "
            f"({record['observation_count']})",
            flush=True,
        )

        time.sleep(0.15)

results = pd.DataFrame(records)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

results.to_csv(
    OUTPUT, index=False
)

summary = (
    results.groupby(
        ["site_no", "station_nm"],
        as_index=False,
    )
    .agg(
        sampled_years_with_data=("has_data", "sum"),
        sample_observations=("observation_count", "sum"),
        request_errors=(
            "status",
            lambda s: int((s == "request_error").sum()),
        ),
    )
    .sort_values(
        ["sampled_years_with_data", "sample_observations"],
        ascending=False,
    )
)

print("\nHISTORICAL SAMPLE SUMMARY")
print("-" * 55)
print(
    summary[
        [
            "site_no",
            "sampled_years_with_data",
            "sample_observations",
            "request_errors",
        ]
    ].to_string(index=False)
)

print("\nSaved to:", OUTPUT)
