
from pathlib import Path
import json

import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
H5_PATH = ROOT / "data" / "processed" / "dc_flood_dataset_with_nasa.h5"


def decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.generic):
        return decode(value.item())
    if isinstance(value, np.ndarray):
        return [decode(v) for v in value]
    return value


def attrs_dict(group):
    return {k: decode(v) for k, v in group.attrs.items()}


def event_table(h5):
    """Read the event index directly from HDF5."""
    return pd.DataFrame({
        name: [decode(v) for v in dataset[:]]
        for name, dataset in h5["events"].items()
    })


# 1. List events, sources, variables, stations, dates, metadata.
def list_available_data(h5):
    stations = h5["metadata/usgs_stations"]

    return {
        "events": event_table(h5),
        "sources": {
            "daymet": attrs_dict(h5["daymet"]),
            "usgs": attrs_dict(h5["usgs"]),
        },
        "variables": {
            "daymet": decode(h5["daymet"].attrs["variable"]),
            "usgs": decode(h5["usgs"].attrs["parameter_code"]),
        },
        "dates": sorted(h5["daymet"].keys()),
        "stations": {
            site: attrs_dict(group)
            for site, group in stations.items()
        },
        "metadata": attrs_dict(h5["metadata"]),
    }


# 2. Retrieve raster, coordinates, units, and CRS.
def get_raster(h5, date, event_id=None):
    date_key = str(date).replace("-", "")

    if event_id is not None:
        events = event_table(h5)
        matches = events[events["event_id"] == event_id]

        if matches.empty:
            raise KeyError(f"Unknown event: {event_id}")

        event = matches.iloc[0]
        first = pd.Timestamp(event["begin_date"])
        last = pd.Timestamp(event["end_date"])
        selected = pd.Timestamp(date_key)

        if not first <= selected <= last:
            raise ValueError(
                f"{date_key} is outside {event_id}'s local dates"
            )

    if date_key not in h5["daymet"]:
        raise KeyError(f"Missing Daymet date: {date_key}")

    group = h5["daymet"][date_key]

    return {
        "date": date_key,
        "event_id": event_id,
        "precipitation": group["precipitation"][:],
        "latitude": group["lat"][:],
        "longitude": group["lon"][:],
        "x": group["x"][:],
        "y": group["y"][:],
        "units": decode(h5["daymet"].attrs["unit"]),
        "crs": attrs_dict(h5["daymet"]),
        "metadata": json.loads(decode(group["metadata_json"][()])),
    }


# 3. Visualize the raster directly from HDF5.
def plot_raster(h5, date, event_id=None, ax=None):
    raster = get_raster(h5, date, event_id)

    if ax is None:
        _, ax = plt.subplots(figsize=(9, 6))

    values = np.ma.masked_invalid(raster["precipitation"])

    mesh = ax.pcolormesh(
        raster["longitude"],
        raster["latitude"],
        values,
        shading="auto",
        cmap="Blues",
    )

    ax.figure.colorbar(
        mesh,
        ax=ax,
        label=f"Precipitation ({raster['units']})",
    )

    ax.set_title(
        f"NASA Daymet - {raster['date']}"
        + (f" - {event_id}" if event_id else "")
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    return ax


# 4. Retrieve USGS time series by event, station, and UTC window.
def get_gauge_timeseries(
    h5, event_id, station_id, start=None, end=None
):
    path = f"usgs/{event_id}/{station_id}"

    columns = [
        "timestamp_utc",
        "gage_height_ft",
        "qualifiers",
        "series_index",
        "within_event",
    ]

    if path not in h5:
        return pd.DataFrame(columns=columns)

    group = h5[path]

    data = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(
            [decode(v) for v in group["timestamp_utc"][:]],
            utc=True,
        ),
        "gage_height_ft": group["gage_height_ft"][:],
        "qualifiers": [
            decode(v) for v in group["qualifiers"][:]
        ],
        "series_index": group["series_index"][:],
        "within_event": group["within_event"][:],
    })

    if start is not None:
        data = data[
            data["timestamp_utc"] >= pd.to_datetime(start, utc=True)
        ]

    if end is not None:
        data = data[
            data["timestamp_utc"] <= pd.to_datetime(end, utc=True)
        ]

    return data.sort_values(
        "timestamp_utc"
    ).reset_index(drop=True)


