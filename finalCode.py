import arcpy
import numpy as np
import pandas as pd
import math

##Create Geodatabase for project
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
    ##moves on if table is already created
    if arcpy.Exists("BaseInfo"):
        print(f"File already imported: {csvFile}")
        importedCSVPath = "BaseInfo"
    else:
        #import CSV
        importedCSVPath = arcpy.TableToTable_conversion(csvFile, geodatabase, "BaseInfo")
        print(f"CSV File: {importedCSVPath}, imported into Geodatabase")
    
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

##Updates a table by adding a field that stores the count of AFSCs for each base, using counts derived from a 'baseInfo' table.
def addAFSCCount(baseInfoTable, geodatabase, identifierField, countField='AFSC_Count'):
    
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

##Calculates the standard distance for each AFSC based on base locations extracted from a shapefile and updates an existing table in the geodatabase with these distances.
def standardDistance(inputDict, geodatabase, tableName, baseTable):

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
    ##find coordinates for each base
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

##Creates Point Shapefile from baseInfoTable
def createPointShapeFile(tableName, shapeName, geodatabase, mappingVar):
    arcpy.env.workspace = geodatabase
    # Name of the input table
    pointShapeFile = f"{shapeName}points"
    # Path to the output feature class
    if arcpy.Exists(pointShapeFile):
        arcpy.Delete_management(pointShapeFile)
        print(f"Existing shapeFile '{pointShapeFile}' was deleted.")
    # Set the spatial reference using a well-known ID (WGS 1984)
    spatial_reference = arcpy.SpatialReference(4326)  # WGS 1984

    # Create an empty Point feature class
    arcpy.management.CreateFeatureclass(arcpy.env.workspace, pointShapeFile, "POINT", "", "", "", spatial_reference)

    # Add fields to store the latitude, longitude, and other details
    
    ##Creates shapefile for bases that includes the number of AFSCs at each base
    if mappingVar == "AFSCCount":
        arcpy.management.AddField(pointShapeFile, "AFSCCount", "DOUBLE")
        insertFields = ["Base", "Latitude", "Longitude", "AFSCCount", "SHAPE@XY"]
        searchFields = ["Base", "Latitude", "Longitude", "AFSCCount"]
        arcpy.management.AddField(pointShapeFile, "Base", "TEXT")
        arcpy.management.AddField(pointShapeFile, "Latitude", "DOUBLE")
        arcpy.management.AddField(pointShapeFile, "Longitude", "DOUBLE")
        arcpy.management.AddField(pointShapeFile, "AFSCCount", "DOUBLE")
    
    ##Creates a shapefile for a user selected base that lists AFSCs at each base
    elif mappingVar == "Base":
        insertFields = ["Base", "Latitude", "Longitude", "AFSC", "SHAPE@XY"]
        searchFields = ["Base", "Latitude", "Longitude", "AFSC"]
        arcpy.management.AddField(pointShapeFile, "Base", "TEXT")
        arcpy.management.AddField(pointShapeFile, "Latitude", "DOUBLE")
        arcpy.management.AddField(pointShapeFile, "Longitude", "DOUBLE")
        arcpy.management.AddField(pointShapeFile, "AFSC", "TEXT")
    
    ##Creates a shapefile for a user slected AFSC that includes points for every base for that AFSC
    elif mappingVar == "AFSC":
        insertFields = ["Base", "Latitude", "Longitude", "SHAPE@XY"]
        searchFields = ["Base", "Latitude", "Longitude"]
        arcpy.management.AddField(pointShapeFile, "Base", "TEXT")
        arcpy.management.AddField(pointShapeFile, "Latitude", "DOUBLE")
        arcpy.management.AddField(pointShapeFile, "Longitude", "DOUBLE")
    ## Use an InsertCursor to create new points and populate the feature class
    ## Use a search cursor to parse through designated serach fields to populate shapefile fields
    with arcpy.da.SearchCursor(tableName, searchFields) as search_cursor, \
         arcpy.da.InsertCursor(pointShapeFile, insertFields) as insert_cursor:
        if searchFields == ["Base", "Latitude", "Longitude", "AFSCCount"]:
            for base_name, lat, lon, count in search_cursor:
                # Ensure that the coordinates are valid
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    point = (lon, lat)  # Create Point object as a tuple
                    row = [base_name, lat, lon, count, point]  # Prepare row data
                    insert_cursor.insertRow(row)
                else:
                    print(f"Skipped invalid coordinates for {base_name}: Latitude {lat}, Longitude {lon}")
        elif searchFields == ["Base", "Latitude", "Longitude", "AFSC"]:
            for base_name, lat, lon, AFSC in search_cursor:
                # Ensure that the coordinates are valid
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    point = (lon, lat)  # Create Point object as a tuple
                    row = [base_name, lat, lon, AFSC, point]  # Prepare row data
                    insert_cursor.insertRow(row)
        elif searchFields == ["Base", "Latitude", "Longitude"]:
            for base_name, lat, lon in search_cursor:
                # Ensure that the coordinates are valid
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    point = (lon, lat)  # Create Point object as a tuple
                    row = [base_name, lat, lon, point]  # Prepare row data
                    insert_cursor.insertRow(row)
                else:
                    print(f"Skipped invalid coordinates for {base_name}: Latitude {lat}, Longitude {lon}")     
        print(f"ShapeFile '{pointShapeFile}' was created.")
    return pointShapeFile

