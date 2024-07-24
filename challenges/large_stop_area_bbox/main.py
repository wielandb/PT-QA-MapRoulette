import sys, math
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "shared"))
import challenge_builder as mrcb
from geopy import distance
import geojson

## Functions specific to this challenge

# Use this function to determine if a task needs to be created for a given element
# use this function for filtering things that overpass cannot filter, maybe by using a function from a different file that you specifically implemented for this task
# if your overpass query already returns all elements that need to be fixed, make this function return True
def needsTask(e):
    # The feature is a geojson feature
    # Extract coordinates from the geometry
    print(e)
    coords = e["geometry"]["coordinates"]
    # Calculate the distance between the upper right conrner and the lower right corner and the distance between the upper right corner and the upper left corner
    # If any of them is greater than 1 km, return True

    # Calculate the distance between the upper right corner and the lower right corner
    upperRight = coords[0]
    lowerRight = coords[1]
    upperLeft = coords[2]
    
    distanceURtoLR = distance.distance(upperRight, lowerRight).km
    distanceURtoUL = distance.distance(upperRight, upperLeft).km

    return distanceURtoLR > 1 or distanceURtoUL > 1

opQuery = """
[out:json][timeout:250];
area(id:3600051477)->.searchArea;
relation["public_transport"="stop_area"](area.searchArea);
foreach {
  >> -> .ancestors;
  make myCustomElement
    ::id=min(id()),
    ::geom=ancestors.gcat(geom());
  out bb;
}
"""

op = mrcb.Overpass()
resultElements = op.queryElementsAsGeoJSON(opQuery)

challenge = mrcb.Challenge()

for element in resultElements:
    print(element)
    if needsTask(element):
        mainFeature = mrcb.GeoFeature.withId(
            osmType="relation", 
            osmId=element["properties"]["@id"],
            geometry=element, 
            properties=element["properties"])
        t = mrcb.Task(
            mainFeature=mainFeature)
        challenge.addTask(t)

challenge.saveToFile("large_stop_area_bbox.json")
