import arcpy
import numpy as np
import pandas as pd
import math

def AFSCBaseReorg(destinationFolder, CSVPath):
    # Load the data from the CSV file
    data = pd.read_csv(CSVPath)

    dfMelted = data.melt(var_name='AFSC', value_name='Base')
    # Remove any leading or trailing spaces in 'Base' names
    dfMelted['Base'] = df_melted['Base'].str.strip()

    # Drop rows with None values
    dfMelted = df_melted.dropna()

    # Group by base make list of the AFSCs for each base
    baseAfscs = dfMelted.groupby('Base')['AFSC'].apply(list).reset_index()

    # Rename columns for clarity
    baseAfscs.columns = ['Base', 'AFSC']

    # Set CSV Name
    resultCSVName = "AFSCAtEachBase"

    # Save the resulting table to a CSV file
    AFSCBaseReorgCSV = f"{destinationFolder}/{resultCSVName}.csv"
    baseAfscs.to_csv(AFSCBaseReorgCSV, index=False)
    return AFSCBaseReorgCSV

def coordinateCleanUp(destinationFolder, AFSCBaseReorgCSV):

    # Load the CSV file
    data = pd.read_csv(AFSCBaseReorgCSV)

    # Split the 'Coordinates' column into 'Longitude' and 'Latitude'
    data[['Longitude', 'Latitude']] = data['Coordinates'].str.split(';', expand=True)

    # Convert the new columns to numeric types, ensuring they are signed numbers
    data['Longitude'] = pd.to_numeric(data['Longitude'], errors='coerce')
    data['Latitude'] = pd.to_numeric(data['Latitude'], errors='coerce')
    
    resultCSVName = "AFSCBaseCoordinateClean"

    # Save the corrected dataframe back to a CSV file
    AFSCBaseCoordinateClean = f"{destinationFolder}/{resultCSVName}.csv"

    data.to_csv(AFSCBaseCoordinateClean, index=False)
    return AFSCBaseCoordinateClean

def csvMerge():
    # Merge the dataframes on Base ID while preserving all rows from AFSCs at Each Base dataframe
    merged_df = afscs_at_base.merge(corrected_info[['BASE-ID', 'Longitude', 'Latitude']],
                                    left_on='Base ID',
                                    right_on='BASE-ID',
                                    how='left')

    # Drop the 'BASE-ID' column as it's redundant after the merge
    merged_df.drop(columns=['BASE-ID'], inplace=True)

    # Show the first few rows of the merged dataframe
    merged_df.head()

def createGeodatabase(outputDirectory, geodatabaseName):
    
    # Construct the full path for the new geodatabase
    gdbPath = f"{outputDirectory}/{geodatabaseName}.gdb"

    # Check if the geodatabase already exists
    if arcpy.Exists(gdbPath):
        print(f"Geodatabase already exists: {gdbPath}")
    else:
        # Create the file geodatabase
        arcpy.CreateFileGDB_management(outputDirectory, geodatabaseName)
        print(f"Geodatabase created at: {gdbPath}")

    return gdbPath    
    
def importCSVIntoGeodatabase(csvFile, geodatabase):
    importedCSVPath = arcpy.TableToTable_conversion(csvFile, geodatabase, "BaseInfo")
    return importedCSVPath

def cleanCSVinGeodatabase(table_path):
    ##Use an UpdateCursor to modify the AFSC field
    with arcpy.da.UpdateCursor(table_path, ["AFSC"]) as cursor:
        for row in cursor:
            if row[0].startswith('[') and row[0].endswith(']'):
                # Clean the AFSC field by removing unwanted characters
                clean_afsc = row[0].replace('[', '').replace(']', '').replace("'", "").strip()
                clean_afsc = clean_afsc.replace(" ", "")
                #Ensure clean formatting as a comma-separated string
                row[0] = ', '.join(clean_afsc.split(', '))
                cursor.updateRow(row)

