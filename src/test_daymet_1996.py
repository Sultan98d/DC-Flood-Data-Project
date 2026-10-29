
import earthaccess
import xarray as xr
import numpy as np

auth = earthaccess.login(strategy="interactive")

if not auth.authenticated:
    raise RuntimeError("NASA Earthdata authentication failed.")

session = earthaccess.get_requests_https_session()

base_url = (
    "dap4://opendap.earthdata.nasa.gov/collections/"
    "C2532426483-ORNL_CLOUD/granules/"
)

datasets = {}

try:
    for year in [1996, 2019]:
        url = (
            base_url
            + f"Daymet_Daily_V4R1.daymet_v4_daily_na_prcp_{year}.nc"
        )

        ds = xr.open_dataset(
            url,
            engine="pydap",
            backend_kwargs={"session": session},
            decode_cf=False,
        )

        datasets[year] = ds

    spatial_data = {}

    for year, ds in datasets.items():
        spatial_data[year] = {}

        for coordinate in ["x", "y", "lat", "lon"]:
            if coordinate in ["x", "y"]:
                values = ds[coordinate].values
            else:
                values = ds[coordinate].isel(
                    y=slice(5092, 5119),
                    x=slice(6432, 6456),
                ).values

            spatial_data[year][coordinate] = values

    print("\nDAYMET GRID CONSISTENCY CHECK")
    print("-" * 45)

    for coordinate in ["x", "y", "lat", "lon"]:
        a = spatial_data[1996][coordinate]
        b = spatial_data[2019][coordinate]

        same = np.array_equal(a, b)

        print(
            f"{coordinate}: "
            f"Shape 1996={a.shape}, "
            f"Shape 2019={b.shape}, "
            f"Identical={same}"
        )

    all_identical = all(
        np.array_equal(
            spatial_data[1996][coordinate],
            spatial_data[2019][coordinate],
        )
        for coordinate in ["x", "y", "lat", "lon"]
    )

    print("\nALL COORDINATES IDENTICAL:", all_identical)

finally:
    for ds in datasets.values():
        ds.close()
