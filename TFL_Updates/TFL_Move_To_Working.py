######################################################################
## TFL_Move_To_Working.py
## Purpose: 1. Move folder to the TFL Working folder from Pending or
##             Review folders. Used if changes are requested by reviewer
##             or for any other reason before a TFL change is finalized.
## Date: October, 2019
## Author: Jed Harrison, GeoBC
###############################################################################

# Import modules
import arcpy, sys, os, shutil
sys.path.append(TFL_Config.Resources.GEOBC_LIBRARY_PATH)
import geobc
import TFL_Config

###############################################################################
# set constants (always upper case)
# constants for file and folder locations (local current state gdb, staging gdb)
TFL_WORKING_FOLDERS = TFL_Config.TFL_Path.EDITS_FOLDER
TFL_REVIEW_FOLDERS = TFL_Config.TFL_Path.REVIEW_FOLDERS
TFL_PENDING_FOLDERS = TFL_Config.TFL_Path.PENDING_FOLDERS

###############################################################################
# get script tool parameters
input_main_folder = arcpy.GetParameterAsText(0) #Main folder (either Review or Pending)
input_tfl = arcpy.GetParameterAsText(1) #Folder containing the TFL package

def runapp(move_to_working):

    if input_main_folder == 'Review':
        input_folder = TFL_REVIEW_FOLDERS + os.sep + input_tfl
    else:
        input_folder = TFL_PENDING_FOLDERS + os.sep + input_tfl

    input_gdb = input_folder + os.sep +'Data' + os.sep + 'FADM_' + input_tfl + '.gdb'

    arcpy.AddMessage('input folder to move is: ' + input_folder)

    # Call check_for_locks method to check the gdb - compact first to address self-locks
    arcpy.Compact_management(input_gdb)
    gdb_object = geobc.GDBInfo(input_gdb)
    lock_owner_list = gdb_object.check_for_locks()
    if not lock_owner_list:
        arcpy.UncompressFileGeodatabaseData_management(input_gdb) #If the GDB is in pending - it is probably compressed
        #Move the required entities to the pending area
        try:
            shutil.copytree(input_folder,TFL_WORKING_FOLDERS + os.sep + input_tfl)
            #message user and end script
            arcpy.AddMessage('TFL folder has been copied to 2_TFL_Working folder')
            try:
                shutil.rmtree(input_folder)
                arcpy.AddMessage('TFL folder has been deleted from ' + input_main_folder)
            except:
                arcpy.AddWarning('Failed to delete entire contents from ' + input_main_folder + '. Please check that all files are closed and manually delete.')
        except:
            arcpy.AddWarning('Unable to fully copy folder - please check to ensure no files are open, delete the contents in TFL working if any, and try again')
    else:
        arcpy.AddWarning('WARNING: Found lock on geodatabase: ' + str(lock_owner_list) + 'Clear locks before trying again')



###############################################################################
## Functions section
###############################################################################

#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('move_to_working')