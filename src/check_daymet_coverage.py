
from pathlib import Path
import pandas as pd

# Project paths
ROOT = Path(__file__).resolve().parents[1]

EVENTS_FILE = (
    ROOT / "data" / "processed" / "validated_events.csv"
)

# Load validated flood events
events = pd.read_csv(EVENTS_FILE)

core_days = set()
expanded_days = set()

for _, event in events.iterrows():

    start = pd.Timestamp(event["begin_date"])
    end = pd.Timestamp(event["end_date"])

    # Days during the actual flood event
    event_days = pd.date_range(
        start=start,
        end=end,
        freq="D"
    )

    core_days.update(event_days)

    # Include one day before and one day after
    context_days = pd.date_range(
        start=start - pd.Timedelta(days=1),
        end=end + pd.Timedelta(days=1),
        freq="D"
    )

    expanded_days.update(context_days)

additional_days = expanded_days - core_days

print("\nDAYMET TEMPORAL COVERAGE REVIEW")
print("-" * 45)

print("Total events:", len(events))
print("Original unique days:", len(core_days))
print("Expanded unique days:", len(expanded_days))
print("Additional context days:", len(additional_days))

print(
    "Years:",
    len({date.year for date in expanded_days})
)

print(
    "First:",
    min(expanded_days).date()
)

print(
    "Last:",
    max(expanded_days).date()
)

print("\nCoverage review completed.")
