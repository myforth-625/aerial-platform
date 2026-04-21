import json
import random

def generate_irregular_terminals():
    # Bounds based on previous terminal analysis
    # Lon: 116.3565 to 116.361
    # Lat: 39.9618 to 39.964
    
    terminals = []
    
    # Define cluster centers
    clusters = [
        {"center": (116.3575, 39.9625), "count": 40, "std": 0.0003},
        {"center": (116.3595, 39.9632), "count": 40, "std": 0.0004},
        {"center": (116.3585, 39.9620), "count": 20, "std": 0.0008} # More scattered
    ]
    
    node_id = 1
    for cluster in clusters:
        center_lon, center_lat = cluster["center"]
        std = cluster["std"]
        for _ in range(cluster["count"]):
            lon = center_lon + random.gauss(0, std)
            lat = center_lat + random.gauss(0, std)
            
            # Constrain to general area
            lon = max(116.356, min(116.362, lon))
            lat = max(39.961, min(39.965, lat))
            
            terminals.append({
                "id": str(node_id),
                "name": f"Terminal{node_id:03d}",
                "longitude": f"{lon:.22f}",
                "latitude": f"{lat:.22f}",
                "type": "GroundTerminal"
            })
            node_id += 1
            
    output_path = "过程快照/-1/terminalSnapshot_irregular.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(terminals, f, indent=4)
    print(f"Generated 100 irregular terminals to {output_path}")

if __name__ == "__main__":
    generate_irregular_terminals()
