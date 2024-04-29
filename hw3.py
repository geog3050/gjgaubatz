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
    return(["name", "hawkid"])

###################################################################### 
# Problem 1: 20 Points
#
# Given a csv file import it into the database passed as in the second parameter
# Each parameter is described below:

# csvFile: The absolute path of the file should be included (e.g., C:/users/ckoylu/test.csv)
# geodatabase: The workspace geodatabase
###################################################################### 
import arcpy
def importCSVIntoGeodatabase(csvFile, geodatabase):
    importedCSVPath = arcpy.TableToTable_conversion(csvFile, geodatabase, "imported")
    return importedCSVPath
##################################################################################################### 
# Problem 2: 80 Points Total
#
# Given a csv table with point coordinates, this function should create an interpolated
# raster surface, clip it by a polygon shapefile boundary, and generate an isarithmic map

# You can organize your code using multiple functions. For example,
# you can first do the interpolation, then clip then equal interval classification
# to generate an isarithmic map

# Each parameter is described below:

# inTable: The name of the table that contain point observations for interpolation       
# valueField: The name of the field to be used in interpolation
# xField: The field that contains the longitude values
# yField: The field that contains the latitude values
# inClipFc: The input feature class for clipping the interpolated raster
# workspace: The geodatabase workspace

# Below are suggested steps for your program. More code may be needed for exception handling
#    and checking the accuracy of the input values.

# 1- Do not hardcode any parameters or filenames in your code.
#    Name your parameters and output files based on inputs. For example,
#    interpolated raster can be named after the field value field name 
# 2- You can assume the input table should have the coordinates in latitude and longitude (WGS84)
# 3- Generate an input feature later using inTable
# 4- Convert the projection of the input feature layer
#    to match the coordinate system of the clip feature class. Do not clip the features yet.
# 5- Check and enable the spatial analyst extension for kriging
# 6- Use KrigingModelOrdinary function and interpolate the projected feature class
#    that was created from the point feature layer.
# 7- Clip the interpolated kriging raster, and delete the original kriging result
#    after successful clipping. 
#################################################################################################################### 
## qulity check function: if there are non-numeric values they will be set to none
def tableQualityCheck (inTable):
    fields = arcpy.ListFields(inTable)
    fieldNames = [field.name for field in fields]
    # Open a up cursor to iterate through rows in the table
    with arcpy.da.UpdateCursor(inTable, fieldNames) as cursor:
        for row in cursor:
            ##look through each value to change them if they are not a numeric variable such as a float that appears as a string
            for i, value in enumerate(row):
                
                ##fixes some values that are listed incorrectly
                if row[i] == 'M':
                    row[i] = None
                if row[i] != None:
                    try:
                        row[i] = float(row[i])
                    except ValueError:
                        pass
            cursor.updateRow(row)

def krigingFromPointCSV(inTable, valueField, xField, yField, inClipFc, workspace):
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = True
    ##call previous function to import table into Geodatabase
    inTable = importCSVIntoGeodatabase(inTable, workspace)
    
    ##perform quality check on the imported table
    tableQualityCheck (inTable)
    #generate input feature
    pointsFromInTable = arcpy.MakeXYEventLayer_management(inTable, xField, yField, "pointsFromInTable")
    
    #check if spatial analyist is availible 
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        raise Exception("Spatial Analyst extension is not available.")
        
    ##project point class    
    pointsFromInTableProjected = arcpy.Project_management(pointsFromInTable, "pointsFromInTableProjected", inClipFc)
  
    ##create krig with projected points 
    krigingOut = arcpy.Kriging_3d(pointsFromInTableProjected, valueField, "krigingOut")
    
    ##clip krig
    krigingClip = arcpy.Clip_management(krigingOut,"#","krigingClipped", inClipFc,  "None", "ClippingGeometry", "MAINTAIN_EXTENT")

    
    if arcpy.Exists(krigingClip):
        arcpy.Delete_management(krigingOut)
        arcpy.Delete_management(pointsFromInTable)

##run statement asking for user input and running main body of code
def run():
    geodatabase = input("enter full path for geodatabase: ")
    csvFile = input("enter full path for CSV that contains data: ")
    inClipFc = input("enter name of file for clipping: ")
    valueField = input("enter name of field that will serve as z value for krig: ")
    xField = input("enter name of field that will serve as x value for krig: ")
    yField = input("enter name of field that will serve as y value for krig: ")
    
    krigingFromPointCSV(csvFile, valueField, xField, yField, inClipFc, geodatabase)

run()            

######################################################################
# MAKE NO CHANGES BEYOND THIS POINT.
######################################################################
if __name__ == '__main__' and hawkid()[1] == "hawkid":
    print('### Error: YOU MUST provide your hawkid in the hawkid() function.')
