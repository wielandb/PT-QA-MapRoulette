import os, sys, json
from dataclasses import dataclass, field
from typing import List, Dict
import requests
import geojson
from turfpy.measurement import distance, bbox, centroid

@dataclass
class GeoFeature(geojson.Feature):
    geometry: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)
    id: str = None

    def __init__(self, geometry, properties, id=None):
        super().__init__(geometry=geometry, properties=properties, id=id)

    @classmethod
    def withId(cls, osmType, osmId, geometry, properties):
        properties["@id"] = f"{osmType}/{osmId}"
        return cls(geometry=geometry, properties=properties)

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

    def queryElementsAsGeoJSON(self, overpass_query):
        elements = self.queryElementsRaw(overpass_query)
        geojson_features = []
        
        for element in elements:
            if element['type'] == 'node':
                feature = geojson.Feature(
                    geometry=geojson.Point((element['lon'], element['lat'])),
                    properties={key: value for key, value in element.items() if key not in ['type', 'lat', 'lon']}
                )
            elif element['type'] == 'way':
                coordinates = [(node['lon'], node['lat']) for node in element['geometry']]
                feature = geojson.Feature(
                    geometry=geojson.LineString(coordinates),
                    properties={key: value for key, value in element.items() if key not in ['type', 'geometry']}
                )
            elif element['type'] == 'relation':
                members = element.get('members', [])
                outer_polygons = []
                inner_polygons = []
                
                for member in members:
                    if member['type'] == 'way':
                        member_coords = [(node['lon'], node['lat']) for node in member['geometry']]
                        if member['role'] == 'outer':
                            outer_polygons.append(member_coords)
                        elif member['role'] == 'inner':
                            inner_polygons.append(member_coords)
                
                if outer_polygons:
                    geometry = geojson.Polygon(outer_polygons)
                    if inner_polygons:
                        geometry = geojson.MultiPolygon([outer_polygons + inner_polygons])
                    
                    feature = geojson.Feature(
                        geometry=geometry,
                        properties={key: value for key, value in element.items() if key not in ['type', 'members']}
                    )
                else:
                    continue  # Skip relations without outer polygons
            elif 'geometry' in element:
                geojson_type = element['geometry']['type']
                coordinates = element['geometry']['coordinates']
                
                if geojson_type == 'Point':
                    geometry = geojson.Point(coordinates)
                elif geojson_type == 'LineString':
                    geometry = geojson.LineString(coordinates)
                elif geojson_type == 'Polygon':
                    geometry = geojson.Polygon(coordinates)
                else:
                    continue  # Skip unsupported geometry types
                
                feature = geojson.Feature(
                    geometry=geometry,
                    properties={"@"+str(key): value for key, value in element.items() if key != 'geometry'}
                )
            else:
                continue  # Skip unknown element types
            
            geojson_features.append(feature)
        
        return geojson_features
