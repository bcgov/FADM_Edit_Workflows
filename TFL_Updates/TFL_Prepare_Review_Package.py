######################################################################
## TFL_Prepare_Review_Package.py
## Purpose: 1. Create a polygon feature for the areas of change
##          2. Create a TFL review map from template that highlights line and
##              area changes
##          3. Request summary text and create a draft change readme document
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
# constants for file and folder locations (local current state gdb, staging gdb)


###############################################################################
# get script tool parameters
input_folder = arcpy.GetParameterAsText(0) #Folder containing the TFL line edits
CHANGE_SUMMARY = arcpy.GetParameterAsText(1) #Text input - short statement of the nature of the change
CHANGE_DESCRIPTION = arcpy.GetParameterAsText(2) #Text input - short paragraph (or less) with detail as required


def runapp(TFL_Prepare_Review_Package):
#Create working geodatabase on the T drive

#Find areas of change by comparing the before and after polygons #IAN: could use Symmetrical Difference Overlay Tool

#Add the review map template to the review folder and path it

#Create the draft change summary and add it to the folder

#Consider testing for required contents (e.g. one MXD minimum, one document etc. . . discuss)

#If all tests are successful, message user and end script



###############################################################################
## Functions section
###############################################################################
def check_input_tfl():
    #check to make sure the fields are there - if not then the data source likely wrong



#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('TFL_Prepare_Review_Package')