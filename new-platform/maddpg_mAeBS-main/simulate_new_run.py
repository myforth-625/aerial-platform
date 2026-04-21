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

def simulate():
    input_nodes_path = "过程快照/-1/aerialNode.json"
    input_terminals_path = "过程快照/-1/terminalSnapshot_new.json"
    model_dir = "models"
    steps = 1000
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # Load inputs
    if not os.path.exists(input_nodes_path):
        print(f"Error: {input_nodes_path} not found")
        return
    if not os.path.exists(input_terminals_path):
        print(f"Error: {input_terminals_path} not found")
        return
        
    aerial_nodes = load_json(input_nodes_path)
    terminals = load_json(input_terminals_path)
    aerial_nodes.sort(key=lambda x: x.get('id', ''))

    # 1. Calculate Fixed Bounding Box
    all_lons = [float(n['longitude']) for n in aerial_nodes] + [float(t['longitude']) for t in terminals]
    all_lats = [float(n['latitude']) for n in aerial_nodes] + [float(t['latitude']) for t in terminals]
    
    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)
    
    lon_pad = (max_lon - min_lon) * 0.1 or 0.001
    lat_pad = (max_lat - min_lat) * 0.1 or 0.001
    
    ref_lon = min_lon - lon_pad
    ref_lat = min_lat - lat_pad
    max_bound_lon = max_lon + lon_pad
    max_bound_lat = max_lat + lat_pad
    
    SCALE_X = 111320.0 * math.cos(math.radians(ref_lat)) 
    SCALE_Y = 110574.0
    real_w = (max_bound_lon - ref_lon) * SCALE_X
    real_h = (max_bound_lat - ref_lat) * SCALE_Y
    TRAIN_DIM = 6000.0

    # Helper functions
    def to_model_x(lon): return ((lon - ref_lon) * SCALE_X / real_w) * TRAIN_DIM
    def to_model_y(lat): return ((lat - ref_lat) * SCALE_Y / real_h) * TRAIN_DIM
    def to_real_lon(mx): return ref_lon + (mx / TRAIN_DIM * real_w / SCALE_X)
    def to_real_lat(my): return ref_lat + (my / TRAIN_DIM * real_h / SCALE_Y)

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
    
    print(f"Starting simulation for {steps} steps...")
    
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
            
            model_x = max(0, min(TRAIN_DIM, to_model_x(gps_lon)))
            model_y = max(0, min(TRAIN_DIM, to_model_y(gps_lat)))
            
            obs = [model_x / TRAIN_DIM, model_y / TRAIN_DIM, gps_alt / 300.0]
            
            if input_dim > 3:
                user_obs = []
                for t in terminals:
                    user_obs.extend([to_model_x(float(t['longitude'])) / TRAIN_DIM, 
                                     to_model_y(float(t['latitude'])) / TRAIN_DIM])
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
                
                new_model_x = max(0, min(TRAIN_DIM, model_x + dx * sensitivity))
                new_model_y = max(0, min(TRAIN_DIM, model_y + dy * sensitivity))
                new_z = max(100.0, min(300.0, gps_alt + dz * sensitivity))
                
                new_node = node.copy()
                new_node['longitude'] = "{:.22f}".format(to_real_lon(new_model_x))
                new_node['latitude'] = "{:.22f}".format(to_real_lat(new_model_y))
                new_node['altitude'] = "{:.1f}".format(new_z)
                new_nodes.append(new_node)
        
        current_nodes = new_nodes
        if (step+1) % 200 == 0:
            print(f"Step {step+1}/{steps} completed...")

    # 4. Save and Plot
    output_path = "过程快照/-1/aerialNodeResult_new_1000steps.json"
    with open(output_path, 'w') as f:
        json.dump(current_nodes, f, indent=4)
    print(f"Saved final results to {output_path}")

    # Plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    lons = [float(t['longitude']) for t in terminals]
    lats = [float(t['latitude']) for t in terminals]
    ax.scatter(lons, lats, [0]*len(terminals), c='blue', s=10, alpha=0.3, label='Terminals (New)')
    
    for n in current_nodes:
        lon, lat, alt = float(n['longitude']), float(n['latitude']), float(n['altitude'])
        ax.scatter(lon, lat, alt, c='red', marker='^', s=100)
        ax.plot([lon, lon], [lat, lat], [0, alt], color='red', linestyle='--', alpha=0.4)
        ax.text(lon, lat, alt+10, n['name'], color='black', fontsize=8)
    
    ax.set_xlabel('Lon')
    ax.set_ylabel('Lat')
    ax.set_zlabel('Alt')
    plt.legend()
    plt.savefig('过程快照/-1/visualization_new_1000steps.png')
    print("Saved plot to 过程快照/-1/visualization_new_1000steps.png")

if __name__ == "__main__":
    simulate()
