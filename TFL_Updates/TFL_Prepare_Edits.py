######################################################################
## TFL_Prepare_Edits.py
## Purpose: 1. Create a folder containing all required geodatabase classes
##          and folder requirements for the TFL Edit process. #IAN - add bit more detail
##          Works with the TFL_Check_Edits, TFL_Prepare_Review_Package
##          and TFL_Submit_Edits script tools
## Date: February, 2019
## Author: Jed Harrison, GeoBC
###############################################################################
#IAN - add versioning and modification notes after satisfied w/ v0.1

# Import modules
import arcpy, sys, os, datetime, shutil, getpass
from os.path import join
from datetime import datetime
from distutils.dir_util import copy_tree
import TFL_Config
sys.path.append(TFL_Config.Resources.GEOBC_LIBRARY_PATH)
import geobc
from utils.test_prod_check import test_in_working_dir


###############################################################################
# set constants (always upper case)
working_location = os.path.abspath(__file__)
test = test_in_working_dir(working_location)

TFL_Path = TFL_Config.TFL_Path(test=test)

TFL_FINAL_FOLDER = TFL_Path.FINAL_FOLDER
TFL_EDITS_FOLDER = TFL_Path.EDITS_FOLDER
TFL_REVIEW_FOLDER = TFL_Path.REVIEW_FOLDERS
TFL_PENDING_FOLDER = TFL_Path.PENDING_FOLDERS

TFL_TEMPLATES_GDB = TFL_Path.TEMPLATES_GDB

###############################################################################
# get script tool parameters
input_tfl = arcpy.GetParameterAsText(1) #Folder containing the final TFL data for editing
input_tfl = TFL_FINAL_FOLDER + os.sep + input_tfl #combine the input folder name with the base folder to get full path
bcgw_uname = arcpy.GetParameterAsText(2)
bcgw_pw = arcpy.GetParameterAsText(3)

#determine TFL basename from the input folder
folder_basename = (input_tfl.split(os.sep)[-1])[0:6]
extract_timestamp = datetime.now()

#NOTE: Consider adding code to check domain values in template GDB and update local if required

def runapp(tfl_prepare_edits):

    arcpy.AddMessage('extracted at '+str(extract_timestamp))

    #establish the BCGW connection to check the schedule A AND TFL Boundary
    BCGWConnection = get_bcgw_connection(bcgw_uname,bcgw_pw)

    if not BCGWConnection is False: #only proceed if connection succeeds

        #Copy the final folder to the Edit area
        can_copy = copy_input_tfl(folder_basename)

        #only proceed if the edit folder does not already exist and copy succeeded
        if can_copy == True:
            manage_keep_folder(folder_basename)


            #uncompress the gdb - final is compressed to prevent accidental edits
            arcpy.UncompressFileGeodatabaseData_management(TFL_EDITS_FOLDER + os.sep + folder_basename + os.sep + \
            'data' + os.sep + 'FADM_' + folder_basename + '.gdb')

            #Workspace is the feature dataset
            workspace = TFL_EDITS_FOLDER + os.sep + folder_basename + os.sep + \
            'data' + os.sep + 'FADM_' + folder_basename + '.gdb' + os.sep + 'TFL_Data'

            # enable editor tracking on lines
            tfl_lines = os.path.join(workspace, folder_basename + '_Line')
            arcpy.EnableEditorTracking_management(tfl_lines, 'created_user', 'created_date', 'last_edited_user', 'last_edited_date', 'NO_ADD_FIELDS', 'DATABASE_TIME')

            #Delete all tables from Edit gdb except the TFL Lines and Schedule A
            delete_tables(workspace)

            #Copy empty feature classes and metadata table from template
            copy_tables_from_template(workspace, folder_basename)

            #Delete all lines with status NOT active
            delete_non_active_lines(workspace, folder_basename)

            #check to see if the lines build one or more polygons
            create_polys(workspace,folder_basename)

            #check the schedule A AND TFL Boundary layers for differences
            check_bcgw_to_final_differences(folder_basename,workspace,BCGWConnection)

            #Create topology and add lines to it
            create_topology(workspace,folder_basename)

            #Run topology and report any errors - these are info only
            run_topology(workspace)

            #Set initial values for the Change History table
            user = getpass.getuser()
            table = workspace[:-9] + os.sep + folder_basename + '_Change_History'
            update_change_history(table,extract_timestamp,user)

    else:
        arcpy.AddError('Error creating BCGW Connection - try again')

