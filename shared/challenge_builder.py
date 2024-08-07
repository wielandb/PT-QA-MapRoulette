import os, sys, json
from dataclasses import dataclass, field
from typing import List, Dict
import requests
import geojson
from turfpy.measurement import distance, bbox, centroid


class MainGeoFeature(geojson.Feature):
    def __init__(self, feature=None, geometry=None, properties=None, osmType=None, osmId=None):
        # Initialize from an existing feature if provided
        if feature:
            print(feature)
            geometry = feature['geometry']
            properties = feature.get('properties', {})
        
        # Ensure properties is not None and is a dictionary
        properties = properties or {}

        # Add the custom @id property if osmType and osmId are provided
        if osmType and osmId:
            properties['@id'] = f"{osmType}/{osmId}"
        
        # Initialize the parent geojson.Feature class
        super().__init__(geometry=geometry, properties=properties)

    @classmethod
    def withId(cls, osmType, osmId, Feature):
        Feature['geometry']['properties']['@id'] = f"{osmType}/{osmId}"
        return cls(feature=Feature)

@dataclass
class TagFix:
    def __init__(self, osmType, osmId, tags):
        self.osmType = osmType
        self.osmId = osmId
        self.tagsToDelete = [key for key, value in tags.items() if value is None]
        self.tagsToSet = {key: value for key, value in tags.items() if value is not None}
        if not isinstance(self.tagsToDelete, list):
            raise ValueError("tagsToDelete must be a list, e.g. ['tag1', 'tag2']")
        if not isinstance(self.tagsToSet, dict):
            raise ValueError("tagsToSet must be a dict e.g. {'tag1': 'value1', 'tag2': 'value2'}")
        
    def toGeoJSON(self):
        return {"meta": {"version": 2, "type": 1}, 
                "operations": [
                    {"operationType": "modifyElement", 
                     "data": {
                         "id": f"{self.osmType}/{self.osmId}",  
                         "operations": [
                             {"operation": "setTags", "data": self.tagsToSet},
                             {"operation": "unsetTags", "data": self.tagsToDelete}
                         ]
                     }
                    }
                ]
                }

@dataclass
class Task:
    def __init__(self, mainFeature, additionalFeatures=[], cooperativeWork=None):
        self.mainFeature = mainFeature
        self.additionalFeatures = additionalFeatures
        self.cooperativeWork = cooperativeWork

    def toGeoJSON(self):
        features = [self.mainFeature] + [f.toGeoJSON() for f in self.additionalFeatures]
        return geojson.FeatureCollection(features, **({"cooperativeWork": self.cooperativeWork.toGeoJSON()} if self.cooperativeWork else {}))

@dataclass
class Challenge:
    def __init__(self):
        self.tasks = []

    def addTask(self, task):
        self.tasks.append(task)

    def saveToFile(self, filename):
        with open(filename, 'w', encoding="UTF-8") as f:
            for task in self.tasks:
                f.write('\x1E')
                json.dump(task.toGeoJSON(), f, ensure_ascii=False)
                f.write('\n')

class Overpass:
    def __init__(self, overpass_url="https://overpass-api.de/api/interpreter"):
        self.overpass_url = overpass_url

    def queryElementsRaw(self, overpass_query):
        response = requests.get(self.overpass_url, params={'data': overpass_query})
        if response.status_code != 200:
            raise ValueError("Invalid return data")
        return response.json()["elements"]

    def getFeatureFromOverpassElement(self, element, GeomType=None):
        if GeomType is None:
            if 'lat' in element or 'center' in element:
                GeomType = "Point"
            elif 'bounds' in element:
                GeomType = "Polygon"
            elif 'geometry' in element:
                GeomType = element['geometry']['type']
            else:
                raise ValueError("No handleable coordinates found for element")

        if GeomType == "Point":
            if 'geometry' in element:
                return {"type": "Feature", "geometry": geojson.Point([element['geometry']['lon'], element['geometry']['lat']], properties=element.get('tags', {})) }
            elif 'center' in element:
                return geojson.Point([element['center']['lon'], element['center']['lat']], properties=element.get('tags', {}))
            else:
                return geojson.Point([element['lon'], element['lat']], properties=element.get('tags', {}))
        elif GeomType == "LineString":
            return geojson.LineString([[point['lon'], point['lat']] for point in element['geometry']], properties=element.get('tags', {}))
        elif GeomType == "Polygon":
            if 'bounds' in element:
                # Turn the bounds into a polygon
                return geojson.Polygon([[
                    [element['bounds']['minlon'], element['bounds']['minlat']],
                    [element['bounds']['minlon'], element['bounds']['maxlat']],
                    [element['bounds']['maxlon'], element['bounds']['maxlat']],
                    [element['bounds']['maxlon'], element['bounds']['minlat']],
                    [element['bounds']['minlon'], element['bounds']['minlat']]
                ]], properties=element.get('tags', {}))
            else:
                # Return a polygon that is defined by the list of lists with coordinate pairs in the geometry field
                try:
                    return {"type": "Feature", "geometry": geojson.Polygon([element['geometry']['coordinates']], properties=element.get('tags', {})) }
                except Exception as e:
                    print(f"Error: {e}")
                    return None
        else:
            raise ValueError("Unsupported geometry type")

def makeAdditionalFeature(Feature):
    # remove the @id property and return
    Feature['properties'].pop('@id', None)
