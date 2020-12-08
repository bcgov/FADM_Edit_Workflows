######################################################################
## TFL_Prepare_Review_Package.py
## Purpose: 1. Create polygon features for the areas of change
##          2. Create a TFL review map from template that highlights line and
##              area changes
##          3. Request summary text and create a draft change readme document
## Date: February, 2019
## Author: Jed Harrison, GeoBC
###############################################################################


# Import modules
import arcpy, sys, os, datetime, shutil, getpass
from datetime import datetime
import TFL_Config
sys.path.append(TFL_Config.Resources.GEOBC_LIBRARY_PATH)
import geobc


###############################################################################
# constants for file and folder locations
TFL_REVIEW_FOLDERS = TFL_Config.TFL_Path.REVIEW_FOLDERS
TFL_WORKING_FOLDERS = TFL_Config.TFL_Path.EDITS_FOLDER
TFL_FINAL_FOLDERS = TFL_Config.TFL_Path.FINAL_FOLDER
TFL_TEMPLATE_MAP = TFL_Config.TFL_Path.TEMPLATE_MAP

###############################################################################
# get script tool parameters
input_tfl = arcpy.GetParameterAsText(0) #Folder containing the TFL line edits
bcgw_uname = arcpy.GetParameterAsText(1)
bcgw_pw = arcpy.GetParameterAsText(2)
change_description = arcpy.GetParameterAsText(3) #Text input - short statement of the nature of the change
change_summary = arcpy.GetParameterAsText(4) #Text input - short paragraph (or less) with detail as required

input_folder = TFL_WORKING_FOLDERS + os.sep + input_tfl
input_gdb = input_folder + os.sep +'Data' + os.sep + 'FADM_' + input_tfl + '.gdb'


def runapp(TFL_Prepare_Review_Package):

    arcpy.AddMessage('Starting new script run . . .')
    is_locked = ''

    # Call check_for_locks method to check the gdb - compact first to remove self locks
    arcpy.Compact_management(input_gdb)
    gdb_object = geobc.GDBInfo(input_gdb)
    lock_owner_list = gdb_object.check_for_locks()

    if not lock_owner_list:
        is_locked = 'No'
    elif len(lock_owner_list) == 1:
        if lock_owner_list[0] == getpass.getuser().upper():
            is_locked = 'Self'

    if is_locked == 'No' or is_locked == 'Self':

        #check the BCGW connection before doing any actual work
        BCGWConnection = get_bcgw_connection(bcgw_uname,bcgw_pw)

        if BCGWConnection: #only proceed if connection succeeds -

            #check to ensure data has passed the check edits stage and no edits have been made since
            check_ready = check_prerequisites(input_gdb,input_tfl, BCGWConnection)

            if check_ready is False:
                arcpy.AddWarning('ERROR: Review messages and resolve before running tool')
            else:

                #Add changes (if any) to the working database
                save_changes_to_gdb(input_gdb,input_tfl,BCGWConnection)

                #Add the review map template to the review folder and path it
                create_review_map(input_gdb,input_tfl)

                #Create the draft change summary and add it to the folder - or Update if already there
                create_update_readme(input_folder,input_tfl,input_gdb)

                #Move folder to review area
                try:
                    shutil.copytree(input_folder,TFL_REVIEW_FOLDERS + os.sep + input_tfl)
                    #message user and end script
                    arcpy.AddMessage('TFL folder has been copied to 3_TFL_Review folder')
                    try:
                        shutil.rmtree(input_folder)
                        arcpy.AddMessage('TFL folder has been deleted from 2_TFL_Working folder')
                    except:
                        arcpy.AddWarning('WARNING: Unable to delete entire folder after copy - please check that review folder is complete then close all files and delete working folder')
                except:
                    arcpy.AddWarning('WARNING: Unable to copy entire folder - please delete the folder and all contents in 3_TFL_Review. Then be sure all files are closed before trying again')

                #IAN - add email to reviewers + cc to editor
        else:
            arcpy.AddMessage('Unable to make BCGW Connection')
    else:
        arcpy.AddWarning('Found lock on geodatabase: ' + str(lock_owner_list))