###############################################################################
## Functions section
###############################################################################
def copy_input_tfl(folder_basename):
    """ Takes input folder - creates folder structure and copies data from final folder returns Boolean True for success"""
    tfl_edit_folder = join(TFL_EDITS_FOLDER, folder_basename)
    tfl_final_folder = join(TFL_FINAL_FOLDER, folder_basename)

    subdirs = os.listdir(tfl_final_folder)

    # if not os.path.exists(tfl_edit_folder):
    if not tfl_exists(folder_basename):

        #create new edit folder and add all the folders except data (gets copied below)
        arcpy.AddMessage('Creating edit folder: ' + tfl_edit_folder)
        os.mkdir(tfl_edit_folder)

        for subdir in subdirs:
            os.mkdir(join(tfl_edit_folder, subdir))


        arcpy.Copy_management(join(input_tfl, 'data', 'FADM_' + folder_basename + '.gdb'), \
                            join(TFL_EDITS_FOLDER, folder_basename, 'data', 'FADM_' + folder_basename + '.gdb'))

        arcpy.AddMessage('Completed copy from TFL Final\n')
        return True
    else:
        # arcpy.AddError(folder_basename + ' already exits in 2_TFL_Edits Folder. Please review data within existing folder to ensure no-one else is working on TFL edits')
        return False


def manage_keep_folder(folder_basename):
    """
    Written to manage the folder in 'documents' which contains any document relevant to the current TFL update
    """
    
    update_support_dir = join(TFL_FINAL_FOLDER, folder_basename, 'documents', 'Update_Support_Documents')   # Dir containing relevant update documents in Final folder

    edit_folder_documents_dir = join(TFL_EDITS_FOLDER, folder_basename, 'documents')    # Dir where we want to copy relevant documents to

    if len(os.listdir(update_support_dir)) > 0:
        copy_tree(update_support_dir, edit_folder_documents_dir)
        arcpy.AddWarning('==== THERE ARE DOCUMENTS RELEVANT TO THIS UPDATE, PLEASE CHECK DOCUMENTS FOLDER\n')


def tfl_exists(folder_basename):
    """
    Checks to ensure that the TFL being loaded for edits is not present anywhere else in the update process
    """

    dirs_to_check = [TFL_EDITS_FOLDER, TFL_REVIEW_FOLDER, TFL_PENDING_FOLDER]

    for dir in dirs_to_check:
        tfls_being_updated = os.listdir(dir)
        if folder_basename in tfls_being_updated:
            arcpy.AddError('{} already exists in {}. You cannot start another update of {} while it is present elsewhere in the update workflow'.format(folder_basename, (dir.split(os.sep))[-1], folder_basename))
            return True

    return False


def delete_tables(workspace):
    """Take edit workspace and delete all database tables that are not used as inputs (TFL Lines and Schedule A excepted)"""
    arcpy.env.workspace = workspace
    feature_classes = arcpy.ListFeatureClasses()
    if not feature_classes:
        arcpy.AddError('ERROR: no feature classes found in input database')
    else:
        for feature_class in feature_classes:
            if not ((str(feature_class)[-4:] == 'Line') or (str(feature_class)[-10:] == 'Schedule_A')or (str(feature_class)[-9:] == 'Map_Point')):
                arcpy.Delete_management(feature_class)
                #Delete polygons and map points

        #reset workspace back up to remove feature dataset from path
        #to delete un-needed f/c and transaction table within root of Edit gdb
        arcpy.env.workspace = workspace[:-9]
        tables = arcpy.ListTables()
        #delete all tables except the change history
        if not tables == []:
            for table in tables:
                if not (str(table)[-14:] == 'Change_History'):
                    arcpy.AddMessage('----- deleting table: ' + table)
                    arcpy.Delete_management(table)
        #delete any feature classes that were added to the geodatabase
        feature_classes = arcpy.ListFeatureClasses()
        for feature_class in feature_classes:
            arcpy.AddMessage('----- deleting feature class: ' + feature_class)
            arcpy.Delete_management(feature_class)
        arcpy.AddMessage('Completed delete tables\n')

