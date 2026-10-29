
import earthaccess
import xarray as xr
import numpy as np

auth = earthaccess.login(strategy="interactive")

if not auth.authenticated:
    raise RuntimeError("NASA Earthdata authentication failed")

url = (
    "dap4://opendap.earthdata.nasa.gov/collections/"
    "C2532426483-ORNL_CLOUD/granules/"
    "Daymet_Daily_V4R1.daymet_v4_daily_na_prcp_2019.nc"
)

session = earthaccess.get_requests_https_session()

ds = xr.open_dataset(
    url,
    engine="pydap",
    backend_kwargs={"session": session},
    decode_cf=False,
)

try:
    day_index = 188

    raster = ds["prcp"].isel(
        time=day_index,
        y=slice(5092, 5119),
        x=slice(6432, 6456),
    ).values

    valid = raster[
        np.isfinite(raster) & (raster != -9999)
    ]

    print("DATE: 2019-07-08")
    print("DAY OF YEAR:", int(ds["yearday"].isel(time=day_index).values))
    print("RASTER SHAPE:", raster.shape)
    print("VALID CELLS:", valid.size)
    print("RAINY CELLS:", int(np.sum(valid > 0)))
    print("MINIMUM:", float(valid.min()) if valid.size else "N/A")
    print("MAXIMUM:", float(valid.max()) if valid.size else "N/A")
    print("MEAN:", float(valid.mean()) if valid.size else "N/A")
    print("UNIQUE VALUES:", np.unique(valid)[:20])

finally:
    ds.close()
