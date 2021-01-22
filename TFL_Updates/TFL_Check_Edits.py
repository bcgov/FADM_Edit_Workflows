######################################################################
## TFL_Check_Edits.py
## Purpose: 1. Check the edited TFL lines for attribute integrity
##          2. Run topology rules on the TFL lines
##          3. Build polygons and check spatial rules (overlaps)
## Date: February, 2019
## Author: Jed Harrison, GeoBC
###############################################################################
#IAN - consider slightly permanent log file for error messages

# Import modules
import arcpy, sys, os, datetime, getpass
from datetime import datetime
import TFL_Config
sys.path.append(TFL_Config.Resources.GEOBC_LIBRARY_PATH)
import geobc


###############################################################################
# set constants (always upper case)
working_location = os.path.abspath(__file__)
test = False
if 'test' in working_location.lower():
    test = True
TFL_Path = TFL_Config.TFL_Path(test=test)

TFL_EDITS_FOLDER = TFL_Path.EDITS_FOLDER

###############################################################################
# get script tool parameters
input_folder = arcpy.GetParameterAsText(0) #Folder containing the TFL line edits
bcgw_uname = arcpy.GetParameterAsText(1)
bcgw_pw = arcpy.GetParameterAsText(2)
input_gdb = TFL_EDITS_FOLDER + os.sep + input_folder + os.sep + 'data' + os.sep + 'FADM_' + input_folder + '.gdb'

tfl_basename = input_folder
tfl_lines = input_gdb + os.sep + 'TFL_Data' + os.sep + tfl_basename + '_Line'

def runapp(tfl_check_edits):

        BCGWConnection = get_bcgw_connection(bcgw_uname,bcgw_pw)
        #CONSIDER rewriting the BCGW connection function - was copied from other code without much review

        if not BCGWConnection is False: #only proceed if connection succeeds -
            #Create active line topology
            create_topology(input_gdb + os.sep + 'TFL_Data', tfl_lines)

            #Run topology tools and report on any errors
            topology_result = run_topology(input_gdb + os.sep + 'TFL_data')

            #Get list of domain values for the line attribute check
            domain_list = get_coded_values(input_gdb, 'STATUS_CODE')

            #Check attribute rules on the lines
            attributes_result = check_line_attributes(tfl_lines, domain_list)

            #Convert lines to polygons using TFL lines - inform if build fails
            build_result = create_polys(input_gdb,tfl_lines,tfl_basename)

            #The next two checks use the TFL boundary - only run them if the polygons built
            if build_result is True:

                #Check that the new TFL Boundary does not overlap with any other TFL
                #This is a soft rule that will not prevent submission as there may be multiple overlaps
                tfl_overlap_result = check_tfl_overlaps(tfl_basename,input_gdb,BCGWConnection)

                #Check to see if there are any schedule A polygons NOT within the Schedule B - warn if found
                schedule_a_within_result = check_schedule_a_is_within(tfl_basename,input_gdb)

            #track completion of this stage in transaction details table
            if topology_result is True and attributes_result is True and build_result is True:
                #Mark as passed and update table
                update_transaction_details(input_gdb,tfl_basename,"Yes")
                arcpy.AddMessage('\nScript completed with no errors - data can proceed to review stage when ready.\n \
                Any changes to data will require this script to be re-run')
            else:
                #Mark as failed
                update_transaction_details(input_gdb,tfl_basename,"No")
                arcpy.AddWarning('\nScript completed with errors found - please review the error messages and \
                correct before re-running test')

        else:
            arcpy.AddError('\nProblem creating BCGW Connection - please re-enter credentials')

###############################################################################
## Functions section
###############################################################################

