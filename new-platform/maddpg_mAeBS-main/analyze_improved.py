import json
import numpy as np

# Analyze the improved simulation results
def analyze_improved_results():
    # Load improved results
    with open('过程快照/-1/aerialNodeResult_improved.json', 'r', encoding='utf-8') as f:
        final_nodes = json.load(f)
    
    with open('过程快照/-1/70新终端纯still.json', 'r', encoding='utf-8') as f:
        terminals = json.load(f)
    
    # Extract positions
    uav_lons = []
    uav_lats = []
    uav_alts = []
    uav_types = []
    
    term_lons = []
    term_lats = []
    
    for node in final_nodes:
        uav_lons.append(float(node['longitude']))
        uav_lats.append(float(node['latitude']))
        uav_alts.append(float(node['altitude']))
        uav_types.append(node['type'])
    
    for term in terminals:
        term_lons.append(float(term['longitude']))
        term_lats.append(float(term['latitude']))
    
    # Calculate coverage metrics
    print("Number of aerial nodes:", len(uav_lons))
    print("Number of terminals:", len(term_lons))
    print("UAV types:", set(uav_types))
    
    # Calculate average distance from each terminal to nearest UAV
    avg_dist = 0
    min_dists = []
    
    for tl, tt in zip(term_lons, term_lats):
        min_dist = float('inf')
        for ul, ut in zip(uav_lons, uav_lats):
            # Convert to meters
            dist_x = (tl - ul) * 111320.0 * np.cos(np.radians((tt + ut) / 2))
            dist_y = (tt - ut) * 110574.0
            dist = np.sqrt(dist_x**2 + dist_y**2)
            if dist < min_dist:
                min_dist = dist
        min_dists.append(min_dist)
        avg_dist += min_dist
    
    avg_dist /= len(term_lons)
    
    print("Average distance from terminal to nearest UAV:", round(avg_dist, 1), "meters")
    print("Maximum distance from terminal to nearest UAV:", round(max(min_dists), 1), "meters")
    print("Minimum distance from terminal to nearest UAV:", round(min(min_dists), 1), "meters")
    
    # Calculate UAV spread
    uav_lon_range = max(uav_lons) - min(uav_lons)
    uav_lat_range = max(uav_lats) - min(uav_lats)
    uav_lon_range_m = uav_lon_range * 111320.0 * np.cos(np.radians(np.mean(uav_lats)))
    uav_lat_range_m = uav_lat_range * 110574.0
    
    print("UAV spread:", round(uav_lon_range_m, 1), "m x", round(uav_lat_range_m, 1), "m")
    
    # Calculate terminal spread for comparison
    term_lon_range = max(term_lons) - min(term_lons)
    term_lat_range = max(term_lats) - min(term_lats)
    term_lon_range_m = term_lon_range * 111320.0 * np.cos(np.radians(np.mean(term_lats)))
    term_lat_range_m = term_lat_range * 110574.0
    
    print("Terminal spread:", round(term_lon_range_m, 1), "m x", round(term_lat_range_m, 1), "m")
    
    # Analyze altitude distribution
    print("\n=== ALTITUDE DISTRIBUTION ===")
    print("Average altitude:", round(np.mean(uav_alts), 1), "m")
    print("Min altitude:", round(min(uav_alts), 1), "m")
    print("Max altitude:", round(max(uav_alts), 1), "m")
    
    # Check if UAVs are spread out
    if uav_lon_range_m > term_lon_range_m * 0.8 and uav_lat_range_m > term_lat_range_m * 0.8:
        print("\nUAVs are well spread out across the terminal distribution!")
    else:
        print("\nUAVs spread is smaller than terminal spread")
    
    # Check coverage density
    if avg_dist < 200:
        print("Good coverage density - terminals are close to UAVs!")
    elif avg_dist < 300:
        print("Moderate coverage density - some terminals are far from UAVs")
    else:
        print("Poor coverage density - many terminals are too far from UAVs")
    
    # Show final positions
    print("\n=== FINAL UAV POSITIONS ===")
    for i, (lon, lat, alt, type_) in enumerate(zip(uav_lons, uav_lats, uav_alts, uav_types)):
        print("UAV", i+1, "(", type_, "):", "Lon=", round(lon, 6), "Lat=", round(lat, 6), "Alt=", round(alt, 1), "m")

if __name__ == "__main__":
    analyze_improved_results()
