
from pathlib import Path
import json
import re
import shutil

import h5py
import numpy as np
import rasterio
import matplotlib.pyplot as plt

from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from rasterio.windows import from_bounds, bounds as window_bounds
from rasterio.windows import transform as window_transform
from rasterio.warp import transform_bounds


# ============================================================
# 1. PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SOURCE_H5 = (
    ROOT / "data" / "processed" / "dc_flood_dataset_final.h5"
)

OUTPUT_H5 = (
    ROOT / "data" / "processed" / "dc_flood_dataset_with_nasa.h5"
)

NASA_FOLDER = ROOT / "data" / "raw" / "nasa_flood_extent"

FIGURE_PATH = (
    ROOT / "outputs" / "figures"
    / "nasa_flood_event_125_comparison.png"
)

REPORT_PATH = (
    ROOT / "outputs" / "reports"
    / "nasa_flood_extent_report.md"
)

EVENT_ID = "event_125"

# Washington, DC-area rectangular bounding box.
# Order: west, south, east, north.
BBOX_WGS84 = (-77.15, 38.75, -76.85, 39.00)

EXPECTED_DATES = ["20250718", "20250721"]

CLASS_LABELS = {
    0: "Not water",
    1: "Open water",
    2: "Partial surface water",
    252: "Snow/ice",
    253: "Cloud/cloud shadow",
    254: "Ocean masked",
    255: "No data",
}

CLASS_COLORS = [
    "#eeeeee",
    "#1464a0",
    "#74b9ff",
    "#bcbcbc",
    "#888888",
    "#d8c8a0",
    "#ffffff",
]

CLASS_CODES = np.array(sorted(CLASS_LABELS))


# ============================================================
# 2. EXTRACT ACQUISITION DATE
# ============================================================

def extract_date(filename):
    """
    Extract YYYYMMDD from the OPERA acquisition timestamp.

    Example:
    OPERA_L3_DSWx-HLS_T18SUJ_20250718T154819Z_..._B01_WTR.tif
    """

    match = re.search(r"_(20\d{6})T\d{6}Z_", filename)

    if match is None:
        raise ValueError(
            f"Cannot extract acquisition date from: {filename}"
        )

    return match.group(1)


# ============================================================
# 3. READ AND CROP NASA RASTERS
# ============================================================

def load_nasa_rasters():
    files = sorted(NASA_FOLDER.glob("*_B01_WTR.tif"))

    print("NASA FILES FOUND:", len(files))

    if len(files) != 2:
        raise RuntimeError(
            "Expected exactly two NASA B01_WTR GeoTIFF files."
        )

    results = []

    for file in files:
        date = extract_date(file.name)

        print("\nREADING:", file.name)
        print("ACQUISITION DATE:", date)

        with rasterio.open(file) as src:

            if src.crs is None:
                raise RuntimeError(
                    f"Missing coordinate system: {file.name}"
                )

            # Convert the DC geographic bounding box
            # into the raster's projected coordinate system.
            projected_bounds = transform_bounds(
                "EPSG:4326",
                src.crs,
                *BBOX_WGS84,
                densify_pts=21,
            )

            left = max(projected_bounds[0], src.bounds.left)
            bottom = max(projected_bounds[1], src.bounds.bottom)
            right = min(projected_bounds[2], src.bounds.right)
            top = min(projected_bounds[3], src.bounds.top)

            if left >= right or bottom >= top:
                raise RuntimeError(
                    f"Raster does not overlap the DC area: {file.name}"
                )

            window = from_bounds(
                left,
                bottom,
                right,
                top,
                transform=src.transform,
            )

            window = window.round_offsets().round_lengths()

            # Read original classification values.
            data = src.read(1, window=window)

            if data.size == 0:
                raise RuntimeError(
                    f"Empty raster after cropping: {file.name}"
                )

            transform = window_transform(
                window,
                src.transform,
            )

            cropped_bounds = window_bounds(
                window,
                src.transform,
            )

            classes, counts = np.unique(
                data,
                return_counts=True,
            )

            class_counts = {
                str(int(code)): int(count)
                for code, count in zip(classes, counts)
            }

            unknown_classes = set(
                int(code) for code in classes
            ) - set(CLASS_LABELS)

            if unknown_classes:
                raise RuntimeError(
                    f"Unexpected classification codes: "
                    f"{unknown_classes}"
                )

            results.append({
                "date": date,
                "data": data,
                "crs": src.crs.to_string(),
                "transform": tuple(transform)[:6],
                "bounds": tuple(cropped_bounds),
                "source_filename": file.name,
                "class_counts": class_counts,
                "resolution": tuple(src.res),
                "nodata": src.nodata,
            })

            print("CROPPED SHAPE:", data.shape)
            print("CRS:", src.crs)
            print("CLASS COUNTS:", class_counts)

    results.sort(key=lambda item: item["date"])

    actual_dates = [item["date"] for item in results]

    if actual_dates != EXPECTED_DATES:
        raise RuntimeError(
            f"Unexpected acquisition dates: {actual_dates}"
        )

    # Both observations must use the same grid for
    # meaningful pixel-by-pixel comparisons.
    first, second = results

    if first["data"].shape != second["data"].shape:
        raise RuntimeError(
            "NASA rasters have different cropped dimensions."
        )

    if first["crs"] != second["crs"]:
        raise RuntimeError(
            "NASA rasters have different coordinate systems."
        )

    if not np.allclose(
        first["transform"],
        second["transform"],
        rtol=0,
        atol=1e-6,
    ):
        raise RuntimeError(
            "NASA rasters are not aligned on the same grid."
        )

    print("\nRASTER VALIDATION: PASSED")

    return results


