# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import pandas as pd
import numpy as np
import pathlib as plib
from functions import AttachShapeID, CalcDistToNextAndInterv, CalcTmin, AddStopTimeToTmin, AdjustIntervals
from tests import TripIDNotMatches, StopIDNotMatches, TestStopToStopSpeed, CheckAndFillShapeDistances

# THIS PART NEEDS REVISION

########################### IMPORTANT NOTES #############################
# Check the unit in column 'shape_dist_traveled'. The code's default is km, if GTFS is m, then tweak the code. 
# THIS IS FOR GTFS DATA THAT HAVE ONLY ONE DEPARTURE TIME AT THE BEGINNING OF A TRIP 
# AND ONE ARRIVAL TIME AT THE END OF A TRIP IN STOP_TIMES.CSV FILE
# For GTFS data that have detailed arrival and departure time for each stop, use 2. 1st...py
# For GTFS data that have rounded arrival and departure time for each stop, use 2. 2nd...py
# For GTFS data that have arrival and departure times for some stops, use 2. 3rd...py
# For GTFS data that have only beginning and end time of trips, use 2. 4th...py



# FIRST make sure the speed limit is matching BOLT Cloud
# SECOND make sure the stop time for each stop is matching BOLT Cloud
acc   = 12960        # km/h^2 = 1.0m/s^2
decc  = 25920        # km/h^2 = 2.0m/s^2
vLimitLow  = 50      # km/h SPEEDLIMIT most downtown
vLimitHigh = 80      # km/h speedlimit most freeway
distRule   = 2       # km, if stop-to-stop dist is smaller than this, vLimitLow is used. Otherwise, vLimitHigh is used
min_stop_time  = 5/3600  # h  stop time for non terminal stops
dist_unit_conv = 1000    # use 1000 if GTFS is in M, 1 if GTFS is in KM, 0.6214 if in miles.
dist_criterion = 0.05    # km, stops within this criterion will be removed



# %%
input_path  = plib.Path(r'C:\Users\cayz075617\Documents\BOLT Projects\1. Projects\Sample Data\Kingston Transit\GTFS data\csv files')
output_path = plib.Path(r'C:\Users\cayz075617\Documents\BOLT Projects\1. Projects\Sample Data\Kingston Transit\Results')


# %%
stops      = pd.read_csv(input_path / "stops.csv",
                    dtype={'stop_id'  : str,
                           'stop_code': str,
                           'stop_lat' : float,
                           'stop_lon' : float})
stop_times = pd.read_csv(output_path / "stop_times.csv",
                         dtype={'trip_id'      : str,
                                'stop_id'      : str,
                                'stop_sequence': 'int64'})
col_names = list(stop_times.columns)

usecols = ['route_id', 'shape_id', 'service_id', 'trip_id']
trips   = pd.read_csv(input_path / "trips.csv", usecols=usecols, 
                      dtype={'service_id'  : str, 
                             'route_id'    : str, 
                             'shape_id'    : str, 
                             'trip_id'     : str})


# %%
StopIDNotMatches(stop_times, stops, output_path)
TripIDNotMatches(trips, stop_times, output_path)


# %%
stop_times = AttachShapeID(stop_times, trips)


# %%
stop_times = CheckAndFillShapeDistances(stop_times, input_path, output_path)
stop_times['shape_dist_traveled'] = stop_times['shape_dist_traveled']/dist_unit_conv   # change unit to km



# %%
# ASSUMING DEPARTURE_TIME HAS THE START TIME AND ARRIVAL_TIME HAS THE END TIME OF THE TRIP (NEEDS CHECK ONCE DATA BECOME AVAILABLE)
# The time interval is no longer needed to create here as it can be done in the tmin calculation part.
stop_times['arrival_time'].fillna(method='ffil', inplace=True)
stop_times['departure_time'].fillna(method='ffil', inplace=True)
stop_times = CalcDistToNextAndInterv(stop_times, dist_criterion)
stop_times.to_csv(output_path / "stop_times_w_dist_times.csv", index=False)


# %%
temp_df = stop_times.copy(deep=True)   # make a copy to do tmin calculation
temp_df = CalcTmin(temp_df, acc, decc, vLimitLow, vLimitHigh, distRule)
temp_df = AddStopTimeToTmin(temp_df, min_stop_time)
stop_times['tmin (s)'] = temp_df['tmin']                       # store the tmin into the results



# %%
# Make adjustment on the schedule
# This method uses the actual intervals for time adjustment, which is unlike the rest three methods.
trip_id_list       = []
trip_seq_list      = []
adjustments        = []
cumulative_adj     = []
corrected_interval = []

for name, trip in temp_df.groupby('trip_id'):
    trip_id_list.extend(trip['trip_id'])
    trip_seq_list.extend(trip['stop_sequence'])

    startTime  = pd.to_timedelta(trip['departure_time'].iat[0])
    finishTime = pd.to_timedelta(trip['departure_time'].iat[-1])
    totalTime  = (finishTime - startTime).total_seconds()
    totalTmin  = sum(trip['tmin'])
    
    # When tmin is bigger than actual schedule, use tmin instead
    if totalTime < totalTmin:
        print(f'insufficient trip time for trip {name}, using tmin to replace')
        trip['adjustments']    = np.roll(trip['tmin'], 1)           # the first stop doesn't need adjustment, so shift the last 0 to first
        trip['cumulative_adj'] = trip['adjustments'].cumsum()       # This is the part that is different from the 1st algorithm
        adjustments.extend(trip['adjustments'])
        cumulative_adj.extend(trip['cumulative_adj'])               # this is used to adjust schedules. May not be useful
        corrected_interval.extend(trip['tmin'])

    # When tmin is smaller than actual schedule, create the interval which is the corrected interval 
    else:
        timeToSpare = totalTime - totalTmin
        trip['distribution']       = trip['dist_to_next']*trip['tmin']         # distribution factor based on distance and time
        trip['interval'] = trip['distribution']/sum(trip['distribution'])*timeToSpare + trip['tmin']
        trip['interval'] = np.round(trip['interval'].astype(np.double))    # the round func can cause the last cummulative adjustment not equal to 0 (1 and 3 methods give 0). 
        
        trip['adjustments']        = np.roll(trip['interval'], 1)    # the first stop doesn't need adjustment, so shift the last 0 to first
        trip['cumulative_adj']     = trip['adjustments'].cumsum()
        adjustments.extend(trip['adjustments'])
        cumulative_adj.extend(trip['cumulative_adj'])
        corrected_interval.extend(trip['interval'])
    
# Compile all corrected trips into a dataframe
correction_df = pd.DataFrame({'trip_id'     : trip_id_list, 
                            'stop_sequence' : trip_seq_list, 
                            'adjustments'   : adjustments, 
                            'cumulative_adj': cumulative_adj, 
                            'interval'      : corrected_interval})
temp_df = temp_df.merge(correction_df, how='left', on=['trip_id','stop_sequence'])  # Add the values back 
temp_df.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)
temp_df.reset_index(drop=True, inplace=True)



#%%
stop_times = AdjustIntervals(temp_df, stop_times)



#%%
# stop-to-stop speed test after it's been fixed and tested
TestStopToStopSpeed(stop_times, output_path, vLimitLow, vLimitHigh, distRule)


# %%
stop_times = stop_times[col_names]
stop_times.to_csv(output_path / "stop_times.txt", index=False)

# %%