###############################################################################
## Functions section
###############################################################################
#checks to ensure that the check edits tool was run AFTER any edit datestamps
#and that the check edits tool passed
def check_prerequisites(input_gdb,input_tfl, BCGWConnection):
    """Takes the input database, checks to see that check edits datestamp is
    after the last tracked edits on lines and Schedule A, and that the check
    edits result was passed. Also checks to ensure all TFL Poly features
    have a Poly_Type set. Returns True if all tests pass and False if not"""

    transaction_details = input_gdb + os.sep + input_tfl + '_Transaction_Details'

    #IAN - consider making global variables for functions using same data
    tfl_lines = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Line'
    tfl_schedule_a = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Schedule_A'
    tfl_poly = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Boundary'

    table_object = geobc.TableInfo()
    check_edits_date = table_object.get_last_date(transaction_details,'Check_Edits_Date')

    if check_edits_date: #function will return None if there is no date
        with arcpy.da.SearchCursor(transaction_details,'Check_Edits_Passed') as cursor:
            for row in cursor:
                check_edit_result = row[0]
            del row
        del cursor

        if check_edit_result == 'No':
            arcpy.AddWarning('Issues found during last check edits - please re-run tool and resolve before running the Prepare Review Package tool')
            return(False)
        else:
            arcpy.AddMessage('Check edits passed last run')
    else:
        arcpy.AddWarning('Check edits tool has not been run')
        return(False)

    poly_check = check_poly(tfl_poly,input_gdb, BCGWConnection) #call function to check boundary attribute rules
    if not poly_check:
        return(False)

    lines_table = geobc.TableInfo()
    lines_last_edit = lines_table.get_last_date(tfl_lines,'last_edited_date')

    schedule_a_table = geobc.TableInfo()
    schedule_a_last_edit = schedule_a_table.get_last_date(tfl_schedule_a,'last_edited_date')

    if ((lines_last_edit is None) or (lines_last_edit < check_edits_date)) and ((schedule_a_last_edit is None) or (schedule_a_last_edit < check_edits_date)):
        arcpy.AddMessage('no edits to lines or Schedule A since last check')
        return(True)
    else:
        arcpy.AddWarning('Edits done to TFL lines or Schedule A since last check - Run Check Edits tool before running Prepare Review Package tool')
        return(False)

def check_poly(tfl_poly, input_gdb, BCGWConnection):
    """Takes input poly feature class and input gdb, checks to make sure that all rows have a poly type and that it and leg tool are
        using domain values. Checks to ensure if replacement then that is only poly type. If replacement, adds timber licences
        to the gdb"""
    arcpy.AddMessage('Checking polygon attribute rules')
    poly_type_values = get_coded_values(input_gdb,'POLY_TYPE') #get values for poly type domain
    leg_tools_values = get_coded_values(input_gdb, 'Legislative_Tool')
    #check the TFL_Boundary to make sure all features have a poly type
    #also check if poly type is consistent (either ALL replacement - or combo of others)
    poly_type_set = True
    poly_types = set()
    domain_error = set()
    with arcpy.da.SearchCursor(tfl_poly,['Poly_Type', 'Legislative_Tool']) as cursor:
        for row in cursor:
            if row[0] is None:
                poly_type_set = False
            else:
                if row[0] not in poly_type_values:
                    domain_error.add('Poly_Type')
                poly_types.add(row[0])
            if row[1]:
                if row[1] not in leg_tools_values:
                    domain_error.add('Legislative_Tool')
        del row
    del cursor
    if domain_error:
        arcpy.AddWarning('WARNNG: One or more TFL_Boundary features are not using domain values in ' + str(domain_error))
    if not poly_type_set:
        arcpy.AddWarning('WARNNG: One or more TFL_Boundary features missing a Poly_Type')
    if (not poly_type_set) or domain_error:

        return(False)
    if ('Replacement' in poly_types) and (len(poly_types) > 1):
        #If the change is replacement - there should not be any other poly types
        arcpy.AddWarning('WARNING: found a mix of Replacement with other poly types. Check all poly types before submitting again')
        return(False)
    elif 'Replacement' in poly_types:
        #If the change is replacement - check to make sure all schedule A polygons are inside the boundary
        schedule_a_outside = check_schedule_a_is_within(input_tfl,input_gdb)
        if not schedule_a_outside:
            return(False)
        #If replacement - get the list of intersecting timber licenses for confirmation by Forest Tenures
        #message_text = message_text + 'Change is replacement - please confirm the list of timber licenses below with FTB' + '\r\n'
        timber_licenses = get_timber_licences(tfl_poly,input_gdb,BCGWConnection)
        return(True)

    else:
        #otherwise - list the poly types in the message
        for item in poly_types:
            #message_text = message_text + 'Change includes ' + item + '\r\n'
            arcpy.AddMessage('Poly type includes ' + item)
        return(True)