##Builds a dictionary mapping base names to a list of AFSCs as a list contataining a string
def buildBaseDict(importedCSVPath, geodatabase):
    ##uses table mported into geodatabase
    # Set the environment workspace (assuming the table is in a geodatabase)
    arcpy.env.workspace = geodatabase

    # Name of your table
    tableName = importedCSVPath
    # Fields in the table: Base, Latitude, Longitude, AFSC
    fields = ['Base', 'Latitude', 'Longitude', 'AFSC']

    # Initialize an empty dictionary to store base data
    baseDict = {}

    # Create a search cursor to iterate over the rows in the table
    with arcpy.da.SearchCursor(tableName, fields) as cursor:
        for row in cursor:
            base = row[0]
            lat = row[1]
            lon = row[2]
            afsc = row[3]

            # Check if the base is already in the dictionary
            if base not in baseDict:
                baseDict[base] = {'Location': {'Latitude': lat, 'Longitude': lon}, 'AFSC': [afsc]}
            else:
                # Add the AFSC to the list if it's not already included
                if afsc not in baseDict[base]['AFSC']:
                    baseDict[base]['AFSC'].append(afsc)
            
    return baseDict
    
##Builds a dictionary mapping AFSC codes to a list of bases where the AFSC is present.
def buildAFSCDict(baseData):
    ##imports previously created base Dict
    afsc_dict = {}

    # Iterate over each base in the provided dictionary
    for base, info in baseData.items():
        # Extract the single string from the 'AFSC' list and split it into individual AFSC codes
        if info['AFSC']:  # Check if there's an AFSC entry
            afsc_list = info['AFSC'][0].split(',')  # Split the string on commas

            for afsc in afsc_list:
                clean_afsc = afsc.strip()
                # Clean up whitespace around the AFSC codes
                if clean_afsc not in afsc_dict:
                    afsc_dict[clean_afsc] = []
                afsc_dict[clean_afsc].append(base)

    # Convert lists of bases to comma-separated strings
    ##for afsc in afsc_dict:
    ##    afsc_dict[afsc] = ', '.join(set(afsc_dict[afsc]))  # Use `set` to remove duplicate bases
    
    return afsc_dict
    
##Creates a table in the geodatabase with AFSC codes only.
def AFSCTable(afscDict, geodatabase):
    ##afscDict (dict): Dictionary with AFSC codes as keys.
    ##geodatabase (str): Path to the geodatabase where the table will be created.

    arcpy.env.workspace = geodatabase
    tableName = "afscTable"

    # Delete the table if it exists
    if arcpy.Exists(tableName):
        arcpy.Delete_management(tableName)
        print(f"Existing table '{tableName}' was deleted.")

    # Create the table anew
    arcpy.CreateTable_management(geodatabase, tableName)
    arcpy.AddField_management(tableName, "AFSC", "TEXT", field_length=100)
    
    print(f"New table '{tableName}' created in the geodatabase.")

    # Insert records
    fields = ["AFSC"]
    with arcpy.da.InsertCursor(tableName, fields) as cursor:
        for afsc in afscDict.keys():
            cursor.insertRow([afsc])
            

    print("AFSC table has been successfully created with updated data.")
    return tableName
    
