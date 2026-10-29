# Independent Open-Data Investigation: DC Precipitation Station

## Purpose

This investigation addresses the independent open-data requirement of the STAT 6289 DC Flood Data Project, Version 4.

The assigned primary datasets are NASA Daymet gridded precipitation and DC-area water-level gauges. This investigation is separate from those assigned datasets.

## Data Source

- Network: Community Collaborative Rain, Hail and Snow Network (CoCoRaHS)
- Station ID: DC-DC-14
- Station name: Washington 5.1 NW
- State/District: District of Columbia, USA
- Station record begins: June 15, 2011
- Data source: https://dex.cocorahs.org/stations/DC-DC-14
- Historical observation table: https://dex.cocorahs.org/stations/DC-DC-14/obs-tables

## Available Observations

The station provides daily precipitation observations, reported observation times, and related weather information.

The station overview displayed 4,670 daily precipitation observations and approximately 86% coverage through October 19, 2026.

The historical observation table was successfully inspected for January 1 through December 31, 2012, displaying 346 daily precipitation observations and two multi-day precipitation observations.

## Comparison With Flood Events

The supplied project contains 125 flood events between 1996 and 2025.

Of these, 76 events overlap the station's overall operating period. This is a potential temporal overlap, not confirmation that observations exist for every event.

For event_058, October 29-30, 2012, precipitation observations were identified around the flood-event dates.

A six-observation sample is saved in:

outputs/reports/dc_precipitation_station_sample.csv

The October 30, 2012 observation reported 4.91 inches of precipitation at 9:00 AM.

## Measurement Interpretation

CoCoRaHS daily precipitation observations generally represent accumulation over a reporting interval ending at the observation time.

Therefore, the reported amount must not be interpreted automatically as precipitation falling entirely on the observation date or entirely within a flood-event time window.

Precipitation is reported in inches. Trace precipitation, missing observations, and multi-day accumulation records must be distinguished from measured zero precipitation.

## Availability and Limitations

- The station record begins in 2011 and cannot cover flood events before its operation.
- The station overview reports approximately 86% day coverage, indicating missing observation days.
- Individual flood-event observation availability has not yet been exhaustively checked.
- Observations are point measurements, unlike Daymet gridded precipitation.
- Daily station reports do not provide the same temporal resolution as subdaily water-level measurements.
- The six-row CSV is a documented illustrative sample, not a complete station archive.

## Retrieval Method and Reproducibility

The CoCoRaHS Data Explorer station page and historical observation tables were inspected using date-range filters.

Example historical observation URL:

https://dex.cocorahs.org/stations/DC-DC-14/obs-tables?from=2012-10-28&to=2012-11-02

The sample CSV transcribes the six observations displayed for that period. Its values should be checked against the source before further analysis.

## Conclusion

A precipitation observation station physically located in the District of Columbia was identified, and historical precipitation measurements were confirmed for dates surrounding one assigned flood event.

The station is a suitable documented example for the independent open-data investigation. Its observations are not substituted for the assigned Daymet or USGS datasets.

Further event-by-event availability assessment would be necessary before using this station as a comprehensive event-level precipitation dataset.
