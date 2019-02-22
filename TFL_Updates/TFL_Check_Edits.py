######################################################################
## TFL_Check_Edits.py
## Purpose: 1. Check the edited TFL lines for attribute integrity
##          2. Run topology rules on the TFL lines
##          3. Build polygons and check spatial rules (overlaps, dangles)
## Date: February, 2019
## Author: Jed Harrison, GeoBC
###############################################################################


# Import modules
import arcpy, sys, os, datetime
from datetime import datetime
sys.path.append(r"\\spatialfiles.bcgov\work\ilmb\dss\dsswhse\Tools and Resources\Scripts\Python\Library")
import geobc

###############################################################################
# set constants (always upper case)
# constants for file and folder locations

###############################################################################
# get script tool parameters
input_tfl = arcpy.GetParameterAsText(0) #Folder containing the TFL line edits


def runapp(tfl_check_edits):
#Create working geodatabase on the T drive

#Check attribute rules on the lines (Need to discuss . . . )

#Run topology rules on the TFL lines - inform if there is any exceptions

#Convert lines to polygons on the TFL lines - inform if build fails #IAN: removed 'build'

#Append the output polygons to the empty schema

#   Consider tool map need map interaction - if the edit is a deletion or addition #IAN: to be removed

#Check to ensure that there are no lines that fall outside the TFL polys (external dangles)

#Internal buffer the poly and check that there are no polygons that intersect (internal dangles)

#Check that the poly does not overlap with any other TFL

#If all tests are successful, message user and end script



###############################################################################
## Functions section
###############################################################################
def check_input_tfl():
    #check to make sure the fields are there - if not then the data source likely wrong



#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('tfl_check_edits')