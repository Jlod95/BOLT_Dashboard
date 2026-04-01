#%%

import pandas as pd
from config import output_path

#%% Block Count per Service ID


# Replace this with your file path
file_path = output_path / "trips.txt"
sheet_name = 'Trips'  # Only needed if Excel file


# === LOAD DATA ===
if file_path.endswith('.csv'):
    df = pd.read_csv(file_path, usecols=['service_id', 'block_id'])
else:
    df = pd.read_excel(file_path, sheet_name=sheet_name, usecols=['service_id', 'block_id'])

# === CALCULATE UNIQUE BLOCK COUNTS ===
unique_counts = df.groupby('service_id')['block_id'].nunique()

# === PRINT RESULTS ===
for service_id, count in unique_counts.items():
    print(f"{service_id}: {count}")

#%%