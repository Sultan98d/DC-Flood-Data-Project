
import earthaccess
import xarray as xr
import numpy as np

auth = earthaccess.login(strategy="interactive")

if not auth.authenticated:
    raise RuntimeError("NASA Earthdata authentication failed")

session = earthaccess.get_requests_https_session()

BASE_URL = (
    "dap4://opendap.earthdata.nasa.gov/collections/"
    "C2532426483-ORNL_CLOUD/granules/"
)

Y_SLICE = slice(5092, 5119)
X_SLICE = slice(6432, 6456)


def load_grid(year):
    url = (
        BASE_URL
        + f"Daymet_Daily_V4R1.daymet_v4_daily_na_prcp_{year}.nc"
    )

    ds = xr.open_dataset(
        url,
        engine="pydap",
        backend_kwargs={"session": session},
        decode_cf=False,
    )

    try:
        return {
            "x": ds["x"].isel(x=X_SLICE).values.copy(),
            "y": ds["y"].isel(y=Y_SLICE).values.copy(),
            "lat": ds["lat"].isel(
                y=Y_SLICE, x=X_SLICE
            ).values.copy(),
            "lon": ds["lon"].isel(
                y=Y_SLICE, x=X_SLICE
            ).values.copy(),
        }
    finally:
        ds.close()


grid_1996 = load_grid(1996)
grid_2020 = load_grid(2020)

print("\nDAYMET GRID COMPARISON: 1996 VS 2020")
print("-" * 55)

for key in ["x", "y", "lat", "lon"]:
    a = grid_1996[key]
    b = grid_2020[key]

    print(f"\nCoordinate: {key}")
    print("Shape identical:", a.shape == b.shape)
    print("Exactly identical:", np.array_equal(a, b))

    if a.shape == b.shape:
        difference = np.abs(
            a.astype(np.float64)
            - b.astype(np.float64)
        )

        print("Maximum difference:", float(np.nanmax(difference)))
        print("Mean difference:", float(np.nanmean(difference)))

        print(
            "Close within 0.00001:",
            bool(np.allclose(a, b, rtol=0, atol=1e-5))
        )

        print(
            "Close within 0.001:",
            bool(np.allclose(a, b, rtol=0, atol=1e-3))
        )

print("\nGrid comparison completed.")