def create_topology(workspace, tfl_lines):
    """Creates topology in the edit workspace creates an ACTIVE TFL line FC and adds rules to it
    workspace is the feature dataset"""
    arcpy.env.workspace = workspace
    topology = workspace + os.sep + 'TFL_Active_Line_Topology'
    if arcpy.Exists(topology):
        arcpy.Delete_management(topology)
    #make feature layer of active lines
    if arcpy.Exists(workspace + os.sep + 'TFL_Active_Lines'):
        arcpy.Delete_management(workspace + os.sep + 'TFL_Active_Lines')
    tfl_active_lines_layer = arcpy.MakeFeatureLayer_management(tfl_lines, 'tfl_active_lines_layer', "Status_Code IN ('ACTIVE')")
    arcpy.CopyFeatures_management('tfl_active_lines_layer', workspace + os.sep + 'TFL_Active_Lines')
    feature_class = workspace + os.sep + 'TFL_Active_Lines'
    del tfl_active_lines_layer

    try:
        arcpy.CreateTopology_management(workspace,'TFL_Active_Line_Topology', .0001)
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
        arcpy.AddMessage('Added topology to TFL Active Lines')
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

    #Run topology that was created in TFL_Prepare_Edits
    arcpy.ValidateTopology_management(input_gdb + os.sep + 'TFL_Active_Line_Topology')
    arcpy.ExportTopologyErrors_management(input_gdb + os.sep + 'TFL_Active_Line_Topology', input_gdb, 'Topology_Error')

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
        arcpy.AddMessage('No topology errors found\n')
        return(True)
    else:
        arcpy.AddWarning('Topology errors found - please review the topology results and correct\n')
        for error in errors:
            arcpy.AddWarning(error)
        return(False)

