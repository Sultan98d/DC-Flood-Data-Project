
# DC Flood Data Project

## Project Version 4: Daymet Precipitation and DC Water-Level Gauges

### Overview

This project collects, processes, validates, and organizes historical flood-event data for Washington, DC, and the surrounding area.

The dataset combines three components:

1. Historical flood-event dates and times.
2. NASA Daymet daily gridded precipitation.
3. USGS water-level gauge observations.

The processed information is stored in a structured HDF5 dataset to support efficient retrieval, inspection, and analysis.

## Data Sources

### Flood Events

The input file `data/raw/DC_flood_times.csv` contains 125 flood events spanning January 1996 through July 2025.

The event timestamps are interpreted using a fixed UTC−05:00 offset (EST), without daylight saving time adjustments.

### NASA Daymet

Source: NASA ORNL DAAC, Daymet Version 4 Revision 1.

DOI: https://doi.org/10.3334/ORNLDAAC/2129

- Variable: Daily precipitation (`prcp`)
- Unit: mm/day
- Spatial resolution: Approximately 1 km
- Unique dates extracted: 149
- Spatial extent: Rectangular grid covering the DC study area

The raster tiles are not clipped to the official Washington, DC boundary.

**Important:** Daymet precipitation represents daily totals, not precipitation accumulated exclusively during the flood-event time window.

### USGS Water-Level Gauges

Source: U.S. Geological Survey (USGS), instantaneous water data.

- Parameter code: `00065` (gage height)
- Unit: feet
- Time standard: UTC
- Observation window: Flood-event period with an additional 12 hours before and after each event

Six monitoring stations were included in the data collection. Four are located in Washington, DC, while two are located in nearby Maryland and Virginia.

Data availability varies by station and historical period. Missing observations are preserved as coverage limitations rather than fabricated or interpolated.

## Data Processing

The project includes Python programs for:

- Validating flood-event timestamps.
- Identifying required Daymet dates.
- Downloading and validating Daymet precipitation rasters.
- Discovering and retrieving USGS water-level observations.
- Recording station metadata.
- Building and enriching an HDF5 dataset.
- Verifying dataset integrity.
- Querying and visualizing the processed information.

## Final Dataset

Primary output:

`data/processed/dc_flood_dataset_with_nasa.h5`

The HDF5 structure includes:

```text
/
├── events/
├── daymet/
├── usgs/
└── metadata/
    └── usgs_stations/
```

The dataset contains:

| Component | Quantity |
|---|---:|
| Flood events | 125 |
| Unique Daymet dates | 149 |
| USGS stations | 6 |
| USGS station-event data files | 445 |
| Total USGS observations | 172,074 |
| Observations during events | 28,759 |
| Events with USGS observations | 113 |
| Events without USGS observations | 12 |

## Installation

Python 3.13 was used during development.

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Reading the Dataset

To retrieve information for a flood event:

```powershell
python src/query_flood_hdf5.py --event event_125
```

To retrieve an event and a specific USGS station:

```powershell
python src/query_flood_hdf5.py --event event_125 --site 01651760
```

## Dataset Verification

To verify the enriched HDF5 file against the original:

```powershell
python src/verify_enriched_hdf5.py
```

The previously completed verification reported:

- 712 groups checked
- 3,129 datasets checked
- 0 errors
- Result: PASS

## Data Limitations

1. Daymet precipitation is available at daily temporal resolution, whereas USGS water-level measurements have finer temporal resolution.
2. USGS observation availability is not uniform across all 125 flood events.
3. The Daymet extraction uses a rectangular spatial tile rather than an exact DC administrative-boundary mask.
4. Two of the six USGS stations are outside Washington, DC, and provide nearby regional context.
5. Gage heights are relative to individual station reference datums and should not be directly interpreted as elevations on a common vertical datum.
6. Some provisional USGS measurements require additional quality review.

## Data Provenance

NASA Daymet: https://daymet.ornl.gov/

USGS Water Data: https://waterdata.usgs.gov/

The project retains metadata and validation outputs to document the sources and processing decisions.


## Independent DC Precipitation Station Investigation

An independent investigation identified CoCoRaHS station
**DC-DC-14 (Washington 5.1 NW)**, located within Washington, DC.

- Network: Community Collaborative Rain, Hail and Snow Network (CoCoRaHS)
- Station identifier: DC-DC-14
- Station reporting began: June 15, 2011
- Variable: Observed precipitation
- Unit: inches
- Observation frequency: Primarily daily, with some multiday reports
- Official station page: https://dex.cocorahs.org/stations/DC-DC-14
- Observation records: https://dex.cocorahs.org/stations/DC-DC-14/obs-tables

