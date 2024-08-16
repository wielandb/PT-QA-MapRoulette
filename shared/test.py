import challenge_builder as mrcb
op = mrcb.Overpass()

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

resultElements = op.queryElementsRaw(opQuery)

fe = op.getFeatureFromOverpassElement(resultElements[3])

fe2 = mrcb.MainGeoFeature().withId("relation", 1234565, fe)

print(fe2)