## Table creation function for multiple table types
def tableMaker (baseTable, afscDict, tableName, geodatabase, tableType):
    
    arcpy.env.workspace = geodatabase
    ##creates specific name for AFSC table
    if tableType == "AFSCTable" or tableType == "selectedBaseTable":
        tablePath = tableName.strip('\"')  # Remove potential double quotes
        tablePath = ''.join(char for char in tableName if char.isalnum() or char in ['_', '-'])
    ##creates specific name for selected AFSC    
    elif tableType == "selectedAFSCTable":
        tablePath = tableName.strip('\"')  # Remove potential double quotes
        tablePath = ''.join(char for char in tableName if char.isalnum())
        tablePath = "AFSC_" + tablePath

    ##delete shapefile if exists    
    if arcpy.Exists(tablePath):
        arcpy.Delete_management(tablePath)
        print(f"Existing table '{tablePath}' was deleted.")
    
    # Create the table
    arcpy.CreateTable_management(geodatabase, tablePath)
    print(f"New table '{tablePath}' created in the geodatabase.")
    ##Creates a table for a selected base
    if tableType == "selectedBaseTable":
        arcpy.AddField_management(tablePath, "Base", "TEXT")
        arcpy.AddField_management(tablePath, "Latitude", "DOUBLE")
        arcpy.AddField_management(tablePath, "Longitude", "DOUBLE")
        arcpy.AddField_management(tablePath, "AFSC", "TEXT")
        searchFields =  ["Base", "Latitude", "Longitude", "AFSC"]
        insertFields = ["Base", "Latitude", "Longitude", "AFSC"]
        with arcpy.da.SearchCursor(baseTable, searchFields) as search_cursor, \
             arcpy.da.InsertCursor(tablePath, insertFields) as insert_cursor:
            for baseName, lat, lon, afsc in search_cursor:
                if baseName == tableName:
                    row = [baseName, lat, lon, afsc]  # Prepare row data
                    insert_cursor.insertRow(row)
    
    ##creates a table for a selceted AFSC 
    elif tableType == "selectedAFSCTable":
        bases = afscDict[tableName]
        arcpy.AddField_management(tablePath, "Base", "TEXT")
        arcpy.AddField_management(tablePath, "Latitude", "DOUBLE")
        arcpy.AddField_management(tablePath, "Longitude", "DOUBLE")
        searchFields =  ["Base", "Latitude", "Longitude"]
        insertFields = ["Base", "Latitude", "Longitude"]
        with arcpy.da.SearchCursor(baseTable, searchFields) as search_cursor, \
             arcpy.da.InsertCursor(tablePath, insertFields) as insert_cursor:
            for baseName, lat, lon in search_cursor:
                if baseName in bases:
                    row = [baseName, lat, lon]  # Prepare row data
                    insert_cursor.insertRow(row)
    ##Creates an AFSC only table                
    elif tableType == "AFSCTable":
        arcpy.AddField_management(tableName, "AFSC", "TEXT", field_length=100)
        fields = ["AFSC"]
        with arcpy.da.InsertCursor(tableName, fields) as cursor:
            for afsc in afscDict.keys():
                cursor.insertRow([afsc])

    return tablePath 