##Calculates the standard distance for each AFSC based on base locations extracted from a shapefile and updates an existing table in the geodatabase with these distances.
def standardDistance(inputDict, geodatabase, tableName, baseTable):
    
    ##inputDict (dict): Dictionary containing AFSC codes and associated list of base names.
    ##geodatabase (str): The path to the geodatabase where the table exists.
    ##tableName (str): The name of the table to update.
    ##shapefilePath (str): Path to the shapefile containing base coordinates.

    arcpy.env.workspace = geodatabase

    # Check if the table exists; if it doesn't, print a message and return
    if not arcpy.Exists(tableName):
        print(f"Table '{tableName}' does not exist in the geodatabase. Creating a new table.")
        arcpy.CreateTable_management(geodatabase, tableName)
        arcpy.AddField_management(tableName, "AFSC", "TEXT")
        arcpy.AddField_management("StandardDistance", "DOUBLE")
    else:
        arcpy.AddField_management(tableName, "StandardDistance", "DOUBLE")
        print(f"Table '{tableName}' does exists in the geodatabase. Adding StandardDistance.")
    # Load shapefile
    base_coordinates = {}
    search = ["Base","Latitude","Longitude"]
    with arcpy.da.SearchCursor(baseTable, search) as cursor:
        for row in cursor:
            base = row[0]
            base_coordinates[row[0]] = [row[1], row[2]]  # Map base name to coordinates
    fields = ["AFSC", "StandardDistance"]
    # Calculate standard distance for each AFSC
    afsc_to_distance = {}
    for afsc, bases in inputDict.items():
        coordinates = []
        for base_name in bases:
            if base_name in base_coordinates:
                coordinates.append(base_coordinates[base_name])
        
        if not coordinates:
            print(f"No valid coordinates found for AFSC {afsc}. Skipping.")
            continue
        
        # Calculate centroid
        centroid_x = sum(coord[0] for coord in coordinates) / len(coordinates)
        centroid_y = sum(coord[1] for coord in coordinates) / len(coordinates)
        
        # Calculate standard distance
        sum_squared_distances = sum(math.sqrt((coord[0] - centroid_x) ** 2 + (coord[1] - centroid_y) ** 2) ** 2
                                    for coord in coordinates)
        standard_distance = math.sqrt(sum_squared_distances / len(coordinates))
        afsc_to_distance[afsc] = standard_distance
    # Update the table with calculated standard distances
    with arcpy.da.UpdateCursor(tableName, fields) as cursor:
        for row in cursor:
            afsc = row[0]
            if afsc in afsc_to_distance:
                row[1] = afsc_to_distance[afsc]
                cursor.updateRow(row)
            else:
                print(f"AFSC {afsc} not found in the input dictionary. No distance calculated.")

    print("Updated the table with standard distances.")
    return tableName

##Updates a shapefile by adding a field that stores the count of AFSCs for each base, using counts derived from a 'baseInfo' table.
def addAFSCCount(baseInfoTable, geodatabase, identifierField, countField='AFSC_Count'):
    
    ##baseInfoTable (str): The name of the table within the geodatabase that contains base identifiers and their respective AFSCs.
    ##geodatabase (str): Path to the geodatabase containing the shapefile and baseInfo table.
    ##shapefile_path (str): The file path to the shapefile within the geodatabase.
    ##identifierField (str): The field in the shapefile and the baseInfo table that matches base identifiers.
    ##countField (str): The name of the new field to create in the shapefile for storing the AFSC count.
    
    # Set the workspace to the specified geodatabase
    arcpy.env.workspace = geodatabase

    # Ensure that baseInfoTable exists 
    if not arcpy.Exists(baseInfoTable):
        raise FileNotFoundError(f"The specified table '{baseInfoTable}' does not exist in the geodatabase.")

    # add a field to base info table for the count
    fieldNames = [field.name for field in arcpy.ListFields(baseInfoTable)]
    if countField not in fieldNames:
        arcpy.AddField_management(baseInfoTable, countField, "LONG")
        print(f"Field '{countField}' base info table.")
    else:
        print(f"Field '{countField}' already exists in base Info Table.")

    # Create a dictionary from the baseInfoTable with base identifier as keys and AFSC count as values
    inputDict = {}
    with arcpy.da.SearchCursor(baseInfoTable, [identifierField, 'AFSC']) as cursor:
        for row in cursor:
            base_identifier = row[0]
            afscs = row[1].split(',') if row[1] else []
            inputDict[base_identifier] = len(set(afscs))  # Count unique AFSCs to avoid duplicates using set
    # Update the count field in the shapefile based on the AFSC counts in the dictionary using update cursor
    with arcpy.da.UpdateCursor(baseInfoTable, ['base', countField]) as cursor:
        for row in cursor:
            base_identifier = row[0]
            if base_identifier in inputDict:
                row[1] = inputDict[base_identifier]  # Set the AFSC count
                cursor.updateRow(row)

    print("Count field updated based on AFSC data from the baseInfo table.")
    
