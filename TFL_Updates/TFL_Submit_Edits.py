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
import arcpy, sys, os, datetime, getpass, shutil
from datetime import datetime
import logging
import TFL_Config
sys.path.append(TFL_Config.Resources.GEOBC_LIBRARY_PATH)
import geobc
from utils.test_prod_check import test_in_working_dir


###############################################################################


# set constants (always upper case)
# constants for file and folder locations (local gdb, staging gdb)
working_location = os.path.abspath(__file__)
test = test_in_working_dir(working_location)

TFL_Path = TFL_Config.TFL_Path(test=test)

TFL_STAGING_FOLDER = TFL_Path.STAGING
TFL_PENDING_FOLDERS = TFL_Path.PENDING_FOLDERS
TFL_FINAL_FOLDERS = TFL_Path.FINAL_FOLDER
TFL_ARCHIVE = TFL_Path.ARCHIVE
PMBC = r'\\WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW'
TANTALIS = r'\\WHSE_TANTALIS.TA_SURVEY_PARCELS_SVW'
###################################################################################
# set up basic logging config
log_file = os.path.join(os.path.dirname(working_location), 'tool_errors.log')
logging.basicConfig(filename=log_file, level=logging.ERROR, format='%(asctime)s:%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')

###############################################################################
# get script tool parameters
input_tfl = arcpy.GetParameterAsText(1) #TFL name of folder containing the TFL review package
bcgw_uname = arcpy.GetParameterAsText(2)
bcgw_pw = arcpy.GetParameterAsText(3)
date_confirmation = arcpy.GetParameterAsText(4)
effective_date = arcpy.GetParameterAsText(5)
legislative_tool = arcpy.GetParameterAsText(6)
instrument_number = arcpy.GetParameterAsText(7)
tfl_component = arcpy.GetParameterAsText(8)
multi_instrument_confirmation = arcpy.GetParameterAsText(9)
change_type = arcpy.GetParameterAsText(10)

input_folder = TFL_PENDING_FOLDERS + os.sep + input_tfl
input_gdb = input_folder + os.sep +'Data' + os.sep + 'FADM_' + input_tfl + '.gdb'
tfl_poly = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Boundary'
tfl_schedule_a = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Schedule_A'
tfl_line = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Line'
tfl_line_changes = input_gdb + os.sep + input_tfl + '_Line_Changes'
transaction_details = input_gdb + os.sep + input_tfl + '_Transaction_Details'
change_history = input_gdb + os.sep + input_tfl + '_Change_History'

submitted_timestamp = datetime.now()
submitted_user = getpass.getuser()

#get forest file ID used to update output datasets by replacing underscores and zeros
if '_0' in input_tfl:
    forest_file_id = input_tfl.replace('_0','')
else:
    forest_file_id = input_tfl.replace('_','')

#output datasets to update
staging_overview_db = TFL_STAGING_FOLDER + os.sep + 'TFL_business_views.gdb'
staging_overview = staging_overview_db + os.sep + 'TFL_Overview'
staging_agreement_db = TFL_STAGING_FOLDER + os.sep + 'TFL_Agreement_Boundary.gdb'
staging_agreement_bdy = staging_agreement_db + os.sep + 'FADM_TFL'
staging_schedule_a_db = TFL_STAGING_FOLDER + os.sep + 'TFL_Schedule_A.gdb'
staging_schedule_a = staging_schedule_a_db + os.sep +'FADM_TFL_SCHED_A'
staging_deletion_db = TFL_STAGING_FOLDER + os.sep + 'TFL_Deletion.gdb'
staging_deletion = staging_deletion_db + os.sep + 'FADM_TFL_DELETION'
staging_addition_db = TFL_STAGING_FOLDER + os.sep + 'TFL_Addition.gdb'
staging_addition = staging_addition_db + os.sep + 'FADM_TFL_ADDITION'
    # TO DO - First check to make sure there are no TFL folders for the same TFL in working, review or pending
    #For a TFL to be submitted, these must all be moved to the holding area and any edit must start
    #again from final, manually merging any changes in.

