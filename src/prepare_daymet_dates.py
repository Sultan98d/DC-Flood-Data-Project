
from pathlib import Path
import pandas as pd

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

input_file = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "validated_events.csv"
)

output_file = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "daymet_required_dates.csv"
)

# --------------------------------------------------
# 2. Load validated flood events
# --------------------------------------------------

events = pd.read_csv(input_file)

required_columns = [
    "event_id",
    "begin_date",
    "end_date",
    "start_utc",
    "end_utc",
]

missing_columns = [
    column
    for column in required_columns
    if column not in events.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

if events["event_id"].duplicated().any():
    raise ValueError("Duplicate event IDs found.")

# --------------------------------------------------
# 3. Identify all required Daymet dates
# --------------------------------------------------

all_dates = set()
event_day_counts = []

for _, event in events.iterrows():

    event_id = event["event_id"]

    start_date = pd.to_datetime(
        event["begin_date"],
        errors="raise"
    )

    end_date = pd.to_datetime(
        event["end_date"],
        errors="raise"
    )

    if pd.isna(start_date) or pd.isna(end_date):
        raise ValueError(
            f"Missing date for event: {event_id}"
        )

    if end_date < start_date:
        raise ValueError(
            f"Invalid date range for event: {event_id}"
        )

    event_dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D"
    )

    all_dates.update(event_dates)

    event_day_counts.append({
        "event_id": event_id,
        "number_of_days": len(event_dates)
    })

# --------------------------------------------------
# 4. Create unique Daymet date table
# --------------------------------------------------

required_dates = pd.DataFrame({
    "date": sorted(all_dates)
})

required_dates["year"] = (
    required_dates["date"].dt.year
)

# Updated Pandas syntax
required_dates["day_of_year"] = (
    required_dates["date"].dt.day_of_year
)

required_dates["date"] = (
    required_dates["date"].dt.strftime("%Y-%m-%d")
)

# --------------------------------------------------
# 5. Save output
# --------------------------------------------------

output_file.parent.mkdir(
    parents=True,
    exist_ok=True
)

required_dates.to_csv(
    output_file,
    index=False
)

# --------------------------------------------------
# 6. Event-level statistics
# --------------------------------------------------

event_counts = pd.DataFrame(
    event_day_counts
)

single_day_events = int(
    (event_counts["number_of_days"] == 1).sum()
)

multi_day_events = int(
    (event_counts["number_of_days"] > 1).sum()
)

# --------------------------------------------------
# 7. Print summary
# --------------------------------------------------

print("\nDAYMET DATE PREPARATION")
print("-" * 45)

print("Total events:", len(events))

print(
    "Unique required days:",
    len(required_dates)
)

print(
    "Unique years:",
    required_dates["year"].nunique()
)

print(
    "First date:",
    required_dates["date"].min()
)

print(
    "Last date:",
    required_dates["date"].max()
)

print(
    "Maximum days in one event:",
    event_counts["number_of_days"].max()
)

print(
    "Single-day events:",
    single_day_events
)

print(
    "Multi-day events:",
    multi_day_events
)

print("\nDAYS REQUIRED BY YEAR:")

print(
    required_dates.groupby("year")
    .size()
    .to_string()
)

print("\nEVENTS CROSSING MIDNIGHT:")
print("-" * 45)

multi_day_ids = event_counts.loc[
    event_counts["number_of_days"] > 1,
    "event_id"
]

multi_day_details = events.loc[
    events["event_id"].isin(multi_day_ids),
    [
        "event_id",
        "begin_date",
        "begin_time",
        "end_date",
        "end_time"
    ]
]

if multi_day_details.empty:
    print("No multi-day events found.")
else:
    print(
        multi_day_details.to_string(index=False)
    )

print("\nOutput:", output_file)

print("\nDaymet date preparation completed.")
