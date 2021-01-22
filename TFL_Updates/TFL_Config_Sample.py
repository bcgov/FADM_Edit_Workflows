######################################################################
## TFL_Config.py
## Purpose: 1. Store configuration for folder and connection paths
##          2. Allow a single line switch to reset from test to production constants for above
## Date: February, 2020
## Author: Jed Harrison, GeoBC
###############################################################################
## Edited: January 2021
## By: Brett Edwards, GeoBC
## Change: Add __init__ function, giving the user/code the ability to run in either test or prod upon initializing TFL_Path()


class Resources():
    GEOBC_LIBRARY_PATH = R'\\spatialfiles.bcgov\ilmb\dss\dsswhse\Tools and Resources\Scripts\Python\Library'

class TFL_Path():
    """Class of properties for file paths. Uses test boolean to determine if
       path properties point to test or production data folders. Boolean is
    passed from calling script, with a default setting of working in test"""
    def __init__(self, test = True):
        self.test = test

        if self.test:
            self.FINAL_FOLDER = R'\\UNC\path\to\test\1_TFL_Final'
            self.EDITS_FOLDER = R'\\UNC\path\to\test\2_TFL_Working'
            self.REVIEW_FOLDERS = R'\\UNC\path\to\test\3_TFL_Review'
            self.PENDING_FOLDERS = R'\\UNC\path\to\test\4_TFL_Pending'
            self.ARCHIVE = R'\\UNC\path\to\test\5_TFL_Archive'
            self.STAGING = R'\\UNC\path\to\test\TFL_Staging'
            self.TEMPLATES_GDB = R'\\UNC\path\to\test\TFL_templates\data\FADM_TFL_XX.gdb\TFL_Data'
            self.TEMPLATE_MAP = R'\\UNC\path\to\test\TFL_templates\arcgisprojects\TFL_Review_Edits_template.mxd'
        else:
            self.FINAL_FOLDER = R'\\UNC\path\to\prod\1_TFL_Final'
            self.EDITS_FOLDER = R'\\UNC\path\to\prod\2_TFL_Working'
            self.REVIEW_FOLDERS = R'\\UNC\path\to\prod\3_TFL_Review'
            self.PENDING_FOLDERS = R'\\UNC\path\to\prod\4_TFL_Pending'
            self.ARCHIVE = R'\\UNC\path\to\prod\5_TFL_Archive'
            self.STAGING = R'\\UNC\path\to\prod\TFL_Staging\data'
            self.TEMPLATES_GDB = R'\\\UNC\path\to\prod\TFL_templates\data\FADM_TFL_XX.gdb\TFL_Data'
            self.TEMPLATE_MAP = R'\\UNC\path\to\prod\TFL_templates\arcgisprojects\TFL_Review_Edits_template.mxd'


if __name__ == '__main__':
    pass