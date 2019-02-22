######################################################################
## TFL_Prepare_Edits.py
## Purpose: 1. Create a folder containing all required geodatabase classes,
##          map documents and folder requirements for the TFL Edit process.
##          Works with the TFL_Check_Edits and TFL_Submit_Edits script tools
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
# TFL_FINAL_FOLDER =
# TFL_TEMPLATES_FOLDER =
# TFL_EDITS_FOLDER =

###############################################################################
# get script tool parameters
input_tfl = arcpy.GetParameterAsText(0) #Folder containing the final TFL data for editing
schedule_a_only = arcpy.GetParameterAsText(1) #IF Only schedule A then a bunch of steps can be skipped


def runapp(tfl_prepare_edits):
#Copy the final folder to the Edit area #IAN: Do we need the entire folder or just elements of (e.g., just the gdb)?

#IAN: Copy TFL Poly (from Template)?

#Create the edit metadata table (date stamp and schedule A only flag)

#Rename the edit folder

#Delete all features from the poly and Point FC's


###############################################################################
## Functions section
###############################################################################
def check_input_tfl():



#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('tfl_prepare_edits')