def copy_tables_from_template(workspace, folder_basename):
    """Copies tables from the template database to the edit workspace - excluding TFL Lines and Schedule A"""
    arcpy.env.workspace = TFL_TEMPLATES_GDB
    feature_classes = arcpy.ListFeatureClasses()
    if feature_classes == []:
        arcpy.AddError('ERROR: no feature classes found in template database')
    else:
        for feature_class in feature_classes:
            if (str(feature_class)[-8:] == 'Boundary'):
                source = TFL_TEMPLATES_GDB + os.sep + feature_class
                #replace TFL_xx with folder_basename (e.g., TFL_39)
                destination = workspace + os.sep + folder_basename + (feature_class)[6:]
                arcpy.FeatureClassToFeatureClass_conversion(source,workspace,folder_basename + (feature_class)[6:])
##                arcpy.Copy_management(source, destination)
                arcpy.AlterAliasName(destination,folder_basename + (feature_class)[6:])
                arcpy.AddMessage('Copied ' + feature_class + ' from template')

        #reset the workspace to remove the feature dataset then copy the transaction details table
        arcpy.env.workspace = TFL_TEMPLATES_GDB[:-9]
        tables = arcpy.ListTables()
        if not tables == []:
            for table in tables:
                if table == 'TFL_XX_Transaction_Details':
                    source = TFL_TEMPLATES_GDB[:-9] + os.sep + table
                    destination = workspace[:-9] + os.sep + folder_basename + (table)[6:]
                    arcpy.Copy_management(source, destination)
                    arcpy.AlterAliasName(destination,folder_basename + (table)[6:])
                    arcpy.AddMessage('Copied ' + table + ' from template')
        arcpy.AddMessage('Completed copy of tables from template database\n')

def delete_non_active_lines(workspace, folder_basename):
    """Deletes any lines that do not have Status Code = ACTIVE from the TFL Lines - these should represent the current boundary"""
    arcpy.env.workspace = workspace
    arcpy.MakeFeatureLayer_management(workspace + os.sep + folder_basename + '_Line',folder_basename + '_Line_FL')
    where_clause = "Status_Code <> 'ACTIVE'"
    arcpy.SelectLayerByAttribute_management(folder_basename + '_Line_FL','NEW_SELECTION',where_clause)
    if int(arcpy.GetCount_management(folder_basename + '_Line_FL')[0]) > 0:
        arcpy.DeleteFeatures_management(folder_basename + '_Line_FL')
        arcpy.AddMessage('Deleting non-active lines')
    else:
        arcpy.AddMessage('Did not find any non-active lines')
    #IAN - return something if it can't even evaluate the selectLayerByAttribute...e.g., #arcpy.GetMessages()
    arcpy.AddMessage('Completed search and delete function for non-active lines\n')

def create_polys(input_workspace, folder_basename):
    """"Takes input TFL lines and attempts to build polygons to a temp layer. If build
    succeeds, informs user and deletes the temp feature class. If no polygons created,
    deletes temp feature class and warns user"""

    tfl_lines = input_workspace + os.sep + folder_basename + '_Line'

    #Check if a previous temp poly exists - if so delete it first
    if arcpy.Exists(input_workspace + os.sep + 'Temp_Poly'):
        arcpy.Delete_management(input_workspace + os.sep + 'Temp_Poly')

    #select only the active and retired lines - use to build polys - retired lines are used for deletions
    arcpy.MakeFeatureLayer_management(tfl_lines, 'tfl_lines_layer', "Status_Code = 'ACTIVE'")

    arcpy.FeatureToPolygon_management('tfl_lines_layer', input_workspace + os.sep + 'Temp_Poly')
    if int(arcpy.GetCount_management(input_workspace + os.sep + 'Temp_Poly').getOutput(0)) == 0:
        arcpy.AddWarning("===== Warning - No polygons created using input active lines\n")
        arcpy.Delete_management(input_workspace + os.sep + 'Temp_Poly')
    else:
        #If there are any records then at least one polygon built - inform user
        arcpy.AddMessage('One or more polygons created from active input lines\n')
        arcpy.Delete_management(input_workspace + os.sep + 'Temp_Poly')

