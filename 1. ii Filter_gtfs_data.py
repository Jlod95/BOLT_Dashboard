# -*- coding: utf-8 -*-
"""
GTFS filtering with optional block / route assignment filters
"""

# %%
import pandas as pd
from config import output_path

# %% =========================
# CONFIG — SET PATHS ONCE
# ==========================

folderAll = output_path

BLOCK_ASSIGNMENT_PATH = folderAll / 'block_assignment.csv'
ROUTE_ASSIGNMENT_PATH = folderAll / 'route_assignment.csv'

# Toggle filters
APPLY_BLOCK_FILTER = True
APPLY_ROUTE_FILTER = True

# %% =========================
# READ GTFS FILES
# ==========================

routes     = pd.read_csv(folderAll / 'routes.txt', dtype={'route_short_name': str})
shapes     = pd.read_csv(folderAll / 'shapes.txt')
stop_times = pd.read_csv(folderAll / 'stop_times.txt')
stops      = pd.read_csv(folderAll / 'stops.txt')
trips      = pd.read_csv(folderAll / 'trips.txt')
services   = pd.read_csv(folderAll / 'calendar.txt')

# %% =========================
# FUNCTIONS
# ==========================

def filter_by_block_assignment(trips, routes, shapes, stop_times, block_path):
    blocks = pd.read_csv(block_path)
    block_set = set(blocks['block_id'])

    trips = trips[trips['block_id'].isin(block_set)].reset_index(drop=True)

    trip_ids  = set(trips['trip_id'])
    shape_ids = set(trips['shape_id'])
    route_ids = set(trips['route_id'])

    routes = routes[routes['route_id'].isin(route_ids)].reset_index(drop=True)
    shapes = shapes[shapes['shape_id'].isin(shape_ids)].reset_index(drop=True)
    stop_times = stop_times[stop_times['trip_id'].isin(trip_ids)].reset_index(drop=True)

    return trips, routes, shapes, stop_times


def filter_by_route_assignment(trips, routes, shapes, stop_times, route_path):
    route_assign = pd.read_csv(route_path)
    route_set = set(route_assign['route_id'])

    trips = trips[trips['route_id'].isin(route_set)].reset_index(drop=True)

    trip_ids  = set(trips['trip_id'])
    shape_ids = set(trips['shape_id'])

    routes = routes[routes['route_id'].isin(route_set)].reset_index(drop=True)
    shapes = shapes[shapes['shape_id'].isin(shape_ids)].reset_index(drop=True)
    stop_times = stop_times[stop_times['trip_id'].isin(trip_ids)].reset_index(drop=True)

    return trips, routes, shapes, stop_times

# %% =========================
# APPLY FILTERS (OPTIONAL)
# ==========================

if APPLY_BLOCK_FILTER:
    trips, routes, shapes, stop_times = filter_by_block_assignment(
        trips, routes, shapes, stop_times, BLOCK_ASSIGNMENT_PATH
    )

if APPLY_ROUTE_FILTER:
    trips, routes, shapes, stop_times = filter_by_route_assignment(
        trips, routes, shapes, stop_times, ROUTE_ASSIGNMENT_PATH
    )

# %% =========================
# SAVE OUTPUTS
# ==========================

routes.to_csv(folderAll / 'routes.csv', index=False)
trips.to_csv(folderAll / 'trips.csv', index=False)
shapes.to_csv(folderAll / 'shapes.csv', index=False)
stops.to_csv(folderAll / 'stops.csv', index=False)
stop_times.to_csv(folderAll / 'stop_times.csv', index=False)

#%%