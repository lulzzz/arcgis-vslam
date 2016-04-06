"""
vslam.py
A tool for creating a VSLAM path from visual tracking data compared against RTK GNSS points
"""

__author__ = 'Trevor Stanhope'
__version__ = 0.01

### Setup ###
# Import Modules
import arcpy
import os
from arcpy import env
import math # needed for maths
import numpy as np
env.workspace = os.getcwd()
env.overwriteOutput = True

# Constants
data_dir = 'data'
RTK_dir = 'RTK'
CV_dir = '1NN'
TRIAL_fname = 'asphault-2.csv'
GDB_dir = 'temp.gdb'
THRESHOLD_dir = '500'
skip_rows = 10
fps = 25.0 # camera capture rate

### Functions ###
def clearSchemaLocks(workspace):
    if all([arcpy.Exists(workspace), arcpy.Compact_management(workspace), arcpy.Exists(workspace)]):
        return True
    else:
        raise Exception("Workspace not clear!")

def projectXY(lat, lon, d, brng, R = 6378.1): 
    """
    ARGUMENTS:
        R : Radius of the Earth (kilometers)
        brng = Bearing (in Degrees)
        d : Distance (in Kilometers)
    RETURNS
        lat_proj, lon_prog : (tuple) projected position in decimal degrees
    """
    lat = math.radians(lat) # Current lat point converted to radians
    lon = math.radians(lon) # Current long point converted to radians
    lat_proj = math.asin(math.sin(lat)*math.cos(d/R) + math.cos(lat)*math.sin(d/R)*math.cos(brng))
    lon_proj = lon + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat), math.cos(d/R)-math.sin(lat)*math.sin(lat))
    lat_proj = math.degrees(lat_proj)
    lon_proj = math.degrees(lon_proj)
    return lat_proj, lon_proj

def calculateBearing(pointA, pointB):
    """
    Calculates the bearing between two points.
    NOTES
        The formulae used is the following:
            θ = atan2(sin(Δlong).cos(lat2), cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
        Latitude and longitude must be in decimal degrees
    ARGUMENTS
        pointA: (tuple) latitude/longitude for the first point.
        pointB: (tuple) atitude/longitude for the second point.
    RETURNS
        compass_bearing : (float) The bearing in degrees
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")
    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])
    diffLong = math.radians(pointB[1] - pointA[1])
    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))
    initial_bearing = math.atan2(x, y)
    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

### Run-time ###
# Create paths
print "Creating paths ..."
RTK_path = os.path.join(os.getcwd(), data_dir, RTK_dir, TRIAL_fname)
CV_path = os.path.join(os.getcwd(), data_dir, CV_dir, THRESHOLD_dir, TRIAL_fname)
GDB_path = os.path.join(os.getcwd(), GDB_dir)
print RTK_path, GDB_path, CV_path

# Load RTK table
print "Loading RTK csv-file ..."
RTK_table = os.path.join(GDB_path, 'RTK_table') # Name RTK table
arcpy.CopyRows_management(RTK_path, RTK_table)
arcpy.MakeXYEventLayer_management(RTK_table, "longitude", "latitude", "RTK_points", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision", "")
clearSchemaLocks(GDB_path)

# RTK Table to RTK Points
print "Converting RTK Table to Points ..."
RTK_points = os.path.join(GDB_path, 'RTK_points') # Name RTK points layer
arcpy.FeatureClassToFeatureClass_conversion("RTK_points", GDB_path, "RTK_points")
clearSchemaLocks(GDB_path)

# RTK Points to RTK Line
print "Converting RTK Points to Line ..."
RTK_line = os.path.join(GDB_path, 'RTK_line') # Name RTK table
arcpy.PointsToLine_management(RTK_points, RTK_line, "", "", "NO_CLOSE")
clearSchemaLocks(GDB_path)

# Load CV table
print "Loading CV csv-file ..."
CV_table = os.path.join(GDB_path, 'CV_table') # Name RTK table
arcpy.CopyRows_management(CV_path, CV_table)
clearSchemaLocks(GDB_path)

# Iterate through CV_table
for row in arcpy.SearchCursor(CV_table):
    print row.getValue("v")