def runapp(tfl_submit_edits):

    #First check input parameter requirements - because optional parameters from tool may be required, they cannot be set in tool
    if check_input_parameters():

        #establish the BCGW connection to check the schedule A AND TFL Boundary
        BCGWConnection = get_bcgw_connection(bcgw_uname,bcgw_pw)

        if not BCGWConnection is False: #only proceed if connection succeeds

            # Call check_for_locks method to check the edit gdb
            gdb_object = geobc.GDBInfo(input_gdb)
            lock_owner_list = gdb_object.check_for_locks()
            if not lock_owner_list:
                arcpy.env.workspace = input_gdb

                #Get the extract date - used for the change detection and for the reviewer update
                #add reference
                history_table = geobc.TableInfo()
                check_out_date = history_table.get_last_date(change_history,'Date_Extracted')

                #Check all TFL Poly features and edit date on schedule a - make list of datasets to update
                datasets_to_update = get_update_list(check_out_date, BCGWConnection)

                #Check for locks on all the output datasets to update - only proceed if clear
                if not check_outputs_for_locks(datasets_to_update):
                    #first uncompress the gdb, needed for updating submitter and adding intersecting cadastre
                    arcpy.UncompressFileGeodatabaseData_management(input_gdb)

                    #Remove the previous TFL from the TFL overview and add the updated one
                    update_tfl_overview()

                    if 'Replacement' in datasets_to_update:
                        update_tfl_agreement()

                    if 'Addition' in datasets_to_update:
                        #if a single instrument, first set skey on the local data based on the inputs - also updates input fields
                        if change_type == 'Instrument - Single':
                            if tfl_component == 'Schedule A':
                                update_skey('Addition', 831)
                            else:
                                update_skey('Addition', 832)
                        update_tfl_addition()

                    if 'Deletion' in datasets_to_update:
                        #if a single instrument, first set skey on the local data based on the inputs
                        if change_type == 'Instrument - Single':
                            if tfl_component == 'Schedule A':
                                update_skey('Deletion', 835)
                            else:
                                update_skey('Deletion', 836)
                        update_tfl_deletion()

                    if 'Schedule_A' in datasets_to_update:
                        update_tfl_schedule_a()

                    #Update the change history with the submitter and datestamp
                    check_out_date = check_out_date.strftime("%b %d %Y %H:%M:%S") #format to string for use in query
                    update_submitter(check_out_date)

                    #Create copy of cadastre that intersects TFL lines and add to final folder
                    intersect_cadastre(BCGWConnection,datasets_to_update,check_out_date)

                    #Compress the database now to prevent accidental edits
                    arcpy.CompressFileGeodatabaseData_management(input_gdb)

                    #Move the review package folder to the new final and rename it with datestamp
                    move_and_archive()
                    if change_type == 'Instrument - Multiple':
                        arcpy.AddMessage('CAUTION: Submitted multiple instruments to local staging folders SKEY MUST be populated prior to moving to DataBC Staging')
                    arcpy.AddMessage('Script run complete - check messages and outputs')

                else:
                    print('locks found on output')
                    arcpy.AddMessage('Locks found on output - check and re-run')

            else:
                print(lock_owner_list)
                arcpy.AddWarning('Found lock on geodatabase: ' + str(lock_owner_list))
        else:
            arcpy.AddWarning('Error making BCGW connection - check credentials and re-try')

###############################################################################
## Functions section
###############################################################################
def check_input_parameters():
    arcpy.AddMessage('checking input parameters')
    input_check = True
    if change_type == 'Replacement':
        if not date_confirmation:
            arcpy.AddWarning('WARNING: must confirm EFFECTIVE Date for Replacement')
            input_check = False
        elif not effective_date:
            arcpy.AddWarning('WARNING: must set EFFECTIVE Date for Replacement')
            input_check = False
    elif change_type == 'Instrument - Single':
        if not date_confirmation:
            arcpy.AddWarning('WARNING: must confirm EFFECTIVE Date for Instrument')
            input_check = False
        elif not effective_date:
            arcpy.AddWarning('WARNING: must set EFFECTIVE Date for Instrument')
            input_check = False
        elif not legislative_tool:
            arcpy.AddWarning('WARNING: must set legislative tool for Instrument')
            input_check = False
        elif not instrument_number:
            arcpy.AddWarning('WARNING: must set Instrument number')
            input_check = False
        elif not tfl_component:
            arcpy.AddWarning('WARNING: must choose schedule A or B for instrument')
            input_check = False
    elif change_type == 'Instrument - Multiple':
        if not multi_instrument_confirmation:
            arcpy.AddWarning('WARNING: must confirm that you are submitting multiple instruments')
            input_check = False

    return input_check

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


