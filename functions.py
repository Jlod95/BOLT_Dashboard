# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 10:11:16 2022

@author: CAYZ075617
"""

import json
import requests
import time
import sys
import numpy as np
import pandas as pd


def ConvertDateFormat(date):
    string     = str(date)
    new_format = string[0:4] + '-' + string[4:6] + '-' + string[6:]
    return new_format


def Time24plusFormat(td_obj):
    total_seconds = td_obj.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    str = '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)
    return (str)


# purpose: to calculate the direct shortest distance between two points on earth (flight distance)
def GreatCircleDist(lon1, lat1, lon2, lat2):
    r = 6378.137      # arithmetic mean earth radius in km. Check: https://en.wikipedia.org/wiki/Earth_radius
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dist = r * (np.arccos(np.sin(lat1) * np.sin(lat2) + np.cos(lat1) * np.cos(lat2) * np.cos(lon1 - lon2)))
    return dist


# The results are in accordance with the Earth radius
def Nearest(pattern_seq, shapes, seq_loc, dist_loc, pt_seq_loc, stop_lat_loc, stop_lon_loc, pt_lat_loc, pt_lon_loc):
    nearest_pts = []
    seq_list = []
    dist_travelled = []
    shape_list = []
    for name, group in pattern_seq.groupby('shape_id'):
        first_seq = group.iat[0, seq_loc]
        last_seq = group.iat[-1, seq_loc]
        shape_slice = shapes.loc[shapes['shape_id'] == name]
        j = 1
        for row in group.itertuples(index=False):
            shape_list.append(name)
            seq_list.append(row[seq_loc])
            # if the first stop in the trip, assign the first point in shape
            if row[seq_loc] == first_seq:
                dist_travelled.append(shape_slice.iat[0, dist_loc])
                nearest_pts.append(1)
            # if the last stop in the trip, assign the last point in shape
            elif row[seq_loc] == last_seq:
                dist_travelled.append(shape_slice.iat[-1, dist_loc])
                nearest_pts.append(shape_slice.iat[-1, pt_seq_loc])
            else:
                stop_lat = row[stop_lat_loc]
                stop_lon = row[stop_lon_loc]
                min_dist = 99999
                # Iterate through the list of shape points
                for i in range(j, len(shape_slice)):

                    pt_lat = shape_slice.iat[i, pt_lat_loc]
                    pt_lon = shape_slice.iat[i, pt_lon_loc]
                    if (pt_lat == stop_lat) and (pt_lon == stop_lon):
                        pt_seq = shape_slice.iat[i, pt_seq_loc]
                        cum_dist = shape_slice.iat[i, dist_loc]
                        j = i + 1
                        break
                    else:
                        try:
                            dist = GreatCircleDist(stop_lon, stop_lat, pt_lon, pt_lat)
                        except:
                            dist = 0
                        # This method may have a problem when there is a loop which can cause selecting a later point (the first min_dist should be selected)
                        if dist <= min_dist:
                            min_dist = dist
                            pt_seq = shape_slice.iat[i, pt_seq_loc]
                            cum_dist = shape_slice.iat[i, dist_loc]
                            j = i + 1
                
                nearest_pts.append(pt_seq)
                dist_travelled.append(cum_dist)

    return shape_list, seq_list, nearest_pts, dist_travelled


# use Google map for distance calculation
# For details, check: https://developers.google.com/maps/documentation/directions/get-directions#TextValueObject
# output distance in km and time in min
def GoogleMapAPI(o_lat, o_lon, d_lat, d_lon):
    time.sleep(0.02)   # add this to avoid the code run too fast and miss/skip resutls from server

    direction_url = 'https://maps.googleapis.com/maps/api/directions/json'
    key           = 'AIzaSyDSFOAQ1B6wVBVPxq0vZHcA8LMnNBiu1Os'

    start_point = ','.join([str(o_lat), str(o_lon)])
    end_point   = ','.join([str(d_lat), str(d_lon)])
    
    params = {'origin': start_point, 'destination': end_point, \
        'mode': 'driving', 'units': 'metric', 'avoid':'tolls', 'key': key}
        
    r = requests.get(direction_url, params=params)

    if r.status_code == 200:
        output = json.loads(r.text)
        if output['status'] == 'OK':
            distance = output['routes'][0]['legs'][0]['distance']['value']                # in metre
            duration = output['routes'][0]['legs'][0]['duration']['value']                # in seconds
            # duration = output['routes'][0]['legs'][0]['duration_in_traffic']['value']     # in seconds, Use this when given departure time
            return distance/1000, duration/60  # output distance in km and time in min
        else:
            return -1, -1
    else:
        return -1, -1


# use Bing map for distance calculation
# For details, check: https://learn.microsoft.com/en-us/bingmaps/rest-services/routes/calculate-a-route
def BingMapAPI (o_lat, o_lon, d_lat, d_lon):
    time.sleep(0.03)    # add this to avoid the code run too fast and miss/skip resutls from Bing map
    
    key       = "Your API Key"  # May need update in the future

    opos = ', '.join([str(o_lat), str(o_lon)])
    dpos = ', '.join([str(d_lat), str(d_lon)])
    params = {'wp.0': opos, 'wp.1': dpos, 'avoid': 'tolls', 'key': key}
    try:
        r      = requests.get('http://dev.virtualearth.net/REST/V1/Routes/Driving', params=params)
        output = json.loads(r.text)
    except:
        print('first attempt failed, pausing and trying again')
        time.sleep(5)
        try:
            r = requests.get('http://dev.virtualearth.net/REST/V1/Routes/Driving', params=params)
            output = json.loads(r.text)
        except:
            print('Second attempt failed. Please check code or internet.')
            sys.exit()
            
    try:
        dist     = output['resourceSets'][0]['resources'][0]['travelDistance']  # km
        duration = output['resourceSets'][0]['resources'][0]['travelDuration']  # second
    except:
        # problem results will be given -1 as values. Check final resutls
        dist     = -1
        duration = -1
    return dist, duration/60  #output distance in km and time in min



# use rome to rio for distance calculation
def Rome2RioAPI (o_lat, o_lon, d_lat, d_lon):
    
    key          = "plc8bYor"
    noAir        = 1
    noRail       = 1
    noBus        = 1
    noSpecial    = 1
    noMinorStart = 1
    noMinorEnd   = 1
    noStop       = 1
    
    opos   = ', '.join([str(o_lat), str(o_lon)])
    dpos   = ', '.join([str(d_lat), str(d_lon)])
    params = {'key': key, 'oPos': opos, 'dPos': dpos, 'noAir': noAir, 'noSpecial': noSpecial, 'noStop': noStop}
    try:
        r      = requests.get('http://free.rome2rio.com/api/1.4/json/Search', params=params)
        output = json.loads(r.text)
    except:
        print('first attempt failed, pausing and trying again')
        time.sleep(5)
        try:
            r = requests.get('http://free.rome2rio.com/api/1.4/json/Search', params=params)
            output = json.loads(r.text)
        except:
            print('Second attempt failed.')
            print('Check two things:\n 1. Internet connection; \n 2. Maximum number of requests (500) reached.')
            print('Please wait for 1 hour or try again in 1 hour.')
            print('Sleeping...zzz... wake up in an hour...zzz...')
            time.sleep(3600)
            try:
                r = requests.get('http://free.rome2rio.com/api/1.4/json/Search', params=params)
                output = json.loads(r.text)
            except:
                print('Third attempt still failed after 1 hour. Please stop the program and check problem.')
                sys.exit()
            
    try:
        dist = output['routes'][-2]['distance']
        duration = output['routes'][-2]['totalTransitDuration']
    except:
        # problem results will be given -1 as values. Check final resutls
        dist     = -1
        duration = -1
            
    return dist, duration



def AttachShapeID(stop_times, trips):
    stop_times = stop_times.merge(trips[['trip_id', 'shape_id']], how='left', on='trip_id')
    columnName = stop_times.columns.tolist()        # move shape_id to the first column
    columnName = columnName[-1:] + columnName[:-1]  # move shape_id to the first column
    stop_times = stop_times[columnName]             # move shape_id to the first column
    stop_times.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)
    stop_times.reset_index(drop=True, inplace=True)

    return stop_times


def CalcDistToNextAndInterv(stop_times, dist_criterion):

    stop_times['dist_to_next'] = np.roll(stop_times['shape_dist_traveled'], -1) - stop_times['shape_dist_traveled']
    stop_times = stop_times.loc[(stop_times['dist_to_next'] < 0) | (stop_times['dist_to_next'] >= dist_criterion)]   # remove stops that is shorter than 0.05 km or 50 m
    stop_times.loc[stop_times['dist_to_next'] < 0, 'dist_to_next'] = 0     # set the last one of each trip to 0

    # calculate actual dist_to_next and interval
    stop_times['arrival_time_delta'] = pd.to_timedelta(stop_times['arrival_time'])
    stop_times['interval']           = np.roll(stop_times['arrival_time_delta'], -1) - stop_times['arrival_time_delta']
    stop_times['interval']           = stop_times['interval'].dt.total_seconds()
    stop_times['dist_to_next']       = np.roll(stop_times['shape_dist_traveled'], -1) - stop_times['shape_dist_traveled']

    stop_times_copy = stop_times[0:0]
    for name, group in stop_times.groupby('trip_id'):
        group.reset_index(drop=True, inplace=True)
        group['stop_sequence'] = group.index + 1

        group['dist_to_next'].iat[-1] = 0     # correct to 0 from np.roll above
        group['interval'].iat[-1]     = 0     # correct to 0 from np.roll above

        stop_times_copy = pd.concat([stop_times_copy, group])

    stop_times_copy.drop(labels='arrival_time_delta', axis=1, inplace=True)
    stop_times_copy.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)
    stop_times_copy.reset_index(drop=True, inplace=True)

    return stop_times_copy


def CalcDistToNextOnly(stop_times, dist_criterion):
    stop_times['dist_to_next'] = np.roll(stop_times['shape_dist_traveled'], -1) - stop_times['shape_dist_traveled']
    # stop_times = stop_times.loc[(stop_times['dist_to_next'] < 0) | (stop_times['dist_to_next'] >= dist_criterion)]   # remove stops that is shorter than 0.05 km or 50 m
    stop_times.loc[stop_times['dist_to_next'] < 0, 'dist_to_next'] = 0     # set the last one of each trip to 0

    # calculate actual dist_to_next and interval
    stop_times['dist_to_next']       = np.roll(stop_times['shape_dist_traveled'], -1) - stop_times['shape_dist_traveled']

    stop_times_copy = stop_times[0:0]
    for name, group in stop_times.groupby('trip_id'):
        group.reset_index(drop=True, inplace=True)
        group['stop_sequence'] = group.index + 1
        group['dist_to_next'].iat[-1] = 0

        stop_times_copy = pd.concat([stop_times_copy, group])

    stop_times_copy.drop(labels='arrival_time_delta', axis=1, inplace=True)
    stop_times_copy.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)
    stop_times_copy.reset_index(drop=True, inplace=True)

    return stop_times_copy


def CalcTmin(temp_df, acc, decc, vLimitLow, vLimitHigh, distRule):
    # Calculate minimum required time & max possible speed base on assumed acc and decc
    acdc  = (acc + decc) / (acc * decc)

    v_max = (temp_df['dist_to_next'] * 2 / acdc)**(1 / 2)
    tmin1 = (temp_df['dist_to_next'] * 2 * acdc)**(1 / 2)      # just acceleration and deceleration
    tmin2Low  = temp_df['dist_to_next']/vLimitLow + acdc * vLimitLow / 2   # acceleration + constant speed (Low) + deceleration
    tmin2High = temp_df['dist_to_next']/vLimitHigh + acdc * vLimitHigh / 2 # acceleration + constant speed (High) + deceleration

    temp_df['tmin'] = np.nan
    for i in range(len(temp_df)):
        # most likely downtown road
        if temp_df['dist_to_next'].iat[i] < distRule:
            temp_df['tmin'].iat[i] = tmin1[i] if v_max[i] < vLimitLow else tmin2Low[i]  

        # most likely highway road
        else:
            temp_df['tmin'].iat[i] = tmin1[i] if v_max[i] < vLimitHigh else tmin2High[i]

    return temp_df


def AddStopTimeToTmin(temp_df, min_stop_time):
    temp_df.loc[temp_df['tmin'] != 0, 'tmin'] += min_stop_time
    
    temp_df['tmin'] = temp_df['tmin'] * 3600                       # change to seconds
    temp_df['tmin'] = temp_df['tmin'].apply(np.ceil)               # roundup the values for tmin

    return temp_df



def AdjustIntervals(temp_df, stop_times):
    stop_times['original_interval']  = stop_times['interval']
    stop_times['interval']           = temp_df['corrected_interval']
    stop_times['average speed']      = stop_times['dist_to_next'] / stop_times['interval'] * 3600
    stop_times['adjustments']        = temp_df['adjustments']
    stop_times['cumulative_adj']     = temp_df['cumulative_adj']
    stop_times['interval'].fillna(0, inplace=True)
    stop_times['average speed'].fillna(0, inplace=True)

    stop_times['arrival_time']   = (pd.to_timedelta(stop_times['arrival_time']) 
                                    + pd.to_timedelta(temp_df['cumulative_adj'], unit='S'))
    stop_times['arrival_time']   = stop_times['arrival_time'].apply(Time24plusFormat)
    stop_times['departure_time'] = stop_times['arrival_time']

    return stop_times



