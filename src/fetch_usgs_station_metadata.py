
from pathlib import Path
from datetime import datetime, timezone
import io
import json

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT / "data" / "processed"
    / "usgs_station_metadata.csv"
)
REPORT = (
    ROOT / "outputs" / "reports"
    / "usgs_station_metadata_audit.json"
)

STATIONS = [
    "01652500",
    "01646500",
    "01648000",
    "01651800",
    "01651770",
    "01651760",
]

URL = "https://waterservices.usgs.gov/nwis/site/"

FIELDS = [
    "site_no",
    "station_nm",
    "site_tp_cd",
    "dec_lat_va",
    "dec_long_va",
    "coord_datum_cd",
    "alt_va",
    "alt_datum_cd",
    "state_cd",
    "county_cd",
    "begin_date",
    "end_date",
]


def main():
    print("\nUSGS STATION METADATA AUDIT")
    print("=" * 60)

    params = {
        "format": "rdb",
        "sites": ",".join(STATIONS),
        "siteOutput": "expanded",
        "siteStatus": "all",
    }

    response = requests.get(
        URL,
        params=params,
        timeout=90,
    )
    response.raise_for_status()

    lines = [
        line for line in response.text.splitlines()
        if line.strip() and not line.startswith("#")
    ]

    if len(lines) < 2:
        raise RuntimeError(
            "USGS returned no usable station records."
        )

    rdb = "\n".join([lines[0]] + lines[2:])

    df = pd.read_csv(
        io.StringIO(rdb),
        sep="\t",
        dtype=str,
    )

    if "site_no" not in df.columns:
        raise ValueError(
            "USGS response is missing site_no."
        )

    df = df.drop_duplicates(
        subset=["site_no"]
    )

    available = [
        column for column in FIELDS
        if column in df.columns
    ]

    result = df[available].copy()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(OUTPUT, index=False)

    found = set(result["site_no"])
    missing = sorted(set(STATIONS) - found)

    report = {
        "retrieved_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_url": response.url,
        "requested_stations": STATIONS,
        "stations_found": len(found),
        "missing_stations": missing,
        "available_fields": available,
        "notes": [
            "Coordinates and horizontal datum are "
            "taken from USGS station records.",
            "Station altitude datum is not automatically "
            "equivalent to the gage-height reference datum.",
            "No HDF5 data were modified.",
        ],
    }

    REPORT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nSTATIONS FOUND:", len(found))
    print("MISSING:", missing)

    print("\nSTATION DETAILS")
    print(result.to_string(index=False))

    print("\nSAVED:")
    print(OUTPUT)
    print(REPORT)

    print("\nAUDIT COMPLETED")


if __name__ == "__main__":
    main()