def get_update_list(check_out_date,BCGWConnection):
    """Checks the output poly types in the TFL boundary and the edit date on the
       schedule A and returns a list of datasets to update."""
    update_list = set()
    fields = ['Poly_Type']
    with arcpy.da.SearchCursor(tfl_poly, fields) as cursor:
        for row in cursor:
            if row[0] not in update_list:
                update_list.add(row[0])
        del row
    del cursor
    schedule_a_updated = False

    #Refactor - First check if there is any Schedule A for this TFL in the warehouse - if not - no update

    #If there is in warehouse - check if the difference layer exists (from prepare review package tool) if so, update
    sched_a_whse = BCGWConnection + '\\WHSE_ADMIN_BOUNDARIES.FADM_TFL_SCHED_A'

    #get the format for the forest file ID for query - remove underscores and leading 0
    if '_0' in input_tfl:
        ffid = input_tfl.replace('_0','')
    else:
        ffid = input_tfl.replace('_','')

    bcgw_sched_a_fl = arcpy.MakeFeatureLayer_management(sched_a_whse, 'bcgw_sched_a_fl', "FOREST_FILE_ID = '" + ffid + "'")
    result = arcpy.GetCount_management(bcgw_sched_a_fl)
    if result[0] > 0:
        arcpy.AddMessage('Found ' + str(result[0]) + ' Schedule A records in BCGW')
        if arcpy.Exists(input_gdb + os.sep + input_tfl + '_Schedule_A_Difference'):
            arcpy.AddMessage('Found difference layer for schedule A')
            schedule_a_updated = True


##    fields = ['last_edited_date']
##    with arcpy.da.SearchCursor(tfl_schedule_a, fields) as cursor:
##        for row in cursor:
##            if row[0]: #only compare dates - not nulls
##                update_date = row[0]
##                if update_date >= check_out_date:
##                    schedule_a_updated = True
##    del cursor
    if schedule_a_updated:
        update_list.add('Schedule_A')
    return(update_list)

def check_outputs_for_locks(datasets_to_update):

    # Call check_for_locks method on overview first - this is always updated in normal flow
    gdb_object = geobc.GDBInfo(staging_overview_db)
    lock_owner_list = gdb_object.check_for_locks()
    if lock_owner_list:
        arcpy.AddMessage('WARNING: Lock on staging TFL Overview Database: ' + str(lock_owner_list))
        return True #if there are any locks - return True

    #Then Check locks for the TFL Final folders
    final_gdb = TFL_FINAL_FOLDERS + os.sep + input_tfl + os.sep +'Data' + os.sep + 'FADM_' + input_tfl + '.gdb'
    gdb_object = geobc.GDBInfo(final_gdb)
    lock_owner_list = gdb_object.check_for_locks()
    if lock_owner_list:
        arcpy.AddMessage('WARNING: Lock on TFL Final database: ' + str(lock_owner_list))
        return True #if there are any locks - return True

    #Then call the method for each of the outputs
    if 'Replacement' in datasets_to_update:
        gdb_object = geobc.GDBInfo(staging_agreement_db)
        lock_owner_list = gdb_object.check_for_locks()
        if lock_owner_list:
            arcpy.AddMessage('WARNING: Lock on staging TFL Agreement Database: ' + str(lock_owner_list))
            return True #if there are any locks - return True

    if 'Addition' in datasets_to_update:
        gdb_object = geobc.GDBInfo(staging_addition_db)
        lock_owner_list = gdb_object.check_for_locks()
        if lock_owner_list:
            arcpy.AddMessage('WARNING: Lock on staging TFL Addition Database: ' + str(lock_owner_list))
            return True #if there are any locks - return True

    if 'Deletion' in datasets_to_update:
        gdb_object = geobc.GDBInfo(staging_deletion_db)
        lock_owner_list = gdb_object.check_for_locks()
        if lock_owner_list:
            arcpy.AddMessage('WARNING: Lock on staging TFL Deletion Database: ' + str(lock_owner_list))
            return True #if there are any locks - return True

    if 'Schedule_A' in datasets_to_update:
        gdb_object = geobc.GDBInfo(staging_schedule_a_db)
        lock_owner_list = gdb_object.check_for_locks()
        if lock_owner_list:
            arcpy.AddMessage('WARNING: Lock on staging Schedule A Database: ' + str(lock_owner_list))
            return True #if there are any locks - return True

    return False