# ============================================================
# 4. INTEGRATE NASA DATA INTO HDF5
# ============================================================

def create_integrated_hdf5(rasters):

    if not SOURCE_H5.exists():
        raise FileNotFoundError(SOURCE_H5)

    if OUTPUT_H5.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_H5}\n"
            "The existing file was not overwritten."
        )

    OUTPUT_H5.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(SOURCE_H5, OUTPUT_H5)

    try:
        with h5py.File(OUTPUT_H5, "r+") as h5:

            # Preserve all existing project groups.
            for group_name in [
                "events",
                "daymet",
                "usgs",
                "metadata",
            ]:
                if group_name not in h5:
                    raise RuntimeError(
                        f"Missing required HDF5 group: {group_name}"
                    )

            nasa = h5.create_group(
                "nasa_flood_extent"
            )

            nasa.attrs["product"] = (
                "NASA OPERA L3 DSWx-HLS V1"
            )
            nasa.attrs["source"] = "NASA PO.DAAC"
            nasa.attrs["event_id"] = EVENT_ID
            nasa.attrs["sensor"] = "Sentinel-2B"
            nasa.attrs["variable"] = "B01_WTR"
            nasa.attrs["spatial_resolution_m"] = 30
            nasa.attrs["bbox_wgs84"] = BBOX_WGS84

            nasa.attrs["classification_codes_json"] = (
                json.dumps(CLASS_LABELS)
            )

            nasa.attrs["temporal_limitation"] = (
                "Observations acquired July 18 and July 21, "
                "2025, before and after the July 19 event. "
                "Neither observation directly captures "
                "the event."
            )

            nasa.attrs["interpretation_limitation"] = (
                "Detected surface water is not necessarily "
                "floodwater. Cloud and no-data coverage "
                "restrict temporal comparisons."
            )

            for raster in rasters:

                group = nasa.create_group(
                    raster["date"]
                )

                group.create_dataset(
                    "water_class",
                    data=raster["data"],
                    compression="gzip",
                    compression_opts=6,
                    shuffle=True,
                )

                group.attrs["acquisition_date"] = (
                    raster["date"]
                )

                group.attrs["source_filename"] = (
                    raster["source_filename"]
                )

                group.attrs["crs"] = raster["crs"]

                group.attrs["affine_transform"] = (
                    raster["transform"]
                )

                group.attrs["bounds_projected"] = (
                    raster["bounds"]
                )

                group.attrs["resolution"] = (
                    raster["resolution"]
                )

                group.attrs["class_counts_json"] = (
                    json.dumps(
                        raster["class_counts"]
                    )
                )

                if raster["nodata"] is not None:
                    group.attrs["nodata"] = (
                        raster["nodata"]
                    )

    except Exception:
        OUTPUT_H5.unlink(missing_ok=True)
        raise

    print("\nHDF5 INTEGRATION: COMPLETED")
    print("OUTPUT:", OUTPUT_H5)


# ============================================================
# 5. GENERATE COMPARISON FIGURE FROM HDF5
# ============================================================

