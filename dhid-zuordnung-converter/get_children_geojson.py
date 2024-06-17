import requests
import json
import xmltodict


def get_children_geojson(osm_id):
    url = f"https://api.openstreetmap.org/api/0.6/relation/{osm_id}/full"
    response = requests.get(url)
    data = response.content.decode("utf-8")
    geojson = {"type": "FeatureCollection", "features": []}

    # Parse the XML response and extract node and way children
    # Convert them to GeoJSON features and add them to the feature collection
    # You may need to install the `xmltodict` library for this to work

    xml_data = xmltodict.parse(data)
    print(xml_data)
    for element in xml_data["osm"]["node"]:
        # Add the node as a feature, but only if is not part of any way (<nd ref="{nodeId}"/> does not exist in the whole XML)
        if "<nd ref=\"" + element["@id"] + "\"/>" in data: # Der dreckige Hack funktioniert mal wieder, aber so wie mans eigentlich machen soll nicht :/
            continue
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(element["@lon"]), float(element["@lat"])]
            },
            "properties": {
                "id": element["@id"],
                "type": "node"
            }
        }
        geojson["features"].append(feature)
    # For ways, we need to fetch the way from the osm api to get the coordinates of the nodes that make up the way
    for element in xml_data["osm"]["way"]:
        way_id = element["@id"]
        way_url = f"https://api.openstreetmap.org/api/0.6/way/{way_id}/full"
        way_response = requests.get(way_url)
        way_data = way_response.content.decode("utf-8")
        way_xml_data = xmltodict.parse(way_data)
        nodes = way_xml_data["osm"]["way"]["nd"]
        coordinates = []
        for node in nodes:
            node_id = node["@ref"]
            node_url = f"https://api.openstreetmap.org/api/0.6/node/{node_id}"
            node_response = requests.get(node_url)
            node_data = node_response.content.decode("utf-8")
            node_xml_data = xmltodict.parse(node_data)
            coordinates.append([float(node_xml_data["osm"]["node"]["@lon"]), float(node_xml_data["osm"]["node"]["@lat"])])
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {
                "id": way_id,
                "type": "way"
            }
        }
        geojson["features"].append(feature)
    return geojson

# Example usage
osm_id = 7366007
geojson = get_children_geojson(osm_id)
print(json.dumps(geojson, indent=2))
