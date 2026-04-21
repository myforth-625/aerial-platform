import json
import math

def analyze_terminals():
    with open('过程快照/-1/terminalSnapshot.json', 'r') as f:
        terminals = json.load(f)

    lons = [float(t['longitude']) for t in terminals]
    lats = [float(t['latitude']) for t in terminals]

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    ref_lon = min_lon
    ref_lat = min_lat
    
    print(f"Terminals count: {len(terminals)}")
    print(f"Lon range: {min_lon} to {max_lon} (diff: {max_lon - min_lon})")
    print(f"Lat range: {min_lat} to {max_lat} (diff: {max_lat - min_lat})")

    SCALE_X = 111320.0 * math.cos(math.radians(ref_lat))
    SCALE_Y = 110574.0

    width_meters = (max_lon - min_lon) * SCALE_X
    height_meters = (max_lat - min_lat) * SCALE_Y

    print(f"Scene Width in meters: {width_meters}")
    print(f"Scene Height in meters: {height_meters}")
    print(f"Suggested Ref Lon: {ref_lon}")
    print(f"Suggested Ref Lat: {ref_lat}")

if __name__ == '__main__':
    analyze_terminals()
