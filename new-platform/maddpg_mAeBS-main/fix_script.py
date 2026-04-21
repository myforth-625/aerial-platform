import os
import math

with open('inference.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    # Use fixed reference point from arguments
    ref_lon = args.ref_lon
    ref_lat = args.ref_lat
    
    print(f"Using Fixed Reference Origin: Lon {ref_lon}, Lat {ref_lat}")
    
    # Model Environment Dimensions
    TRAIN_DIM = 6000.0
    real_w = args.scene_width
    real_h = args.scene_height
    
    # Coordinate transformation constants
    # approximate meters per degree at reference latitude
    SCALE_X = 111320.0 * math.cos(math.radians(ref_lat)) 
    SCALE_Y = 110574.0"""

replacement = """    # Dynamic Coordinate Mapping Calculation
    # Find bounding box of all nodes (UAVs and Terminals) to compute real scene dimensions
    all_lons = []
    all_lats = []
    
    for n in aerial_nodes:
        if 'longitude' in n and 'latitude' in n:
            all_lons.append(float(n['longitude']))
            all_lats.append(float(n['latitude']))
            
    for t in terminals:
        if 'longitude' in t and 'latitude' in t:
            all_lons.append(float(t['longitude']))
            all_lats.append(float(t['latitude']))
            
    if not all_lons or not all_lats:
        print("Error: No coordinates found in input files.")
        return
        
    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)
    
    # Add a small padding (10%) to prevent nodes from being exactly on the 0 or 6000 border
    lon_pad = (max_lon - min_lon) * 0.1
    lat_pad = (max_lat - min_lat) * 0.1
    
    # If the scene is effectively a single point, give it a tiny default boundary
    if lon_pad == 0: lon_pad = 0.001
    if lat_pad == 0: lat_pad = 0.001

    ref_lon = min_lon - lon_pad
    ref_lat = min_lat - lat_pad
    
    max_bound_lon = max_lon + lon_pad
    max_bound_lat = max_lat + lat_pad
    
    print(f"Dynamically calculated Scene Bounds:")
    print(f"  Lon: {ref_lon:.6f} to {max_bound_lon:.6f}")
    print(f"  Lat: {ref_lat:.6f} to {max_bound_lat:.6f}")
    
    # Approximate meters per degree at reference latitude
    SCALE_X = 111320.0 * math.cos(math.radians(ref_lat)) 
    SCALE_Y = 110574.0
    
    real_w = (max_bound_lon - ref_lon) * SCALE_X
    real_h = (max_bound_lat - ref_lat) * SCALE_Y
    
    print(f"  Physical Size: {real_w:.2f}m x {real_h:.2f}m")

    # Model Environment Dimensions
    TRAIN_DIM = 6000.0"""

if target in content:
    content = content.replace(target, replacement)
    
    try:
        with open('inference.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully updated inference.py!")
    except Exception as e:
        print(f"File write error: {e}")
else:
    print("Could not find the target text in inference.py")
