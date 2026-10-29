
from pathlib import Path
import io

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT / "data" / "processed"
    / "dc_precipitation_station_candidates.csv"
)

URL = "https://waterservices.usgs.gov/nwis/site/"

PARAMS = {
    "format": "rdb",
    "bBox": "-77.12,38.79,-76.90,39.00",
    "parameterCd": "00045",
    "siteStatus": "all",
    "siteType": "ST",
    "siteOutput": "expanded",
}


def main():

    print("\nDISCOVERING DC PRECIPITATION STATIONS")
    print("-" * 55)

    response = requests.get(
        URL,
        params=PARAMS,
        timeout=90,
    )

    response.raise_for_status()

    lines = [
        line
        for line in response.text.splitlines()
        if line.strip()
        and not line.startswith("#")
    ]

    if len(lines) < 2:
        print("No station records returned.")
        return

    # USGS RDB includes a column-format row
    # immediately after the header.
    clean_text = "\n".join(
        [lines[0]] + lines[2:]
    )

    df = pd.read_csv(
        io.StringIO(clean_text),
        sep="\t",
        dtype=str,
    )

    if "site_no" not in df.columns:
        raise ValueError(
            "USGS response does not contain site_no."
        )

    df = df.drop_duplicates(
        subset=["site_no"]
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT,
        index=False,
    )

    print("Candidate stations:", len(df))

    columns = [
        col for col in [
            "site_no",
            "station_nm",
            "dec_lat_va",
            "dec_long_va",
            "state_cd",
            "county_cd",
        ]
        if col in df.columns
    ]

    if len(df):
        print("\nSTATION CANDIDATES")
        print(
            df[columns].to_string(index=False)
        )

    print("\nSaved:", OUTPUT)
    print(
        "\nNote: Bounding-box results are not "
        "proof that every station lies within "
        "DC administrative boundaries."
    )


if __name__ == "__main__":
    main()
