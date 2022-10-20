import arcpy 
from ConfigParser import ConfigParser
import sys
import os

config_location = os.path.join(os.path.dirname(__file__), 'config.ini')
config = ConfigParser()
config.read(config_location)
geobc_lib = config.get('DEFAULT', 'geobc_lib')
sys.path.append(geobc_lib)
import geobc

PMBC = config.get('DEFAULT', 'pmbc')
PROV_FOREST_DELETIONS = config.get('DEFAULT', 'prov_forest_deletions')

def get_prov_forest_deletion_layer(BCGWConnection):
    layer = '\\WHSE_ADMIN_BOUNDARIES.FADM_PROV_FOREST_DELETION'
    forest_del = arcpy.MakeFeatureLayer_management(BCGWConnection + layer, 'forest_del')

    return forest_del


def get_pmbc_layer(BCGWConnection):
    pmbc = R'\\WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW'
    pmbc = arcpy.MakeFeatureLayer_management(BCGWConnection + pmbc, 'PMBC')

    return pmbc


def check_deletion_intersect(new_deletion_shape, layer2):
    intersect = arcpy.Intersect_analysis([new_deletion_shape, layer2], 'in_memory/intersect')
    intersect_count = arcpy.GetCount_management(intersect)
    count = intersect_count[0]
    if int(count) > 0:
        deletion_shape_name = arcpy.Describe(new_deletion_shape).name
        arcpy.AddWarning('Overlap found with BCGW Provincial Forest Deletion layer. Intersection layer created.')
        intersect_layer = arcpy.CopyFeatures_management(intersect, deletion_shape_name+'_BCGW_PF_Deletion_Intersect')
        return intersect_layer

    else:
        arcpy.AddWarning('No overlaps with the BCGW Provincial Forest Deletion layer\n')
        return None


def check_parcel_intersect(new_deletion_layer, parcel_layer):
    intersect = arcpy.Intersect_analysis([new_deletion_layer, parcel_layer], 'in_memory/intersect')
    intersect_count = arcpy.GetCount_management(intersect)
    count = intersect_count[0]
    if int(count) > 0:
        arcpy.AddMessage('\n{} overlap(s) found in {}.'.format(count, parcel_layer))

        ownership = []
        fields = [f.name for f in arcpy.ListFields(intersect, 'OWNER*')]
        with arcpy.da.SearchCursor(intersect, fields) as cursor:
            for row in cursor:
                ownership.append(row[0])
        arcpy.AddWarning('The overlaps have the following ownership types in {}:'.format(parcel_layer))
        for owner in set(ownership):
            arcpy.AddWarning('\t--{}'.format(owner))
    else:
        arcpy.AddWarning('No overlaps found with {}\n'.format(parcel_layer))
    

def get_bcgw_connection(bcgw_uname, bcgw_pw):
# SET UP BCGW CONNECTION 
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

    return BCGWConnection


def add_layers(new_layer, zoom=False, rename=None):
    mxd = arcpy.mapping.MapDocument('CURRENT')
    df = arcpy.mapping.ListDataFrames(mxd, '*')[0]
    loaded_layers = [layer.name for layer in arcpy.mapping.ListLayers(mxd, "", df)]
    
    layer_to_add = arcpy.mapping.Layer(new_layer)
    if rename:
        layer_to_add.name = rename

    if layer_to_add.name not in loaded_layers:
        arcpy.mapping.AddLayer(df, layer_to_add, add_position='AUTO_ARRANGE')

        if zoom:
            extent = layer_to_add.getExtent()
            df.extent = extent
            arcpy.RefreshActiveView()


def main():
    new_deletion_shape = arcpy.GetParameterAsText(0)
    working_gdb = arcpy.GetParameterAsText(1)
    bcgw_uname = arcpy.GetParameterAsText(2)
    bcgw_pw = arcpy.GetParameterAsText(3)
    arcpy.env.workspace = working_gdb
    arcpy.env.overwriteOutput = True 


    BCGWConnection = get_bcgw_connection(bcgw_uname,bcgw_pw) # get BCGW connection

    deletion_shape = os.path.basename(new_deletion_shape)
    if not arcpy.Exists(deletion_shape):
        deletion_shape = arcpy.MakeFeatureLayer_management(new_deletion_shape, deletion_shape)  # create a feature layer out of the new deletion shape

    forest_del = get_prov_forest_deletion_layer(BCGWConnection) # get the Provincial Forest Deletion layer from the BCGW
    intersect_layer = check_deletion_intersect(deletion_shape, forest_del)  # Check to see if the new deletion shape overlaps the BCGW deletion layer

    pmbc = get_pmbc_layer(BCGWConnection) # get PMBC layer from BCGW
    os.remove(BCGWConnection)
    
    check_parcel_intersect(deletion_shape, pmbc)  # check the new deletion shape to see if it overlaps with PMBC

    add_layers(new_deletion_shape, zoom=True)   # add new deletion shape to the map and zoom to it

    if intersect_layer: # if the intersection layer is not None, load it into the map
        intersect_layer_name = arcpy.Describe(intersect_layer).name
        add_layers(intersect_layer_name)


if __name__=='__main__':
    main()