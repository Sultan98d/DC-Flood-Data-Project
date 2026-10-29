
from pathlib import Path
import argparse
import json

import h5py
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HDF5_FILE = (
    ROOT / "data" / "processed" / "dc_flood_dataset_with_nasa.h5"
)


def read_events(h5):
    """Read all flood events as a DataFrame."""
    group = h5["events"]

    data = {
        column: group[column].asstr()[:]
        for column in group.keys()
    }

    return pd.DataFrame(data)


def read_daymet(h5, date_key):
    """Read a Daymet raster and its stored arrays."""
    path = f"daymet/{date_key}"

    if path not in h5:
        raise KeyError(
            f"Daymet date not found: {date_key}"
        )

    group = h5[path]

    result = {}

    for name, dataset in group.items():
        if h5py.check_string_dtype(dataset.dtype):
            result[name] = dataset.asstr()[()]
        else:
            result[name] = dataset[()]

    return result


def read_usgs(h5, event_id, site_no):
    """Read a USGS station-event time series."""
    path = f"usgs/{event_id}/{site_no}"

    if path not in h5:
        raise KeyError(
            f"USGS data not found: {event_id}, {site_no}"
        )

    group = h5[path]

    df = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(
            group["timestamp_utc"].asstr()[:],
            utc=True,
        ),
        "gage_height_ft": group["gage_height_ft"][:],
        "qualifiers": group["qualifiers"].asstr()[:],
        "series_index": group["series_index"][:],
        "within_event": group["within_event"][:],
    })

    metadata = json.loads(
        group.attrs["metadata_json"]
    )

    return df, metadata


def show_summary(h5):
    """Display dataset-level metadata."""
    summary = h5["metadata"].attrs

    print("\nDC FLOOD HDF5 DATASET")
    print("-" * 55)

    for key in sorted(summary.keys()):
        print(f"{key}: {summary[key]}")

    print("\nAvailable top-level groups:")
    for name in h5.keys():
        print(" -", name)


def main():
    parser = argparse.ArgumentParser(
        description="Read the DC Flood HDF5 dataset."
    )

    parser.add_argument(
        "--event",
        type=str,
        default=None,
        help="Flood event ID, e.g. event_125",
    )

    parser.add_argument(
        "--site",
        type=str,
        default=None,
        help="USGS site number, e.g. 01651760",
    )

    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Daymet date in YYYYMMDD format",
    )

    args = parser.parse_args()

    if not HDF5_FILE.exists():
        raise FileNotFoundError(HDF5_FILE)

    with h5py.File(HDF5_FILE, "r") as h5:

        show_summary(h5)

        events = read_events(h5)

        print("\nEVENTS PREVIEW")
        print("-" * 55)

        preview_columns = [
            "event_id",
            "start_utc",
            "end_utc",
            "duration_hours",
        ]

        print(
            events[preview_columns]
            .head(5)
            .to_string(index=False)
        )

        if args.event:
            match = events[
                events["event_id"] == args.event
            ]

            if match.empty:
                raise ValueError(
                    f"Unknown event: {args.event}"
                )

            print("\nSELECTED EVENT")
            print("-" * 55)
            print(match.to_string(index=False))

            if args.event in h5["usgs"]:
                stations = sorted(
                    h5["usgs"][args.event].keys()
                )

                print(
                    "\nAvailable USGS stations:",
                    ", ".join(stations),
                )
            else:
                print(
                    "\nNo USGS measurements for this event."
                )

        if args.date:
            raster = read_daymet(h5, args.date)

            print("\nDAYMET RASTER")
            print("-" * 55)

            print("Date:", args.date)

            for name, arr in raster.items():
                arr = np.asarray(arr)
                print(
                    f"{name}: shape={arr.shape}, "
                    f"dtype={arr.dtype}"
                )

                if (
                    np.issubdtype(arr.dtype, np.number)
                    and arr.size > 0
                    and np.isfinite(arr).any()
                ):
                    print(
                        "  min:",
                        float(np.nanmin(arr)),
                        "max:",
                        float(np.nanmax(arr)),
                    )

        if args.site and not args.event:
            parser.error(
                "--site requires --event"
            )

        if args.event and args.site:
            df, metadata = read_usgs(
                h5,
                args.event,
                args.site,
            )

            print("\nUSGS WATER LEVELS")
            print("-" * 55)

            print("Event:", args.event)
            print("Station:", args.site)
            print("Readings:", len(df))
            print(
                "Readings during event:",
                int(df["within_event"].sum()),
            )

            print(
                "Minimum gage height (ft):",
                df["gage_height_ft"].min(),
            )

            print(
                "Maximum gage height (ft):",
                df["gage_height_ft"].max(),
            )

            print("\nFirst five measurements:")
            print(df.head(5).to_string(index=False))

            print("\nSource:")
            print(metadata.get("source_url", ""))


if __name__ == "__main__":
    main()
