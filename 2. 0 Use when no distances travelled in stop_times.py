# -*- coding: utf-8 -*-
"""
Created on Tue Dec 14 11:50:08 2021

@author: CAYZ075617
"""

# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import pandas as pd
import numpy as np
import pathlib as plib
from functions import Nearest, GreatCircleDist
from tests import TripIDNotMatches, ShapeIDNotMatches, StopIDNotMatches



# %%
from config import output_path

input_path = output_path

# %%
stops = pd.read_csv(input_path / "stops.csv",
                    dtype={'stop_id': str,
                           'stop_code': str,
                           'stop_lat': float,
                           'stop_lon': float})

# %%
shapes = pd.read_csv(input_path / "shapes.csv",
                     dtype={'shape_id': str,
                            'shape_pt_lat': float,
                            'shape_pt_lon': float,
                            'shape_pt_sequence': 'int64'})


# %%
trips = pd.read_csv(input_path / "trips.csv",
                    usecols=['route_id', 'shape_id', 'service_id', 'block_id', 'trip_id'],
                    dtype={'service_id': str, 
                           'route_id': str, 
                           'block_id': str,
                           'shape_id': str, 
                           'trip_id': str})


# %%
stop_times = pd.read_csv(input_path / "stop_times.csv",
                         dtype={'trip_id': str,
                                'stop_id': str,
                                'stop_sequence': 'int64'})
# stop_times = stop_times.drop(['shape_dist_traveled'], axis=1)



# %%
StopIDNotMatches(stop_times, stops, input_path)
ShapeIDNotMatches(shapes, trips, input_path)
TripIDNotMatches(trips, stop_times, input_path)


# %%
# Sort shape file to accomodate groupby's default sorting behaviour
shapes.sort_values(by=['shape_id', 'shape_pt_sequence'], inplace=True)
shapes.reset_index(inplace=True)


# %%
# Calculate cumulative distance travelled at each point along the shape
cum_dist_list = []
for name, group in shapes.groupby('shape_id'):
    min_seq = min(group['shape_pt_sequence'])
    for i in group.index:
        if group.at[i, 'shape_pt_sequence'] == min_seq:
            cum_dist = 0
        else:
            x1 = group.at[i, 'shape_pt_lon']
            x2 = group.at[i - 1, 'shape_pt_lon']
            y1 = group.at[i, 'shape_pt_lat']
            y2 = group.at[i - 1, 'shape_pt_lat']
            if x1 != x2 or y1 != y2:
                cum_dist += GreatCircleDist(x1, y1, x2, y2)
        cum_dist_list.append(cum_dist)

shapes['shape_dist_traveled'] = cum_dist_list


# %%
# Attach shape ids to stop times
stop_times = stop_times.merge(trips[['trip_id', 'shape_id']], how='left', on='trip_id')
columnName = stop_times.columns.tolist()
columnName = columnName[-1:] + columnName[:-1]
stop_times = stop_times[columnName]             # move shape_id to the first column
stop_times.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)


# %%
# Filter out unique shape_ids with stop sequences using sort method 
pattern_seq = stop_times[['shape_id', 'stop_sequence', 'stop_id']].groupby(['shape_id', 'stop_sequence'],
                                                                           as_index=False).first()


# %%
# Attach stop coordinates to unique shape_ids' stop times
pattern_seq = pattern_seq.merge(stops[['stop_id', 'stop_lat', 'stop_lon']], how='left', on='stop_id')


# %%
seq_loc      = pattern_seq.columns.get_loc('stop_sequence')
stop_lat_loc = pattern_seq.columns.get_loc('stop_lat')
stop_lon_loc = pattern_seq.columns.get_loc('stop_lon')

dist_loc     = shapes.columns.get_loc('shape_dist_traveled')
pt_seq_loc   = shapes.columns.get_loc('shape_pt_sequence')
pt_lat_loc   = shapes.columns.get_loc('shape_pt_lat')
pt_lon_loc   = shapes.columns.get_loc('shape_pt_lon')


# %%
# Find closest point in using shape file to each stop in each trip 
shape_list, seq_list, nearest_pts, dist_traveled = Nearest(
    pattern_seq, shapes, seq_loc, dist_loc, pt_seq_loc, stop_lat_loc, stop_lon_loc, pt_lat_loc, pt_lon_loc)

# %%
df = pd.DataFrame(list(zip(shape_list, seq_list, nearest_pts, dist_traveled)),
                  columns=['shape_id', 'stop_sequence', 'nearest_pt', 'shape_dist_traveled'])

# print(pattern_seq.head())
# print(pattern_seq[['shape_id', 'stop_sequence', 'nearest_pt', 'shape_dist_traveled']].isnull().sum())

# %%
pattern_seq = pattern_seq.merge(df, how='left', on=['shape_id', 'stop_sequence'])

# merge nearest point and the distance along the shape to stop_times file
# This is the new stop_times file for using in next step
stop_times_new = stop_times.merge(
    pattern_seq[['shape_id', 'stop_sequence', 'nearest_pt',
                 'shape_dist_traveled']], how='left',
    on=['shape_id', 'stop_sequence'])


# %%
stop_times_new.drop(labels=['shape_id'], axis=1, inplace=True)
stop_times_new.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)

# re-intitialize
stop_times = pd.read_csv(input_path / "stop_times.csv",
                         dtype={'trip_id': str,
                                'stop_id': str,
                                'stop_sequence': 'int64'})


merged_stop_times = pd.concat([stop_times, stop_times_new], ignore_index=True)

# Edit too short distances to average between the two
# Loop through the rows by index
for i in range(len(merged_stop_times) - 2):  # stop at len - 2 to access i+2 safely
    curr = merged_stop_times.at[i, 'shape_dist_traveled']
    next_val = merged_stop_times.at[i+1, 'shape_dist_traveled']
    
    if pd.notna(curr) and pd.notna(next_val):
        if (next_val - curr) < 0.001 and (next_val - curr) >= 0:
            prev_val = merged_stop_times.at[i-1, 'shape_dist_traveled']
            if pd.notna(prev_val):
                merged_stop_times.at[i, 'shape_dist_traveled'] = curr - (curr - prev_val) / 2 



# Save the merged file
shapes.to_csv(input_path / 'shapes.csv', index=False)
stop_times_new.to_csv(input_path / 'stop_times_merged.csv', index=False)
# %%
