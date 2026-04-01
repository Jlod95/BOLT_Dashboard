#%%
import pathlib as plib
import pandas as pd

from config import output_path
input_path = output_path


# Load the stop_times file
stop_times = pd.read_csv(input_path / "stop_times.csv",
                         dtype={'trip_id': str,
                                'stop_id': str,
                                'stop_sequence': 'int64'})

# Sort by trip_id and stop_sequence
stop_times = stop_times.sort_values(by=['trip_id', 'stop_sequence'])

# Helper function to detect if a trip has 3+ empty shape_dist_traveled in a row
def has_three_missing_in_a_row(trip_df):
    is_missing = trip_df['shape_dist_traveled'].isna()
    count = 0
    for missing in is_missing:
        if missing:
            count += 1
            if count >= 3:
                return True
        else:
            count = 0
    return False

# Split the trips
trips_with_issues = []
trips_without_issues = []

for trip_id, group in stop_times.groupby('trip_id'):
    if len(group) < 3 or has_three_missing_in_a_row(group):
        trips_with_issues.append(group)
    else:
        trips_without_issues.append(group)

# Combine into two DataFrames
df_issues = pd.concat(trips_with_issues)
df_no_issues = pd.concat(trips_without_issues)

# Save to CSV (or TXT)
df_issues.to_csv(input_path / 'stop_times_with_missing_shape_dist_traveled.csv', index=False)
df_no_issues.to_csv(input_path / 'stop_times.csv', index=False)

#%%