A historical sample was examined for flood event `event_058`
(October 29-30, 2012). The observations include reported daily
precipitation of 0.92 inches on October 29 and 4.91 inches on
October 30.

These measurements represent accumulation periods ending at
the station's observation times. They must not be interpreted
as rainfall occurring exclusively during the flood-event hours.

The station began reporting after the earliest events in the
project. Reporting gaps, trace precipitation, missing observations,
and multiday totals require separate interpretation.

This investigation is supplementary to the assigned Daymet
and USGS datasets. The six-record historical sample is not
a complete precipitation time series for all flood events.

Detailed documentation:
`outputs/reports/dc_precipitation_investigation.md`

Historical sample:
`outputs/reports/dc_precipitation_station_sample.csv`


## AI Acknowledgment

AI tools were used for coding, translating, formatting, and fixing some technical issues.

## USGS Data Collection and Reproducibility

Run the coverage check before downloading USGS observations:

    python src/check_all_usgs_events.py
    python src/download_usgs_water_levels.py

The first script creates data/processed/usgs_all_event_coverage.csv. Both scripts require internet access.


## Reproducibility: Build the Dataset

Run these commands from the project root after installing
the dependencies in requirements.txt.

### Prepare the event data

    python src/validate_events.py
    python src/prepare_daymet_dates.py

### Retrieve the assigned observations

    python src/download_daymet.py
    python src/check_all_usgs_events.py
    python src/download_usgs_water_levels.py
    python src/fetch_usgs_station_metadata.py

The download stages require internet access and may take time.
USGS coverage assessment must run before USGS downloading.

### Build the HDF5 database

    python src/build_flood_hdf5.py
    python src/verify_flood_hdf5.py
    python src/enrich_flood_hdf5.py
    python src/verify_enriched_hdf5.py
    python src/finalize_flood_hdf5.py
    python src/integrate_nasa_flood.py

The finalization script refuses to overwrite an existing final
HDF5 file. Preserve or move that file before rebuilding.

Final database:
data/processed/dc_flood_dataset_with_nasa.h5

### Query and visualize

    python src/query_flood_hdf5.py --event event_125 --site 01651760
    python src/visualize_flood_hdf5.py --event event_125 --site 01651760
    python src/summarize_hdf5_coverage.py

The visualization script saves figures to outputs/figures/.
The coverage summary reads directly from the final HDF5 file.

### Data quality documentation

See outputs/reports/data_availability_and_quality_report.md
for observation coverage, missing data, spatial and temporal
resolution, coordinate reference information, and limitations.

## NASA OPERA Surface Water Extension

NASA OPERA L3 DSWx-HLS V1 surface-water classification data were
integrated for event_125, dated July 19, 2025.

- Product: OPERA L3 DSWx-HLS V1
- Variable: B01_WTR
- Resolution: 30 meters
- Source CRS: EPSG:32618
- Observation dates: July 18 and July 21, 2025
- HDF5 group: `/nasa_flood_extent`

Both original NASA GeoTIFF files are included:

- `data/raw/nasa_flood_extent/OPERA_L3_DSWx-HLS_T18SUJ_20250718T154819Z_20250724T182902Z_S2B_30_v1.0_B01_WTR.tif`
- `data/raw/nasa_flood_extent/OPERA_L3_DSWx-HLS_T18SUJ_20250721T155819Z_20250725T143009Z_S2B_30_v1.0_B01_WTR.tif`

Neither scene was acquired during the July 19 flood event.
Clouds, missing pixels, and observation timing limit interpretation.

Figure: `outputs/figures/nasa_flood_event_125_comparison.png`

Report: `outputs/reports/nasa_flood_extent_report.md`

## Assignment-Specified Timezone

The instructor-provided event timestamps use fixed Eastern Standard
Time (EST, UTC-05:00), including during summer months.

The project follows this requirement without daylight-saving
adjustments. USGS observation timestamps remain in UTC.

## Final Integrated HDF5

The final database is:

`data/processed/dc_flood_dataset_with_nasa.h5`

It contains five root groups:

- `/events`
- `/daymet`
- `/usgs`
- `/metadata`
- `/nasa_flood_extent`

## Rebuilding the Database

The dataset-building commands are documented in the original
reproducibility section above.

The workflow validates the supplied event CSV, retrieves Daymet
and USGS data, builds the base HDF5, and then integrates the
included NASA GeoTIFF files using `src/integrate_nasa_flood.py`.

## Reusable HDF5 API

The file `src/flood_data_api.py` provides six functions:

1. `list_available_data`
2. `get_raster`
3. `plot_raster`
4. `get_gauge_timeseries`
5. `plot_gauge_timeseries`
6. `summarize_coverage`

These functions read data directly from the HDF5 database.
