# -*- coding: utf-8 -*-
"""
Created on Fri Nov 19 13:55:41 2021

@author: CAYZ075617
"""

# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import pandas  as pd
import pathlib as plib
from GTFS import GTFS
import os

from config import output_path
# %%
gtfs_path   = output_path                                 
# Create the folder (and any missing parent folders) if it doesn't exist
gtfs_path.mkdir(parents=True, exist_ok=True)

output_path = gtfs_path / "Processed"
output_path.mkdir(parents=True, exist_ok=True) # actually creates “Processed”


# %%
# select services based on different requirements
# check the options below and specify inputs as well
choice = 1
gtfs = GTFS(gtfs_path, choice)

# 1. select certain service ids in calendar.txt file
if choice == 1:
    service_ids = ['SOS2509-2509WK-Weekday-10']

    gtfs.select_service_ids(service_ids)

# 2. select a certain day of the week in calendar.txt
# this does NOT consider calendar_dates.txt
elif choice == 2:
    target_day_of_week = 'monday'
    gtfs.select_service_day_of_week_from_calendar(target_day_of_week)

# 3. select services on a certain date in calendar.txt and calendar_dates.txt files.    
elif choice == 3: 
    target_date = pd.to_datetime("2024-09-04")   # "YYYY-MM-DD" INPUT DATE FORMAT 
    gtfs.select_service_date(target_date)

# 4. select all service ids in calendar.txt file (not recommended)
# this does not consider calendar_dates.txt
elif choice == 4:
    gtfs.select_service_all()
 
# 5. select services based solely on calendar_dates.txt (some transit agencies choose this style) 
elif choice == 5:
    gtfs.select_service_date_from_calendar_dates("2021-12-01")   # choose a date for simulation "YYYY-MM-DD"

# %%
gtfs.convert_files_to_csv(output_path)

# Add check for route names being too long
output_path = gtfs_path / "Processed"

target_routes = output_path / "routes.txt"

print(output_path)
# %%
# Read and check route names
df = pd.read_csv(target_routes)

long_names = df[df['route_id'].astype(str).str.len() > 10]

if not long_names.empty:
    print("⚠️ Routes with names longer than 10 characters found:")
    for _, row in long_names.iterrows():
        print(f" - {row['route_id']}")
else:
    print("✅ All route_name values are within 10 characters.")

# Check for duplicate trips and remove if so -> create output file containing list of duplicates

trips_file = output_path / "trips.txt"

if not trips_file.exists():
    # Some GTFS scripts ignore the output_path and save directly in gtfs_path
    fallback_trips = gtfs_path / "trips.txt"
    if fallback_trips.exists():
        trips_file = fallback_trips
    else:
        print("⚠️ trips.txt not found — skipping duplicate trip check.")
        trips_file = None

if trips_file and trips_file.exists():
    trips_df = pd.read_csv(trips_file)

    if 'trip_id' not in trips_df.columns:
        print("⚠️ Column 'trip_id' not found in trips.txt — cannot check for duplicates.")
    else:
        duplicates = trips_df[trips_df.duplicated(subset=['trip_id'], keep=False)]

        if not duplicates.empty:
            duplicate_file = output_path / "duplicate_trip_ids.csv"
            duplicates.to_csv(duplicate_file, index=False)
            print(f"⚠️ Duplicate trip_ids found — saved to: {duplicate_file}")
            print(duplicates[['trip_id']].drop_duplicates().to_string(index=False))
        else:
            print("✅ No duplicate trip_ids found in trips.txt.")
            

# %%