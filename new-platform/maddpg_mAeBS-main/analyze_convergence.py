import os
import json
import math
import matplotlib.pyplot as plt

def calc_dist(n1, n2):
    lon1, lat1, alt1 = float(n1['longitude']), float(n1['latitude']), float(n1.get('altitude', 100))
    lon2, lat2, alt2 = float(n2['longitude']), float(n2['latitude']), float(n2.get('altitude', 100))
    
    # Rough convert to meters
    SCALE_X = 111320.0 * math.cos(math.radians(39.96))
    SCALE_Y = 110574.0
    
    dx = (lon2 - lon1) * SCALE_X
    dy = (lat2 - lat1) * SCALE_Y
    dz = alt2 - alt1
    
    return math.sqrt(dx**2 + dy**2 + dz**2)

def main():
    steps = 50
    # dict to store movements per step per agent
    agent_moves = {}
    
    # Init based on step 0 = input
    prev_nodes = {}
    with open(r"过程快照\-1\aerialNode.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        for n in data:
            if n['type'] in ('TestUAV', 'UAV', 'HAP'):
                prev_nodes[n['id']] = n
                agent_moves[n['id']] = []

    # Read each step
    for i in range(steps):
        # We cleaned up temp files in the loop! So we can't do this easily.
        pass
        
    print("Cannot read per-step temp files because they were deleted in multi_step_inference.py.")

if __name__ == '__main__':
    main()
