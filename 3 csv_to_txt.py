#%%

import pandas as pd
import os

from config import output_path

# Define input and output directory
input_dir = output_path
input_path = output_path
output_dir = output_path

# List of filenames without extensions
files = ["calendar", "routes", "shapes", "stop_times", "stops", "trips"]

# Loop through each file and convert to TXT
for file in files:
    input_path = os.path.join(input_dir, f"{file}.csv")
    output_path = os.path.join(output_dir, f"{file}.txt")

    try:
        # Read the CSV file
        df = pd.read_csv(input_path)

        # Save as TXT with comma-separated values
        df.to_csv(output_path, sep=",", index=False)
        print(f"Converted {file}.csv to {file}.txt successfully.")
    
    except Exception as e:
        print(f"Error processing {file}.csv: {e}")

print("All files processed.")

#%%