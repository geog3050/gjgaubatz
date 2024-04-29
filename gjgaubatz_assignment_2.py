###################################################################### 
# Edit the following function definition, replacing the words
# 'name' with your name and 'hawkid' with your hawkid.
# 
# Note: Your hawkid is the login name you use to access ICON, and not
# your firsname-lastname@uiowa.edu email address.
# 
# def hawkid():
#     return(["Caglar Koylu", "ckoylu"])
###################################################################### 
def hawkid():
    return(["Grayson Gaubatz", "gjgaubatz"])

import arcpy
import os
###################################################################### 
# Problem 1 (10 Points)
#
# This function reads all the feature classes in a workspace (folder or geodatabase) and
# prints the name of each feature class and the geometry type of that feature class in the following format:
# 'states is a point feature class'

###################################################################### 
def printFC(workspace):
    arcpy.env.workspace = workspace
    AllFc = arcpy.ListFeatureClasses()
    
    for Fc in AllFc:
        d = arcpy.Describe(Fc)
        print("{} is a {} feature class".format(d.name,d.shapeType))

###################################################################### 
# Problem 2 (20 Points)
#
# This function reads all the attribute names in a feature class or shape file and
# prints the name of each attribute name and its type (e.g., integer, float, double)
# only if it is a numerical type

###################################################################### 
def printNumericalFieldNames(inputFc, workspace):
    arcpy.env.workspace = workspace
    fields = arcpy.ListFields (inputFc)
    for field in fields:
        typ = field.type
        if typ in ("Integer", "Double", "Float"):
            name = field.name
            print("{} is a {} feature class".format(name, typ))

###################################################################### 
# Problem 3 (30 Points)
#
# Given a geodatabase with feature classes, and shape type (point, line or polygon) and an output geodatabase:
# this function creates a new geodatabase and copying only the feature classes with the given shape type into the new geodatabase

###################################################################### 
def exportFeatureClassesByShapeType(input_geodatabase, shapeType, output_geodatabase):
    arcpy.env.workspace = input_geodatabase
    AllFc = arcpy.ListFeatureClasses()
    for Fc in AllFc: 
        d = arcpy.Describe(Fc)
        FcName = d.name
        if d.shapetype.lower() ==  shapeType.lower():
            FcOut = os.path.join(output_geodatabase, FcName)
            arcpy.CopyFeatures_management (Fc, FcOut)

###################################################################### 
# Problem 4 (40 Points)
#
# Given an input feature class or a shape file and a table in a geodatabase or a folder workspace,
# join the table to the feature class using one-to-one and export to a new feature class.
# Print the results of the joined output to show how many records matched and unmatched in the join operation. 

###################################################################### 
def exportAttributeJoin(inputFc, idFieldInputFc, inputTable, idFieldTable, workspace):
    arcpy.env.workspace = workspace
    arcpy.JoinField_management(inputFc, idFieldInputFc, inputTable, idFieldTable)
    arcpy.FeatureClassToFeatureClass_conversion(inputFc, workspace, "join")
    
######################################################################
# MAKE NO CHANGES BEYOND THIS POINT.
######################################################################
if __name__ == '__main__' and hawkid()[1] == "hawkid":
    print('### Error: YOU MUST provide your hawkid in the hawkid() function.')
