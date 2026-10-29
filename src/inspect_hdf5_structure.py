
from pathlib import Path
import h5py
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
H5_PATH = ROOT / "data" / "processed" / "dc_flood_dataset_with_nasa.h5"

MAX_DEPTH = 3
MAX_CHILDREN = 12


def describe_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")[:200]

    if isinstance(value, np.ndarray):
        if value.size <= 5:
            return str(value.tolist())[:200]
        return f"array shape={value.shape}, dtype={value.dtype}"

    return str(value)[:200]


def inspect_group(group, depth=0):
    indent = "  " * depth

    print(f"{indent}[GROUP] {group.name}")

    if group.attrs:
        print(f"{indent}  ATTRIBUTES:")
        for key, value in group.attrs.items():
            print(
                f"{indent}    {key}: "
                f"{describe_value(value)}"
            )

    if depth >= MAX_DEPTH:
        return

    keys = list(group.keys())

    for key in keys[:MAX_CHILDREN]:
        item = group[key]

        if isinstance(item, h5py.Group):
            inspect_group(item, depth + 1)

        elif isinstance(item, h5py.Dataset):
            print(
                f"{indent}  [DATASET] {key} "
                f"shape={item.shape} dtype={item.dtype}"
            )

            for attr, value in item.attrs.items():
                print(
                    f"{indent}    ATTR {attr}: "
                    f"{describe_value(value)}"
                )

    if len(keys) > MAX_CHILDREN:
        print(
            f"{indent}  ... {len(keys) - MAX_CHILDREN} "
            "additional children"
        )


def main():
    if not H5_PATH.exists():
        raise FileNotFoundError(H5_PATH)

    print("\nHDF5 STRUCTURE INSPECTION")
    print("=" * 65)

    print("File:", H5_PATH)
    print(
        "Size MB:",
        round(H5_PATH.stat().st_size / 1024**2, 2)
    )

    with h5py.File(H5_PATH, "r") as h5:
        print("\nROOT GROUPS:")
        print(list(h5.keys()))

        print("\nROOT ATTRIBUTES:")
        for key, value in h5.attrs.items():
            print(f"{key}: {describe_value(value)}")

        print("\nSTRUCTURE:")
        for key in h5.keys():
            inspect_group(h5[key], depth=0)

        print("\nSELECTED METADATA CHECKS")

        for path in [
            "/metadata",
            "/events",
            "/daymet",
            "/usgs",
            "/usgs/event_125/01651760",
            "/daymet/20250719",
        ]:
            if path in h5:
                item = h5[path]
                print(f"\nPATH: {path}")
                if isinstance(item, h5py.Group):
                    print("Children:", list(item.keys())[:30])
                print("Attributes:", list(item.attrs.keys()))
            else:
                print(f"\nMISSING PATH: {path}")

    print("\nINSPECTION COMPLETED - NO FILES MODIFIED")


if __name__ == "__main__":
    main()
