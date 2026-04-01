# %%
import pandas as pd
import time
import numpy as np


# %%
# Check for missing values in period column in trips in script 2
def TestTimePeriod (trip_df, output_path):
    empty_time_periods = trip_df[trip_df['period'].isnull()]
    if len(empty_time_periods)>0:
        empty_time_periods .to_csv(output_path / 'Check_empty_period.csv', index=False)
        raise Exception('Time periods are missing, please find the error outputs in the default output path') 
    else:
        print('Time period check ok')

# %%
# Check if all end times greater than start times in trips in script 2
def TestTripsTimesCheck (trips_df, output_path):
    trips_df['start_time'] = pd.to_timedelta( trips_df['start_time'])
    trips_df['end_time'] = pd.to_timedelta( trips_df['end_time'])
    wrong_time = trips_df[trips_df['start_time']>trips_df['end_time']]
    if len(wrong_time)>0:
        wrong_time .to_csv(output_path / 'Check_wrong_time.csv', index=False)
        raise Exception('Start and end times do not make sense, please find the error outputs in the default output path') 
    else:
        print('Start and end time check ok')

# %%
# Stop-to-stop speed check for stop times
# TODO: Could be simplified
def TestStopToStopSpeed (stop_times, output_path, speed_limit_low, speed_limit_high, dist_rule):
    stop_times_copy = stop_times.copy()
    speed_list =[]
    wrong_speed = []
    for _, row in stop_times_copy.iterrows():
        if row['dist_to_next'] ==0:
            speed = 0
            speed_list.append(speed)
        elif row['interval'] ==0:
            speed = float('inf')
            speed_list.append(speed)
        else :
            speed = row['dist_to_next']/(row['interval']/3600)
            speed_list.append(speed)
        if row['dist_to_next'] < dist_rule:
            wrong_speed.append(speed > speed_limit_low)
        else:
            wrong_speed.append(speed > speed_limit_high)
            
    stop_times_copy['GTFS_speed (km/h)'] = speed_list
    wrong_speed_df= stop_times_copy[wrong_speed]

    if len(wrong_speed_df)>0:
        wrong_speed_df.to_csv(output_path / 'Check_wrong_speed.csv', index=False)
        print('Speeds do not make sense, please find the error outputs in the default output path') 
    else:
        print('Speed check ok')


# %%
# stop id input data check in script 2
def StopIDNotMatches(stop_times, stops, output_path):
    stop_times_id = set(stop_times['stop_id'])
    stops_id = set(stops['stop_id'])
    if stop_times_id.issubset(stops_id):
        print('Stop IDs check ok')
    else:
        stop_ids_unmatched = stops_id.symmetric_difference(stop_times_id)
        df = pd.DataFrame(list(stop_ids_unmatched))
        df.to_csv(output_path / 'Check_stop_ids_unmatched.csv', index=False)
        raise Exception('Stop IDs do not match, please find the error outputs in the default output path') 

# %%
# trip id input data check in script 2
def TripIDNotMatches(trips, stop_times, output_path):
    trips_id = set(trips['trip_id'])
    stop_times_id = set(stop_times['trip_id'])
    trip_ids_unmatched = trips_id.symmetric_difference(stop_times_id)
    df = pd.DataFrame(list(trip_ids_unmatched))
    if len(df)>0:
        df.to_csv(output_path / 'Check_trip_ids_unmatched.csv', index=False)
        raise Exception('Trip IDs do not match, please find the error outputs in the default output path') 
    else:
        print('Trip IDs check ok')


# %%
def ShapeIDNotMatches(shapes, trips, output_path):
    shapes_id = set(shapes['shape_id'])
    trips_id = set(trips['shape_id'])
    shape_ids_unmatched = shapes_id.symmetric_difference(trips_id)
    df = pd.DataFrame(list(shape_ids_unmatched))
    if len(df)>0:
        df.to_csv(output_path / 'Check_shape_ids_unmatched.csv', index=False)
        raise Exception('Shape IDs do not match, please find the error outputs in the default output path') 
    else:
        print('Shape IDs check ok')
        
# %%
# %%
def CheckAndFillShapeDistances(stopTimes, inputPath, outputPath):
    missingValues = stopTimes['shape_dist_traveled'].isna() # checks for missing values
    
    if True in set(missingValues):
        for row in range(len(missingValues)-1):
            if missingValues[row] == True:
                print('Fixing')
                # if the first stop missing, then fill 0
                if stopTimes.at[row, 'stop_sequence'] == 1:
                    stopTimes.at[row, 'shape_dist_traveled'] = 0

                # if a single stop is missing,  then fix with average
                elif pd.notna(stopTimes.at[row-1, 'shape_dist_traveled']) and \
                    pd.notna(stopTimes.at[row+1, 'shape_dist_traveled']) and \
                        (stopTimes.at[row+1, 'stop_sequence'] != 1):
                    stopTimes.at[row, 'shape_dist_traveled'] = \
                        (stopTimes.at[row-1, 'shape_dist_traveled'] + stopTimes.at[row+1, 'shape_dist_traveled'])/2
                
                # if tow stops are missing in a row, then fix them both
                elif pd.notna(stopTimes.at[row-1, 'shape_dist_traveled']) and \
                    pd.isna(stopTimes.at[row+1, 'shape_dist_traveled']) and \
                        (stopTimes.at[row+1, 'stop_sequence'] != 1):
                        preStopTime    = pd.to_timedelta(stopTimes.at[row-1, 'arrival_time'])
                        fistStopTime   = pd.to_timedelta(stopTimes.at[row, 'arrival_time'])
                        secondStopTime = pd.to_timedelta(stopTimes.at[row+1, 'arrival_time'])
                        nextStopTime   = pd.to_timedelta(stopTimes.at[row+2, 'arrival_time'])

                        preDist  = stopTimes.at[row-1, 'shape_dist_traveled']
                        nextDist = stopTimes.at[row+2, 'shape_dist_traveled']

                        stopTimes.at[row, 'shape_dist_traveled'] = preDist + (nextDist - preDist) * \
                            (fistStopTime-preStopTime)/(nextStopTime-preStopTime)
                        stopTimes.at[row+1, 'shape_dist_traveled'] = preDist + (nextDist - preDist) * \
                            (secondStopTime-preStopTime)/(nextStopTime-preStopTime)
                        missingValues[row+1] = False
                        
        stopTimes.to_csv(inputPath / 'stop_times_fixed.csv', index=False)
        missingValues = stopTimes['shape_dist_traveled'].isna()
        if True in set(missingValues):
            stopTimes[missingValues].to_csv(outputPath / 'Check_shape_distances.csv')
            raise Exception('Shapes have missing distance values. \
                Please find them in the error output in the default output path. \
                    Correct them in stop_times file.') 
        else:
            print('There were missing values, but fixed now. Check stop_times_fixed for details.')
            return stopTimes
    else:
        print('Shape distances do not have missing values.')
        return stopTimes


# %%
