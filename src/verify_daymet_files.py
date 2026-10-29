
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = (
    ROOT / "data" / "processed" / "daymet_rasters"
)

dates = ["19960119", "19960120"]

print("\nDAYMET SAVED FILE VERIFICATION")
print("-" * 50)

for date in dates:
    file_path = DATA_DIR / f"daymet_prcp_{date}.npz"

    if not file_path.exists():
        raise FileNotFoundError(file_path)

    with np.load(file_path, allow_pickle=False) as data:
        precipitation = data["precipitation"]
        x = data["x"]
        y = data["y"]
        lat = data["lat"]
        lon = data["lon"]

        metadata = json.loads(
            data["metadata_json"].item()
        )

        print(f"\nFILE: {file_path.name}")
        print("Raster shape:", precipitation.shape)
        print("Latitude shape:", lat.shape)
        print("Longitude shape:", lon.shape)
        print("X coordinates:", x.shape)
        print("Y coordinates:", y.shape)

        print("Valid cells:", int(np.isfinite(precipitation).sum()))
        print("Missing cells:", int(np.isnan(precipitation).sum()))

        valid = precipitation[np.isfinite(precipitation)]

        if valid.size:
            print("Minimum:", float(valid.min()))
            print("Maximum:", float(valid.max()))
            print("Mean:", float(valid.mean()))

        print("Date:", metadata["date"])
        print("Units:", metadata["units"])
        print("DOI:", metadata["doi"])

        assert precipitation.shape == lat.shape == lon.shape
        assert precipitation.shape == (len(y), len(x))
        assert metadata["date"].replace("-", "") == date
        assert int(np.isfinite(precipitation).sum()) == metadata["valid_cells"]
        assert int(np.isnan(precipitation).sum()) == metadata["missing_cells"]

        print("Verification: PASSED")

print("\nALL FILE CHECKS PASSED")
