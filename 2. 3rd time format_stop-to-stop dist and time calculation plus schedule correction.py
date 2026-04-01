# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import pandas as pd
import numpy as np
import pathlib as plib
from functions import AttachShapeID, CalcDistToNextOnly, CalcTmin, AddStopTimeToTmin, AdjustIntervals
from tests import TripIDNotMatches, StopIDNotMatches, TestStopToStopSpeed, CheckAndFillShapeDistances


########################### IMPORTANT NOTES #############################
# Check the unit in column 'shape_dist_traveled'. The code's default is km, if GTFS is m, then tweak the code. 
# THIS IS FOR GTFS DATA THAT HAVE ARRIVAL AND DEPARTURE TIMES FOR SOME STOPS 
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
input_path  = plib.Path(r'C:\Users\cayz075617\Documents\01 BOLT Projects\2022 MassDOT Boston\1. MassDOT original and processed data\MART\2022 Feed\csv files')
output_path = plib.Path(r'C:\Users\cayz075617\Documents\01 BOLT Projects\2022 MassDOT Boston\1. MassDOT original and processed data\MART\2022 Feed\Results')


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
stop_times = CalcDistToNextOnly(stop_times, dist_criterion)
stop_times.to_csv(output_path / "stop_times_w_dist_times.csv", index=False)


# %%
temp_df = stop_times.copy(deep=True)   # make a copy to do tmin calculation
temp_df = CalcTmin(temp_df, acc, decc, vLimitLow, vLimitHigh, distRule)
temp_df = AddStopTimeToTmin(temp_df, min_stop_time)
stop_times['tmin (s)'] = temp_df['tmin']                       # store the tmin into the results


# %%
# fill the missing arrival time with time calculated based on tmin ratio + interval calculation
temp_df['arrival_time']   = pd.to_timedelta(temp_df['arrival_time'])
temp_df['departure_time'] = pd.to_timedelta(temp_df['departure_time'])
temp_df['interval'] = 0
tempDF = temp_df[0:0]
for name, group in temp_df.groupby('trip_id'):
    for ind in group.index[0:-1]:
        if (pd.notnull(group['arrival_time'].at[ind])) and (pd.isnull(group['arrival_time'].at[ind+1])):
            indStart = ind
        if (pd.isnull(group['arrival_time'].at[ind])) and (pd.notnull(group['arrival_time'].at[ind+1])):
            indEnd = ind
            totalTime = (group['arrival_time'].at[indEnd+1] - group['arrival_time'].at[indStart]).total_seconds()
            totalTmin = sum(group['tmin'].loc[indStart:indEnd])         # .loc is inclusive on the right end
            timeDistr = np.round((totalTime * (group['tmin'].loc[indStart:indEnd]/totalTmin)).astype(np.double))
            for i in range(indStart+1, indEnd+1):
                group['arrival_time'].at[i] = group['arrival_time'].at[i-1]+pd.to_timedelta(timeDistr[i-1], unit='S')

            indStart = -1
            indEnd   = -1

    # calculate interval
    for i in range(len(group)-1):
        group['interval'].iat[i] = (group['arrival_time'].iat[i+1] - group['arrival_time'].iat[i]).total_seconds()

    tempDF = tempDF.append(group)
temp_df = tempDF
stop_times[['arrival_time', 'interval']] = temp_df[['arrival_time', 'interval']]



# %%
# adjust the arrival time based on whether there are enough time in the schedule
trip_id_list       = []
trip_seq_list      = []
adjustments        = []
cumulative_adj     = []
corrected_interval = []

for name, trip in temp_df.groupby('trip_id'):
    trip_id_list.extend(trip['trip_id'])
    trip_seq_list.extend(trip['stop_sequence'])
    
    # Compare the sum of deficit (s) and sum of surplus (s)
    trip['diff']    = trip['interval'] - trip['tmin']
    trip['deficit'] = trip['diff'].mask(trip['diff'] > 0, 0)
    trip['surplus'] = trip['diff'].where(trip['diff'] > 0, 0)
    overall_deficit = trip['deficit'].sum()
    overall_surplus = trip['surplus'].sum()
    
    # if there is need to adjust the schedule
    if overall_deficit != 0:
        # when tmin is bigger than actual schedule, use tmin instead
        if abs(overall_deficit) >= overall_surplus:
            print(f'insufficient trip time for trip {name}, using tmin to replace')
            trip['adjustments']    = trip['tmin'] - trip['interval']
            trip['adjustments']    = np.roll(trip['adjustments'], 1)    # the first stop doesn't need adjustment, so shift the last 0 to first
            trip['cumulative_adj'] = trip['adjustments'].cumsum()  
            adjustments.extend(trip['adjustments'])
            cumulative_adj.extend(trip['cumulative_adj'])               # this is used to adjust schedules. May not be useful
            corrected_interval.extend(trip['tmin'])
    
        # when tmin is smaller than actual schedule, do some adjustment if needed
        else:
            trip['adjustments'] = abs(trip['deficit'])
            for i in range(int(abs(overall_deficit))):
                maxValueInd = trip['surplus'].idxmax(axis=0)            # find the index of the interval having the most extra time (to spare)
                trip.at[maxValueInd, 'surplus']     -= 1               # reduce the suplus by 1 second
                trip.at[maxValueInd, 'adjustments'] -= 1               # reduce the same row adjustment by 1 second
            trip['adjustments']        = np.roll(trip['adjustments'], 1)    # the first stop doesn't need adjustment, so shift the last 0 to first
            trip['cumulative_adj']     = trip['adjustments'].cumsum()
            trip['corrected_interval'] = trip['interval'] + np.roll(trip['adjustments'], -1)  # have the original order
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
temp_df = temp_df.merge(correction_df, how='left', on=['trip_id','stop_sequence'])  # Add the values back 
temp_df.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)
temp_df.reset_index(drop=True, inplace=True)




# %%
stop_times = AdjustIntervals(temp_df, stop_times)


#%%
TestStopToStopSpeed(stop_times, output_path, vLimitLow, vLimitHigh, distRule)


# %%
stop_times = stop_times[col_names]
stop_times.to_csv(output_path / "stop_times.txt", index=False)


# %%