def save_changes_to_gdb(input_gdb,input_tfl,bcgw_connection):
    """ Takes input database. Finds line changes using last edited date stamp and saves those as separate dataset
    finds area changes using symmetrical difference tool comparison to previous final and saves those (if any)"""

    arcpy.env.workspace = input_gdb

    table_object = geobc.TableInfo()
    check_out_date = table_object.get_last_date(input_gdb + os.sep + input_tfl + '_Change_History','Date_Extracted')
    check_out_date = check_out_date.strftime("%b %d %Y %H:%M:%S") #format to string for use in query

    arcpy.AddMessage('Checked out on ' + check_out_date)
    tfl_lines = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Line' #global?
    schedule_a = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Schedule_A' #global?
    #make a feature layer of the boundary poly not including any deletion areas for the comparison
    boundary = input_gdb + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Boundary'
    arcpy.MakeFeatureLayer_management(boundary, 'Boundary_fl', "Poly_Type <> 'Deletion'"), #global?
    boundary_final = TFL_FINAL_FOLDERS + os.sep + input_tfl + os.sep + 'data' + os.sep + 'FADM_' + input_tfl + '.gdb' + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Boundary' #global?
    schedule_a_final = TFL_FINAL_FOLDERS + os.sep + input_tfl + os.sep + 'data' + os.sep + 'FADM_' + input_tfl + '.gdb' + os.sep + 'TFL_Data' + os.sep + input_tfl + '_Schedule_A' #global?

    #make a feature layer of the changed lines - if there are any - save to database
    if arcpy.Exists(input_gdb + os.sep + input_tfl + '_Line_Changes'):
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Line_Changes')
    changed_lines = arcpy.MakeFeatureLayer_management(tfl_lines,'lines_fl',"last_edited_date >  date '" + check_out_date + "'")
    arcpy.CopyFeatures_management(changed_lines,input_gdb + os.sep + input_tfl + '_Line_Changes')
    arcpy.Delete_management(changed_lines)

    #Get a difference layer for the TFL Boundary (compare to TFL Final)
    if arcpy.Exists(input_gdb + os.sep + input_tfl + '_Boundary_Difference'):
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Boundary_Difference')
    arcpy.SymDiff_analysis(boundary,'boundary_fl',input_gdb + os.sep + input_tfl + '_Boundary_Difference')

    #Difference layer TFL Schedule A from Final
    if arcpy.Exists(input_gdb + os.sep + input_tfl + '_Schedule_A_Difference'):
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Schedule_A_Difference')
    arcpy.SymDiff_analysis(schedule_a,schedule_a_final,input_gdb + os.sep + input_tfl + '_Schedule_A_Difference')

    #set up parameters for
    #Schedule A and Current boundary Difference layers from BCGW to final
    tfl_whse = bcgw_connection + '\\WHSE_ADMIN_BOUNDARIES.FADM_TFL_ALL_SP'
    sched_a_whse = bcgw_connection + '\\WHSE_ADMIN_BOUNDARIES.FADM_TFL_SCHED_A'

    #get the format for the forest file ID for query
    if '_0' in input_tfl:
        ffid = input_tfl.replace('_0','')
    else:
        ffid = input_tfl.replace('_','')

    bcgw_sched_a_fl = arcpy.MakeFeatureLayer_management(sched_a_whse, 'bcgw_sched_a_fl', "FOREST_FILE_ID = '" + ffid + "'")
    if arcpy.Exists(input_gdb + os.sep + input_tfl + '_Sched_A_BCGW_Difference'):
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Sched_A_BCGW_Difference')
    arcpy.SymDiff_analysis(bcgw_sched_a_fl,schedule_a_final,input_gdb + os.sep + input_tfl + '_Sched_A_BCGW_Difference')
    arcpy.Delete_management(bcgw_sched_a_fl)

    #make a difference layer between previous final and BCGW
    bcgw_boundary_fl = arcpy.MakeFeatureLayer_management(tfl_whse,'bcgw_boundary_fl', "FOREST_FILE_ID = '" + ffid + "'")
    if arcpy.Exists(input_gdb + os.sep + input_tfl + '_Boundary_BCGW_Difference'):
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Boundary_BCGW_Difference')
    arcpy.SymDiff_analysis(bcgw_boundary_fl,'boundary_fl',input_gdb + os.sep + input_tfl + '_Boundary_BCGW_Difference')
    arcpy.Delete_management(bcgw_boundary_fl)
    arcpy.Delete_management('boundary_fl')

    #Check the difference layers - if there are any differences notify the editor - otherwise - delete them
    #NOTE: this is pretty repetetive and should probably be within a function
    if int(arcpy.GetCount_management(input_gdb + os.sep + input_tfl + '_Sched_A_BCGW_Difference')[0]) > 0:
        arcpy.AddMessage('Saving Schedule A difference layer for BCGW to Final')
    else:
        arcpy.AddMessage('No differences found for Schedule A final to BCGW')
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Sched_A_BCGW_Difference')

    if int(arcpy.GetCount_management(input_gdb + os.sep + input_tfl + '_Boundary_BCGW_Difference')[0]) > 0:
        arcpy.AddMessage('Saving Boundary difference layer for BCGW to Final')
    else:
        arcpy.AddMessage('No differences found for Boundary final to BCGW')
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Boundary_BCGW_Difference')

    if int(arcpy.GetCount_management(input_gdb + os.sep + input_tfl + '_Schedule_A_Difference')[0]) > 0:
        arcpy.AddMessage('Saving difference layer for schedule A')
    else:
        arcpy.AddMessage('No differences found for Schedule A')
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Schedule_A_Difference')

    if int(arcpy.GetCount_management(input_gdb + os.sep + input_tfl + '_Boundary_Difference')[0]) > 0:
        arcpy.AddMessage('Saving difference layer for boundary')
    else:
        arcpy.AddMessage('No differences found for boundary')
        arcpy.Delete_management(input_gdb + os.sep + input_tfl + '_Boundary_Difference')

