import arcpy
from arcpy import env
import os
import pandas as pd
import numpy as np


IGNORE_FIELDS = ['CHANGE_TYPE']


def get_coded_domain_name_values(gdb):
    """
    This function will accept any gdb object and return a dictionary containing
    the domain names as keys and the domain values as values. It only returns
    the coded domain values, not range values.

    Args:
        gdb: Path to ESRI Geodatabase

    Returns:
        Dictionary of domain names and values.
        Format:: {Domain.name}:{Domain.value1, Domain.value2,...}
    """
    domains = arcpy.da.ListDomains(gdb)
    domain_dict = {}

    for domain in domains:
        if domain.domainType == 'CodedValue':
            coded_values = domain.codedValues
            for key in coded_values.keys():
               domain_dict.setdefault(domain.name,[]).append(key)
    return domain_dict


def table_to_data_frame(in_table, input_fields=None, where_clause=None):
    """Function will convert an arcgis table into a pandas dataframe with an object ID index, and the selected
    input fields using an arcpy.da.SearchCursor.

    Args:
        in_table: Path to ESRI feature class
        input_fields: String or list of strings containing output field names. If None, all fields will be returned.
        where_clause: where_clause as per arcpy.da.SearchCursor documentation

    Returns:
        Pandas dataframe
    """
    OIDFieldName = arcpy.Describe(in_table).OIDFieldName
    if input_fields:
        final_fields = [OIDFieldName] + input_fields
    else:
        final_fields = [field.name for field in arcpy.ListFields(in_table)]
    data = [row for row in arcpy.da.SearchCursor(in_table, final_fields, where_clause=where_clause)]
    fc_dataframe = pd.DataFrame(data, columns=final_fields)
    fc_dataframe = fc_dataframe.set_index(OIDFieldName, drop=True)
    return fc_dataframe


def validate_domains(gdb, arcpy_workspace):
    errors = False  #  Global reporter of errors. False (no errors found) by default

    arcpy.AddMessage('\n----- Validating values for all features... (Layers & Fields will only be reported if nulls or errors found)')

    domain_dict = get_coded_domain_name_values(gdb)
    arcpy.env.workspace = arcpy_workspace

    # this code involving datasets will allow all feature classes in a workspace to be iterated through, even if they are within datasets 
    datasets = arcpy.ListDatasets(feature_type='feature')           
    datasets = [''] + datasets if datasets is not None else []          

    for ds in datasets:
        for fc in arcpy.ListFeatureClasses(feature_dataset=ds):
            fields_with_domain = []             # create a list to store the fields which have a domain
            
            fields = arcpy.ListFields(fc)
            for field in fields:
                if field.domain:
                    fields_with_domain.append(field)

            if fields_with_domain:      # if there are fields which have a domain in this feature
                df = table_to_data_frame(fc, input_fields=[f.name for f in fields_with_domain])     # convert the table to a pandas dataframe. DFs are easy to work with and the syntax hasn't changed so moving code to Python3/ArcPro should go smoothly

                if 'IS_INSET_POINT' in df.columns.values.tolist():     # The domain values for 'IS_INSET_POINT' are ['Yes', 'No'], but values written into fields are commonly ['yes', 'no'] so we must covert the casing to match the domains in order to do checks
                    df = convert_pandas_case(df, 'IS_INSET_POINT')

                for field in fields_with_domain: 
                    error_messages = []     # create a list to store 'special case' error messages that will be printed

                    error_df = df[field.name].isin(domain_dict[field.domain])   # searching field columns for proper domain values. 'True' where domain value is present, 'False' where domain value is not present or value is null
                    err_count = (~error_df).sum()       # Make it 'False' where domain values are present and 'True' where not present. Sum the number of 'True' values

                    null_df = df[field.name].isnull()   # count the number of values where the field is null
                    null_count = null_df.sum()

                    if field.isNullable:        # nulls were included in the error count before. If schema allows for nulls, lets remove them from the error count
                        err_count = err_count - null_count
                        if err_count > 0:       # if after removing allowed null values there are still errors, set errors to True
                            errors = True

                    if field.name == 'Poly_Type':       # special check that wouldn't be caught by schema/domain checks, will add to error messages if problems found
                        poly_type_errors = check_poly_types(df)
                        error_messages.append(poly_type_errors)

                    if field.name == 'Legislative_Tool':    # special check that wouldn't be caught by schema/domain checks, will add to error messages if problems found
                        leg_tool_errors = check_legislative_tool(df)
                        error_messages.append(leg_tool_errors)

                    if any(error_messages):     # if there are any error message, set errors to True
                        errors = True

                    # if (null_count > 0 or err_count > 0 or any(error_messages)) and field.name not in IGNORE_FIELDS:
                    #     print(fc+' : '+field.name)
                    #     print('\tRecords: {}'.format(len(df)))
                    #     print('\tErrors: {}'.format(err_count))
                    #     print('\tNull: {}'.format(null_count))

                    #     for message in error_messages:
                    #         print('\n'.join(message))

                    if (null_count > 0 or err_count > 0 or any(error_messages)) and field.name not in IGNORE_FIELDS:    # print out all results if nulls, domain errors, or error messages found as long as the field is not in the ignored_fields list
                        arcpy.AddMessage(fc+' : '+field.name)
                        arcpy.AddMessage('\tRecords: {}'.format(len(df)))
                        arcpy.AddMessage('\tNull: {}'.format(null_count))
                        arcpy.AddWarning('\tDomain Errors: {}'.format(err_count))

                        for message in error_messages:
                            arcpy.AddWarning('\n'.join(message))

    if errors:
        arcpy.AddError('\n\nERROR: Problems found while validating field values. Please move the TFL back to working and correct errors.')

    return errors


