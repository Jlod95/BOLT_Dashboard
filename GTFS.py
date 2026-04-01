# -*- coding: utf-8 -*-
"""
Created on Wed Mar  2 15:00:36 2022

@author: CAYZ075617
"""

import pandas as pd
import numpy as np
import pathlib as plib
import sys
import os
from functions import ConvertDateFormat


class GTFS:
    
    # read files section #####################################################
    def __init__(self, path: plib.Path, choice: int):
        try:
            self.calendar = pd.read_csv(path / "calendar.txt", parse_dates=['start_date', 'end_date'], dtype={'service_id': str}) if choice != 5 else None
        except:
            print('Double check calendar.txt in GTFS data.')
        
        
        if os.path.isfile(path / "calendar_dates.txt"):
            try: 
                self.calendar_dates = pd.read_csv(path / "calendar_dates.txt", dtype={'service_id': str, 'date': str})
                self.calendar_dates['date'] = self.calendar_dates['date'].apply(ConvertDateFormat)
                self.calendar_dates['date'] = pd.to_datetime(self.calendar_dates['date'])
                print('There is calendar_dates.txt file.')
            except:
                print('Double check calendar_dates.txt in GTFS data.')
                sys.exit()
                
        else:
            print('There is no calendar_dates.txt file in GTFS data.')
            self.calendar_dates = pd.DataFrame()  # set an empty one for calculation later
            

        self.routes     = pd.read_csv(path / "routes.txt", dtype={'route_id': str})
        self.shapes     = pd.read_csv(path / "shapes.txt", dtype={'shape_id': str})
        self.stop_times = pd.read_csv(path / "stop_times.txt", dtype={'trip_id': str, 'stop_id': str, 'stop_sequence': 'int64'})
        self.stops      = pd.read_csv(path / "stops.txt", dtype={'stop_id'  : str, 'stop_code': str, 'stop_lat' : float, 'stop_lon' : float})
        self.trips      = pd.read_csv(path / "trips.txt", dtype={'route_id': str, 'service_id': str, 'trip_id': str, 'block_id': str, 'shape_id': str})
            
    
    # calendar related section ###############################################
    # 1. select certain service ids
    def select_service_ids(self, service_list: list):
        self.services    = self.calendar.loc[self.calendar['service_id'].isin(service_list)]
        self.service_set = service_list
        
    
    # 2. select services on a certain day of the week
    # this does not consider calendar_dates.txt
    def select_service_day_of_week_from_calendar(self, day_of_week: str):
        self.day_of_week = day_of_week.lower()
        self.services    = self.calendar.loc[self.calendar[self.day_of_week]==1]
        self.service_set = set(self.services['service_id'])
    

    # 3. select services on a certain date. 
    def select_service_date(self, date: str):
        target_date      = pd.to_datetime(date)
        self.day_of_week = target_date.day_name().lower()
        self.services    = self.calendar.loc[(self.calendar['start_date'] <= target_date) &
                                             (self.calendar['end_date'] >= target_date) & 
                                             (self.calendar[self.day_of_week] == 1)]

        if not self.calendar_dates.empty:
            # if 'exception_type' is 1, then is is to add the service - defined by Google
            self.services_added   = set(self.calendar_dates.loc[(self.calendar_dates['date'] == target_date) &
                                                                (self.calendar_dates['exception_type'] == 1), 'service_id'])

            # if 'exception_type' is 2, then it is to remove - defined by Google
            self.services_removed = set(self.calendar_dates.loc[(self.calendar_dates['date'] == target_date) &
                                                                (self.calendar_dates['exception_type'] == 2), 'service_id'])
            

            # final services and service_set
            df_added = pd.DataFrame({'service_id': list(self.services_added), 
                                     self.day_of_week: np.ones(len(self.services_added))})
            self.services = pd.concat([self.services, df_added])
            self.services.fillna(0, inplace=True)
            self.services.loc[self.services['service_id'].isin(self.services_added), ['start_date', 'end_date']] = date

            self.services    = self.services[~self.services['service_id'].isin(self.services_removed)]
            self.service_set = set(self.services['service_id'])

    
    # 4. select all service ids in calendar.txt file
    # this does NOT include any calendar_dates.txt service ids
    def select_service_all(self):
        self.service = self.calendar
        self.service_set = set(self.service['service_id'])
        
        
    # 5. select services based on calendar_date.txt (some transit agencies choose this style)     
    def select_service_date_from_calendar_dates(self, date: str):
        if self.calendar_dates.empty:
            print('There is no calendar_date.txt file!')
            sys.exit()

        target_date   = pd.to_datetime(date)

        # if 'exception_type' is 1, then is is to add the service - defined by Google
        self.services = self.calendar_dates.loc[(self.calendar_dates['date'] == target_date) &
                                                                (self.calendar_dates['exception_type'] == 1)]

        # if 'exception_type' is 2, then it is to remove - defined by Google                                                        
        self.services_removed = set(self.calendar_dates.loc[(self.calendar_dates['date'] == target_date) &
                                                                (self.calendar_dates['exception_type'] == 2), 'service_id'])
        self.services = self.services[~self.services['service_id'].isin(self.services_removed)]
        self.service_set = set(self.services['service_id'])

        # add week day columns in the output
        self.day_of_week = target_date.day_name().lower()
        self.services[self.day_of_week] = 1
        col_names = ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'date', 'exception_type']
        self.services  = self.services.reindex(columns=col_names)
        self.services = self.services.fillna(0)
        

    # create service table from calendar_dates with on exception type 1
    def create_service_table_from_calendar_dates(self):
        if self.calendar_dates.empty:
            print('There is no calendar_date.txt file!')
            sys.exit()

        else:
            self.calendar_dates['day'] = self.calendar_dates['date'].dt.day_name()   # get the day of the week
            self.calendar_dates['day'] = self.calendar_dates['day'].str.lower()
            self.calendar_dates = self.calendar_dates.loc[self.calendar_dates['exception_type']==1]
            self.service_added  = pd.pivot_table(self.calendar_dates, values='exception_type', index='service_id', columns='day', aggfunc=max)
            self.service_added['service_id'] = self.service_added.index
            self.service_added[['start_date', 'end_date']] = self.day_of_week
            self.service_added.reset_index(drop=True, inplace=True)
            self.service_added.fillna(0, inplace=True)


    # Output results section #################################################
    # save new files to csv format for future use
    def convert_files_to_csv(self, path: plib.Path):
        self.trips      = self.trips.loc[self.trips['service_id'].isin(self.service_set)].copy(deep=True)
        self.routes     = self.routes.loc[self.routes['route_id'].isin(self.trips['route_id'])].copy(deep=True)
        self.shapes     = self.shapes.loc[self.shapes['shape_id'].isin(self.trips['shape_id'])].copy(deep=True)
        self.stop_times = self.stop_times.loc[self.stop_times['trip_id'].isin(self.trips['trip_id'])].copy(deep=True)
        self.stops      = self.stops.loc[self.stops['stop_id'].isin(self.stop_times['stop_id'])].copy(deep=True)  # Not filtering stops is better. 

        self.services.sort_values(by=['service_id'], inplace=True)
        self.services.to_csv(path / ("calendar.txt"), index=False)
        self.trips.to_csv(path / ("trips.txt"), index=False)
        self.routes.to_csv(path / ("routes.txt"), index=False)
        self.shapes.to_csv(path / ("shapes.txt"), index=False)
        self.stop_times.to_csv(path / ("stop_times.txt"), index=False)
        self.stops.to_csv(path / ("stops.txt"), index=False)
        
        
        