def create_review_map(inputgdb,input_tfl):
    """Takes input database and makes a copy of the review template. Checks for all derived layers in the edit
    database and if they exist, updates the path to the edit version. Updates path for all base layers.
    saves the copy of the review map document"""
    derived_layers_to_update = ['TFL_XX_Line_Changes','TFL_XX_Boundary_BCGW_Difference','TFL_XX_Boundary_Difference','TFL_XX_Sched_A_BCGW_Difference','TFL_XX_Schedule_A_Difference']
    base_layers_to_update = ['TFL_XX_Line','TFL_XX_Boundary','TFL_XX_Schedule_A']
    #delete previous doc if there is one
    temp_map = input_folder + os.sep + 'arcgisprojects' + os.sep + input_tfl + '_Temp.mxd'
    review_map = input_folder + os.sep + 'arcgisprojects' + os.sep + input_tfl + '_Review.mxd'
    if os.path.exists(review_map):
        os.remove(review_map)

    #copy the template with the new name
    shutil.copy(TFL_TEMPLATE_MAP,temp_map)

    #update the data sources to the working data
    mxd = arcpy.mapping.MapDocument(temp_map)
    for data_frame in arcpy.mapping.ListDataFrames(mxd):
        for layer in arcpy.mapping.ListLayers(mxd):
            if layer.supports('DATASOURCE'):
                if layer.datasetName in derived_layers_to_update:
                    if arcpy.Exists(inputgdb + os.sep + layer.datasetName.replace('TFL_XX',input_tfl)):
                        layer.replaceDataSource(inputgdb,"FILEGDB_WORKSPACE", layer.datasetName.replace('TFL_XX',input_tfl))
                        layer.name = layer.datasetName.replace('TFL_XX',input_tfl)
                    else:
                        arcpy.mapping.RemoveLayer(data_frame,layer)
                elif layer.datasetName in base_layers_to_update:
                    if arcpy.Exists(inputgdb + os.sep + 'TFL_Data' + os.sep + layer.datasetName.replace('TFL_XX',input_tfl)):
                        layer.replaceDataSource(inputgdb,"FILEGDB_WORKSPACE", layer.datasetName.replace('TFL_XX',input_tfl))
                        layer.name = layer.datasetName.replace('TFL_XX',input_tfl)
##                    else:
##                        #IAN - addWarning('shouldn't remove')
##                        arcpy.mapping.RemoveLayer(data_frame,layer)
    mxd.saveACopy(review_map)
    del mxd
    del review_map
    os.remove(temp_map)


def check_schedule_a_is_within(tfl_basename, input_gdb):
    """Takes input edit database and checks to ensure that all schedule A land is
    within the newly created/updated TFL Boundary. Returns False if Schedule A
    exists outside of boundary and True if all Schedule A is within"""
    arcpy.env.workspace = input_gdb

    if arcpy.Exists(input_gdb + os.sep + 'schedule_a_outside'):
        arcpy.Delete_management(input_gdb + os.sep + 'schedule_a_outside')

    arcpy.AddMessage('Lookingfor boundary at : ' + input_gdb + os.sep + tfl_basename + '_Boundary')

    tfl_boundary = arcpy.MakeFeatureLayer_management(input_gdb + os.sep + tfl_basename + '_Boundary','tfl_boundary')
    tfl_schedule_a = arcpy.MakeFeatureLayer_management(input_gdb + os.sep + tfl_basename + '_Schedule_A', 'tfl_schedule_a')
    schedule_a_outside = arcpy.Erase_analysis(tfl_schedule_a,tfl_boundary,'schedule_a_outside')
    arcpy.Delete_management(tfl_boundary)
    arcpy.Delete_management(tfl_schedule_a)
    if int(arcpy.GetCount_management(schedule_a_outside)[0])>0:
        arcpy.AddWarning('ERROR: Found Schedule A polygons outside of TFL Boundary - please review the schedule_a_outside feature class and fix before re-submitting')
        return(False)
    else:
        arcpy.AddMessage('Schedule A is all within the boundary')
        arcpy.Delete_management(schedule_a_outside)
        return(True)

