import sys, json
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
output = None

def iataV17_2():
    ns = root.tag.split("}")[0] + '}'

    """ Dict of prices with offer id as key. Value is a list with currency in index 0 and price in index 1."""
    prices = {}
    for price in root.find(ns + "ALaCarteOffer").findall(ns + "ALaCarteOfferItem"):
        prices[price.get("OfferItemID")] = [
            price.find(ns + "UnitPriceDetail")[0][0].get("Code"),
            price.find(ns + "UnitPriceDetail")[0][0].text
        ]

    dataList = root.find(ns + "DataLists")
    """ Dict of seat properties. The definition code is the key and a formatted string is the value."""
    seatDefs = {}
    for seatDef in dataList.find(ns + "SeatDefinitionList"):
        """ List of exceptions to normalize data with predefined JSON schema. """
        exceptions = {
            "AISLE_SEAT": "Aisle",
            "RESTRICTED_RECLINE_SEAT": "Limited Recline",
            "WING": "Overwing",
            "EXIT": "Exit Row",
        }
        seatID = seatDef.get("SeatDefinitionID")
        if seatID in exceptions:
            seatDefs[seatID] = exceptions[seatDef[0][0]]
        seatDefs[seatID] = seatDef[0][0].text.replace('_', ' ').title()
        
    output = {
        "rows": {},
        "flightNumber": root
            .find(ns + "DataLists")[0][0]
            .find(ns + "MarketingCarrier")
            .find(ns + "FlightNumber").text
    }
    for chunk in root.findall(ns + "SeatMap"):
        for row in chunk.find(ns + "Cabin").findall(ns + "Row"):
            rowNum = row.find(ns + "Number").text
            rowObj = {"CabinType": None} # Could not find cabin type data on this file schema. 
            for seat in row.findall(ns + "Seat"):
                seatObj = {
                    "available": "false",
                    "features": []
                }
                priceRef = seat.find(ns + "OfferItemRefs")
                if priceRef is not None and priceRef.text in prices:
                    seatObj["price"] = prices[priceRef.text][1]
                    seatObj["currency"] = prices[priceRef.text][0]
                for feature in seat.findall(ns + "SeatDefinitionRef"):
                    if feature.text == "SD4":
                        seatObj["available"] = "true"
                    elif not feature.text == "SD19":
                        seatObj["features"].append(seatDefs[feature.text])
                column = seat.find(ns + "Column").text
                if column == "B" or column == "E":
                    seatObj["features"].append("Center")
                rowObj[rowNum + column] = seatObj
            output["rows"][rowNum] = rowObj
    return output
                
def openTravelV1():
    ns = root[0][0].tag.split("}")[0] + '}'
    output = {
        "flightNumber": root[0][0]
            .find(ns + "SeatMapResponses")[0][0]
            .get("FlightNumber"),
        "rows": {}
    }
    for row in root.iter(ns + "RowInfo"):
        rowObj = {row.get("RowNumber"): {"cabinType": row.get("CabinType")}}
        for seat in row.findall(ns + "SeatInfo"):
            summary = seat[0]
            features = []
            if seat.get("ExitRowInd") == "true":
                features.append("Exit Row")
            for feature in seat.findall(ns + "Features"):
                if feature.text == "Other_":
                    features.append(feature.get("extension"))
                elif feature.text != "BlockedSeat_Permanent":
                    features.append(feature.text)
            seatObj = {
                "available": summary.get("AvailableInd"),
                "features": features
            }
            if seatObj["available"] == "true":
                fee = seat.find(ns + "Service")[0]
                seatObj["price"] = fee.get("Amount")
                seatObj["taxes"] = fee[0].get("Amount")
                seatObj["currency"] = fee.get("CurrencyCode")
            rowObj[row.get("RowNumber")][summary.get("SeatNumber")] = seatObj
        output["rows"].update(rowObj)
    return output

if root.tag == "{http://schemas.xmlsoap.org/soap/envelope/}Envelope" and root[0][0].tag == "{http://www.opentravel.org/OTA/2003/05/common/}OTA_AirSeatMapRS":
    output = openTravelV1()
elif root.tag == "{http://www.iata.org/IATA/EDIST/2017.2}SeatAvailabilityRS" and root.get("Version") == "17.2":
    output = iataV17_2()
else:
    print("\nSorry, the schema for this file is not supported by this parser.\n")

with open(sys.argv[1][:-4] + "_parsed.json", "w") as jsonFile:
    json.dump(output, jsonFile, indent=4)
    jsonFile.close()