def update_tfl_overview():
    """Makes a backup copy of TFL Overview in staging then deletes the previous
       backup. Takes any TFL Poly features tagged as overview, addition or replacement,
       merges them and then adds them to the new TFL overview in staging. Updates
       The required fields in the new features"""
    #create a feature layer that merges the addition and current view polygons - dissolve to a single feature
    where_clause = "(Poly_Type='Addition') OR (Poly_Type='Current_View')OR (Poly_Type='Replacement')"
    boundary_fl = arcpy.MakeFeatureLayer_management(tfl_poly,'TFL_Boundary_all',where_clause)
    arcpy.Dissolve_management('TFL_Boundary_all','TFL_Boundary_dissolve','FOREST_FILE_ID')
    arcpy.Delete_management(boundary_fl)
    #make a backup copy of the staging overview dataset - delete the old backup first
    arcpy.Delete_management(staging_overview + '_BACKUP')
    arcpy.Copy_management(staging_overview,staging_overview + '_BACKUP')
    #delete the features for the current TFL from overview
    overview_fl = arcpy.MakeFeatureLayer_management(staging_overview,'TFL_Overview_FL', "FOREST_FILE_ID = '" + forest_file_id + "'")
    arcpy.DeleteFeatures_management('TFL_Overview_FL')
    #append the new overview
    arcpy.Append_management('TFL_Boundary_dissolve',staging_overview,'NO_TEST')
    #update the licensee in the overview - use the lookup to find it
    licensee_lookup = r'\\spatialfiles.bcgov\ilmb\dss\projects\Mflnro\FADM_Tree_Farm_Licences\TFL_templates\data\TFL_Lookup_Tables.gdb\Licensee_Lookup'
    where_clause = "FOREST_FILE_ID = '" + forest_file_id + "'"
    fields = ['FOREST_FILE_ID','LICENCEE']
    with arcpy.da.SearchCursor(licensee_lookup,fields,where_clause) as cursor:
        for row in cursor:
            licensee = row[1]
    #edit code to reflect the schema change: remove WHO_UPDATED, OBJECT_VERSION_SKEY, FEATURE_CODE
    #change COMMENTS to DESCRIPTION, DOCUMENT_TYPE to LEGISLATIVE_TOOL, INS_AMD_ID to DOCUMENT_NUMBER
    #fields = ['FOREST_FILE_ID','LICENCEE','TFL_TYPE', 'FEATURE_CLASS_SKEY','WHEN_UPDATED','WHO_UPDATED']
    fields = ['FOREST_FILE_ID','LICENCEE','TFL_TYPE', 'FEATURE_CLASS_SKEY','WHEN_UPDATED']
    with arcpy.da.UpdateCursor(staging_overview,fields,where_clause) as cursor:
        for row in cursor:
            row[1] = licensee
            row[2] = 'See Licence'
            row[3] = 830
            row[4] = submitted_timestamp
            #row[5] = 'GeoBC'
            cursor.updateRow(row)
    arcpy.Delete_management(input_gdb + os.sep + 'TFL_Boundary_dissolve')
    arcpy.Delete_management(overview_fl)
    arcpy.AddMessage('Updated TFL Overview in Staging folder')
    print('Updated TFL Overview in Staging folder')