##Creates Point Shapefile from baseInfoTable
def createPointShapeFile(baseTable, geodatabase, shapeFileName, mappingVar):
    arcpy.env.workspace = geodatabase

    # Name of the input table
    tableName = baseTable
    
    # Path to the output feature class
    pointShapeFile = shapeFileName
    if arcpy.Exists(pointShapeFile):
        arcpy.Delete_management(pointShapeFile)
        print(f"Existing shapeFile '{pointShapeFile}' was deleted.")
    # Set the spatial reference using a well-known ID (WGS 1984)
    spatial_reference = arcpy.SpatialReference(4326)  # WGS 1984

    # Create an empty Point feature class
    arcpy.management.CreateFeatureclass(arcpy.env.workspace, pointShapeFile, "POINT", "", "", "", spatial_reference)

    # Add fields to store the latitude, longitude, and other details
    arcpy.management.AddField(pointShapeFile, "Base", "TEXT")
    arcpy.management.AddField(pointShapeFile, "Latitude", "DOUBLE")
    arcpy.management.AddField(pointShapeFile, "Longitude", "DOUBLE")
    if mappingVar == "AFSCCount":
        arcpy.management.AddField(pointShapeFile, "AFSCCount", "DOUBLE")
        insertFields = ["Base", "Latitude", "Longitude", "AFSCCount", "SHAPE@XY"]
        searchFields = ["Base", "Latitude", "Longitude", "AFSCCount"]
    else:
        insertFields = ["Base", "Latitude", "Longitude", "SHAPE@XY"]
        searchFields = ["Base", "Latitude", "Longitude"]
    # Use an InsertCursor to create new points and populate the feature class
    
    with arcpy.da.SearchCursor(tableName, searchFields) as search_cursor, \
         arcpy.da.InsertCursor(pointShapeFile, insertFields) as insert_cursor:
        if len(searchFields) > 3:
            for base_name, lat, lon, count in search_cursor:
                # Ensure that the coordinates are valid
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    point = (lon, lat)  # Create Point object as a tuple
                    row = [base_name, lat, lon, count, point]  # Prepare row data
                    insert_cursor.insertRow(row)
                else:
                    print(f"Skipped invalid coordinates for {base_name}: Latitude {lat}, Longitude {lon}")
        else:
            for base_name, lat, lon in search_cursor:
                # Ensure that the coordinates are valid
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    point = (lon, lat)  # Create Point object as a tuple
                    row = [base_name, lat, lon, count, point]  # Prepare row data
                    insert_cursor.insertRow(row)
                else:
                    print(f"Skipped invalid coordinates for {base_name}: Latitude {lat}, Longitude {lon}")                   
    return pointShapeFile
    
##creates proportonal symbol map based on the number of AFSCs at each base.
def createPropSymbolMap(geodatabase, pointShapeFile, field_name, newMapName):

    ##geodatabase (str): Path to the geodatabase containing the feature class.
    ##feature_class (str): The name of the feature class to visualize.
    ##field_name (str): The field that contains the number of AFSCs.
    ##map_name (str): The name of the map within the project to use or verify existence.

    # Set the workspace and overwrite output
    arcpy.env.workspace = geodatabase
    arcpy.env.overwriteOutput = True

    # Path to the feature class
    fc_path = f"{geodatabase}\\{pointShapeFile}"

    # Ensure the feature class exists
    if not arcpy.Exists(fc_path):
        raise ValueError(f"The feature class {pointShapeFile} does not exist in the specified geodatabase.")

    # Ensure the field exists in the feature class
    fields = [field.name for field in arcpy.ListFields(fc_path)]
    if field_name not in fields:
        raise ValueError(f"The field {field_name} does not exist in the feature class.")

    # Open the current ArcGIS Project
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    # Retrieve or create the map
    maps = aprx.listMaps(newMapName)
    if not maps:
        # Create a new map
        mapx = arcpy.mp.Map()
        aprx.addMap(mapx)
        mapx.name = newMapName
        print(f"Map named '{newMapName}' was created.")
    else:
        mapx = maps[0]

    # Add the feature class to the map as a layer
    layer = mapx.addDataFromPath(fc_path)

    # Check if the layer supports proportional symbol rendering and configure it
    if layer.symbologyType == "PROPORTIONAL_SYMBOLS":
        layer.symbology.updateRenderer('ProportionalSymbolsRenderer')
        layer.symbology.renderer.field = field_name
        layer.symbology.renderer.minSymbolSize = 10
        layer.symbology.renderer.maxSymbolSize = 50
        # Calculate and set min and max data values for scaling symbols
        min_value = min(row[0] for row in arcpy.da.SearchCursor(fc_path, field_name))
        max_value = max(row[0] for row in arcpy.da.SearchCursor(fc_path, field_name))
        layer.symbology.renderer.setMinMaxDataValues(min_value, max_value)
    else:
        raise RuntimeError("Layer does not support proportional symbols.")

    # Save the project changes
    aprx.save()

    print(f"Proportional symbol map '{newMapName}' has been updated and is available in the project.")
    