def create_comparison_figure():

    FIGURE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cmap = ListedColormap(CLASS_COLORS)

    norm = BoundaryNorm(
        np.arange(-0.5, 7.5, 1),
        cmap.N,
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14, 7),
    )

    titles = [
        "July 18, 2025 — Before event",
        "July 21, 2025 — After event",
    ]

    with h5py.File(OUTPUT_H5, "r") as h5:

        for ax, date, title in zip(
            axes,
            EXPECTED_DATES,
            titles,
        ):

            data = h5[
                f"nasa_flood_extent/{date}/water_class"
            ][:]

            mapped = np.searchsorted(
                CLASS_CODES,
                data,
            )

            ax.imshow(
                mapped,
                cmap=cmap,
                norm=norm,
                interpolation="nearest",
            )

            ax.set_title(title)
            ax.set_xlabel("Raster column")
            ax.set_ylabel("Raster row")

    legend_items = [
        Patch(
            facecolor=CLASS_COLORS[i],
            edgecolor="#555555",
            label=f"{code}: {CLASS_LABELS[int(code)]}",
        )
        for i, code in enumerate(CLASS_CODES)
    ]

    fig.legend(
        handles=legend_items,
        loc="lower center",
        ncol=4,
        fontsize=9,
    )

    fig.suptitle(
        "NASA OPERA Surface Water Classification\n"
        "DC Flood Event 125 — July 19, 2025\n"
        "Clouds and missing data limit comparison",
        fontsize=13,
    )

    fig.tight_layout(
        rect=(0, 0.12, 1, 0.89)
    )

    fig.savefig(
        FIGURE_PATH,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    print("FIGURE CREATED:", FIGURE_PATH)


# ============================================================
# 6. WRITE NASA INVESTIGATION REPORT
# ============================================================

def write_report(rasters):

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lines = [
        "# NASA OPERA Flood Extent Investigation",
        "",
        "## Dataset",
        "",
        "- Provider: NASA PO.DAAC.",
        "- Product: OPERA L3 DSWx-HLS V1.",
        "- Variable: B01_WTR surface water classification.",
        "- Satellite: Sentinel-2B.",
        "- Spatial resolution: 30 meters.",
        "- Coordinate system: EPSG:32618.",
        "",
        "## Event",
        "",
        "- Event ID: event_125.",
        "- Event date: July 19, 2025.",
        "- Before-event observation: July 18, 2025.",
        "- After-event observation: July 21, 2025.",
        "",
        "Neither observation was acquired during the",
        "July 19 flood event.",
        "",
        "## Spatial processing",
        "",
        f"- Geographic search bounds: {BBOX_WGS84}.",
        "- Original raster classification values preserved.",
        "- Raster cropped to the selected DC-area rectangle.",
        "- The crop is not a DC jurisdiction boundary mask.",
        "- Missing pixels were not interpolated.",
        "",
        "## Classification codes",
        "",
    ]

    for code, label in CLASS_LABELS.items():
        lines.append(
            f"- `{code}`: {label}."
        )

    lines.extend([
        "",
        "## Observed class counts",
        "",
    ])

    for raster in rasters:

        total = raster["data"].size

        cloud = raster["class_counts"].get(
            "253", 0
        )

        missing = raster["class_counts"].get(
            "255", 0
        )

        unavailable_pct = (
            100 * (cloud + missing) / total
        )

        lines.extend([
            f"### {raster['date']}",
            "",
            f"- Source file: `{raster['source_filename']}`.",
            f"- Raster shape: {raster['data'].shape}.",
            f"- Total pixels: {total:,}.",
            f"- Cloud/cloud-shadow pixels: {cloud:,}.",
            f"- No-data pixels: {missing:,}.",
            (
                "- Cloud plus no-data percentage: "
                f"{unavailable_pct:.2f}%."
            ),
            (
                "- Class counts: "
                f"`{json.dumps(raster['class_counts'])}`."
            ),
            "",
        ])

    lines.extend([
        "## HDF5 integration",
        "",
        "The integrated database preserves the original",
        "event, Daymet, USGS, and metadata groups.",
        "",
        "The new `/nasa_flood_extent` group contains:",
        "",
        "- Two compressed classification rasters.",
        "- Observation dates.",
        "- Source filenames.",
        "- Coordinate reference system.",
        "- Affine transforms and projected bounds.",
        "- Pixel resolution.",
        "- Original class counts.",
        "",
        "## Scientific limitations",
        "",
        "1. These are before- and after-event observations,",
        "   not measurements acquired during the event.",
        "2. Surface water is not necessarily floodwater.",
        "3. Clouds and missing observations substantially",
        "   restrict valid temporal comparisons.",
        "4. A difference in classified water area cannot",
        "   automatically be interpreted as flood expansion",
        "   or recession.",
        "5. No missing values were fabricated or interpolated.",
        "",
        "## Output files",
        "",
        "- `data/processed/dc_flood_dataset_with_nasa.h5`",
        "- `outputs/figures/nasa_flood_event_125_comparison.png`",
        "- `outputs/reports/nasa_flood_extent_report.md`",
    ])

    REPORT_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("REPORT CREATED:", REPORT_PATH)


# ============================================================
# 7. FINAL VERIFICATION
# ============================================================

def verify_results():

    with h5py.File(OUTPUT_H5, "r") as h5:

        required_groups = [
            "events",
            "daymet",
            "usgs",
            "metadata",
            "nasa_flood_extent",
        ]

        for name in required_groups:
            assert name in h5, (
                f"Missing HDF5 group: {name}"
            )

        for date in EXPECTED_DATES:

            path = (
                f"nasa_flood_extent/"
                f"{date}/water_class"
            )

            assert path in h5, (
                f"Missing dataset: {path}"
            )

            dataset = h5[path]

            assert dataset.ndim == 2
            assert dataset.compression == "gzip"

    assert FIGURE_PATH.exists()
    assert REPORT_PATH.exists()

    print("\nFINAL VERIFICATION: PASSED")


# ============================================================
# 8. MAIN
# ============================================================

def main():

    print("=" * 55)
    print("NASA OPERA FLOOD EXTENT INTEGRATION")
    print("=" * 55)

    rasters = load_nasa_rasters()

    create_integrated_hdf5(rasters)

    create_comparison_figure()

    write_report(rasters)

    verify_results()

    print("\n" + "=" * 55)
    print("NASA INTEGRATION COMPLETED SUCCESSFULLY")
    print("=" * 55)

    print("HDF5:", OUTPUT_H5)
    print("FIGURE:", FIGURE_PATH)
    print("REPORT:", REPORT_PATH)
    print("SCENES:", EXPECTED_DATES)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
