def therm(climate, tempList):
    threshold = 18
    if climate == "Tropical":
        threshold = 30
    elif climate == "Continental":
        threshold = 25

    for temp in tempList:
        if temp <= threshold:
            print ("F")

        else:
            print ("U")
        
    
    
