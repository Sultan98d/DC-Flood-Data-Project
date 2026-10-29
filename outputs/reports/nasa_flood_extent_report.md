# NASA OPERA Flood Extent Investigation

## Dataset

- Provider: NASA PO.DAAC.
- Product: OPERA L3 DSWx-HLS V1.
- Variable: B01_WTR surface water classification.
- Satellite: Sentinel-2B.
- Spatial resolution: 30 meters.
- Coordinate system: EPSG:32618.

## Event

- Event ID: event_125.
- Event date: July 19, 2025.
- Before-event observation: July 18, 2025.
- After-event observation: July 21, 2025.

Neither observation was acquired during the
July 19 flood event.

## Spatial processing

- Geographic search bounds: (-77.15, 38.75, -76.85, 39.0).
- Original raster classification values preserved.
- Raster cropped to the selected DC-area rectangle.
- The crop is not a DC jurisdiction boundary mask.
- Missing pixels were not interpolated.

## Classification codes

- `0`: Not water.
- `1`: Open water.
- `2`: Partial surface water.
- `252`: Snow/ice.
- `253`: Cloud/cloud shadow.
- `254`: Ocean masked.
- `255`: No data.

## Observed class counts

### 20250718

- Source file: `OPERA_L3_DSWx-HLS_T18SUJ_20250718T154819Z_20250724T182902Z_S2B_30_v1.0_B01_WTR.tif`.
- Raster shape: (944, 888).
- Total pixels: 838,272.
- Cloud/cloud-shadow pixels: 838,272.
- No-data pixels: 0.
- Cloud plus no-data percentage: 100.00%.
- Class counts: `{"253": 838272}`.

### 20250721

- Source file: `OPERA_L3_DSWx-HLS_T18SUJ_20250721T155819Z_20250725T143009Z_S2B_30_v1.0_B01_WTR.tif`.
- Raster shape: (944, 888).
- Total pixels: 838,272.
- Cloud/cloud-shadow pixels: 570,330.
- No-data pixels: 224,736.
- Cloud plus no-data percentage: 94.85%.
- Class counts: `{"0": 36538, "1": 2230, "2": 3983, "252": 455, "253": 570330, "255": 224736}`.

## HDF5 integration

The integrated database preserves the original
event, Daymet, USGS, and metadata groups.

The new `/nasa_flood_extent` group contains:

- Two compressed classification rasters.
- Observation dates.
- Source filenames.
- Coordinate reference system.
- Affine transforms and projected bounds.
- Pixel resolution.
- Original class counts.

## Scientific limitations

1. These are before- and after-event observations,
   not measurements acquired during the event.
2. Surface water is not necessarily floodwater.
3. Clouds and missing observations substantially
   restrict valid temporal comparisons.
4. A difference in classified water area cannot
   automatically be interpreted as flood expansion
   or recession.
5. No missing values were fabricated or interpolated.

## Output files

- `data/processed/dc_flood_dataset_with_nasa.h5`
- `outputs/figures/nasa_flood_event_125_comparison.png`
- `outputs/reports/nasa_flood_extent_report.md`
