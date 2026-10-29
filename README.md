
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

This project includes NASA OPERA L3 DSWx-HLS V1
surface-water observations for flood event_125
(July 19, 2025).

Two Sentinel-2B B01_WTR classification rasters
were obtained for July 18 and July 21, 2025.

### Dataset properties

- Provider: NASA PO.DAAC.
- Product: OPERA L3 DSWx-HLS V1.
- Variable: B01_WTR.
- Spatial resolution: 30 meters.
- Coordinate reference system: EPSG:32618.
- Observations: July 18 and July 21, 2025.
- HDF5 group: `/nasa_flood_extent`.

### Integrated dataset

The final distributed database is:

`data/processed/dc_flood_dataset_with_nasa.h5`

It contains five root groups:

- `/events`
- `/daymet`
- `/usgs`
- `/metadata`
- `/nasa_flood_extent`

### NASA outputs

Visualization:

`outputs/figures/nasa_flood_event_125_comparison.png`

Investigation report:

`outputs/reports/nasa_flood_extent_report.md`

### Scientific limitations

Neither satellite observation was acquired during
the July 19 flood event.

Detected surface water is not necessarily floodwater.

Clouds, cloud shadows, and missing pixels restrict
comparisons between the two dates.

The observations should not be interpreted as
a direct measurement of flood expansion or recession.

### Rebuilding the NASA extension

The integration script is:

`src/integrate_nasa_flood.py`

Rebuilding the integrated dataset requires:

1. The original `dc_flood_dataset_with_nasa.h5`.
2. Both NASA B01_WTR GeoTIFF source files.

These source inputs are not included in the
GitHub distribution.

The provided integrated HDF5 file can be used
directly without rebuilding the NASA extension.

## Reusable HDF5 Data Access API

The project includes six reusable functions
in `src/flood_data_api.py`:

1. `list_available_data`
2. `get_raster`
3. `plot_raster`
4. `get_gauge_timeseries`
5. `plot_gauge_timeseries`
6. `summarize_coverage`

These functions provide access to Daymet
precipitation rasters and USGS gage-height
observations stored in HDF5.



## Final Dataset and Reproducibility Notes

The authoritative distributed dataset is:

`data/processed/dc_flood_dataset_with_nasa.h5`

It contains event records, NASA Daymet precipitation
rasters, USGS gage-height observations, metadata,
and the NASA OPERA surface-water extension.

The dataset can be opened directly using Python and h5py.

### NASA source observations

NASA OPERA L3 DSWx-HLS V1, B01_WTR,
Sentinel-2B, tile T18SUJ:

- July 18, 2025:
  `OPERA_L3_DSWx-HLS_T18SUJ_20250718T154819Z_20250724T182902Z_S2B_30_v1.0_B01_WTR.tif`
- July 21, 2025:
  `OPERA_L3_DSWx-HLS_T18SUJ_20250721T155819Z_20250725T143009Z_S2B_30_v1.0_B01_WTR.tif`

Source portal: https://search.earthdata.nasa.gov/

The original GeoTIFF inputs and intermediate HDF5
are not distributed in this GitHub package.
The NASA integration script therefore requires
those inputs to be downloaded or reconstructed
before it can be rerun.

The included integrated HDF5 file is ready for
analysis without rerunning data acquisition.

### Timezone interpretation

USGS observation timestamps are stored in UTC.

The flood-event processing uses a fixed UTC-05:00
offset labeled EST. This is not equivalent to
historical Washington, DC civil time during daylight
saving time (EDT, UTC-04:00).

Consequently, event-window alignment may differ
by one hour from actual local civil time in summer.
This is a documented limitation of the analysis.

Daymet precipitation represents daily accumulated
precipitation, not hourly rainfall.

### NASA interpretation

NASA scenes are from July 18 and July 21, 2025.
Neither directly observes the July 19 flood.

Surface-water classification is not definitive
flood extent. Clouds, shadows, and missing pixels
limit before/after comparisons.

### Data access

The six functions in `src/flood_data_api.py` are:

- `list_available_data`
- `get_raster`
- `plot_raster`
- `get_gauge_timeseries`
- `plot_gauge_timeseries`
- `summarize_coverage`

The main distributed HDF5 file is
`dc_flood_dataset_with_nasa.h5`.

## Assignment-specific timezone and NASA source files

### Event timestamps

The instructor-provided `DC_flood_times.csv` uses fixed Eastern
Standard Time (EST, UTC-05:00), including during summer months.
This is an explicit assignment requirement.

The project therefore interprets event timestamps using UTC-05:00
throughout the year. Daylight-saving adjustments must not be applied
to the supplied event timestamps. USGS observations retain their
UTC timestamps for temporal alignment.

### NASA source files

Both original OPERA DSWx-HLS B01_WTR GeoTIFF files are included in:

`data/raw/nasa_flood_extent/`

The scenes are dated July 18 and July 21, 2025. They are integrated
into `data/processed/dc_flood_dataset_with_nasa.h5`.

These scenes are not direct observations during the July 19 flood
event. Cloud cover, no-data areas, and the temporal difference
limit flood interpretation.

### Rebuilding the integrated HDF5

The repository includes the final integrated HDF5 and the original
NASA GeoTIFF inputs. The script `src/integrate_nasa_flood.py`
integrates NASA observations into the original flood HDF5 dataset.

Rebuilding the integrated HDF5 from scratch also requires
regenerating the intermediate flood HDF5 using the project source
scripts and upstream Daymet/USGS data. The complete rebuild has
not been independently tested in a clean environment.

## Final source-file and timezone clarification

### Assignment timezone

The supplied flood-event CSV specifies fixed Eastern Standard Time
(EST, UTC-05:00), including during summer months. This is an explicit
assignment requirement. Event timestamps are interpreted using this
fixed offset throughout the year; daylight-saving adjustments are not
applied. USGS observation timestamps remain in UTC.

### Original NASA inputs

Both original OPERA DSWx-HLS B01_WTR GeoTIFF source files are included:

- `data/raw/nasa_flood_extent/OPERA_L3_DSWx-HLS_T18SUJ_20250718T154819Z_20250724T182902Z_S2B_30_v1.0_B01_WTR.tif`
- `data/raw/nasa_flood_extent/OPERA_L3_DSWx-HLS_T18SUJ_20250721T155819Z_20250725T143009Z_S2B_30_v1.0_B01_WTR.tif`

The scenes represent July 18 and July 21, 2025, not direct observations
during the July 19 event. Cloud and no-data coverage limit interpretation.

### Rebuilding the integrated HDF5

The final integrated HDF5 is included for direct use at:

`data/processed/dc_flood_dataset_with_nasa.h5`

The NASA integration script is `src/integrate_nasa_flood.py`.
Rebuilding it requires the pre-NASA base HDF5 and both GeoTIFF files.
The two GeoTIFF files are included above; the separate pre-NASA base HDF5
must be regenerated through the documented source-data workflow.
A complete rebuild in a clean environment has not yet been verified.
