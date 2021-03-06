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
import re
import TFL_Config
sys.path.append(TFL_Config.Resources.GEOBC_LIBRARY_PATH)
import geobc
from utils import coded_domain_validation
from utils.test_prod_check import test_in_working_dir


###############################################################################
# set constants (always upper case)
# constants for file and folder locations
working_location = os.path.abspath(__file__)
test = test_in_working_dir(working_location)

TFL_Path = TFL_Config.TFL_Path(test=test)

TFL_REVIEW_FOLDERS = TFL_Path.REVIEW_FOLDERS
TFL_PENDING_FOLDERS = TFL_Path.PENDING_FOLDERS

###############################################################################
# get script tool parameters
input_tfl = arcpy.GetParameterAsText(1) #Folder containing the TFL review package
check_1 = arcpy.GetParameterAsText(2)
check_2 = arcpy.GetParameterAsText(3)
check_3 = arcpy.GetParameterAsText(4)

input_folder = TFL_REVIEW_FOLDERS + os.sep + input_tfl
tfl_number = re.search("^TFL_[0-9]+", input_tfl).group()
input_gdb = input_folder + os.sep + 'Data' + os.sep + 'FADM_' + tfl_number + '.gdb'
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
            if test:
                user = 'Test_Username'

            edit_user = get_editor()
            arcpy.Compact_management(input_gdb)
            lock_owner_list = gdb_object.check_for_locks()
            arcpy.AddMessage('Check for locks after get editor: ' + str(lock_owner_list))
            if not user == edit_user:

                errors = coded_domain_validation.validate_domains(input_gdb, workspace)

                if not errors:
                    arcpy.AddMessage('\nNo attribute value errors found')

                    #Remove the topologies
                    remove_topology_and_active_lines(workspace)
                    arcpy.Compact_management(input_gdb)
                    lock_owner_list = gdb_object.check_for_locks()
                    arcpy.AddMessage('Check for locks after remove topology: ' + str(lock_owner_list))

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
def remove_topology_and_active_lines(workspace):
    """Removes topology from the database"""
    arcpy.env.workspace = workspace

    for fc in arcpy.ListDatasets():
        if 'Topology' in fc:
            arcpy.Delete_management(fc)

    for fc in arcpy.ListFeatureClasses():
        if fc.startswith('TFL_Active_Lines'):
            arcpy.Delete_management(fc)
  

def get_editor():
    """takes input gdb and tfl name, and finds the user for the check edits
        note that this table should only ever have a single record"""
    table = input_gdb + os.sep + tfl_number + '_Transaction_Details'
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
    table = input_gdb + os.sep + tfl_number + '_Transaction_Details'
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