import os
import sys
import json
import torch
import numpy as np
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# add current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from model import openai_actor

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def simulate_fixed(input_terminals_path, output_suffix):
    input_nodes_path = "过程快照/-1/aerialNode.json"
    model_dir = "models"
    steps = 1000
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # Load inputs
    aerial_nodes = load_json(input_nodes_path)
    terminals = load_json(input_terminals_path)
    aerial_nodes.sort(key=lambda x: x.get('id', ''))

    # FIXED Parameters matching training environment
    TRAIN_DIM = 6000.0
    # Use a fixed center for all scenarios to observe real movement
    # Training area is 6000x6000m. Let's map its center to a fixed GPS.
    # From previous analyses:
    # Lon: 116.356 to 116.362 (~0.006 deg, ~600m)
    # Lat: 39.961 to 39.965 (~0.004 deg, ~400m)
    # The entire user cluster is actually MUCH smaller than the 6000m training area.
    
    # FIXED Origin
    ref_lon = 116.355
    ref_lat = 39.960
    
    SCALE_X = 111320.0 * math.cos(math.radians(ref_lat)) 
    SCALE_Y = 110574.0
    
    # Fixed scale (6000m)
    AREA_SIZE = 6000.0

    # Helper functions
    def to_model_x(lon): return ((lon - ref_lon) * SCALE_X) # Meters from origin
    def to_model_y(lat): return ((lat - ref_lat) * SCALE_Y) # Meters from origin
    def to_real_lon(mx): return ref_lon + (mx / SCALE_X)
    def to_real_lat(my): return ref_lat + (my / SCALE_Y)

    # 2. Load Models
    actors = []
    for i in range(len(aerial_nodes)):
        model_file = os.path.join(model_dir, f'a_c_{i}.pt')
        if os.path.exists(model_file):
            actor = torch.load(model_file, map_location=device, weights_only=False)
            actor.eval()
            actors.append(actor)
        else:
            actors.append(None)

    # 3. Simulation Loop
    current_nodes = aerial_nodes.copy()
    
    print(f"Starting Fixed Simulation for {output_suffix}...")
    
    for step in range(steps):
        new_nodes = []
        for i, node in enumerate(current_nodes):
            actor = actors[i]
            if actor is None:
                new_nodes.append(node)
                continue
                
            input_dim = actor.linear_a1.in_features
            gps_lon = float(node['longitude'])
            gps_lat = float(node['latitude'])
            gps_alt = float(node['altitude'])
            
            # Distance from fixed origin in meters
            mx = to_model_x(gps_lon)
            my = to_model_y(gps_lat)
            
            # Normalize for Neural Network (divide by fixed AREA_SIZE=6000)
            obs = [mx / AREA_SIZE, my / AREA_SIZE, gps_alt / 300.0]
            
            if input_dim > 3:
                user_obs = []
                for t in terminals:
                    user_obs.extend([to_model_x(float(t['longitude'])) / AREA_SIZE, 
                                     to_model_y(float(t['latitude'])) / AREA_SIZE])
                obs.extend(user_obs[:input_dim-3])
                if len(obs) < input_dim:
                    obs.extend([0.0] * (input_dim - len(obs)))

            obs_tensor = torch.tensor([obs], dtype=torch.float32).to(device)
            with torch.no_grad():
                action_probs = actor(obs_tensor)
                action_idx = torch.argmax(action_probs, dim=1).item()
                
                sensitivity = 100.0
                dx, dy, dz = 0, 0, 0
                if action_idx == 1: dx = -1
                elif action_idx == 2: dx = 1
                elif action_idx == 3: dy = -1
                elif action_idx == 4: dy = 1
                elif action_idx == 5: dz = -1
                elif action_idx == 6: dz = 1
                
                new_mx = max(0, min(AREA_SIZE, mx + dx * sensitivity))
                new_my = max(0, min(AREA_SIZE, my + dy * sensitivity))
                new_z = max(100.0, min(300.0, gps_alt + dz * sensitivity))
                
                new_node = node.copy()
                new_node['longitude'] = "{:.22f}".format(to_real_lon(new_mx))
                new_node['latitude'] = "{:.22f}".format(to_real_lat(new_my))
                new_node['altitude'] = "{:.1f}".format(new_z)
                new_nodes.append(new_node)
        
        current_nodes = new_nodes

    # Plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    lons_t = [float(t['longitude']) for t in terminals]
    lats_t = [float(t['latitude']) for t in terminals]
    ax.scatter(lons_t, lats_t, [0]*len(terminals), c='blue', s=10, alpha=0.3)
    for n in current_nodes:
        lon, lat, alt = float(n['longitude']), float(n['latitude']), float(n['altitude'])
        ax.scatter(lon, lat, alt, c='red', marker='^', s=100)
    
    ax.set_title(f"Fixed Normalization: {output_suffix}")
    plt.savefig(f'过程快照/-1/visualization_fixed_norm_{output_suffix}.png')
    plt.close()
    print(f"Saved plot to 过程快照/-1/visualization_fixed_norm_{output_suffix}.png")

if __name__ == "__main__":
    # Run for both scenarios to see the difference clearly
    simulate_fixed("过程快照/-1/terminalSnapshot_irregular.json", "irregular")
    simulate_fixed("过程快照/-1/terminalSnapshot_new.json", "new")
