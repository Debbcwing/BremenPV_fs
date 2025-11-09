"""This script is to convert OSM to DXF"""
import json
import xml.etree.ElementTree as ET
import subprocess
from pyproj import Transformer              

# Bremen is in UTM Zone 32N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)   # WGS84 to ETRS89 / UTM zone 32N

# Merging multiple osm input files based on the node coordinates
# https://pypi.org/project/osmxtract/

def merge_osm_buildings(osm_files):
    """Extract buildings from multiple OSM files"""
    all_nodes = {}                  # nodes consisting id, timestamp, lat, lon
    buildings = []
    
    for osm_file in osm_files:      # parsing OSM XML data
        tree = ET.parse(osm_file)
        root = tree.getroot()
        
        # Collect lat, lon from nodes
        for node in root.findall('node'):
            all_nodes[node.get('id')] = (float(node.get('lon')), float(node.get('lat')))
        
        # Extract buildings with house numbers
        for way in root.findall('way'):
            tags = way.findall('tag')
            if any(tag.get('k') == 'building' for tag in tags) and any(tag.get('k') == 'addr:housenumber' for tag in tags):
                coords = [all_nodes[nd.get('ref')] for nd in way.findall('nd')
                         if nd.get('ref') in all_nodes]
                if len(coords) >= 3:
                    buildings.append(coords)
    return buildings


def to_dxf(buildings, output_dxf):
    """Convert buildings to DXF via GeoJSON"""
    features = []
    for coords in buildings:
        utm_coords = [transformer.transform(lon, lat) for lon, lat in coords]   # Transform to UTM and create polygons in accurate form
        if utm_coords[0] != utm_coords[-1]:                                     # Close the polygon if not closed
            utm_coords.append(utm_coords[0])
        features.append({"type": "Feature",
                         "geometry": {"type": "Polygon", "coordinates": [utm_coords]},
                         "properties": {}})
    
    # Write GeoJSON with UTM CRS
    geojson = {"type": "FeatureCollection",
               "crs": {"type": "name", "properties": {"name": "EPSG:25832"}},
               "features": features}
    
    temp_json = output_dxf.replace('.dxf', '.geojson')
    with open(temp_json, 'w') as f:
        json.dump(geojson, f)
    
    # Convert to DXF
    subprocess.run(['ogr2ogr', '-f', 'DXF', output_dxf, temp_json], check=True)
    return len(features)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 osm2dxf_noSim.py output.dxf map1.osm map2.osm")
        sys.exit(1)
    
    buildings = merge_osm_buildings(sys.argv[2:])
    count = to_dxf(buildings, sys.argv[1])
    print(f"Converted {count} buildings → {sys.argv[1]}")