
from pathlib import Path
from io import StringIO
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "usgs_station_candidates.csv"

# Washington DC and nearby Potomac/Anacostia area
BBOX = "-77.30,38.70,-76.80,39.10"

URL = "https://waterservices.usgs.gov/nwis/site/"

PARAMS = {
    "format": "rdb",
    "bBox": BBOX,
    "parameterCd": "00065",
    "hasDataTypeCd": "iv",
    "siteType": "ST",
    "siteStatus": "all",
    "siteOutput": "expanded",
}

print("\nUSGS STATION DISCOVERY")
print("-" * 50)
print("Parameter: 00065 (gage height)")
print("Bounding box:", BBOX)
print("Requesting station metadata...", flush=True)

response = requests.get(
    URL,
    params=PARAMS,
    timeout=90,
)
response.raise_for_status()

lines = [
    line for line in response.text.splitlines()
    if line.strip() and not line.startswith("#")
]

if len(lines) < 2:
    raise RuntimeError(
        "USGS returned no tabular station records."
    )

# RDB contains a header followed by a field-format row.
table_text = "\n".join(
    [lines[0]] + lines[2:]
)

stations = pd.read_csv(
    StringIO(table_text),
    sep="\t",
    dtype=str,
)

if stations.empty:
    print("No stations matched the filters.")
else:
    stations = stations.drop_duplicates(
        subset=["site_no"]
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    stations.to_csv(
        OUTPUT,
        index=False,
    )

    display_columns = [
        col for col in [
            "site_no",
            "station_nm",
            "dec_lat_va",
            "dec_long_va",
            "begin_date",
            "end_date",
        ]
        if col in stations.columns
    ]

    print("\nStations found:", len(stations))
    print("\nStation candidates:")
    print(
        stations[display_columns].to_string(
            index=False,
            max_rows=60,
        )
    )

    print("\nSaved to:", OUTPUT)

print("\nDiscovery completed.")
