# Create a new line feature class using a text file of coordinates.
#   Each coordinate entry is semicolon delimited in the format of ID;X;Y

# Import native arcgisscripting module and other required modules
#
import arcgisscripting
import fileinput
import os
import string

# Create the geoprocessor object
#
gp = arcgisscripting.create(9.3)
gp.OverWriteOutput = 1

# Get the coordinate ascii file
#
infile = gp.GetParameterAsText(0)

# Get the output feature class
#
fcname = gp.GetParameterAsText(1)

# Get the template feature class
#
template = gp.GetParameterAsText(2)
try:
   # Create the output feature class
   #
   gp.CreateFeatureClass(os.path.dirname(fcname),os.path.basename(fcname), 
                              "Polyline", template)

   # Open an insert cursor for the new feature class
   #
   cur = gp.InsertCursor(fcname)

   # Create an array and point object needed to create features
   #
   lineArray = gp.CreateObject("Array")
   pnt = gp.CreateObject("Point")

   # Initialize a variable for keeping track of a feature's ID.
   #
   ID = -1 
   for line in fileinput.input(infile): # Open the input file
      # set the point's ID, X and Y properties
      #
      pnt.id, pnt.x, pnt.y = string.split(line,";")
      print pnt.id, pnt.x, pnt.y
      if ID == -1:
         ID = pnt.id

      # Add the point to the feature's array of points
      #   If the ID has changed, create a new feature
      #
      if ID != pnt.id:
         # Create a new row or feature, in the feature class
         #
         feat = cur.NewRow()

         # Set the geometry of the new feature to the array of points
         #
         feat.shape = lineArray

         # Insert the feature
         #
         cur.InsertRow(feat)
         lineArray.RemoveAll()
      lineArray.add(pnt)
      ID = pnt.id

   # Add the last feature
   #
   feat = cur.NewRow()
   feat.shape = lineArray
   cur.InsertRow(feat)

   lineArray.RemoveAll()
   fileinput.close()
   del cur
except:
   print gp.GetMessages(2)