# Data Availability and Quality Report

## 1. Scope

This report documents the availability and observed limitations of the datasets
collected for the STAT 6289 DC Flood Data Project, Version 4.

The assigned datasets are NASA Daymet gridded daily precipitation and USGS
water-level observations. The supplied flood-event index contains
125 events.

This report describes the collected dataset, not the complete historical
availability of every observation maintained by the original providers.

## 2. NASA Daymet Precipitation

- Source: NASA Daymet Version 4, daily gridded precipitation (`prcp`).
- Measurement: Daily precipitation amount, in millimeters per day.
- Spatial representation: Approximately 1-km gridded observations covering
  the selected Washington, DC, area.
- Temporal representation: Daily data, not hourly precipitation measurements.
- Event-date checks: 154.
- Successful event-date checks: 154.
- Events with missing required Daymet dates:
  0.

All required event-local dates passed the file-availability check.
This does not establish that every grid cell is valid or that daily
precipitation can be allocated precisely to the hours of a flood event.

Daymet uses its own daily time conventions, which must not be interpreted
as subdaily observation timestamps. Original grid coordinates, spatial
metadata, units, and missing-data conventions should be preserved when
retrieving the raster arrays from the HDF5 database.

## 3. USGS Water-Level Observations

- Source: USGS water-level time series.
- Parameter: `00065`, gauge height.
- Measurement units: Feet.
- Timestamp representation: UTC.
- Selected monitoring stations: 6.
- Flood events: 125.
- Station-event combinations: 750.
- Station-event files retrieved: 445.
- Station-event combinations with in-event readings:
  443.
- Events with at least one in-event USGS reading:
  113.
- Events without in-event USGS readings:
  12.
- Total in-event USGS readings: 28,759.

### Station-Level Coverage

| USGS Station ID | Files Available | Events With Readings | Events Without Readings | In-Event Readings |
|---|---:|---:|---:|---:|
| 01646500 | 87 | 87 | 38 | 1,655 |
| 01648000 | 87 | 87 | 38 | 1,635 |
| 01651760 | 3 | 3 | 122 | 44 |
| 01651770 | 68 | 67 | 58 | 10,090 |
| 01651800 | 87 | 86 | 39 | 8,771 |
| 01652500 | 113 | 113 | 12 | 6,564 |

The table counts event-specific station observations, not unique
continuous monitoring periods.

### Events Without USGS Readings

The following events have no retrieved USGS readings during the
event window:

event_001, event_002, event_003, event_004, event_005, event_006, event_007, event_008, event_009, event_010, event_011, event_036

The absence of a retrieved file or event-window observation must not
be interpreted as proof that no historical USGS data exist.

## 4. Missingness and Temporal Gaps

Across the 750 possible station-event
combinations:

- 445 have retrieved files.
- 443 have readings inside the event.
- 305
  have no retrieved station-event file.
- 2
  have a retrieved file but no in-event readings.

The detailed station-event coverage file includes observed measurement
intervals, largest gaps, boundary gaps, and coverage status.

A long observed interval does not, by itself, prove that scheduled
measurements are missing. Sampling intervals and operational history
can vary by station and period.

No missing measurements were interpolated or artificially generated.
Missing observations must not be represented as zero precipitation
or zero water level.

## 5. Spatial and Measurement Considerations

Daymet provides gridded precipitation estimates, whereas USGS provides
point-based water-level measurements at monitoring stations.

Daymet precipitation is expressed in millimeters per day. USGS
parameter `00065` is gauge height in feet relative to a local gauge
datum; it is not interchangeable with streamflow or absolute
water-surface elevation.

The project includes DC and nearby monitoring stations. Nearby stations
must not be described as physically inside the District of Columbia
unless their coordinates confirm that location.

Raster grid geometry, coordinate reference information, station
coordinates, and source metadata should be consulted when comparing
observations across sources.

## 6. Temporal Alignment

The original event index records local event dates and times.
Validated event boundaries are stored in UTC for comparison with
USGS observations.

