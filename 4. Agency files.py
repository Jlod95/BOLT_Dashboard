#%%

import os
import shutil
import pathlib as plib
from pathlib import Path

# Define base path
from config import output_path

file_path = output_path

# Define source folders
processed_path = file_path / 'Processed'
agency_path = file_path / 'Agency'

# Create Agency folder if it doesn't exist
agency_path.mkdir(exist_ok=True)

# Define files to copy
files_from_processed = ['routes.txt', 'shapes.txt', 'stop_times.txt', 'stops.txt', 'trips.txt', 'calendar.txt']
files_from_root = ['agency.txt', 'feed_info.txt', 'calendar_dates.txt', 'transfers.txt',
                   'depot_list.csv', 'block_assignment.csv']

# Copy files from Processed
for file_name in files_from_processed:
    src = processed_path / file_name
    dest = agency_path / file_name
    if src.exists():
        shutil.copy2(src, dest)
    else:
        print(f"File not found in Processed: {file_name}")

# Copy files from root
for file_name in files_from_root:
    src = file_path / file_name
    dest = agency_path / file_name
    if src.exists():
        shutil.copy2(src, dest)
    else:
        print(f"File not found in root: {file_name}")


#%% Clean calendar.txt start_date / end_date (remove "-")
import pandas as pd

calendar_file = agency_path / 'calendar.txt'

if calendar_file.exists():
    df = pd.read_csv(calendar_file, dtype=str)

    for col in ['start_date', 'end_date']:
        if col in df.columns:
            df[col] = df[col].str.replace('-', '', regex=False)

    df.to_csv(calendar_file, index=False)
else:
    print("calendar.txt not found in Agency folder")
#%%
