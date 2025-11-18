"""This script is to convert OSM to DXF"""
import json
import xml.etree.ElementTree as ET
from pyproj import Transformer              

# Bremen is in UTM Zone 32N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)   # WGS84 to ETRS89 / UTM zone 32N


# Merge multiple osm input files based on the node coordinates
# to-try (direct osm to geojson): https://pypi.org/project/osmxtract/

def merge_osm_buildings(osm_files):
    """Extract buildings from multiple OSM files"""
    all_nodes = {}                  # nodes consist of id, timestamp, lat, lon
    all_buildings = []
    
    for osm_file in osm_files:      # parse OSM XML data
        tree = ET.parse(osm_file)
        root = tree.getroot()
        
        # Collect lat, lon from nodes
        for node in root.findall('node'):
            all_nodes[node.get('id')] = (float(node.get('lon')), float(node.get('lat')))
        
        # Extract buildings with house numbers
        for way in root.findall('way'):
            # an initialization for the loop
            is_building = False
            has_housenumber = False

            for tag in way.findall('tag'):
                if tag.get('k') == 'building':
                    is_building = True
                if tag.get('k') == 'addr:housenumber':
                    has_housenumber = True
            
            if is_building and has_housenumber:
                coords = [all_nodes[nd.get('ref')] for nd in way.findall('nd')]
                if coords and coords[0] != coords[-1]:
                        print(f"Warning: Building {way.get('id')} not closed found. They will be closed.")
                        coords.append(coords[0])                # close it if it is not closed
                all_buildings.append(coords)
    return all_buildings


def write_geojson(all_buildings, output_json):
    features = []
    for coords in all_buildings:
        utm_coords = [transformer.transform(lon, lat) for lon, lat in coords]   # Transform to UTM and create polygons in accurate form
        features.append({"type": "Feature",
                         "geometry": {"type": "Polygon", "coordinates": [utm_coords]},
                         "properties": {}})  
    # Write GeoJSON with transformed UTM CRS
    geojson = {"type": "FeatureCollection",
               "crs": {"type": "name", "properties": {"name": "EPSG:25832"}},
               "features": features}
    with open(output_json, 'w') as f:
        json.dump(geojson, f)
    print(f"Created {output_json} - now run: ogr2ogr -f DXF output.dxf {output_json}")
    
    return len(features)
    

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 osm2dxf.py bremen.geojson map1.osm map2.osm")
        sys.exit(1)
    
    all_buildings = merge_osm_buildings(sys.argv[2:])
    count = write_geojson(all_buildings, sys.argv[1])
    print(f"Converted {count} buildings → {sys.argv[1]}")
    print(f"Run: ogr2ogr -f DXF output.dxf {sys.argv[1]}")