def inputAFSCTable (baseDict, afscDict, selectedAFSC):
    
    tableName = selectedAFSC
    if arcpy.Exists(tableName):
        arcpy.Delete_management(tableName)
        print(f"Existing table '{tableName}' was deleted.")
    print(f"New table '{tableName}' created in the geodatabase.")
    
    arcpy.CreateTable_management(geodatabase, tableName)
    arcpy.AddField_management(tableName, "Base", "TEXT")
    arcpy.AddField_management(tableName, "Latitude", "DOUBLE")
    arcpy.AddField_management(tableName, "Longitude", "DOUBLE")
    # Start an insert cursor for adding data
    with arcpy.da.InsertCursor(tableName, ["Base","Latitude", "Longitude", "AFSC"]) as cursor:
        if selectedAFSC in afscDict:
            # Prepare the data to be inserted
            bases = afscDict[selectedAFSC]
            for base in bases:
                lat = baseDict[Latitude]
                lon = baseDict[Longitude]
                # Insert the data into the table
                cursor.insertRow([selectedBase, lat, lon])
        else:
            print("Base not found.")
    
    return tableName
    
def tableMaker (baseTable, afscDict, tableName, geodatabase, tableType):
    ##Prints the AFSCs that are at the selected base.
    ##param baseDict: Dictionary with base names as keys and lists of AFSC codes as values.
    ##param afscDict: Dictionary with AFSC codes as keys and their descriptions as values.
    ##param selectedBase: The base selected by the user as a string.
    # Check if the selected base is in the baseDict
    arcpy.env.workspace = geodatabase
    print(tableName)

    if arcpy.Exists(tableName):
        arcpy.Delete_management(tableName)
        print(f"Existing table '{tableName}' was deleted.")
    
    # Create the table
    arcpy.CreateTable_management(geodatabase, tableName)
    print(f"New table '{tableName}' created in the geodatabase.")
    if tableType == "selectedBaseTable":
        arcpy.AddField_management(tableName, "Base", "TEXT")
        arcpy.AddField_management(tableName, "Latitude", "DOUBLE")
        arcpy.AddField_management(tableName, "Longitude", "DOUBLE")
        arcpy.AddField_management(tableName, "AFSC", "TEXT")
        searchFields =  ["Base", "Latitude", "Longitude", "AFSC"]
        insertFields = ["Base", "Latitude", "Longitude", "AFSC"]
        with arcpy.da.SearchCursor(baseTable, searchFields) as search_cursor, \
             arcpy.da.InsertCursor(tableName, insertFields) as insert_cursor:
            for baseName, lat, lon, afsc in search_cursor:
                if baseName == tableName:
                    row = [baseName, lat, lon, afsc]  # Prepare row data
                    insert_cursor.insertRow(row)
                    print(row)
                    
    elif tableType == "selectedAfscTable":
        bases = afscDict[selectedAFSC]
        arcpy.AddField_management(tableName, "Base", "TEXT")
        arcpy.AddField_management(tableName, "Latitude", "DOUBLE")
        arcpy.AddField_management(tableName, "Longitude", "DOUBLE")
        with arcpy.da.SearchCursor(baseTable, searchFields) as search_cursor, \
             arcpy.da.InsertCursor(tableName, insertFields) as insert_cursor:
            for baseName, lat, lon, afsc in search_cursor:
                if baseName in bases:
                    row = [baseName, lat, lon, afsc]  # Prepare row data
                    insert_cursor.insertRow(row)
                    print("base added to selected AFSC table")
                    
    elif tableType == "AFSCTable":
        arcpy.AddField_management(tableName, "AFSC", "TEXT", field_length=100)
        fields = ["AFSC"]
        with arcpy.da.InsertCursor(tableName, fields) as cursor:
            for afsc in afscDict.keys():
                cursor.insertRow([afsc])

    return tableName