def get_timber_licences(tfl_poly, input_gdb, BCGW_Connection):
    """Used only when change is replacement. Takes the TFL Poly and finds all
       Timber Licenses that are within. Adds the list of licenses to the email
       message text so that FADM staff can confirm with FTB if they should be
       included in the TFL"""
    timber_licences = []
    bcgw_timber_licence = BCGW_Connection + '\\WHSE_FOREST_TENURE.FTEN_TIMBER_LICENCE_POLY_SVW'
    arcpy.env.workspace = input_gdb
    #make a point layer from the timber licenses to check within
    temp_points = arcpy.FeatureToPoint_management(bcgw_timber_licence,'Temp_TL_Points', "INSIDE")
    #make a feature layer of the points to allow a selection
    temp_points_fl = arcpy.MakeFeatureLayer_management(temp_points,'temp_points_fl')
    #make a feature layer of the active timber licences - we will select into this layer after using points to intersect (avoids intersect on edges)
    timber_licence_fl = arcpy.MakeFeatureLayer_management(bcgw_timber_licence, 'timber_licence_fl', "LIFE_CYCLE_STATUS_CODE = 'ACTIVE'")
    arcpy.SelectLayerByLocation_management(temp_points_fl,'INTERSECT',tfl_poly)
    #then select the timber licences that intersect these points
    arcpy.SelectLayerByLocation_management(timber_licence_fl,'INTERSECT',temp_points_fl)
    #delete if the timber licences exists, then create
    if arcpy.Exists(input_gdb + os.sep + 'Timber_Licence'):
        arcpy.Delete_management(input_gdb + os.sep + 'Timber_Licence')
    arcpy.CopyFeatures_management(timber_licence_fl,input_gdb + os.sep + 'Timber_Licence')

    with arcpy.da.SearchCursor(temp_points_fl,['FOREST_FILE_ID']) as cursor:
        for row in cursor:
            arcpy.AddMessage('found forest file ID : ' + row[0])

    arcpy.Delete_management(temp_points)
    arcpy.Delete_management(temp_points_fl)
    arcpy.Delete_management(timber_licence_fl)


def create_update_readme(input_folder,input_tfl, input_gdb):
    """Takes the input Change Description and Change Summary text and creates a readme
    file in the working directory. Overwrites if there is one already.
    Updates the change history table with the description and summary"""
    #delete previous file if there is one - then make a new one
    the_readme = input_folder + os.sep + 'documents' + os.sep + input_tfl + '_change_readme.txt'

    if os.path.exists(the_readme):
        os.remove(the_readme)

    f = open(the_readme,"w+")
    f.write('Change Short Description: \r\n' + change_description + '\r\n' + '\r\n' + 'Change Summary: \r\n' + change_summary)
    f.close()

    #update the last row of the change history table with the input values from the tool
    table = input_gdb + os.sep + input_tfl + '_Change_History'

    #get the last extract date for the query - only want to update the last row
    table_object = geobc.TableInfo()
    extract_date = table_object.get_last_date(table,'Date_Extracted')
    extract_date = extract_date.strftime("%b %d %Y %H:%M:%S")

    fields = ['Date_Extracted','Change_Description','Change_Summary']
    with arcpy.da.UpdateCursor(table,fields, "Date_Extracted >= date '" + extract_date + "'") as cursor:
        for row in cursor:
            row[1] = change_description
            row[2] = change_summary
            cursor.updateRow(row)
        del row
    del cursor

def get_coded_values(gdb, domain_name):
    """takes a gdb object and a string of a domain name, returns a list of domain values.
       NOTE: only works for coded value domains"""
    domains = arcpy.da.ListDomains(gdb)
    domain_list = []
    for domain in domains:
        if domain.name == domain_name:
            values = domain.codedValues
            for val in values.items():
                domain_list.append(val[0])

    return(domain_list)

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


#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('TFL_Prepare_Review_Package')