def update_tfl_agreement():
    """Makes a backup copy of TFL Agreement in staging then deletes the previous
       backup. Removes features for the TFL from the staging agreement then
       takes any TFL Poly features tagged as replacement, and adds them
       to the TFL Agreement in staging. Updates the required fields in the new features"""
    #make a backup copy of the staging agreement dataset - delete the old backup first
    arcpy.Delete_management(staging_agreement_bdy + '_BACKUP')
    arcpy.Copy_management(staging_agreement_bdy,staging_agreement_bdy + '_BACKUP')
    #delete the features for the current TFL from agreement
    arcpy.MakeFeatureLayer_management(staging_agreement_bdy,'TFL_Agreement_FL', "FOREST_FILE_ID = '" + forest_file_id + "'")
    arcpy.DeleteFeatures_management('TFL_Agreement_FL')
    arcpy.Delete_management('TFL_Agreement_FL')
    #append the new agreement boundary
    arcpy.Append_management(tfl_poly,staging_agreement_bdy,'NO_TEST')
    #update the required fields in the new record
    where_clause = "FOREST_FILE_ID = '" + forest_file_id + "'"
    #fields = ['FOREST_FILE_ID','EFFECTIVE_DATE','FEATURE_CLASS_SKEY','WHO_UPDATED','WHEN_UPDATED']
    fields = ['FOREST_FILE_ID','EFFECTIVE_DATE','FEATURE_CLASS_SKEY','WHEN_UPDATED']
    with arcpy.da.UpdateCursor(staging_agreement_bdy,fields,where_clause) as cursor:
        for row in cursor:
            row[1] = effective_date
            row[2] = 830
            #row[3] = 'GeoBC'
            #row[4] = submitted_timestamp
            row[3] = submitted_timestamp
            cursor.updateRow(row)
    arcpy.AddMessage('Updated TFL Agreement Boundary in Staging folder')

def update_tfl_addition():
    """Makes a backup copy of TFL Addition in staging then deletes the previous
       backup. Takes any TFL Poly features tagged as addition, and adds them
       to the new TFL Addition in staging."""
    #create a feature layer
    where_clause = "Poly_Type='Addition'"
    TFL_Boundary_addition = arcpy.MakeFeatureLayer_management(tfl_poly,'TFL_Boundary_addition',where_clause)
    #make a backup copy of the staging overview dataset - delete the old backup first
    arcpy.Delete_management(staging_addition + '_BACKUP')
    arcpy.Copy_management(staging_addition,staging_addition + '_BACKUP')
    count = arcpy.GetCount_management(TFL_Boundary_addition)
    arcpy.AddMessage('Appending ' + str(count) + ' additions to staging')

    #make a field map for the deletion feature layer
    field_mappings_addition = arcpy.FieldMappings()
    #legislative tool
    f_map_tool = arcpy.FieldMap()
    f_map_tool.addInputField(TFL_Boundary_addition, 'Legislative_Tool')
    tool                  = f_map_tool.outputField
    #change the field name from document_type to legislative_tool by YJ
    tool.name             = 'Legislative_Tool'
    f_map_tool.outputField  = tool
    field_mappings_addition.addFieldMap(f_map_tool)
    #document number
    f_map_number = arcpy.FieldMap()
    f_map_number.addInputField(TFL_Boundary_addition, 'Document_Number')
    number                  = f_map_number.outputField
    #change INS_AMD_ID TO DOCUMENT_NUMBER by yj
    number.name             = 'DOCUMENT_NUMBEER'
    f_map_number.outputField  = number
    field_mappings_addition.addFieldMap(f_map_number)
    #description
    f_map_description = arcpy.FieldMap()
    f_map_description.addInputField(TFL_Boundary_addition, 'Description')
    description             = f_map_description.outputField
    #change COMMENTS to DESCRIPTION by yj
    description.name        = 'Description'
    f_map_description.outputField  = description
    field_mappings_addition.addFieldMap(f_map_description)
    #Forest File ID
    f_map_ffid = arcpy.FieldMap()
    f_map_ffid.addInputField(TFL_Boundary_addition, 'FOREST_FILE_ID')
    ffid             = f_map_ffid.outputField
    ffid.name        = 'FOREST_FILE_ID'
    f_map_ffid.outputField  = ffid
    field_mappings_addition.addFieldMap(f_map_ffid)
    #Feature class skey
    f_map_skey = arcpy.FieldMap()
    f_map_skey.addInputField(TFL_Boundary_addition, 'FEATURE_CLASS_SKEY')
    skey             = f_map_skey.outputField
    skey.name        = 'FEATURE_CLASS_SKEY'
    f_map_skey.outputField  = skey
    field_mappings_addition.addFieldMap(f_map_skey)
    #effective date
    f_map_date = arcpy.FieldMap()
    f_map_date.addInputField(TFL_Boundary_addition, 'EFFECTIVE_DATE')
    date             = f_map_date.outputField
    date.name        = 'EFFECTIVE_DATE'
    f_map_date.outputField  = date
    field_mappings_addition.addFieldMap(f_map_date)

    #append the new addition
    arcpy.Append_management(TFL_Boundary_addition,staging_addition,'NO_TEST',field_mappings_addition)
    arcpy.Delete_management(TFL_Boundary_addition)

    #update the required fields in the new record
    where_clause = "WHEN_UPDATED IS NULL"
    #remove WHO_UPDATED by yj
    fields = ['WHEN_UPDATED']
    with arcpy.da.UpdateCursor(staging_addition,fields,where_clause) as cursor:
        for row in cursor:
            #row[0] = 'GeoBC'
            #row[1] = datetime.now()
            row[0] = datetime.now()
            cursor.updateRow(row)
    arcpy.AddMessage('Updated TFL Addition in Staging folder')


