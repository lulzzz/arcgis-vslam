# ---------------------------------------------------------------------------
# Table2Lines.py
# Created: 2011-01-12
# Author: Regan Sarwas, National Park Service
#
# Builds a line feature class from a line data table and a point feature class
# The line table must have three fields for the line Id, point1 Id, and point2 Id
# The point feature class must be a point (not multi-point) shape type and have a
# field with the point id that matches the type and domain of the point ids in the line table.
# The names of all fields are provided in the input arguments
#
# usage:
# python Table2Lines.py path_to_line_table Line_ID_Field From_Point_ID_Field To_Point_ID_Field
#                       path_to_point_FC Point_ID_Field output_line_FC
# example:
# python Table2Lines.py "c:\tmp\lines.csv" "ID" "From" "To" "c:\tmp\pts.shp" "MY_ID" "c:\tmp\lines.shp"
#
# License:
#  Public Domain
# Disclaimer:
#  This software is provide "as is" and the National Park Service gives
#  no warranty, expressed or implied, blah, blah, blah 
# ---------------------------------------------------------------------------

import os, arcgisscripting
gp = arcgisscripting.create(9.3)
gp.Overwriteoutput = 1

#I use one search cursor and cache all the points in a dictionary.
#This avoids creating a search cursor for each point as lines are processed
#Assumes Python is more efficient and faster than ArcGIS.  Should be tested.
def GetPoints(pointFC,pointIDField):
    points = {}
    pointDescription = gp.Describe(pointFC)
    pointShapeField = pointDescription.ShapeFieldName
    pointIdFieldDelimited = gp.AddFieldDelimiters(pointFC, pointIdField)
    where = pointIdFieldDelimited + " is not null"
    spatialRef = ""
    fields = pointIDField +"; " + pointShapeField
    sort = ""
    pts = gp.SearchCursor(pointFC, where, spatialRef, fields, sort)
    pt = pts.Next()
    while pt != None:
        points[pt.GetValue(pointIDField)] = pt.Shape.getPart()
        pt = pts.Next()
    return points

def MakeLine(pt1, pt2):
    """ pt1 and pt2 should be gp point objects or None """
    if (pt1 == None or pt2 == None):
        return None
    pts = gp.createobject("Array")
    pts.add(pt1)
    pts.add(pt2)
    line = gp.createobject("geometry", "polyline", pts)
    if (line == None) or (line.FirstPoint == None) or (line.LastPoint == None):
        return None
    return line

# Input field types must be in mapType (defined below).
# Point id type in both input data sets must map to the same type, i.e. OID and Integer

# Maps the string returned by gp.describe.Field.Type to the string required by gp.AddField()
mapType = {"SmallInteger" : "SHORT",
           "Integer" : "LONG",
           "Single" : "FLOAT",
           "Double" : "DOUBLE",
           "String" : "TEXT",
           "Date" : "DATE",
           "OID" : "LONG",      #Not usually creatable with AddField() - use with Caution
           "Geometry" : "BLOB", #Not usually creatable with AddField() - use with Caution
           "BLOB" : "BLOB"}

#GET INPUT
lineTable = gp.GetParameterAsText(0)
lineIdField = gp.GetParameterAsText(1)
fromPointIdField = gp.GetParameterAsText(2)
toPointIdField = gp.GetParameterAsText(3)
pointFC = gp.GetParameterAsText(4)
pointIdField = gp.GetParameterAsText(5)
lineFC = gp.GetParameterAsText(6)

#VERIFY INPUT (mostly for command line.  Toolbox does some validation for us)
lineIdFieldType = ""
fromPointIdFieldType = ""
toPointIdFieldType = ""
tableDescription = gp.Describe(lineTable)
for field in tableDescription.Fields:
    if field.Name == lineIdField:
        lineIdFieldType = mapType[field.Type]
    if field.Name == fromPointIdField:
        fromPointIdFieldType = mapType[field.Type]
    if field.Name == toPointIdField:
        toPointIdFieldType = mapType[field.Type]

