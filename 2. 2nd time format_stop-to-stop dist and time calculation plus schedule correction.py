# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import pandas as pd
import numpy as np
import pathlib as plib
from functions import AttachShapeID, CalcDistToNextAndInterv, CalcTmin, AddStopTimeToTmin, AdjustIntervals
from tests import TripIDNotMatches, StopIDNotMatches, TestStopToStopSpeed, CheckAndFillShapeDistances


########################### IMPORTANT NOTES #############################
# Check the unit in column 'shape_dist_traveled'. The code's default is km, if GTFS is m, then tweak the code. 
# THIS IS FOR ARRIVAL AND DEPARTURE TIME ROUNDED TO MINUTE IN STOP_TIMES.CSV FILE
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
dist_unit_conv = 1000    # use 1000 if GTFS is in M, 1 if GTFS is in KM, 0.6214 if in miles
dist_criterion = 0.05    # km, stops within this criterion will be removed



# %%
from config import output_path

# Define input and output directory
input_dir = output_path
input_path = output_path
output_dir = output_path

# %%
# check things to make sure no issues
stops = pd.read_csv(input_path / "stops.csv",
                    dtype={'stop_id'  : str,
                           'stop_code': str,
                           'stop_lat' : float,
                           'stop_lon' : float})
stop_times = pd.read_csv(input_path / "stop_times.csv",
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
stop_times['shape_dist_traveled'] = pd.to_numeric(stop_times['shape_dist_traveled'], errors="coerce")

stop_times = CheckAndFillShapeDistances(stop_times, input_path, output_path)
stop_times['shape_dist_traveled'] = stop_times['shape_dist_traveled']/dist_unit_conv    # change unit to km


# %%
stop_times = CalcDistToNextAndInterv(stop_times, dist_criterion)
stop_times.to_csv(output_path / "stop_times.txt", index=False)


# %%
temp_df = stop_times.copy(deep=True)
temp_df = CalcTmin(temp_df, acc, decc, vLimitLow, vLimitHigh, distRule)
temp_df = AddStopTimeToTmin(temp_df, min_stop_time)

# create and adjust Min limit
temp_df['Minimum(s)'] = (temp_df['interval']/60-1)*60 + 1      # calculate the minimum limit on stop-to-stop time
temp_df['tmin']       = np.where(temp_df['tmin'] > temp_df['Minimum(s)'], 
                               temp_df['tmin'], temp_df['Minimum(s)'])  # choose the maximum value between tmin and limitMin as new limitMin

stop_times['tmin (s)'] = temp_df['tmin']                       # store the tmin into the results

# create and adjust Max limit
temp_df['Maximum(s)'] = (temp_df['interval']/60+1)*60 - 1      # calculate the maximum limit on stop-to-stop time
indices = temp_df[temp_df['tmin'] > temp_df['Maximum(s)']].index
temp_df.loc[indices, 'Maximum(s)'] = temp_df['tmin'][indices]      # assign tmin to maximum limit when tmin is bigger than maximum limit

temp_df['diff_tmin_max'] = temp_df['Maximum(s)'] - temp_df['tmin']            # calculate the room between tmin and maximum limit
temp_df['distribution']  = temp_df['diff_tmin_max']*temp_df['dist_to_next']   # calculate the distribution factor



# %%
trip_id_list       = []
trip_seq_list      = []
adjustments        = []
cumulative_adj     = []
corrected_interval = []

for name, trip in temp_df.groupby('trip_id'):
    trip_id_list.extend(trip['trip_id'])
    trip_seq_list.extend(trip['stop_sequence'])
    
    # check if interval falls into the minimum and maximum limit, if yes, there is no need to adjust
    # 0 will be good, 1+ means time interval needs adjustment
    intervalCheck  = sum(trip['tmin']>=trip['interval'])          # if there is any point out of boundry will be 1 and above
    intervalCheck += sum(trip['Maximum(s)']<=trip['interval'])    # if there is any point out of boundry will be 1 and above
    
    # if there is need to adjust the schedule
    if intervalCheck > 0:
        
        totalTime = sum(trip['interval'])    # total scheduled trip time
        totalTmin = sum(trip['tmin'])    # total minimum trip time
        
        # when tmin is bigger than actual schedule, use tmin instead
        if totalTmin >= totalTime:
            print(f'insufficient trip time for trip {name}, using tmin to replace')
            trip['adjustments']    = trip['tmin'] - trip['interval']
            trip['adjustments']    = np.roll(trip['adjustments'], 1)    # the first stop doesn't need adjustment, so shift the last 0 to first
            trip['cumulative_adj'] = trip['adjustments'].cumsum()  
            adjustments.extend(trip['adjustments'])
            cumulative_adj.extend(trip['cumulative_adj'])               # this is used to adjust schedules. May not be useful
            corrected_interval.extend(trip['tmin'])
    
        # when tmin is smaller than actual schedule, do some adjustment if needed
        else:
            timeToSpare  = totalTime - totalTmin
            distribution = trip['distribution']/sum(trip['distribution'])*timeToSpare
            trip['corrected_interval'] = np.round((distribution + trip['tmin']).astype(np.double))  # the round func can cause the last cummulative adjustment not equal to 0 (1 and 3 methods give 0). 
    
            trip['adjustments']    = trip['corrected_interval'] - trip['interval']
            trip['adjustments']    = np.roll(trip['adjustments'], 1)    # the first stop doesn't need adjustment, so shift the last 0 to first
            trip['cumulative_adj'] = trip['adjustments'].cumsum()  
            adjustments.extend(trip['adjustments'])
            cumulative_adj.extend(trip['cumulative_adj'])
            corrected_interval.extend(trip['corrected_interval'])
    
    # if there is no need to adjust the schedule                  
    else:
        adjustments.extend(np.zeros(len(trip)))
        cumulative_adj.extend(np.zeros(len(trip)))
        corrected_interval.extend(trip['interval'])

# Compile all corrected trips into a dataframe
correction_df = pd.DataFrame({'trip_id'         : trip_id_list, 
                            'stop_sequence'     : trip_seq_list, 
                            'adjustments'       : adjustments, 
                            'cumulative_adj'    : cumulative_adj, 
                            'corrected_interval': corrected_interval})
print(temp_df.columns)
# Merge after type conversion

temp_df = temp_df.merge(correction_df, how='left', on=['trip_id','stop_sequence'])  # Add the values back 
temp_df.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)
temp_df.reset_index(drop=True, inplace=True)

print(temp_df.columns)


#%%
stop_times = AdjustIntervals(temp_df, stop_times)


#%%
TestStopToStopSpeed(stop_times, output_path, vLimitLow, vLimitHigh, distRule)


# %%
stop_times = stop_times[col_names]
stop_times.to_csv(output_path / "stop_times.csv", index=False)

# %%