def create_topology(workspace, folder_basename):
    """Creates topology in the edit workspace and adds rules to the TFL Lines"""
    arcpy.env.workspace = workspace
    cluster_tol = 0.0001
    topology = workspace + os.sep + 'TFL_Line_Topology'
    feature_class = workspace + os.sep + folder_basename + '_Line'

    try:
        arcpy.CreateTopology_management(workspace,'TFL_Line_Topology', cluster_tol)
        arcpy.AddFeatureClassToTopology_management(topology,feature_class)
        #set the rules then add them to the topology
        rules = ['Must Not Overlap (Line)',
        'Must Not Intersect (Line)',
        'Must Not Have Dangles (Line)',
        'Must Not Self-Overlap (Line)',
        'Must Not Self-Intersect (Line)',
        'Must Be Single Part (Line)']
        for rule in rules:
            arcpy.AddRuleToTopology_management(topology,rule,feature_class)
        arcpy.AddMessage('Added topology to TFL Lines')
    except:
        arcpy.AddError('Error adding topology')

def run_topology(input_gdb):
    """Runs topology on the TFL lines and prints any errors as arcpy messages
    returns true if all tests pass and false otherwise. If errors are found then
    the topology_Error feature classes will be saved in the edit database, otherwise
    they will be deleted"""
    #Check for pre-existing topology featureclasses
    if arcpy.Exists(input_gdb + os.sep + 'Topology_Error_line'):
        arcpy.Delete_management(input_gdb + os.sep + 'Topology_Error_line')
    if arcpy.Exists(input_gdb + os.sep + 'Topology_Error_point'):
        arcpy.Delete_management(input_gdb + os.sep + 'Topology_Error_point')

    try:
        #Run topology that was created in TFL_Prepare_Edits
        arcpy.ValidateTopology_management(input_gdb + os.sep + 'TFL_Line_Topology')
        arcpy.ExportTopologyErrors_management(input_gdb + os.sep + 'TFL_Line_Topology', input_gdb, 'Topology_Error')

        #Check output topology feature classes - if they are empty - delete them, otherwise add the errors to a list
        errors = []
        arcpy.env.workspace = input_gdb
        arcpy.env.XYTolerance = "0.0001 Meters"
        feature_classes = arcpy.ListFeatureClasses()
        for feature_class in feature_classes:
            if 'Topology_Error' in feature_class:
                if int(arcpy.GetCount_management(feature_class).getOutput(0)) > 0:
                    with arcpy.da.SearchCursor(feature_class, 'RuleDescription') as cursor:
                        for row in cursor:
                            errors.append(row[0])
                else:
                    arcpy.Delete_management(feature_class)

        if not errors:
            arcpy.AddMessage('No topology errors found')
            return(True)
        else:
            arcpy.AddWarning('Topology errors found - please review the topology results and correct during editing')
            for error in errors:
                arcpy.AddWarning(error)
            return(False)
    except:
        arcpy.AddWarning('Error validating topology - manual repair of topology errors using map extent may be required')
        return(False)

def get_bcgw_connection(bcgw_uname, bcgw_pw):
# SET UP BCGW CONNECTION -----------------------------------------------------------------
    arcpy.AddMessage(" ")
    arcpy.AddMessage("Setting up the BCGW connection...")

    # Run the  "BCGWConnectionFileModule.create" function which creates the BCGW
    # connection file and save the pathname to the variable "BCGWConnection"
    connection = geobc.BCGWConnection()
    success = connection.create_bcgw_connection_file(bcgw_uname,bcgw_pw)
    if success:
        BCGWConnection = connection.bcgw_connection_file
    else:
        BCGWConnection = False
    #-----------------------------------------------------------------------------------------
    return BCGWConnection


