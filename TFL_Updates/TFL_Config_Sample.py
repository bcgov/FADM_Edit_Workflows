######################################################################
## TFL_Config.py
## Purpose: 1. Store configuration for folder and connection paths
##          2. Allow a single line switch to reset from test to production constants for above
## Date: February, 2020
## Author: Jed Harrison, GeoBC
###############################################################################

#MOST IMPORTANT: Set this one variable to true/false when switching between test and production tools
#TEST - Checking to determine Github desktop diff behaviour when using delete/copy from other folder
test = True

class Resources():
    GEOBC_LIBRARY_PATH = R'\\UNC\path\to\GeoBC\library'

class TFL_Path():
    """Class of properties for file paths. Uses test boolean to determine if
       path properties point to test or production data folders. Boolean is
       hard-coded in TFL_Config.py, not passed from calling script"""

    if test:
        FINAL_FOLDER = R'\\UNC\path\to\test\1_TFL_Final'
        EDITS_FOLDER = R'\\UNC\path\to\test\2_TFL_Working'
        REVIEW_FOLDERS = R'\\UNC\path\to\test\3_TFL_Review'
        PENDING_FOLDERS = R'\\UNC\path\to\test\4_TFL_Pending'
        ARCHIVE = R'\\UNC\path\to\test\5_TFL_Archive'
        STAGING = R'\\UNC\path\to\test\TFL_Staging'
        TEMPLATES_GDB = R'\\UNC\path\to\test\TFL_templates\data\FADM_TFL_XX.gdb\TFL_Data'
        TEMPLATE_MAP = R'\\UNC\path\to\test\TFL_templates\arcgisprojects\TFL_Review_Edits_template.mxd'
    else:
        FINAL_FOLDER = R'\\UNC\path\to\prod\1_TFL_Final'
        EDITS_FOLDER = R'\\UNC\path\to\prod\2_TFL_Working'
        REVIEW_FOLDERS = R'\\UNC\path\to\prod\3_TFL_Review'
        PENDING_FOLDERS = R'\\UNC\path\to\prod\4_TFL_Pending'
        ARCHIVE = R'\\UNC\path\to\prod\5_TFL_Archive'
        STAGING = R'\\UNC\path\to\prod\TFL_Staging\data'
        TEMPLATES_GDB = R'\\\UNC\path\to\prod\TFL_templates\data\FADM_TFL_XX.gdb\TFL_Data'
        TEMPLATE_MAP = R'\\UNC\path\to\prod\TFL_templates\arcgisprojects\TFL_Review_Edits_template.mxd'

if __name__ == '__main__':
    pass