##main data draw and creation function creates geodatabase, main table, cleans the imported table, builds dicts and does calculations
def dataMan(folder,csvPath, geodatabaseName):
    geodatabase = createGeodatabase(folder, geodatabaseName)
    baseTable = importCSVIntoGeodatabase(csvPath, geodatabase)
    cleanCSVinGeodatabase(baseTable)
    baseDict = buildBaseDict(baseTable, geodatabase)
    afscDict = buildAFSCDict(baseDict)
    afscTable = tableMaker(baseTable, afscDict, "AFSCTable", geodatabase, "AFSCTable")
    standardDistance(afscDict, geodatabase, afscTable, baseTable)
    addAFSCCount(baseTable, geodatabase, "Base", countField='AFSCCount')
    return geodatabase, baseTable, afscTable, afscDict, baseDict

##function that creates an overall shapefile for all bases
def overallMapping (geodatabase, baseTable, baseDict):
    shapeFile = createPointShapeFile(baseTable, "baseInfo", geodatabase, "AFSCCount")
    print ("Overall Mapping Shapefile Created")
    return shapeFile

##Function that allows the user to enter a base that produces a point shapefile for the selected base
def baseMapping (geodatabase, baseTable, afscTable, afscDict, baseDict, selectedBase):
    ##call table maker function to create a table for individual base selected
    selectedBaseTable = tableMaker(baseTable, afscDict, selectedBase, geodatabase, 'selectedBaseTable')
    shapeFile = createPointShapeFile(selectedBaseTable,selectedBaseTable, geodatabase, "Base")
    ##deletes intermediate table created for shapefile creation
    if arcpy.Exists(selectedBaseTable):
        arcpy.Delete_management(selectedBaseTable)
        print(f"Existing table '{selectedBaseTable}' was deleted.")

##Function that allows the user to select an AFSC that produces a point file representing all bases that AFSC is station at
def AFSCMapping (geodatabase, baseTable, afscTable, afscDict, baseDict, selectedAFSC):
    ##call table maker function to make an a tbale for the bases included in the afsc selected
    selectedAFSCTable = tableMaker(baseTable, afscDict, selectedAFSC, geodatabase, 'selectedAFSCTable')
    selectedAFSC = selectedAFSC.strip('\"')  # Remove potential double quotes
    selectedAFSC = ''.join(char for char in selectedAFSC if char.isalnum())
    ##Create shapefile
    shapeFile = createPointShapeFile(selectedAFSCTable,selectedAFSCTable, geodatabase, "AFSC")
    ##deletes intermediate table created for shapefile creation
    if arcpy.Exists(selectedAFSCTable):
        arcpy.Delete_management(selectedAFSCTable)
        print(f"Existing table '{selectedAFSCTable}' was deleted.")

def runForAllMapping():
    ##User input for file folder for the storage of geodatabase and subsiquent files created by program
    folder = input('enter folder for geodatabase to be stored in: ')
    ##User input for file path for csv provided with program
    csvPath = input('enter CSV path: ')
    ##User name for geodatabase, can be an exisiting geodatabase or one created by the program and reused
    geodatabaseName = input('enter geodatabase name: ')
    ##call dataman fuction to get geoprocessing started
    geodatabase, baseTable, afscTable, afscDict, baseDict = dataMan(folder,csvPath, geodatabaseName)
    overallMapping (geodatabase, baseTable, baseDict)