def check_bcgw_to_final_differences(tfl_basename, input_gdb, BCGWConnection): #IAN - use standard variable names here
    """takes input folder and bcgw connection - compares the TFL Final with BCGW for schedule A and boundary and
    saves any differences between them to the edit database."""

    final_tfl_data_folder = join(TFL_FINAL_FOLDER, folder_basename, 'data', 'FADM_' + folder_basename + '.gdb', 'TFL_Data')

    #This function is also implemented in TFL_Prepare_Review_Package.py
    boundary_final = join(final_tfl_data_folder, folder_basename + '_Boundary')
    schedule_a_final = join(final_tfl_data_folder, folder_basename + '_Schedule_A')


    arcpy.AddMessage('Checking differences between BCGW and final TFLs...')

    tfl_whse = BCGWConnection + '\\WHSE_ADMIN_BOUNDARIES.FADM_TFL_ALL_SP'
    sched_a_whse = BCGWConnection + '\\WHSE_ADMIN_BOUNDARIES.FADM_TFL_SCHED_A'
    #IAN - this may change when we standardize TFL Current View ForestFileID
    if '_0' in folder_basename:
        sched_a_ffid = folder_basename.replace('_0','')
    else:
        sched_a_ffid = folder_basename.replace('_','')

    #Compare Schedule A sources
    sched_a_diff = join(input_gdb, folder_basename+'_Sched_A_BCGW_Difference')

    bcgw_sched_a_fl = arcpy.MakeFeatureLayer_management(sched_a_whse, 'bcgw_sched_a_fl', "FOREST_FILE_ID = '" + sched_a_ffid + "' AND RETIREMENT_DATE IS NULL")
    if arcpy.Exists(sched_a_diff):
        arcpy.Delete_management(sched_a_diff)

    arcpy.SymDiff_analysis(bcgw_sched_a_fl, schedule_a_final, sched_a_diff)

    #Compare TFL Current View sources
    boundary_diff = join(input_gdb, folder_basename+'_Boundary_BCGW_Difference')

    bcgw_boundary_fl = arcpy.MakeFeatureLayer_management(tfl_whse,'bcgw_boundary_fl', "FOREST_FILE_ID = '" + folder_basename.replace('_',' ') + "'")
    if arcpy.Exists(boundary_diff):
        arcpy.Delete_management(boundary_diff)

    arcpy.SymDiff_analysis(bcgw_boundary_fl,boundary_final,boundary_diff)

    #Check the difference layers - if there are any differences warn the editor - otherwise - delete them
    if int(arcpy.GetCount_management(sched_a_diff)[0]) > 0:
        arcpy.AddWarning('===== Warning: differences found in Schedule A: TFL Final and BCGW are not equal')
        arcpy.AddWarning('Make sure to check the _Sched_A_BCGW_Difference dataset in the working folder to review and resolve differences')
    else:
        arcpy.AddMessage('No differences found between TFL Final Schedule A and BCGW Schedule A')
        arcpy.Delete_management(sched_a_diff)

    if int(arcpy.GetCount_management(boundary_diff)[0]) > 0:
        arcpy.AddWarning('===== Warning: differences found in Boundary: TFL Final and BCGW are not equal')
        arcpy.AddWarning('Make sure to check the _Boundary_BCGW_Differenc dataset in the working folder to review and resolve differences\n')
    else:
        arcpy.AddMessage('No differences found between Final TFL Boundary and BCGW TFL Boundary\n')
        arcpy.Delete_management(boundary_diff)


def update_change_history(table, timestamp, user):
    """takes input table, timestamp and user, and adds a new row to the change history table showing who extracted
    for editing and when"""
    fields = ['Date_Extracted','Extracted_By']
    cursor = arcpy.da.InsertCursor(table,fields)
    cursor.insertRow((timestamp,user))
    del cursor


#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('tfl_prepare_edits')