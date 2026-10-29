from pathlib import Path
import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HDF5_FILE = ROOT / "data" / "processed" / "dc_flood_dataset_with_nasa.h5"


def summarize_coverage(h5):
    """Summarize event, USGS, and Daymet coverage directly from HDF5."""
    events = h5["events"]["event_id"].asstr()[:]
    dates = sorted(h5["daymet"].keys())

    stations = set()
    events_with_usgs = 0
    event_readings = 0
    missing_pixels = 0
    total_pixels = 0

    for event in events:
        has_readings = False

        if event not in h5["usgs"]:
            continue

        for station, group in h5["usgs"][event].items():
            stations.add(station)

            values = group["gage_height_ft"][:]
            within = group["within_event"][:].astype(bool)

            count = int(np.count_nonzero(
                within & np.isfinite(values)
            ))

            event_readings += count

            if count > 0:
                has_readings = True

        if has_readings:
            events_with_usgs += 1

    for date in dates:
        raster = h5["daymet"][date]["precipitation"][:]
        total_pixels += raster.size
        missing_pixels += int(
            np.count_nonzero(~np.isfinite(raster))
        )

    return {
        "total_events": len(events),
        "daymet_dates": len(dates),
        "usgs_stations": len(stations),
        "events_with_usgs": events_with_usgs,
        "events_without_usgs": len(events) - events_with_usgs,
        "usgs_in_event_readings": event_readings,
        "daymet_total_pixels": total_pixels,
        "daymet_missing_pixels": missing_pixels,
        "daymet_missing_percent": round(
            100 * missing_pixels / total_pixels, 4
        ) if total_pixels else None,
    }


def main():
    with h5py.File(HDF5_FILE, "r") as h5:
        results = summarize_coverage(h5)

    print("\nDC FLOOD DATA COVERAGE SUMMARY")
    print("-" * 45)

    for key, value in results.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
