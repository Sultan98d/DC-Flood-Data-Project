
from pathlib import Path
from datetime import datetime, timezone
import json

import h5py
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = PROCESSED / "dc_flood_dataset.h5"

EVENTS = PROCESSED / "validated_events.csv"
DAYMET_DIR = PROCESSED / "daymet_rasters"
USGS_DIR = PROCESSED / "usgs_water_levels"

UTF8 = h5py.string_dtype(encoding="utf-8")


def add_string(group, name, values):
    group.create_dataset(
        name,
        data=np.asarray(
            [str(v) if pd.notna(v) else "" for v in values],
            dtype=object,
        ),
        dtype=UTF8,
        compression="gzip",
    )


def add_attributes(obj, attributes):
    for key, value in attributes.items():
        if value is not None:
            obj.attrs[key] = value


def main():
    if not EVENTS.exists():
        raise FileNotFoundError(EVENTS)

    events = pd.read_csv(EVENTS, dtype=str).fillna("")

    if len(events) != 125:
        raise ValueError(
            f"Expected 125 events, found {len(events)}"
        )

    if events["event_id"].duplicated().any():
        raise ValueError("Duplicate event IDs")

    daymet_files = sorted(
        DAYMET_DIR.glob("daymet_prcp_*.npz")
    )
    usgs_files = sorted(
        USGS_DIR.glob("event_*.csv")
    )

    if len(daymet_files) != 149:
        raise ValueError(
            f"Expected 149 Daymet rasters, found {len(daymet_files)}"
        )

    if len(usgs_files) != 445:
        raise ValueError(
            f"Expected 445 USGS files, found {len(usgs_files)}"
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    print("\nBUILDING DC FLOOD HDF5")
    print("-" * 55)

    with h5py.File(OUTPUT, "w") as h5:

        # ====================================================
        # ROOT METADATA
        # ====================================================

        add_attributes(h5, {
            "title": "DC Flood Environmental Dataset",
            "created_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "format_version": "1.0",
            "event_count": len(events),
            "daymet_raster_count": len(daymet_files),
            "usgs_station_event_count": len(usgs_files),
            "event_original_timezone": (
                "Fixed EST (UTC-05:00), without DST"
            ),
            "event_time_standard": "UTC",
            "description": (
                "Flood event metadata, NASA Daymet daily "
                "precipitation, and USGS instantaneous "
                "gage-height observations."
            ),
        })

        # ====================================================
        # EVENTS
        # ====================================================

        event_group = h5.create_group("events")

        for column in events.columns:
            add_string(
                event_group,
                column,
                events[column].tolist(),
            )

        print("Events stored:", len(events))

        # ====================================================
        # DAYMET
        # ====================================================

        daymet_group = h5.create_group("daymet")

        add_attributes(daymet_group, {
            "source": "NASA ORNL DAAC Daymet V4 R1",
            "doi": "10.3334/ORNLDAAC/2129",
            "variable": "prcp",
            "unit": "mm/day",
            "spatial_resolution": "approximately 1 km",
            "spatial_scope": (
                "DC-area rectangular tile; "
                "not clipped to DC jurisdiction"
            ),
            "temporal_resolution": "daily",
        })

        for index, path in enumerate(daymet_files, 1):

            date_key = path.stem.replace(
                "daymet_prcp_", ""
            )

            with np.load(path, allow_pickle=False) as npz:

                raster_group = daymet_group.create_group(
                    date_key
                )

                for key in npz.files:
                    arr = np.asarray(npz[key])

                    if arr.dtype.kind in "OUS":
                        # Store text arrays as UTF-8.
                        flat = [
                            str(v) for v in arr.reshape(-1)
                        ]
                        data = np.asarray(
                            flat, dtype=object
                        ).reshape(arr.shape)

                        raster_group.create_dataset(
                            key,
                            data=data,
                            dtype=UTF8,
                        )
                    else:
                        raster_group.create_dataset(
                            key,
                            data=arr,
                            compression="gzip"
                            if arr.ndim > 0 else None,
                        )

            if index % 25 == 0 or index == len(daymet_files):
                print(
                    f"Daymet rasters: {index}/{len(daymet_files)}"
                )

        # ====================================================
        # USGS
        # ====================================================

        usgs_group = h5.create_group("usgs")

        add_attributes(usgs_group, {
            "source": "USGS NWIS Instantaneous Values",
            "parameter_code": "00065",
            "variable": "Gage height",
            "unit": "ft",
            "timestamp_timezone": "UTC",
            "context_hours": 12,
            "quality_note": (
                "Original qualifiers retained. "
                "Negative gage heights are not "
                "automatically removed."
            ),
        })

        stations = set()
        events_with_usgs = set()
        total_readings = 0
        event_readings = 0

        for index, path in enumerate(usgs_files, 1):

            metadata_path = path.with_suffix(".json")

            if not metadata_path.exists():
                raise FileNotFoundError(metadata_path)

            with open(
                metadata_path,
                "r",
                encoding="utf-8",
            ) as f:
                metadata = json.load(f)

            event_id = metadata["event_id"]
            site_no = str(metadata["site_no"])

            if event_id not in set(events["event_id"]):
                raise ValueError(
                    f"Unknown event ID: {event_id}"
                )

            stations.add(site_no)
            events_with_usgs.add(event_id)

            frame = pd.read_csv(path)

            group = usgs_group.require_group(
                event_id
            ).create_group(site_no)

            for field in [
                "timestamp_utc",
                "qualifiers",
            ]:
                add_string(
                    group,
                    field,
                    frame[field].fillna("").tolist(),
                )

            group.create_dataset(
                "gage_height_ft",
                data=frame[
                    "gage_height_ft"
                ].to_numpy(dtype=np.float64),
                compression="gzip",
            )

            group.create_dataset(
                "series_index",
                data=frame[
                    "series_index"
                ].to_numpy(dtype=np.int32),
                compression="gzip",
            )

            flags = (
                frame["within_event"]
                .astype(str)
                .str.lower()
                .map({"true": True, "false": False})
            )

            if flags.isna().any():
                raise ValueError(
                    f"Invalid within_event flags: {path.name}"
                )

            group.create_dataset(
                "within_event",
                data=flags.to_numpy(dtype=np.bool_),
                compression="gzip",
            )

            group.attrs["metadata_json"] = json.dumps(
                metadata,
                ensure_ascii=False,
            )

            group.attrs["event_id"] = event_id
            group.attrs["site_no"] = site_no
            group.attrs["unit"] = "ft"

            total_readings += len(frame)
            event_readings += int(flags.sum())

            if index % 50 == 0 or index == len(usgs_files):
                print(
                    f"USGS files: {index}/{len(usgs_files)}"
                )

        # ====================================================
        # SUMMARY
        # ====================================================

        summary = h5.create_group("metadata")

        add_attributes(summary, {
            "total_events": len(events),
            "events_with_usgs": len(events_with_usgs),
            "events_without_usgs": (
                len(events) - len(events_with_usgs)
            ),
            "daymet_dates": len(daymet_files),
            "usgs_stations": len(stations),
            "usgs_station_event_files": len(usgs_files),
            "usgs_total_readings": total_readings,
            "usgs_event_readings": event_readings,
        })

    print("\nHDF5 BUILD SUMMARY")
    print("-" * 55)
    print("Events:", len(events))
    print("Daymet rasters:", len(daymet_files))
    print("USGS stations:", len(stations))
    print("USGS station-event files:", len(usgs_files))
    print("Events with USGS:", len(events_with_usgs))
    print(
        "Events without USGS:",
        len(events) - len(events_with_usgs),
    )
    print("Total USGS readings:", total_readings)
    print("USGS readings during events:", event_readings)
    print(
        "HDF5 size (MB):",
        round(OUTPUT.stat().st_size / (1024 ** 2), 2),
    )
    print("Output:", OUTPUT)


if __name__ == "__main__":
    main()