##Run Function for mapping a user entered Base from a list of Bases in data base
def runForUserBaseMapping():
    ##User input for file folder for the storage of geodatabase and subsiquent files created by program
    folder = input('enter folder for geodatabase to be stored in: ')
    ##User input for file path for csv provided with program
    csvPath = input('enter CSV path: ')
    ##User name for geodatabase, can be an exisiting geodatabase or one created by the program and reused
    geodatabaseName = input('enter geodatabase name: ')
    ##call dataman fuction to get geoprocessing started
    geodatabase, baseTable, afscTable, afscDict, baseDict = dataMan(folder,csvPath, geodatabaseName)
    baseNameList = []
    ##Cursor to pull base names for listing to user
    with arcpy.da.SearchCursor(baseTable, ["Base"]) as search_cursor:
        for base in search_cursor:
            base = base[0]
            filteredBaseName = ''.join([char for char in base if char.isalpha() or char.isspace()])
            baseNameList += [filteredBaseName]
            print(filteredBaseName)
    selectedBase = ""
    ##User Input iteration that asks for input until stop statement is entered by user
    while selectedBase != "STOP":
        print ("To stop iteration enter: STOP")
        selectedBase = input("enter one of the above bases of interest: ")
        if selectedBase == "STOP":
            print("User Base Mapping Stopped")
            return
        elif selectedBase in baseNameList:
            baseMapping (geodatabase, baseTable, afscTable, afscDict, baseDict, selectedBase)
        else: 
            print("invalid entry")
            print ("To stop iteration enter: STOP")
            input("enter one of the above bases of interest: ")

##Run Function for mapping a user entered AFSC from a list of AFSCs in data base
def runForUserAFSCMapping():
    ##User input for file folder for the storage of geodatabase and subsiquent files created by program
    folder = input('enter folder for geodatabase to be stored in: ')
    ##User input for file path for csv provided with program
    csvPath = input('enter CSV path: ')
    ##User name for geodatabase, can be an exisiting geodatabase or one created by the program and reused
    geodatabaseName = input('enter geodatabase name: ')
    ##call dataman fuction to get geoprocessing started
    geodatabase, baseTable, afscTable, afscDict, baseDict = dataMan(folder,csvPath, geodatabaseName)
    afscList = []
    ## for loop to pulls afscs from afsc dist for lsiting to the user
    for afsc in afscDict.keys():
        afscList += [afsc]
        print(afsc)
    selectedAFSC = ""
    ##User Input iteration that asks for input until stop statement is entered by user
    while selectedAFSC != "STOP":
        print ("To stop iteration enter: STOP")
        selectedAFSC = input("enter one of the above AFSCs of interest: ")
        if selectedAFSC == "STOP":
            print("User AFSC Mapping Stopped")
            return
        elif selectedAFSC in afscList:
            AFSCMapping (geodatabase, baseTable, afscTable, afscDict, baseDict, selectedAFSC)
        else: 
            print("invalid entry")
            print ("To stop iteration enter: STOP")
            input("enter one of the above AFSCs of interest: ")    

##creates a sperate point file that includes the bases for every AFSC
def allAFSCMapping (geodatabase, baseTable, afscTable, afscDict, baseDict):
    for selectedAFSC in afscDict.keys():
        selectedAFSCTable = tableMaker(baseTable, afscDict, selectedAFSC, geodatabase, 'selectedAFSCTable')
        selectedAFSC = selectedAFSC.strip('\"')  # Remove potential double quotes
        selectedAFSC = ''.join(char for char in selectedAFSC if char.isalnum())
        shapeFile = createPointShapeFile(selectedAFSCTable,selectedAFSCTable, geodatabase, "AFSC")

##Run Funtion to Produce an independent shapefile for every AFSC in original file
def runForAllAFSCMapping():
    ##User input for file folder for the storage of geodatabase and subsiquent files created by program
    folder = input('enter folder for geodatabase to be stored in: ')
    ##User input for file path for csv provided with program
    csvPath = input('enter CSV path: ')
    ##User name for geodatabase, can be an exisiting geodatabase or one created by the program and reused
    geodatabaseName = input('enter geodatabase name: ')
    ##call dataman fuction to get geoprocessing started
    geodatabase, baseTable, afscTable, afscDict, baseDict = dataMan(folder,csvPath, geodatabaseName)
    allAFSCMapping (geodatabase, baseTable, afscTable, afscDict, baseDict)

##call to run the runForAllMapping function
runForAllMapping()

##call to run the runForUserBaseMapping function
runForUserBaseMapping()

##call to run the runForUserAFSCMapping function
runForUserAFSCMapping ()

##call to run the runForAllAFSCMapping function
##Creates 40+ files do not run without good destination
runForAllAFSCMapping()