def dataMan ():
    folder = input('enter folder for geodatabase to be stored in: ')
    csvPath = input('enter CSV path: ')
    geodatabase = createGeodatabase(folder, "baseAndAFSC")
    baseTable = importCSVIntoGeodatabase(csvPath, geodatabase)
    cleanCSVinGeodatabase(baseTable)
    baseDict = buildBaseDict(baseTable, geodatabase)
    print(baseDict)
    afscDict = buildAFSCDict(baseDict)
    print(afscDict)
    afscTable = AFSCTable(afscDict, geodatabase)
    standardDistance(afscDict, geodatabase, afscTable, baseTable)
    addAFSCCount(baseTable, geodatabase, "Base", countField='AFSCCount')
    
    ##shapeFile = createPointShapeFile(importedCSVPath, geodatabase)
    ##createPropSymbolmap(geodatabase, shapeFile, "AFSCCount", 'outputMap')
    return geodatabase, baseTable, afscTable, afscDict, baseDict

geodatabase, baseTable, afscTable, afscDict, baseDict = dataMan()
##C:/Users/gjgaubatz/OneDrive - University of Iowa/Desktop/FinalProject
##"C:/Users/gjgaubatz/OneDrive - University of Iowa/Desktop/Merged_AFSCs_with_Coordinates.csv"

def overallMapping (geodatabase, baseTable, baseDict):
    shapeFile = createPointShapeFile(baseTable, geodatabase, "OverallBaseLocations", "AFSCCount")
    print ("Overall Mapping Shapefile Created")
    overallPropSymbol = createPropSymbolMap(geodatabase, shapeFile, "AFSCCount", 'OverallPropMap')
    print ("Overall Symbol Mapping Shapefile Created")
    return shapeFile, overallPropSymbol
overallMapping(geodatabase, baseTable, baseDict)

def userBaseMapping (geodatabase, baseTable, afscTable, afscDict, baseDict):
    with arcpy.da.SearchCursor(baseTable, ["Base"]) as search_cursor:
        for base in search_cursor:
            base = base[0]
            filteredBaseName = ''.join([char for char in base if char.isalpha() or char.isspace()])
            print(filteredBaseName)
    selectedBase = input("enter one of the above bases of interest: ")
    selectedBaseTable = tableMaker(baseTable, afscDict, selectedBase, geodatabase, 'selectedBaseTable')
    shapeFile = createPointShapeFile(selectedBaseTable, geodatabase, selectedBase, None)
userBaseMapping (geodatabase, baseTable, afscTable, afscDict, baseDict)

def userAFSCMapping (geodatabase, baseTable, afscTable, afscDict, baseDict):
    AFSCList = []
    with arcpy.da.SearchCursor(afscTable, ["AFSC"]) as search_cursor:
        for AFSC in search_cursor:
            AFSCList = AFSCList.append(AFSC)
    print(AFSCList)
    AFSC = input("enter one of the above AFSCs of interest: ")
    selectedAFSCTable = tableMaker(baseTable, afscDict, selectedBase, geodatabase, 'selectedAFSCTable')
    shapeFile = createPointShapeFile(selectedBaseTable, geodatabase, selectedBase, None)
