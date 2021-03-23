import sys, json
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
print(root.tag)
output = None

def iataV17_2():
    namespace = root.tag.split("}")[0] + '}'
    prices = {}
    for price in root.iter(namespace + "ALaCarteOfferItem"):
        prices[price.get("OfferItemID")] = [price[1][0][0].get("Code"),price[1][0][0].text]

def openTravelV1():
    namespace = root[0][0].tag.split("}")[0] + '}'
    output = {"flightNumber": root[0][0][1][0][0].get("FlightNumber"), "rows": {}}
    for row in root.iter(namespace + "RowInfo"):
        rowObj = {row.get("RowNumber"): {"cabinType": row.get("CabinType")}}
        for seat in row.findall(namespace + "SeatInfo"):
            summary = seat[0]
            features = []
            if seat.get("ExitRowInd") == "true":
                features.append("exitRow")
            for feature in seat.findall(namespace + "Features"):
                if feature.text == "Other_":
                    features.append(feature.get("extension"))
                elif feature.text != "BlockedSeat_Permanent":
                    features.append(feature.text)
            seatObj = {
                "available": summary.get("AvailableInd"),
                "features": features
            }
            if seatObj["available"] == "true":
                fee = seat.find(namespace + "Service")[0]
                seatObj["price"] = fee.get("Amount")
                seatObj["taxes"] = fee[0].get("Amount")
                seatObj["currency"] = fee.get("CurrencyCode")
            rowObj[row.get("RowNumber")][summary.get("SeatNumber")] = seatObj
        output["rows"].update(rowObj)
    return output

if root.tag == "{http://schemas.xmlsoap.org/soap/encoding/}Envelope" and root[0][0][0].tag == "{http://www.opentravel.org/OTA/2003/05/common/}OTA_AirSeatMapRS":
    output = openTravelV1()
elif root.tag == "{http://www.iata.org/IATA/EDIST/2017.2}SeatAvailabilityRS" and root.get("Version") == "17.2":
    output = iataV17_2()
else:
    print("\nSorry, the schema for this file is not supported by this parser.\n")

with open(sys.argv[1][:-4] + "_parsed.json", "w") as jsonFile:
    json.dump(output, jsonFile, indent=4)
    jsonFile.close()