def update_tfl_deletion():
    """Makes a backup copy of TFL Deletion in staging then deletes the previous
       backup. Takes any TFL Poly features tagged as deletion, and appends them
       to the new TFL Deletion in staging."""
    #create a feature layer
    where_clause = "Poly_Type='Deletion'"
    TFL_Boundary_deletion = arcpy.MakeFeatureLayer_management(tfl_poly,'TFL_Boundary_deletion',where_clause)
    count = arcpy.GetCount_management(TFL_Boundary_deletion)
    arcpy.AddMessage('Appending ' + str(count) + ' deletions to staging')

    #make a backup copy of the staging overview dataset - delete the old backup first
    arcpy.Delete_management(staging_deletion + '_BACKUP')
    arcpy.Copy_management(staging_deletion,staging_deletion + '_BACKUP')
    #make a field map for the deletion feature layer
    field_mappings_deletion = arcpy.FieldMappings()
    #legislative tool
    f_map_tool = arcpy.FieldMap()
    f_map_tool.addInputField(TFL_Boundary_deletion, 'Legislative_Tool')
    tool                  = f_map_tool.outputField
    tool.name             = 'DOCUMENT_TYPE'
    f_map_tool.outputField  = tool
    field_mappings_deletion.addFieldMap(f_map_tool)
    #document number
    f_map_number = arcpy.FieldMap()
    f_map_number.addInputField(TFL_Boundary_deletion, 'Document_Number')
    number                  = f_map_number.outputField
    number.name             = 'INS_AMD_ID'
    f_map_number.outputField  = number
    field_mappings_deletion.addFieldMap(f_map_number)
    #description
    f_map_description = arcpy.FieldMap()
    f_map_description.addInputField(TFL_Boundary_deletion, 'Description')
    description             = f_map_description.outputField
    description.name        = 'COMMENTS'
    f_map_description.outputField  = description
    field_mappings_deletion.addFieldMap(f_map_description)
    #Forest File ID
    f_map_ffid = arcpy.FieldMap()
    f_map_ffid.addInputField(TFL_Boundary_deletion, 'FOREST_FILE_ID')
    ffid             = f_map_ffid.outputField
    ffid.name        = 'FOREST_FILE_ID'
    f_map_ffid.outputField  = ffid
    field_mappings_deletion.addFieldMap(f_map_ffid)
    #Feature class skey
    f_map_skey = arcpy.FieldMap()
    f_map_skey.addInputField(TFL_Boundary_deletion, 'FEATURE_CLASS_SKEY')
    skey             = f_map_skey.outputField
    skey.name        = 'FEATURE_CLASS_SKEY'
    f_map_skey.outputField  = skey
    field_mappings_deletion.addFieldMap(f_map_skey)

    f_map_date = arcpy.FieldMap()
    f_map_date.addInputField(TFL_Boundary_deletion, 'EFFECTIVE_DATE')
    date             = f_map_date.outputField
    date.name        = 'EFFECTIVE_DATE'
    f_map_date.outputField  = date
    field_mappings_deletion.addFieldMap(f_map_date)

    #append the new deletion
    arcpy.Append_management(TFL_Boundary_deletion,staging_deletion,'NO_TEST', field_mappings_deletion)
    arcpy.Delete_management(TFL_Boundary_deletion)

    #update the required fields in the new record
    where_clause = "WHEN_UPDATED IS NULL"
    #remove WHO_UPDATED by yj
    #fields = ['WHO_UPDATED','WHEN_UPDATED']
    fields = ['WHEN_UPDATED']
    with arcpy.da.UpdateCursor(staging_deletion,fields,where_clause) as cursor:
        for row in cursor:
            #row[0] = 'GeoBC'
            #row[1] = datetime.now()
            row[0] = datetime.now()
            cursor.updateRow(row)
    arcpy.AddMessage('Updated TFL Deletion in Staging folder')

