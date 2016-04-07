"""
vslam.py
A tool for creating a VSLAM path from visual tracking data compared against RTK GNSS points
"""

__author__ = 'Trevor Stanhope'
__version__ = 0.01

### Setup ###
# Import Modules
print "Importing modules ..."
import arcpy
import os
from arcpy import env
import math # needed for maths
import numpy as np
import matplotlib.pyplot as plt # plotting library
env.workspace = os.getcwd()
env.overwriteOutput = True

# Constants
print "Setting constants ..."
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
def calculateBearing(lat1, lon1, lat2, lon2):
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
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    diffLong = math.radians(lon2 - lon1)
    # Check if there is no movement between the two points
    if np.isclose(diffLong, 0):
        return np.NAN
    elif np.isclose(lat2 - lat1, 0):
        return np.NAN
    else:
        x = math.sin(diffLong) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))
        initial_bearing = math.atan2(x, y)
        # Now we have the initial bearing but math.atan2 return values
        # from -180° to + 180° which is not what we want for a compass bearing
        # The solution is to normalize the initial bearing as shown below
        initial_bearing = math.degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360
        return compass_bearing
def calculateDistance(lon1, lat1, lon2, lat2, R = 6371):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    RETURNS
        distance : (float) Great circle distance in units of R
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2 # haversine formula 
    c = 2 * math.asin(math.sqrt(a))
    distance = c * R # scale by radius of earth in kilometers (Use 3956 for miles)
    return distance
def linterpNAN(data):
    """
    linearly interpolates NaN values using their nearest neighbors
    ARGUMENTS:
        data : (ndArray) data array containing NaNs
    RETURNS:
        data : (ndArray) data array without NaNs
    """
    mask = np.isnan(data)
    data[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), data[~mask])
    return data
def smooth(y, box_pts=10):
    """
    Smooth data using a moving average by convolution
    """
    box = np.ones(box_pts) / box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth

### Run-time ###
# Create paths
print "Generating paths to files..."
RTK_path = os.path.join(os.getcwd(), data_dir, RTK_dir, TRIAL_fname)
CV_path = os.path.join(os.getcwd(), data_dir, CV_dir, THRESHOLD_dir, TRIAL_fname)
GDB_path = os.path.join(os.getcwd(), GDB_dir)
print "\tRTK: " + RTK_path
print "\tGDB: " + GDB_path
print "\tCV: " + CV_path

# Load RTK table
print "Loading RTK csv-file ..."
RTK_table = os.path.join(GDB_path, 'RTK_table') # Name RTK table
arcpy.CopyRows_management(RTK_path, RTK_table)
arcpy.MakeXYEventLayer_management(RTK_table, "longitude", "latitude", "RTK_points", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision", "")
#clearSchemaLocks(GDB_path)

# RTK Table to RTK Points
print "Converting RTK Table to Points ..."
RTK_points = os.path.join(GDB_path, 'RTK_points') # Name RTK points layer
arcpy.FeatureClassToFeatureClass_conversion("RTK_points", GDB_path, "RTK_points") # need to use imaginary feature name
#clearSchemaLocks(GDB_path)

# RTK Points to RTK Line
print "Converting RTK Points to Line ..."
RTK_line = os.path.join(GDB_path, 'RTK_line') # Name RTK table
arcpy.PointsToLine_management(RTK_points, RTK_line, "", "", "NO_CLOSE")
#clearSchemaLocks(GDB_path)

# Load CV table
print "Loading CV csv-file ..."
CV_table = os.path.join(GDB_path, 'CV_table') # Name RTK table
arcpy.CopyRows_management(CV_path, CV_table)
#clearSchemaLocks(GDB_path)

# Iterate through RTK Table
print "Estimating bearing using for RTK ..."
lat_start = 0.0
lon_start = 0.0
lat1 = 0.0
lon1 = 0.0
lat2 = 0.0
lon2 = 0.0
bearing_array = []
distance_array = []
i = 0
for row in arcpy.SearchCursor(RTK_table):    
    # store previous values
    lat1 = lat2
    lon1 = lon2
    lat2 = row.getValue("latitude")
    lon2 = row.getValue("longitude")
    if i == 0: # get the first point
        lat_start = lat2
        lon_start = lon2
    point1 = (lat1, lon1)
    point2 = (lat2, lon2)
    bearing = calculateBearing(lat1, lon1, lat2, lon2)
    bearing_array.append(bearing)
    distance = calculateDistance(lat1, lon1, lat2, lon2)
bearing_array = smooth(linterpNAN(np.array(bearing_array)))
plt.plot(bearing_array)
plt.show()

# Iterate through CV Table
speed_array = []
direction_array = []
for row in arcpy.SearchCursor(CV_table):
    speed = row.getValue("v")
    speed_array.append(speed)
    direction = row.getValue("t")
    direction_array.append(direction)
speed_array = np.array(speed_array)
direction_array = np.array(direction_array)
plt.plot(speed_array)
plt.show()

# Convert NumPy array to a feature class
#arcpy.da.NumPyArrayToFeatureClass(arr, out_fc, ['XY'], spatial_ref)
