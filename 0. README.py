# -*- coding: utf-8 -*-
"""
Created on Wed Nov 10 14:11:32 2021

@author: CAYZ075617
"""
# CHECK POINT 1
# How to get the elevation values for stops.csv in QGIS
# 1. Go to website: https://earthexplorer.usgs.gov/ to download the DEM data
# 2. Use "sample rastor data" in QGIS to get elevation values for all stops 
# 3. Name the elevation column "elevation" in QGIS
# 4. Save the new data with elevation values into "stops_with_elevation.csv"


# CHECK POINT 2
# make sure the 'shape_dist_traveled' in 'stop_times' and 'shapes' in GTFS data is in KM unit


# CHECK POINT 3:
# the depot_list.csv file should have the following exact columns:
# 'Garage ID', 'Garage Name', 'Latitude', 'Longitude', 'Elevation', 'Gate', 'Agency ID'
# columns 'Gate' and 'Agency ID' can be blank
# 'Garage ID' should be garage if there is only one garage; or garage1, garage2... if there are more garages


# CHECK POINT 4:
# the charger location file needs to be.....