
from pathlib import Path
import hashlib
import json

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

ORIGINAL = DATA / "dc_flood_dataset.h5"
ENRICHED = DATA / "dc_flood_dataset_enriched.h5"

REPORT = (
    ROOT / "outputs" / "reports"
    / "enriched_hdf5_verification.json"
)


def normalize(value):
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, np.ndarray):
        return [normalize(v) for v in value.tolist()]

    if isinstance(value, np.generic):
        return normalize(value.item())

    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]

    if isinstance(value, dict):
        return {
            str(k): normalize(v)
            for k, v in value.items()
        }

    return value


def dataset_digest(dataset):
    digest = hashlib.sha256()

    digest.update(str(dataset.shape).encode())
    digest.update(str(dataset.dtype).encode())

    values = dataset[()]

    if dataset.dtype.kind in ("O", "S", "U"):
        normalized = normalize(values)
        payload = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")

        digest.update(payload)
    else:
        array = np.asarray(values)
        digest.update(array.tobytes())

    return digest.hexdigest()


def compare_attributes(original, enriched, path, errors):
    for key, value in original.attrs.items():
        if key not in enriched.attrs:
            errors.append(
                f"{path}: missing attribute {key}"
            )
            continue

        left = normalize(value)
        right = normalize(enriched.attrs[key])

        if left != right:
            errors.append(
                f"{path}: changed attribute {key}"
            )


def compare_objects(original, enriched, path, errors, stats):
    compare_attributes(original, enriched, path, errors)

    if isinstance(original, h5py.Dataset):
        stats["datasets_checked"] += 1

        if not isinstance(enriched, h5py.Dataset):
            errors.append(f"{path}: object type changed")
            return

        if original.shape != enriched.shape:
            errors.append(f"{path}: shape changed")
            return

        if original.dtype != enriched.dtype:
            errors.append(f"{path}: dtype changed")
            return

        if dataset_digest(original) != dataset_digest(enriched):
            errors.append(f"{path}: DATA CHANGED")

        return

    if not isinstance(enriched, h5py.Group):
        errors.append(f"{path}: group type changed")
        return

    stats["groups_checked"] += 1

    for key in original.keys():
        child_path = (
            f"{path.rstrip('/')}/{key}"
        )

        if key not in enriched:
            errors.append(
                f"{child_path}: missing from enriched file"
            )
            continue

        compare_objects(
            original[key],
            enriched[key],
            child_path,
            errors,
            stats,
        )


def main():
    print("\nENRICHED HDF5 INTEGRITY VERIFICATION")
    print("=" * 65)

    if not ORIGINAL.exists():
        raise FileNotFoundError(ORIGINAL)

    if not ENRICHED.exists():
        raise FileNotFoundError(ENRICHED)

    errors = []
    stats = {
        "groups_checked": 0,
        "datasets_checked": 0,
    }

    with h5py.File(ORIGINAL, "r") as source:
        with h5py.File(ENRICHED, "r") as target:
            compare_objects(
                source,
                target,
                "/",
                errors,
                stats,
            )

            metadata_path = "/metadata/usgs_stations"

            if metadata_path not in target:
                errors.append(
                    "Missing new station metadata group"
                )
            elif len(target[metadata_path]) != 6:
                errors.append(
                    "Station metadata count is not 6"
                )

            stats["original_events"] = len(
                source["events/event_id"]
            )
            stats["enriched_events"] = len(
                target["events/event_id"]
            )
            stats["original_daymet_dates"] = len(
                source["daymet"]
            )
            stats["enriched_daymet_dates"] = len(
                target["daymet"]
            )

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        **stats,
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
    }

    REPORT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nRESULTS")
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("errors:", len(errors))

    for error in errors[:20]:
        print("ERROR:", error)

    print("\nRESULT:", report["result"])
    print("Report:", REPORT)


if __name__ == "__main__":
    main()
