
from pathlib import Path
import json

import h5py
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

HDF5_FILE = PROCESSED / "dc_flood_dataset.h5"
EVENTS_FILE = PROCESSED / "validated_events.csv"
DAYMET_DIR = PROCESSED / "daymet_rasters"
USGS_DIR = PROCESSED / "usgs_water_levels"


def decode_strings(dataset):
    return dataset.asstr()[:].tolist()


def main():
    checks = []

    def check(name, condition):
        passed = bool(condition)
        checks.append((name, passed))
        print(
            f"{'PASS' if passed else 'FAIL'}: {name}"
        )

    events = pd.read_csv(EVENTS_FILE, dtype=str).fillna("")
    daymet_files = sorted(
        DAYMET_DIR.glob("daymet_prcp_*.npz")
    )
    usgs_files = sorted(
        USGS_DIR.glob("event_*.csv")
    )

    with h5py.File(HDF5_FILE, "r") as h5:

        print("\nHDF5 VERIFICATION")
        print("-" * 55)

        check(
            "Required groups exist",
            all(
                group in h5
                for group in [
                    "events",
                    "daymet",
                    "usgs",
                    "metadata",
                ]
            ),
        )

        check(
            "All 125 events stored",
            len(h5["events"]["event_id"]) == len(events) == 125,
        )

        check(
            "Event IDs match source",
            decode_strings(
                h5["events"]["event_id"]
            ) == events["event_id"].tolist(),
        )

        check(
            "Event UTC times match source",
            decode_strings(
                h5["events"]["start_utc"]
            ) == events["start_utc"].tolist()
            and decode_strings(
                h5["events"]["end_utc"]
            ) == events["end_utc"].tolist(),
        )

        check(
            "149 Daymet dates stored",
            len(h5["daymet"]) == len(daymet_files) == 149,
        )

        daymet_match = True

        for path in daymet_files:
            date_key = path.stem.replace(
                "daymet_prcp_", ""
            )

            if date_key not in h5["daymet"]:
                daymet_match = False
                break

            with np.load(path, allow_pickle=False) as npz:
                stored = h5["daymet"][date_key]

                if set(npz.files) != set(stored.keys()):
                    daymet_match = False
                    break

                for key in npz.files:
                    original = npz[key]
                    saved = stored[key][()]

                    if original.dtype.kind in "OUS":
                        original = original.astype(str)
                        saved = np.asarray(saved).astype(str)
                        equal = np.array_equal(original, saved)
                    else:
                        equal = np.array_equal(
                            original,
                            saved,
                            equal_nan=True,
                        )

                    if not equal:
                        daymet_match = False
                        break

            if not daymet_match:
                break

        check(
            "Daymet arrays match original files",
            daymet_match,
        )

        total_readings = 0
        event_readings = 0
        stored_pairs = 0
        usgs_match = True
        events_with_usgs = set()
        stations = set()

        for path in usgs_files:

            metadata_path = path.with_suffix(".json")

            with open(
                metadata_path,
                "r",
                encoding="utf-8",
            ) as f:
                metadata = json.load(f)

            event_id = metadata["event_id"]
            site_no = str(metadata["site_no"])

            if (
                event_id not in h5["usgs"]
                or site_no not in h5["usgs"][event_id]
            ):
                usgs_match = False
                break

            group = h5["usgs"][event_id][site_no]
            df = pd.read_csv(path)

            original_values = df[
                "gage_height_ft"
            ].to_numpy(dtype=np.float64)

            saved_values = group[
                "gage_height_ft"
            ][:]

            original_times = df[
                "timestamp_utc"
            ].astype(str).tolist()

            saved_times = decode_strings(
                group["timestamp_utc"]
            )

            original_qualifiers = df[
                "qualifiers"
            ].astype(str).tolist()

            saved_qualifiers = decode_strings(
                group["qualifiers"]
            )

            original_series = df[
                "series_index"
            ].to_numpy(dtype=np.int32)

            saved_series = group[
                "series_index"
            ][:]

            original_flags = (
                df["within_event"]
                .astype(str)
                .str.lower()
                .map({"true": True, "false": False})
                .to_numpy(dtype=np.bool_)
            )

            saved_flags = group[
                "within_event"
            ][:]

            equal = (
                np.array_equal(
                    original_values,
                    saved_values,
                    equal_nan=True,
                )
                and original_times == saved_times
                and original_qualifiers == saved_qualifiers
                and np.array_equal(
                    original_series,
                    saved_series,
                )
                and np.array_equal(
                    original_flags,
                    saved_flags,
                )
            )

            if not equal:
                usgs_match = False
                print(
                    "Mismatch found:",
                    path.name,
                )
                break

            total_readings += len(df)
            event_readings += int(
                original_flags.sum()
            )
            stored_pairs += 1

            events_with_usgs.add(event_id)
            stations.add(site_no)

        check(
            "All USGS station-event datasets match",
            usgs_match
            and stored_pairs == len(usgs_files) == 445,
        )

        check(
            "USGS reading counts match",
            total_readings == 172074
            and event_readings == 28759,
        )

        check(
            "USGS coverage matches",
            len(events_with_usgs) == 113
            and len(stations) == 6,
        )

        summary = h5["metadata"].attrs

        check(
            "HDF5 metadata counts match",
            int(summary["total_events"]) == 125
            and int(summary["daymet_dates"]) == 149
            and int(summary["usgs_stations"]) == 6
            and int(summary["usgs_total_readings"]) == 172074
            and int(summary["usgs_event_readings"]) == 28759,
        )

    print("\nFINAL VERIFICATION SUMMARY")
    print("-" * 55)

    passed = sum(result for _, result in checks)

    print("Checks passed:", passed)
    print("Total checks:", len(checks))
    print("Checks failed:", len(checks) - passed)

    if passed == len(checks):
        print("\nALL CHECKS PASSED")
    else:
        print("\nVERIFICATION FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