def update_skey(poly_type, skey):
    """takes , and finds the last (most recent)
    record in the change history table and adds the reviewer user"""
    table = input_gdb + os.sep + input_tfl + '_Boundary'
    fields = ['Poly_Type','FEATURE_CLASS_SKEY', 'Legislative_Tool','Document_Number','EFFECTIVE_DATE']
    with arcpy.da.UpdateCursor(table,fields, "Poly_Type = '" + poly_type + "'") as cursor:
        for row in cursor:
            row[1] = skey
            if legislative_tool:
                row[2] = legislative_tool
            if instrument_number:
                row[3] = instrument_number
            if effective_date:
                row[4] = effective_date

            cursor.updateRow(row)
    del cursor
    arcpy.AddMessage('Updated SKEY for ' + poly_type)

def update_tfl_schedule_a():
    """Makes a backup copy of TFL Schedule A in staging then deletes the previous
       backup. Takes any TFL Poly features tagged as deletion, and adds them
       to the new TFL Deletion in staging."""
    #TO DO: check to ensure schedule A attributes are correct - when should this happen? might be better in a different tool?

    where_clause = "FOREST_FILE_ID = '" + forest_file_id + "'"
    #make a backup copy of the staging overview dataset - delete the old backup first
    arcpy.Delete_management(staging_schedule_a + '_BACKUP')
    arcpy.Copy_management(staging_schedule_a,staging_schedule_a + '_BACKUP')
    #delete the features for the current TFL from additions
    arcpy.MakeFeatureLayer_management(staging_schedule_a,'TFL_Schedule_A_FL', where_clause)
    arcpy.DeleteFeatures_management('TFL_Schedule_A_FL')
    #append the new addition
    arcpy.Append_management(tfl_schedule_a,staging_schedule_a,'NO_TEST')
    #update the required fields in the new records
    #remove WHO_UPDATED by yj
    #fields = ['WHO_UPDATED','WHEN_UPDATED','FEATURE_CLASS_SKEY']
    fields = ['WHEN_UPDATED','FEATURE_CLASS_SKEY']
    with arcpy.da.UpdateCursor(staging_schedule_a,fields,where_clause) as cursor:
        for row in cursor:
            #row[0] = 'GeoBC'
            #row[1] = datetime.now()
            #row[2] = 837
            row[0] = datetime.now()
            row[1] = 837
            cursor.updateRow(row)
    arcpy.AddMessage('Updated TFL Schedule A in Staging folder')
    arcpy.Delete_management('TFL_Schedule_A_FL')

def update_submitter(check_out_date):
    """takes , and finds the last (most recent)
    record in the change history table and adds the reviewer user"""
    table = input_gdb + os.sep + input_tfl + '_Change_History'
    fields = ['Date_Extracted','Date_Submitted','Submitted_By']
    with arcpy.da.UpdateCursor(table,fields, "Date_Extracted >= date '" + check_out_date + "'") as cursor:
        for row in cursor:
            row[1] = submitted_timestamp
            row[2] = submitted_user
            cursor.updateRow(row)
    del cursor
    arcpy.AddMessage('Updated Submitter and date')

