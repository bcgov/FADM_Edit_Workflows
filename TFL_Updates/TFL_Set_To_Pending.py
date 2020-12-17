######################################################################
## TFL_Set_To_Pending.py
## Purpose: 1. After review - remove topology and
##          2. Move folder to the TFL Pending folder where a separate
##             process will watch for the pending dates and when date is
##             reached notify reviewers to trigger the next stage
## Date: September, 2019
## Author: Jed Harrison, GeoBC
###############################################################################

# Import modules
import arcpy, sys, os, datetime, getpass, shutil
from datetime import datetime
import time
import TFL_Config
sys.path.append(TFL_Config.Resources.GEOBC_LIBRARY_PATH)
import geobc
from utils import coded_domain_validation

###############################################################################
# set constants (always upper case)
# constants for file and folder locations
TFL_REVIEW_FOLDERS = TFL_Config.TFL_Path.REVIEW_FOLDERS
TFL_PENDING_FOLDERS = TFL_Config.TFL_Path.PENDING_FOLDERS

###############################################################################
# get script tool parameters
input_tfl = arcpy.GetParameterAsText(0) #Folder containing the TFL review package
check_1 = arcpy.GetParameterAsText(1)
check_2 = arcpy.GetParameterAsText(2)
check_3 = arcpy.GetParameterAsText(3)

input_folder = TFL_REVIEW_FOLDERS + os.sep + input_tfl
input_gdb = input_folder + os.sep +'Data' + os.sep + 'FADM_' + input_tfl + '.gdb'
workspace = os.path.join(input_gdb, 'TFL_Data')
reviewed_timestamp = datetime.now()

def runapp(tfl_set_to_pending):

    #Confirm that user marked all checks as complete
    if check_1 and check_2 and check_3:

        arcpy.AddMessage('dataset to move is ' + input_gdb)

        # Call check_for_locks method to check the gdb
        gdb_object = geobc.GDBInfo(input_gdb)
        lock_owner_list = gdb_object.check_for_locks()
        if not lock_owner_list:

            #Check to ensure the reviewer running the tool is not the user who extracted the TFL (assumed to be the editor)
            user = getpass.getuser()
            edit_user = get_editor()
            arcpy.Compact_management(input_gdb)
            lock_owner_list = gdb_object.check_for_locks()
            arcpy.AddMessage('Check for locks after get editor: ' + str(lock_owner_list))
            if not user == edit_user:

                errors = coded_domain_validation.validate_domains(input_gdb, workspace)

                if not errors:
                    arcpy.AddMessage('\nNo attribute value errors found')

                    #Remove the topologies
                    remove_topology(input_gdb)
                    arcpy.Compact_management(input_gdb)
                    lock_owner_list = gdb_object.check_for_locks()
                    arcpy.AddMessage('Check for locks after remove topology: ' + str(lock_owner_list))
                    #Remove TFL_Active_Lines FC
                    if arcpy.Exists(input_gdb + os.sep + 'TFL_Data' + os.sep + 'TFL_Active_Lines'):
                        arcpy.Delete_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'TFL_Active_Lines')
                    #Set the reviewer
                    set_reviewer(user)
                    #Move the required entities to the pending area
                    arcpy.Compact_management(input_gdb) #compact to remove any self-locks
                    gdb_object = geobc.GDBInfo(input_gdb)
                    lock_owner_list = gdb_object.check_for_locks()
                    arcpy.AddMessage('Check for locks after setting reviewer ' + str(lock_owner_list))
                    arcpy.CompressFileGeodatabaseData_management(input_gdb) #compress gdb to prevent changes from here to final
                    if not lock_owner_list:
                        try:
                            shutil.copytree(input_folder,TFL_PENDING_FOLDERS + os.sep + input_tfl)
                            #message user and end script
                            arcpy.AddMessage('Copied - TFL folder to 4_TFL_Pending folder')
                            try:
                                shutil.rmtree(input_folder)
                                arcpy.AddMessage('Deleted- TFL folder from 3_TFL_Review folder')
                            except:
                                arcpy.AddWarning('WARNING: Unable to delete entire folder after copy - please check that Pending folder is complete then close all files and delete Review folder')
                        except:
                            arcpy.AddWarning('WARNING: Unable to copy entire folder - please delete the folder and all contents in 3_TFL_Review. Then be sure all files are closed before trying again')
                    else:
                        arcpy.AddWarning('Found lock on geodatabase: ' + str(lock_owner_list))
            else: #Message the user that the editor cannot review and promote the data
                arcpy.AddWarning('Review cannot be completed by the same user that ran edit tools')

        else:
            arcpy.AddWarning('WARNING: Found lock on geodatabase: ' + str(lock_owner_list))
    else:
        arcpy.AddWarning('WARNING: Tool cannot be run until all checks have been confirmed')

###############################################################################
## Functions section
###############################################################################
def remove_topology(input_gdb):
    """Removes topology from the database"""
    if arcpy.Exists(input_gdb + os.sep + 'TFL_Data' + os.sep + 'TFL_Line_Topology'):
        arcpy.Delete_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'TFL_Line_Topology')
        arcpy.AddMessage('Deleted TFL_Line_Topology')
    if arcpy.Exists(input_gdb + os.sep + 'TFL_Data' + os.sep + 'TFL_Active_Line_Topology'):
        arcpy.Delete_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'TFL_Active_Line_Topology')
        arcpy.AddMessage('Deleted TFL_Active_Line_Topology')

def get_editor():
    """takes input gdb and tfl name, and finds the user for the check edits
        note that this table should only ever have a single record"""
    table = input_gdb + os.sep + input_tfl + '_Transaction_Details'
    fields = ['Edits_Checked_By']
    edit_user = ''
    with arcpy.da.SearchCursor(table,fields,) as cursor:
        for row in cursor:
            edit_user = row[0]
        del row
    del cursor
    return(edit_user)


def set_reviewer(user):
    """sets the user for the reviewer
        note that this table should only ever have a single record"""
    table = input_gdb + os.sep + input_tfl + '_Transaction_Details'
    fields = ['Review_Passed','Reviewed_Date','Reviewed_By']
    with arcpy.da.UpdateCursor(table,fields,) as cursor:
        for row in cursor:
            row[0] = 'Yes'
            row[1] = reviewed_timestamp
            row[2] = user
            cursor.updateRow(row)
        del row
    del cursor


#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('set_to_pending')