Daymet daily precipitation values must not be interpreted as
measurements taken at the precise event start or end time.
Daily precipitation totals and instantaneous gauge-height
observations have different temporal meanings.

Any cross-source comparison must preserve these distinctions.
No hourly Daymet precipitation values were manufactured.

## 7. Independent DC Precipitation Investigation

A separate precipitation station within Washington, DC, was identified:

- Network: CoCoRaHS.
- Station: DC-DC-14, Washington 5.1 NW.
- Record begins: June 15, 2011.
- Measurement: Daily precipitation, in inches.

Historical observations surrounding `event_058` were documented.

See:
- `outputs/reports/dc_precipitation_investigation.md`
- `outputs/reports/dc_precipitation_station_sample.csv`

This independent station investigation does not replace either
assigned primary dataset.

## 8. Reproducibility and Supporting Files

- `outputs/reports/coverage_audit_summary.json`
- `outputs/reports/flood_event_coverage.csv`
- `outputs/reports/usgs_station_event_coverage.csv`
- `outputs/reports/usgs_station_coverage_summary.csv`
- `outputs/reports/usgs_station_metadata_audit.json`
- USGS station metadata embedded in the final HDF5 file
- `data/processed/dc_flood_dataset_final.h5`

These files provide event-level coverage, station-level coverage,
station metadata, and the integrated HDF5 database.

## 9. Limitations

1. Retrieved data do not necessarily represent all records held by
   NASA or USGS.
2. Some historical flood events have no retrieved USGS observations.
3. Daymet daily precipitation cannot resolve subdaily rainfall timing.
4. Point gauges and gridded precipitation differ in spatial support.
5. Observed gaps do not automatically establish missing scheduled samples.
6. Data availability does not establish measurement accuracy or eliminate
   quality-control concerns.
7. Raster missingness was audited across the 149 collected Daymet files;
   the audit does not establish completeness outside the selected dates or area.

## 10. Conclusion

The collected Daymet files cover all required event-local dates
according to the project coverage checks.

USGS observations are available during 113
of 125 flood events, with
28,759 in-event readings.

The remaining coverage limitations are documented rather than filled
with synthetic observations.

## 11. Additional Spatial, Temporal, and Missingness Audit

### Daymet raster completeness

The 149 collected daily rasters each contain 27 by 24 cells,
for 96,552 stored raster cells in total.

- Valid precipitation cells: 96,403.
- Missing precipitation cells: 149 (approximately 0.1543%).
- Each raster contains one missing cell.
- No negative or infinite precipitation values were detected.
- Grid spacing is approximately 1,000 meters in both directions.
- The stored grid covers a rectangular DC-area buffer and is
  not clipped to the District's administrative boundary.

A missing raster cell is not equivalent to zero precipitation.

### Coordinate reference system

The Daymet grid uses Lambert Conformal Conic coordinates,
with the following parameters stored in the final HDF5:

- Standard parallels: 25 and 60 degrees.
- Central meridian: -100 degrees.
- Latitude of projection origin: 42.5 degrees.
- Datum/ellipsoid: WGS84.
- Coordinate units: meters.

Latitude and longitude arrays are also retained for each raster.
A numerical comparison with stored coordinates was performed
for the 1996-01-19 raster, with differences below 0.0001 degrees.

Some source NPZ metadata records omit the grid-mapping field,
although their coordinate arrays remain available.

### Event and observation time conventions

The source flood-event index contains local dates and times.
The validation pipeline interprets these times using a fixed
UTC-05:00 offset. This is a processing assumption, not a
historical daylight-saving-time conversion.

The resulting UTC event windows are used to select USGS
observations. USGS timestamps are stored in UTC.

Daymet precipitation represents daily accumulated precipitation.
It must not be treated as an instantaneous or hourly observation.
The daily reporting convention and event-local date selection
must be considered when comparing Daymet with USGS readings.

CoCoRaHS precipitation observations are observer-reported daily
accumulations, typically ending at the recorded observation time.
They are not direct measurements of precipitation during the
exact hours of a flood event.

No missing data were filled, interpolated, or converted to zero.
