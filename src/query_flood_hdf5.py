
from pathlib import Path
import argparse
import json

import h5py
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
H5_PATH = (
    ROOT / "data" / "processed"
    / "dc_flood_dataset_with_nasa.h5"
)


def decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")

    if isinstance(value, np.generic):
        return decode(value.item())

    return value


def read_event(h5, event_id):
    events = h5["events"]

    ids = [
        decode(v)
        for v in events["event_id"][()]
    ]

    if event_id not in ids:
        raise ValueError(
            f"Unknown event: {event_id}"
        )

    index = ids.index(event_id)

    return {
        key: decode(events[key][index])
        for key in events.keys()
    }


def event_dates(event):
    return pd.date_range(
        start=event["begin_date"],
        end=event["end_date"],
        freq="D",
    ).strftime("%Y%m%d").tolist()


def read_daymet(h5, date):
    path = f"daymet/{date}"

    if path not in h5:
        return None

    group = h5[path]

    data = group["precipitation"][()]

    valid = data[np.isfinite(data)]

    return {
        "date": date,
        "shape": list(data.shape),
        "valid_cells": int(len(valid)),
        "missing_cells": int(data.size - len(valid)),
        "minimum_mm_day": (
            float(valid.min()) if valid.size else None
        ),
        "maximum_mm_day": (
            float(valid.max()) if valid.size else None
        ),
        "mean_mm_day": (
            float(valid.mean()) if valid.size else None
        ),
    }


def read_usgs(h5, event_id, site_no):
    path = f"usgs/{event_id}/{site_no}"

    if path not in h5:
        return None

    group = h5[path]

    values = group["gage_height_ft"][()]
    mask = group["within_event"][()].astype(bool)

    valid = values[np.isfinite(values)]
    during = values[mask & np.isfinite(values)]

    result = {
        "station_id": site_no,
        "total_readings": int(len(values)),
        "event_readings": int(mask.sum()),
        "minimum_ft": (
            float(valid.min()) if valid.size else None
        ),
        "maximum_ft": (
            float(valid.max()) if valid.size else None
        ),
        "event_minimum_ft": (
            float(during.min()) if during.size else None
        ),
        "event_maximum_ft": (
            float(during.max()) if during.size else None
        ),
    }

    metadata_path = f"metadata/usgs_stations/{site_no}"

    if metadata_path in h5:
        station = h5[metadata_path]
        result["station_name"] = decode(
            station.attrs["station_nm"]
        )
        result["latitude"] = float(
            station.attrs["dec_lat_va"]
        )
        result["longitude"] = float(
            station.attrs["dec_long_va"]
        )
        result["horizontal_datum"] = decode(
            station.attrs["coord_datum_cd"]
        )

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--event",
        default="event_125",
    )

    parser.add_argument(
        "--site",
        default=None,
    )

    args = parser.parse_args()

    with h5py.File(H5_PATH, "r") as h5:
        event = read_event(h5, args.event)

        print("\nEVENT")
        print(json.dumps(event, indent=2, default=str))

        print("\nDAYMET")
        for date in event_dates(event):
            result = read_daymet(h5, date)
            print(
                json.dumps(result, indent=2)
                if result is not None
                else f"Missing Daymet date: {date}"
            )

        print("\nUSGS")

        event_path = f"usgs/{args.event}"

        if event_path not in h5:
            print("No USGS records for this event.")
            return

        sites = (
            [args.site] if args.site
            else list(h5[event_path].keys())
        )

        for site in sites:
            result = read_usgs(
                h5,
                args.event,
                site,
            )

            print(
                json.dumps(result, indent=2)
                if result is not None
                else f"No records for station {site}"
            )


if __name__ == "__main__":
    main()
