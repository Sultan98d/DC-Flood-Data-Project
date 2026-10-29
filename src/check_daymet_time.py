
import earthaccess
import xarray as xr
import numpy as np

auth = earthaccess.login(strategy="interactive")

if not auth.authenticated:
    raise RuntimeError("NASA Earthdata authentication failed.")

session = earthaccess.get_requests_https_session()

url = (
    "dap4://opendap.earthdata.nasa.gov/collections/"
    "C2532426483-ORNL_CLOUD/granules/"
    "Daymet_Daily_V4R1.daymet_v4_daily_na_prcp_2019.nc"
)

ds = xr.open_dataset(
    url,
    engine="pydap",
    backend_kwargs={"session": session},
    decode_cf=False,
)

try:
    print("\nDAYMET TIME METADATA")
    print("-" * 45)

    print("Time attributes:", ds["time"].attrs)

    print("\nTime bounds attributes:")
    print(ds["time_bnds"].attrs)

    for day in [0, 188, 304]:
        print(f"\nDay index: {day}")

        print(
            "Day of year:",
            int(ds["yearday"].isel(time=day).values)
        )

        print(
            "Time value:",
            ds["time"].isel(time=day).values
        )

        print(
            "Time bounds:",
            ds["time_bnds"].isel(time=day).values
        )

finally:
    ds.close()