def create_polys(input_gdb, tfl_lines, tfl_basename):
    """"Takes input TFL lines and attempts to build polygons to a temp layer. If build
    succeeds, appends them to the empty TFL Boundary feature class, deletes the temp
    layer and returns True. If no polygons created, deleted temp layer and returns False"""

    #Check if a previous temp poly exists - if so delete it first
    if arcpy.Exists(input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Poly'):
        arcpy.Delete_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Poly')

    #select only the active and retired lines - use to build polys - retired lines are used for deletions
    arcpy.MakeFeatureLayer_management(tfl_lines, 'tfl_lines_layer', "Status_Code IN ('ACTIVE', 'RETIRED')")

    #If there are any records in the TFL Boundary poly, copy the layer to points (to save attributes), then create the polys
    if int(arcpy.GetCount_management(input_gdb + os.sep + 'TFL_Data' + os.sep + tfl_basename + '_Boundary')[0]) > 0:
        #check for previous temp points layer
        if arcpy.Exists(input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Boundary_Points'):
            arcpy.Delete_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Boundary_Points')
        #copy polygons to points to allow the attributes to be copied over later
        arcpy.AddMessage('----- copying TFL boundary to temp points')
        #Use feature to point to save poly attributes temporarily
        arcpy.FeatureToPoint_management(input_gdb + os.sep + 'TFL_Data' + os.sep + tfl_basename + '_Boundary','Temp_Boundary_Points', "INSIDE")
        arcpy.AddMessage('----- deleting previous boundary')
        arcpy.DeleteRows_management(input_gdb + os.sep + 'TFL_Data' + os.sep + tfl_basename + '_Boundary')
        #create temp poly using the points as attributes
        arcpy.FeatureToPolygon_management('tfl_lines_layer',input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Poly','','','Temp_Boundary_Points')
        #run inverted selection to create a feature layer for poly's with no points, then delete it
        arcpy.MakeFeatureLayer_management('Temp_Poly','Poly_Without_Points')
        arcpy.SelectLayerByLocation_management('Poly_Without_Points','INTERSECT','Temp_Boundary_Points','','','INVERT')
        arcpy.DeleteFeatures_management('Poly_Without_Points')

    #otherwise - just create them without using the temp points
    else:
        arcpy.FeatureToPolygon_management('tfl_lines_layer',input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Poly')

    if int(arcpy.GetCount_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Poly').getOutput(0)) == 0:
        arcpy.AddWarning("===== Error - No polygons created\n")
        return(False)
    else:

        #Append Temp_Poly into empty _Boundary
        arcpy.AddMessage('Appending new geometry to TFL Boundary polygon')
        arcpy.Append_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Poly',input_gdb + os.sep + 'TFL_Data' + os.sep + tfl_basename + '_Boundary', 'NO_TEST')
        arcpy.Delete_management(input_gdb + os.sep + 'TFL_Data' + os.sep + 'Temp_Poly')

        #If there are temp boundary points, delete them
        if arcpy.Exists(input_gdb + os.sep + 'Temp_Boundary_Points'):
            arcpy.Delete_management(input_gdb + os.sep + 'Temp_Boundary_Points')

        #replace underscores and zeros to create the Forest File ID
        if '_0' in tfl_basename:
            forest_file_id = tfl_basename.replace('_0','')
        else:
            forest_file_id = tfl_basename.replace('_','')

        #Populate the required fields
        arcpy.AddMessage('----- Populating TFL Boundary polygon attributes\n')
        fields = ['FOREST_FILE_ID', 'FEATURE_CLASS_SKEY']
        with arcpy.da.UpdateCursor(input_gdb + os.sep + 'TFL_Data' + os.sep + tfl_basename + '_Boundary', fields) as cursor:
            for row in cursor:
                row[0] = forest_file_id
                row[1] = 830
                cursor.updateRow(row)
        return(True) #success

def check_line_attributes(tfl_lines, domain_list):
    """Checks the TFL Lines for null values in fields that should be populated
    if nulls are found, prints arcpy message with the null fields. Returns true
    if no nulls are found, and False if nulls are found. Calls function to check required line attributes from domain"""
    fields = ['Legal_Description', 'Status_Code','Source_Code']
    #use set instead of list because it only stores unique values and we are only
    #interested in knowing which fields have nulls
    nulls_found = set()
    domain_error = False
    with arcpy.da.SearchCursor(tfl_lines, fields) as cursor:
        for row in cursor:
            if row[0] == None:
                nulls_found.add('Legal_Description')
            if row[1] == None:
                nulls_found.add('Status_Code')
            if row[2] == None:
                nulls_found.add('Source_Code')
            if row[1] not in domain_list:
                domain_error = True

    if nulls_found:
        arcpy.AddWarning('ERROR: Null values found in ' + str(nulls_found))
    if domain_error:
        arcpy.AddWarning('ERROR: one or more lines are not using domain values for STATUS_CODE')
    if nulls_found or domain_error:
        return(False)
    else:
        return(True)

def get_bcgw_connection(bcgw_uname, bcgw_pw):
# SET UP BCGW CONNECTION -----------------------------------------------------------------
    arcpy.AddMessage(" ")
    arcpy.AddMessage("Setting up the BCGW connection...\n")

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


def check_tfl_overlaps(tfl_basename, input_gdb, BCGWConnection):
    """takes input TFL and GCBW connection. Checks to see if the
    new TFL Boundary overlaps with any other TFL's in the BCGW.
    If overlaps exist, saves them in the working database and
    returns False. If no overlaps, deletes temp layer and returns True"""
    #clean up from any previous runs
    if arcpy.Exists(input_gdb + os.sep + 'TFL_Overlaps'):
        arcpy.Delete_management(input_gdb + os.sep + 'TFL_Overlaps')
    if arcpy.Exists(input_gdb + os.sep + 'tfl_whse_selection'):
        arcpy.Delete_management(input_gdb + os.sep + 'tfl_whse_selection')

    tfl_whse_fc = BCGWConnection + '\\WHSE_ADMIN_BOUNDARIES.FADM_TFL_ALL_SP'
    if '_0' in tfl_basename:
        tfl_FFID_modified = tfl_basename.replace('_0','')
    else:
        tfl_FFID_modified = tfl_basename.replace('_','')
    arcpy.MakeFeatureLayer_management(tfl_whse_fc, 'tfl_whse_fl')
    arcpy.SelectLayerByAttribute_management('tfl_whse_fl','NEW_SELECTION', "FOREST_FILE_ID <> '" + tfl_FFID_modified + "'")
    arcpy.CopyFeatures_management('tfl_whse_fl',input_gdb + os.sep + 'tfl_whse_selection')
    input_layers = [input_gdb + os.sep + 'TFL_Data' + os.sep + tfl_basename + '_Boundary',input_gdb + os.sep + 'tfl_whse_selection']

    arcpy.Intersect_analysis(input_layers,input_gdb + os.sep + 'TFL_Overlaps')
    arcpy.Delete_management(input_gdb + os.sep + 'tfl_whse_selection')

    if int(arcpy.GetCount_management(input_gdb + os.sep + 'TFL_Overlaps').getOutput(0)) > 0:
        arcpy.AddWarning('===== Overlaps found with another TFL in BCGW Current View - please check the TFL Overlaps feature class in the working GDB\n')
        return(False)
    else:
        arcpy.AddMessage('No TFL overlaps found\n')
        arcpy.Delete_management(input_gdb + os.sep + 'TFL_Overlaps')
        return(True)

def check_schedule_a_is_within(tfl_basename, input_gdb):
    """Takes input edit database and checks to ensure that all schedule A land is
    within the newly created/updated TFL Boundary. Returns False if Schedule A
    exists outside of boundary and True if all Schedule A is within"""

    arcpy.env.workspace = input_gdb

    if arcpy.Exists(input_gdb + os.sep + 'schedule_a_outside'):
        arcpy.Delete_management(input_gdb + os.sep + 'schedule_a_outside')

    tfl_boundary = arcpy.MakeFeatureLayer_management(input_gdb + os.sep + tfl_basename + '_Boundary','tfl_boundary')
    tfl_schedule_a = arcpy.MakeFeatureLayer_management(input_gdb + os.sep + tfl_basename + '_Schedule_A', 'tfl_schedule_a')
    schedule_a_outside = arcpy.Erase_analysis(tfl_schedule_a,tfl_boundary,'schedule_a_outside')
    if int(arcpy.GetCount_management(schedule_a_outside)[0])>0:
        arcpy.AddWarning('===== Found Schedule A polygons outside of TFL Boundary - please review the schedule_a_outside feature class\n')
        return(False)
    else:
        arcpy.AddMessage('Schedule A is all within the boundary\n')
        arcpy.Delete_management(schedule_a_outside)
        return(True)

def update_transaction_details(input_gdb,tfl_basename, result):
    """Takes the result of all checks and either inserts (if there is no record
    or updates (if there is a record) the transaction details table. This table
    should only ever have 0 or 1 records as it is used to track completion of stages
    in the edit process. Saves check results and editor user name"""
    fields = ['Check_Edits_Passed','Check_Edits_Date','Edits_Checked_By']
    user = getpass.getuser()
    timestamp = datetime.now()
    transaction_table = input_gdb + os.sep + tfl_basename + '_Transaction_Details'
    #Check to see if there is already a record - then update or insert as needed
    count = arcpy.GetCount_management(transaction_table)

    if int(count[0]) == 0:
        cursor = arcpy.da.InsertCursor(transaction_table,fields)
        cursor.insertRow((result,timestamp,user))
        del cursor
    elif int(count[0]) == 1:
        with arcpy.da.UpdateCursor(transaction_table,fields) as cursor:
            for row in cursor:
                row[0] = result
                row[1] = timestamp
                row[2] = user
                cursor.updateRow(row)
    else:
        arcpy.AddError('ERROR - more than one row in transaction details table - something wrong')

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

#This section calls the other routines (def)
if __name__ == '__main__':
    runapp('tfl_check_edits')