def intersect_cadastre(bcgw_connection, datasets_to_update, check_out_date):
    """If change is replacement, intersects all TFL lines with cadastral datasets
       (PMBC, Tantalis), otherwise, intersects only updated lines. Saves
       Intersecting features to a FC in the local GDB to provide context for
       future research."""
    #removed ICF BCGW connection/intersection
    pmbc_whse = bcgw_connection + PMBC
    tantalis_whse = bcgw_connection + TANTALIS
    cadastral_to_copy = {'PMBC': pmbc_whse ,'TANTALIS': tantalis_whse}
    if 'Replacement' in datasets_to_update:
        #make feature layer of all active lines
        where_clause = "Status_Code = 'ACTIVE'"
        lines_fl = arcpy.MakeFeatureLayer_management(tfl_line,'TFL_Line_FL',where_clause)
    else:
        #If not a replacement, use the line changes feature class created for the review package (minus deleted lines)
        where_clause = "Status_Code IN ('ACTIVE','RETIRED')"
        lines_fl = arcpy.MakeFeatureLayer_management(tfl_line_changes,'TFL_Line_FL',where_clause)

    line_count = int(arcpy.GetCount_management('TFL_Line_FL')[0])

    #For each cadastre - make a selection that instersects the feature layer and copy to the local
    for key, value in cadastral_to_copy.iteritems(): #NOTE: iteritems is python2 and will need to be updated for arcPro to python 3
        temp_fl = arcpy.MakeFeatureLayer_management(value, key + '_FL')
        arcpy.SelectLayerByLocation_management(key + '_FL','INTERSECT','TFL_Line_FL')
        feature_count = int(arcpy.GetCount_management(key + '_FL')[0])
        if feature_count == 0:
            arcpy.AddMessage('No intersecting features found for ' + key)
        else:
            arcpy.CopyFeatures_management(key + '_FL',key + '_Intersection')
            arcpy.AddMessage('Copied intersecting features from ' + key)
        arcpy.Delete_management(temp_fl)

    arcpy.Delete_management(lines_fl)


def move_and_archive():
    arcpy.env.workspace = working_location

    now = datetime.now()
    date = now.strftime("%Y%m%d")

    update_support_dir = os.path.join(TFL_FINAL_FOLDERS, input_tfl, 'documents', 'Update_Support_Documents')   # Dir containing relevant update documents in Final folder
    if os.path.isdir(update_support_dir):
        shutil.rmtree(update_support_dir)   # delete the directory from the final folder, it shouldn't be archived

    #move the previous final to archive
    shutil.move(TFL_FINAL_FOLDERS + os.sep + input_tfl, TFL_ARCHIVE + os.sep + input_tfl + '_' + date)
    arcpy.AddMessage('Moved previous TFL folder to archive')

    #copy the working folder to final
    arcpy.Copy_management(input_folder, TFL_FINAL_FOLDERS + os.sep + input_tfl)
    arcpy.Compact_management(os.path.join(TFL_FINAL_FOLDERS, input_tfl, 'Data', 'FADM_' + input_tfl + '.gdb'))      # there may be leftover locks, compacting seems to get rid of them in this situation
    # shutil.copytree(input_folder, TFL_FINAL_FOLDERS + os.sep + input_tfl, ignore=shutil.ignore_patterns('*.lock'))    #alternative workaround for lock issues
    arcpy.AddMessage('Moved package to TFL Final folder')

    #recreate the Update_Support_Documents folder in Final
    os.mkdir(update_support_dir)

    # attempt to delete the working folder from Pending
    try:
        arcpy.Compact_management(input_gdb)
        shutil.rmtree(input_folder)
    except Exception as e:
        arcpy.AddWarning('\n== ACTION REQUIRED == {} could not be deleted from the Pending folder. Please be sure to manually delete it'.format(input_tfl))
        logging.error(e)


#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('tfl_submit_edits')