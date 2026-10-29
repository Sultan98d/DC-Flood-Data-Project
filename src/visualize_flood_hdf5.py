
from pathlib import Path
import argparse
import json

import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

HDF5_FILE = (
    ROOT / "data" / "processed" / "dc_flood_dataset_with_nasa.h5"
)

OUTPUT_DIR = ROOT / "outputs" / "figures"


# ============================================================
# READ EVENT
# ============================================================

def read_event(h5, event_id):

    event_ids = h5["events"]["event_id"].asstr()[:]

    matches = np.where(event_ids == event_id)[0]

    if len(matches) != 1:
        raise ValueError(
            f"Event not found or duplicated: {event_id}"
        )

    index = int(matches[0])

    start = pd.to_datetime(
        h5["events"]["start_utc"].asstr()[index],
        utc=True,
    )

    end = pd.to_datetime(
        h5["events"]["end_utc"].asstr()[index],
        utc=True,
    )

    return start, end


# ============================================================
# READ DAYMET
# ============================================================

def read_daymet(h5, date_key):

    path = f"daymet/{date_key}"

    if path not in h5:
        raise ValueError(
            f"Daymet raster not available: {date_key}"
        )

    group = h5[path]

    precipitation = group["precipitation"][:]
    latitude = group["lat"][:]
    longitude = group["lon"][:]

    metadata = {}

    if "metadata_json" in group:
        raw = group["metadata_json"].asstr()[()]
        metadata = json.loads(raw)

    return precipitation, latitude, longitude, metadata


# ============================================================
# READ USGS
# ============================================================

def read_usgs(h5, event_id, site_no):

    path = f"usgs/{event_id}/{site_no}"

    if path not in h5:
        raise ValueError(
            f"No USGS data for {event_id} / {site_no}"
        )

    group = h5[path]

    df = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(
            group["timestamp_utc"].asstr()[:],
            utc=True,
        ),
        "gage_height_ft": group["gage_height_ft"][:],
        "within_event": group["within_event"][:],
        "qualifiers": group["qualifiers"].asstr()[:],
    })

    return df.sort_values("timestamp_utc")


# ============================================================
# FIGURE 1: FLOOD EVENT TIMELINE
# ============================================================

def plot_event_timeline(start, end, event_id):

    fig, ax = plt.subplots(figsize=(11, 3))

    ax.axvspan(
        start,
        end,
        color="steelblue",
        alpha=0.35,
        label="Flood event",
    )

    ax.axvline(
        start,
        color="navy",
        linestyle="--",
        label="Event start",
    )

    ax.axvline(
        end,
        color="darkred",
        linestyle="--",
        label="Event end",
    )

    ax.set_xlim(
        start - pd.Timedelta(hours=3),
        end + pd.Timedelta(hours=3),
    )

    ax.set_yticks([])

    ax.set_title(
        f"Flood Event Timeline â€” {event_id}"
    )

    ax.set_xlabel("Time (UTC)")

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%m-%d %H:%M",
            tz=mdates.UTC,
        )
    )

    ax.legend(loc="upper right")

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig


# ============================================================
# FIGURE 2: DAYMET PRECIPITATION MAP
# ============================================================

def plot_precipitation(
    precipitation,
    latitude,
    longitude,
    date_key,
):

    fig, ax = plt.subplots(figsize=(9, 7))

    mesh = ax.pcolormesh(
        longitude,
        latitude,
        precipitation,
        shading="auto",
        cmap="Blues",
    )

    colorbar = fig.colorbar(
        mesh,
        ax=ax,
    )

    colorbar.set_label(
        "Daily precipitation (mm/day)"
    )

    ax.set_title(
        f"NASA Daymet Daily Precipitation â€” {date_key}"
    )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    ax.set_aspect("equal", adjustable="box")

    fig.tight_layout()

    return fig


# ============================================================
# FIGURE 3: USGS WATER LEVEL TIME SERIES
# ============================================================

def plot_water_levels(
    df,
    start,
    end,
    event_id,
    site_no,
):

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        df["timestamp_utc"],
        df["gage_height_ft"],
        linewidth=1.6,
        color="darkgreen",
        label="USGS gage height",
    )

    ax.axvspan(
        start,
        end,
        color="orange",
        alpha=0.25,
        label="Flood event",
    )

    ax.axvline(
        start,
        color="darkorange",
        linestyle="--",
        alpha=0.8,
    )

    ax.axvline(
        end,
        color="darkred",
        linestyle="--",
        alpha=0.8,
    )

    ax.set_title(
        f"USGS Water Level â€” {site_no} â€” {event_id}"
    )

    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Gage height (ft)")

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%m-%d %H:%M",
            tz=mdates.UTC,
        )
    )

    ax.grid(alpha=0.25)
    ax.legend()

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Visualize DC flood events using HDF5 data."
        )
    )

    parser.add_argument(
        "--event",
        default="event_125",
    )

    parser.add_argument(
        "--site",
        default="01651760",
    )

    parser.add_argument(
        "--date",
        default=None,
        help=(
            "Daymet date YYYYMMDD. "
            "Defaults to UTC start date."
        ),
    )

    args = parser.parse_args()

    if not HDF5_FILE.exists():
        raise FileNotFoundError(HDF5_FILE)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with h5py.File(HDF5_FILE, "r") as h5:

        start, end = read_event(
            h5,
            args.event,
        )

        # The event dates originate in fixed EST.
        # Convert UTC start back to fixed UTC-05:00
        # to select the corresponding local Daymet date.
        fixed_est_start = (
            start - pd.Timedelta(hours=5)
        )

        date_key = (
            args.date
            if args.date
            else fixed_est_start.strftime("%Y%m%d")
        )

        precipitation, lat, lon, _ = read_daymet(
            h5,
            date_key,
        )

        water_levels = read_usgs(
            h5,
            args.event,
            args.site,
        )

        # Figure 1
        fig1 = plot_event_timeline(
            start,
            end,
            args.event,
        )

        path1 = (
            OUTPUT_DIR
            / f"{args.event}_timeline.png"
        )

        fig1.savefig(
            path1,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig1)

        # Figure 2
        fig2 = plot_precipitation(
            precipitation,
            lat,
            lon,
            date_key,
        )

        path2 = (
            OUTPUT_DIR
            / f"{args.event}_daymet_{date_key}.png"
        )

        fig2.savefig(
            path2,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig2)

        # Figure 3
        fig3 = plot_water_levels(
            water_levels,
            start,
            end,
            args.event,
            args.site,
        )

        path3 = (
            OUTPUT_DIR
            / f"{args.event}_usgs_{args.site}.png"
        )

        fig3.savefig(
            path3,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig3)

    print("\nVISUALIZATION SUMMARY")
    print("-" * 55)
    print("Event:", args.event)
    print("USGS station:", args.site)
    print("Daymet date:", date_key)
    print("Figures created: 3")
    print("\nSaved figures:")
    print(path1)
    print(path2)
    print(path3)


if __name__ == "__main__":
    main()

