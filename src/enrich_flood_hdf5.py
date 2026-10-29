
from pathlib import Path
from datetime import datetime, timezone
import shutil

import h5py
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

SOURCE_H5 = PROCESSED / "dc_flood_dataset.h5"
TARGET_H5 = PROCESSED / "dc_flood_dataset_enriched.h5"

STATION_CSV = PROCESSED / "usgs_station_metadata.csv"

REQUIRED_COLUMNS = [
    "site_no",
    "station_nm",
    "dec_lat_va",
    "dec_long_va",
    "coord_datum_cd",
    "alt_va",
    "alt_datum_cd",
    "state_cd",
    "county_cd",
]


def main():
    print("\nENRICHING DC FLOOD HDF5")
    print("=" * 60)

    if not SOURCE_H5.exists():
        raise FileNotFoundError(SOURCE_H5)

    if not STATION_CSV.exists():
        raise FileNotFoundError(STATION_CSV)

    stations = pd.read_csv(
        STATION_CSV,
        dtype=str,
        keep_default_na=False,
    )

    missing = [
        c for c in REQUIRED_COLUMNS
        if c not in stations.columns
    ]

    if missing:
        raise ValueError(
            f"Missing metadata columns: {missing}"
        )

    if stations["site_no"].duplicated().any():
        raise ValueError(
            "Duplicate station IDs detected."
        )

    if len(stations) != 6:
        raise ValueError(
            f"Expected 6 stations, found {len(stations)}."
        )

    if TARGET_H5.exists():
        raise FileExistsError(
            f"Target already exists: {TARGET_H5}\n"
            "Existing output will not be overwritten."
        )

    shutil.copy2(SOURCE_H5, TARGET_H5)

    try:
        with h5py.File(TARGET_H5, "r+") as h5:
            metadata = h5.require_group("metadata")
            group = metadata.create_group("usgs_stations")

            group.attrs["source"] = (
                "USGS NWIS Site Service"
            )
            group.attrs["coordinate_note"] = (
                "Latitude and longitude are station "
                "coordinates in the stated horizontal datum."
            )
            group.attrs["vertical_datum_note"] = (
                "Station altitude datum does not "
                "automatically establish the reference "
                "datum of instantaneous gage-height values."
            )
            group.attrs["created_utc"] = datetime.now(
                timezone.utc
            ).isoformat()

            for _, station in stations.iterrows():
                site_no = station["site_no"]

                site_group = group.create_group(site_no)

                for column in REQUIRED_COLUMNS:
                    value = station[column]

                    if column in [
                        "dec_lat_va",
                        "dec_long_va",
                        "alt_va",
                    ]:
                        try:
                            site_group.attrs[column] = float(value)
                        except (ValueError, TypeError):
                            site_group.attrs[column] = value
                    else:
                        site_group.attrs[column] = str(value)

            h5.attrs["station_metadata_enriched"] = True
            h5.attrs["station_metadata_count"] = len(stations)

        with h5py.File(TARGET_H5, "r") as h5:
            group = h5["metadata/usgs_stations"]

            assert len(group) == 6
            assert len(h5["events/event_id"]) == 125
            assert len(h5["daymet"]) == 149

            print("\nVERIFICATION")
            print("Stations:", len(group))
            print("Events:", len(h5["events/event_id"]))
            print("Daymet dates:", len(h5["daymet"]))

            for site_no in sorted(group.keys()):
                site = group[site_no]
                print(
                    site_no,
                    site.attrs["station_nm"],
                    site.attrs["dec_lat_va"],
                    site.attrs["dec_long_va"],
                )

        print("\nSOURCE PRESERVED:")
        print(SOURCE_H5)

        print("\nENRICHED FILE CREATED:")
        print(TARGET_H5)

        print("\nRESULT: PASS")

    except Exception:
        if TARGET_H5.exists():
            TARGET_H5.unlink()
        raise


if __name__ == "__main__":
    main()
