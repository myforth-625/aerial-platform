import json
import math

def check_coords_distribution():
    input_file = r"d:\maddpg_mAeBS-main\过程快照\-1\aerialNode.json"
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    lons = []
    lats = []
    
    for node in data:
        lons.append(float(node.get('longitude', 0)))
        lats.append(float(node.get('latitude', 0)))
        
    if not lons:
        print("No nodes found.")
        return

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    
    print(f"Lon Range: {min_lon} - {max_lon} (Diff: {max_lon - min_lon})")
    print(f"Lat Range: {min_lat} - {max_lat} (Diff: {max_lat - min_lat})")
    
    # Calculate approx meters
    ref_lat = 39.962
    SCALE_X = 111320.0 * math.cos(math.radians(ref_lat)) 
    SCALE_Y = 110574.0
    
    dist_x = (max_lon - min_lon) * SCALE_X
    dist_y = (max_lat - min_lat) * SCALE_Y
    
    print(f"Approx Width (m): {dist_x:.2f}")
    print(f"Approx Height (m): {dist_y:.2f}")
    
    # Compare to Scene Width 6000
    SCENE_W = 6000.0
    print(f"Occupancy X: {dist_x / SCENE_W * 100:.2f}% of 6000m")
    print(f"Occupancy Y: {dist_y / SCENE_W * 100:.2f}% of 6000m")

if __name__ == "__main__":
    check_coords_distribution()
