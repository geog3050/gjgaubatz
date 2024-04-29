import arcpy
##gather user input for gdb and polygon files
workspace = input("enter gdb: ")
fcPolygonA = input("enter name of first polygon file: ")
fcPolygonB = input("enter name of second polygon file: ")
idFieldPolygonB = input("enter name of ID field for identifying FC: ")

##function for calculating area of polygons 
def calculatePercentAreaOfPolygonAInPolygonB(workspace, fcPolygonA, fcPolygonB, idFieldPolygonB):
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = True
    ##add field to polygon B file
    arcpy.AddField_management(fcPolygonB, "PercentAreaA", "DOUBLE")
	##the fields that will be used in the update cursor, the 
    fieldsUpdate = [idFieldPolygonB, "Shape@", "PercentAreaA" ]        
    ##create a cursor that goes through intersect and finds each polygon's area
    with arcpy.da.UpdateCursor(fcPolygonB, fieldsUpdate) as cursor_Block:
        for row_Block in cursor_Block:
            blockID = row_Block[0]
            blockShape = row_Block[1]
            blockArea = blockShape.area
            
            ##creating a second cursor to curse through second file
            fieldsSearch = [idFieldPolygonB, "Shape@"]
            totalIntersectArea = 0 
            with arcpy.da.SearchCursor(fcPolygonA, fieldsSearch) as cursor_Parks:
                for row_Parks in cursor_Parks:
                    parkID = row_Parks[0]
                    parkShape = row_Parks[1]
                    
                    ##perform and intersect to find the area of the intersection between the two polygons
                    intersect = parkShape.intersect(blockShape, 4)
                    ##calculate the area of the intersection
                    intersectArea = intersect.area
                    ##add the area to the total intersect area for the first polygon and the second
                    totalIntersectArea += intersectArea
                    arcpy.Delete_management(intersect)
            ## calculate the percentage of the area of the block group that the intersection takes up       
            percentOfArea = totalIntersectArea / blockArea
            ##update the field in the row of the cursor 
            row_Block[2] += percentOfArea 
            ##update the row in the file
            cursor_Block.updateRow(row_Block)        
            
##run function the run the program with the user inputs                    
calculatePercentAreaOfPolygonAInPolygonB(workspace, fcPolygonA, fcPolygonB, idFieldPolygonB)