if lineIdFieldType == "":
    raise ValueError("Field '" + lineIdField + "' not found in " + lineTable)
if fromPointIdFieldType == "":
    raise ValueError("Field '" + fromPointIdField + "' not found in " + lineTable)
if toPointIdFieldType == "":
    raise ValueError("Field '" + toPointIdField + "' not found in " + lineTable)

pointDescription = gp.Describe(pointFC)
if pointDescription.shapeType != "Point":
    raise ValueError(pointFC + " is a " + pointDescription.shapeType +
                     " not a Point Feature Class.")

pointIdFieldType = ""    
for field in pointDescription.Fields:  
    if field.Name == pointIdField:
        pointIdFieldType = mapType[field.Type]
        break

if pointIdFieldType == "":
    raise ValueError("Field '" + pointIdField + "' not found in " + pointFC)
if (pointIdFieldType != fromPointIdFieldType or
    pointIdFieldType != fromPointIdFieldType):
    raise ValueError("Field types do not match - cannot link points to lines.")

gp.AddMessage("Input validated")

# Create Feature Class...
outSpatialRef = pointDescription.SpatialReference
outPath, outName = os.path.split(lineFC)
gp.CreateFeatureclass_management(outPath, outName, "POLYLINE", "", "DISABLED", "DISABLED", outSpatialRef, "", "0", "0", "0")

gp.AddMessage("Created the output feature class")

# Add Fields...
lineIdFieldValid = gp.ValidateFieldName(lineIdField,outPath)
gp.AddField_management(lineFC, lineIdFieldValid, lineIdFieldType, "", "", "", "", "NON_NULLABLE", "REQUIRED", "")
fromPointIdFieldValid = gp.ValidateFieldName(fromPointIdField,outPath)
gp.AddField_management(lineFC, fromPointIdFieldValid, fromPointIdFieldType, "", "", "", "", "NON_NULLABLE", "REQUIRED", "")
toPointIdFieldValid = gp.ValidateFieldName(toPointIdField,outPath)
gp.AddField_management(lineFC, toPointIdFieldValid, toPointIdFieldType, "", "", "", "", "NON_NULLABLE", "REQUIRED", "")

gp.AddMessage("Added the fields to the output feature class")

points = GetPoints(pointFC,pointIdField)

fromPointIdFieldDelimited = gp.AddFieldDelimiters(lineTable, fromPointIdField)
toPointIdFieldDelimited = gp.AddFieldDelimiters(lineTable, toPointIdField)
where = fromPointIdFieldDelimited + " is not null and " + toPointIdFieldDelimited + " is not null"
spatialRef = ""
#fields = lineIdField +"; " + fromPointIdField +"; " +toPointIdField
fields = ""
sort = ""
#Create the input(search) and output(insert) cursors.
lines = gp.SearchCursor(lineTable, where, spatialRef, fields, sort)
newLines = gp.InsertCursor(lineFC)

line = lines.Next()
while line != None:
    pt1Id = line.GetValue(fromPointIdField)
    pt2Id = line.GetValue(toPointIdField)
    try:
        lineGeom = MakeLine(points[pt1Id],points[pt2Id])
    except:
        lineGeom = None
    if lineGeom == None:
        gp.AddWarning("Unable to create line " + str(line.GetValue(lineIdField)))
    else:
        # Create a new feature in the feature class
        newLine = newLines.NewRow()
        newLine.Shape = lineGeom
        newLine.SetValue(lineIdFieldValid, line.GetValue(lineIdField))
        newLine.SetValue(fromPointIdFieldValid, pt1Id)
        newLine.SetValue(toPointIdFieldValid, pt2Id)
        newLines.insertRow(newLine)
    line = lines.Next()

#Closes the insert cursor, and releases the exclusive lock
del newLine
del newLines
gp.AddMessage("Done.")