# 5. Visualize USGS time series without filling missing data.
def plot_gauge_timeseries(
    h5, event_id, station_id, start=None, end=None, ax=None
):
    data = get_gauge_timeseries(
        h5, event_id, station_id, start, end
    )

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))

    if data.empty:
        ax.text(
            0.5, 0.5,
            "No observations available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
    else:
        # Show individual observations without inventing values
        # between timestamps.
        ax.scatter(
            data["timestamp_utc"],
            data["gage_height_ft"],
            s=12,
            label="Observed USGS readings",
        )
        ax.legend()

    ax.set_title(f"USGS {station_id} - {event_id}")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Gage height (ft)")
    ax.grid(alpha=0.3)
    ax.figure.autofmt_xdate()

    return ax


# 6. Summarize source availability and missingness per event.
def summarize_coverage(h5):
    events = event_table(h5)
    records = []

    for _, event in events.iterrows():
        event_id = event["event_id"]

        dates = pd.date_range(
            event["begin_date"],
            event["end_date"],
            freq="D",
        ).strftime("%Y%m%d").tolist()

        available_dates = [
            date for date in dates if date in h5["daymet"]
        ]

        missing_pixels = sum(
            int(np.count_nonzero(
                ~np.isfinite(
                    h5["daymet"][date]["precipitation"][:]
                )
            ))
            for date in available_dates
        )

        usgs_readings = 0
        stations_with_readings = 0

        if event_id in h5["usgs"]:
            for station in h5["usgs"][event_id].values():
                count = int(
                    np.count_nonzero(station["within_event"][:])
                )
                usgs_readings += count

                if count > 0:
                    stations_with_readings += 1

        records.append({
            "event_id": event_id,
            "daymet_dates_required": len(dates),
            "daymet_dates_available": len(available_dates),
            "daymet_dates_missing": (
                len(dates) - len(available_dates)
            ),
            "daymet_missing_pixels": missing_pixels,
            "usgs_stations_with_readings": stations_with_readings,
            "usgs_event_readings": usgs_readings,
            "usgs_no_event_readings": usgs_readings == 0,
        })

    return pd.DataFrame(records)


def main():
    if not H5_PATH.exists():
        raise FileNotFoundError(H5_PATH)

    with h5py.File(H5_PATH, "r") as h5:
        inventory = list_available_data(h5)
        coverage = summarize_coverage(h5)

        print("HDF5 ACCESS TEST")
        print("-" * 45)
        print("Events:", len(inventory["events"]))
        print("Daymet dates:", len(inventory["dates"]))
        print("USGS stations:", len(inventory["stations"]))

        raster = get_raster(
            h5, "20250719", event_id="event_125"
        )
        print("Raster shape:", raster["precipitation"].shape)

        series = get_gauge_timeseries(
            h5,
            "event_125",
            "01651760",
            start="2025-07-19T22:00:00Z",
            end="2025-07-19T23:34:00Z",
        )
        print("USGS event-window readings:", len(series))

        print("Coverage events:", len(coverage))
        print(
            "Events without USGS readings:",
            int(coverage["usgs_no_event_readings"].sum()),
        )

        fig, axes = plt.subplots(2, 1, figsize=(10, 10))

        plot_raster(
            h5, "20250719", "event_125", ax=axes[0]
        )

        plot_gauge_timeseries(
            h5, "event_125", "01651760",
            start="2025-07-19T22:00:00Z",
            end="2025-07-19T23:34:00Z",
            ax=axes[1],
        )

        fig.tight_layout()

        output = ROOT / "outputs/figures/event_125_api_demo.png"
        output.parent.mkdir(parents=True, exist_ok=True)

        fig.savefig(output, dpi=150)
        plt.close(fig)

        print("Figure saved:", output)
        print("TEST COMPLETED")


if __name__ == "__main__":
    main()