def check_poly_types(df):
    """ 
    Special checks to ensure the Poly_Types field adheres to what we want apart
    from domain/schema checks. 

    Args:
        df: Pandas dataframe of feature class table containing the field 'Poly_Type'

    Returns:
        errors: list of error message strings to print to the console
    """
    errors = []

    poly_types = df['Poly_Type'].unique().tolist()      # If the change is a Replacement, check to make sure all Poly_Types are Replacement
    if ('Replacement' in poly_types) and (len(poly_types) > 1):
        errors.append('\tWARNING: The Poly_Type field contains "Replacement" along with other Poly_Types. This is not allowed')

    null_count = df['Poly_Type'].isnull().sum()     # Poly_Types is allowed to be null according to schema, but we don't want it to be at this stage
    if null_count > 0:
        message = '\tWARNING: {} features are missing a Poly_Type'.format(null_count)
        errors.append(message)

    return errors


def check_legislative_tool(df):
    """
    Special checks to ensure the Legislative_Tool field adheres to what we want apart
    from domain/schema checks.
    """
    errors = []

    # Legislative tool should really only be null where the Poly_type is Current View. Find the places where that isn't true
    leg_issues_index = np.where((df['Legislative_Tool'].isnull()) & (df['Poly_Type'] != 'Current_View'))
    num_leg_issues = len(leg_issues_index[0]) # np.where returns a 2d array, with the results we care about being in the first array

    if num_leg_issues > 0:
        message = '\tWARNING: There are {} instances where Legislative_Tool is null, but Poly_Type is not a "Current View"'.format(num_leg_issues)
        errors.append(message)

    return errors


def convert_pandas_case(df, field):
    df[field] = df[field].str.title()   # change the casing to Title casing. This was only made a function in case we run into this anywhere else.
    return df


if __name__=='__main__':
    gdb = R"H:\__FADM\__code_tests\FADM_TFL_57.gdb"
    workspace = R'H:\__FADM\__code_tests\FADM_TFL_57.gdb\TFL_Data'

    errors = validate_domains(gdb, workspace)
    print(errors)

