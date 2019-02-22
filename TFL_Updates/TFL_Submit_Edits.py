######################################################################
## TFL_Submit_Edits.py
## Purpose: 1. Archive the previous TFL change folder in the final
##          2. Move and rename the TFL edit folder to final - clean up as needed
##          2. Update TFL overview / TFL additions-delections as required
##          3. Post required changes to the BCGW staging area
##          4. Notify required staff that a change has been posted
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
#DATABC_STAGING_FOLDER =
#TFL_FINAL_FOLDER =
#TFL_OVERVIEW_FINAL =

###############################################################################
# get script tool parameters
input_folder = arcpy.GetParameterAsText(0) #Folder containing the TFL review package
REVIEWER_COMMENTS = arcpy.GetParameterAsText(1) #Do we need this?

def runapp(tfl_submit_edits):
#Move the review package folder to the new final and rename it with datestamp

#Remove the previous TFL from the TFL overview and add the updated one

#IF addition or deletion, update the FC in the databc staging area

#Update the readme doc header with the reviewer and editor names and any comments

#Move the required entities to the staging area (WE NEED FULL LIST OF PRODUCTS HERE)

#TFL Current view (to BCGW)
#TFL Additions (to BCGW)
#TFL Deletions (to BCGW)
#TFL Schedule A (Discuss!!! Does this need to be part of automation?)
#IAN: TFL Replacement (or Agreement Boundary) - i.e., the layer that gets updated only once every 10 years

#Create and update local outputs

#TFL Final folder renamed with date and moved from edits
#Create copy of cadastre that intersects TFL lines and add to final folder
#Trigger any scripts that are required (e.g. does interest report tool need an updated layer?
#TFL/TSA layer (GeoBC Local)

#If all tests are successful, message user and end script



###############################################################################
## Functions section
###############################################################################
def check_input_tfl():


#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('tfl_submit_edits')