import os
import sys
import json
import torch
import numpy as np
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import argparse

# add current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from model import openai_actor

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def simulate(input_nodes_path, input_terminals_path, output_nodes_path, output_image_path):
    model_dir = "models"
    steps = 1000
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # Load inputs
    aerial_nodes = load_json(input_nodes_path)
    terminals = load_json(input_terminals_path)
    aerial_nodes.sort(key=lambda x: x.get('id', ''))

    # 1. Use dynamic coordinate mapping to adapt to actual terminal distribution
    # while ensuring consistent scaling with training environment
    
    # Find bounding box of all nodes (initial UAVs and Terminals)
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
        
    # Calculate dynamic bounds with padding
    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)
    
    # Add padding (5% of each dimension)
    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat
    
    # Minimum padding to ensure reasonable area
    min_padding = 0.0005  # ~50 meters at middle latitudes
    lon_pad = max(lon_range * 0.05, min_padding)
    lat_pad = max(lat_range * 0.05, min_padding)
    
    ref_lon = min_lon - lon_pad
    ref_lat = min_lat - lat_pad
    max_bound_lon = max_lon + lon_pad
    max_bound_lat = max_lat + lat_pad
    
    print(f"Dynamic Simulation Bounds:")
    print(f"  Lon: {ref_lon:.6f} to {max_bound_lon:.6f}")
    print(f"  Lat: {ref_lat:.6f} to {max_bound_lat:.6f}")
    
    # Calculate scene dimensions in meters
    SCALE_X = 111320.0 * math.cos(math.radians((ref_lat + max_bound_lat) / 2))
    SCALE_Y = 110574.0
    
    real_w = (max_bound_lon - ref_lon) * SCALE_X
    real_h = (max_bound_lat - ref_lat) * SCALE_Y
    
    print(f"  Physical Size: {real_w:.2f}m x {real_h:.2f}m")
    
    # Model Environment Dimensions (training uses 6000x6000m)
    TRAIN_DIM = 6000.0
    
    # But limit the maximum scaling factor to prevent excessive movement
    max_scene_size = 8000.0  # Maximum real scene size we'll map to 6000m
    scale_factor_x = min(TRAIN_DIM / real_w, max_scene_size / real_w)
    scale_factor_y = min(TRAIN_DIM / real_h, max_scene_size / real_h)

    # Helper functions - map GPS coordinates to scaled model space
    def to_model_x(lon):
        dist_x = (lon - ref_lon) * SCALE_X
        return dist_x * scale_factor_x
    
    def to_model_y(lat):
        dist_y = (lat - ref_lat) * SCALE_Y
        return dist_y * scale_factor_y
        
    def to_real_lon(model_x):
        real_dist = model_x / scale_factor_x
        return ref_lon + (real_dist / SCALE_X)
        
    def to_real_lat(model_y):
        real_dist = model_y / scale_factor_y
        return ref_lat + (real_dist / SCALE_Y)

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
    history = [] # Keep track of positions for visualization if needed
    
    print(f"Starting simulation for {steps} steps...")
    
    for step in range(steps):
        new_nodes = []
        for i, node in enumerate(current_nodes):
            # HAPs are not movable - keep their original position
            if node['type'] == 'HAP':
                new_nodes.append(node)
                continue
                
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
                # Find nearest 10 terminals to reduce dimensionality
                nearest_terminals = []
                current_pos = (gps_lon, gps_lat)
                for t in terminals:
                    t_lon = float(t['longitude'])
                    t_lat = float(t['latitude'])
                    distance = ((t_lon - current_pos[0])**2 + (t_lat - current_pos[1])**2)**0.5
                    nearest_terminals.append((distance, t))
                nearest_terminals.sort(key=lambda x: x[0])
                nearest_terminals = nearest_terminals[:10]  # Keep only 10 nearest terminals
                
                user_obs = []
                for _, t in nearest_terminals:
                    user_obs.extend([to_model_x(float(t['longitude'])) / TRAIN_DIM, 
                                     to_model_y(float(t['latitude'])) / TRAIN_DIM])
                obs.extend(user_obs)
                if len(obs) < input_dim:
                    obs.extend([0.0] * (input_dim - len(obs)))

            obs_tensor = torch.tensor([obs], dtype=torch.float32).to(device)
            with torch.no_grad():
                action_probs = actor(obs_tensor)
                
                # Enhanced exploration with terminal distribution awareness
                exploration_rate = 0.1  # 10% chance to explore, reduced further for more focused deployment
                
                # Calculate nearest terminal to guide movement
                nearest_dist = float('inf')
                for t in terminals:
                    t_lon = float(t['longitude'])
                    t_lat = float(t['latitude'])
                    dist = math.sqrt((t_lon - gps_lon)**2 + (t_lat - gps_lat)**2)
                    if dist < nearest_dist:
                        nearest_dist = dist
                
                # Calculate terminal density in current area
                terminal_density = 0
                current_pos = (gps_lon, gps_lat)
                for t in terminals:
                    t_lon = float(t['longitude'])
                    t_lat = float(t['latitude'])
                    distance = ((t_lon - current_pos[0])**2 + (t_lat - current_pos[1])**2)**0.5
                    if distance < 0.001:  # Within 100 meters
                        terminal_density += 1
                
                # Balanced exploration with model guidance and terminal proximity
                if np.random.rand() < exploration_rate:
                    # Prefer actions that move toward undercovered areas
                    if nearest_dist > 0.001:  # If far from terminals, prioritize horizontal movement toward nearest
                        # Calculate direction to nearest terminal for more targeted exploration
                        nearest_t = None
                        for t in terminals:
                            t_lon = float(t['longitude'])
                            t_lat = float(t['latitude'])
                            distance = ((t_lon - current_pos[0])**2 + (t_lat - current_pos[1])**2)**0.5
                            if distance < nearest_dist:
                                nearest_dist = distance
                                nearest_t = t
                        
                        if nearest_t:
                            t_lon = float(nearest_t['longitude'])
                            t_lat = float(nearest_t['latitude'])
                            if t_lon > current_pos[0] and t_lat > current_pos[1]:
                                action_idx = np.random.choice([2, 4])  # East or North
                            elif t_lon > current_pos[0] and t_lat < current_pos[1]:
                                action_idx = np.random.choice([2, 3])  # East or South
                            elif t_lon < current_pos[0] and t_lat > current_pos[1]:
                                action_idx = np.random.choice([1, 4])  # West or North
                            else:
                                action_idx = np.random.choice([1, 3])  # West or South
                        else:
                            action_idx = np.random.choice([1, 2, 3, 4])  # Horizontal movement
                        print(f"  Exploring: Action {action_idx} (far from terminals)")
                    else:  # If close to terminals, prioritize altitude adjustment
                        action_idx = np.random.choice([5, 6])  # Vertical movement
                        print(f"  Exploring: Action {action_idx} (near terminals)")
                else:
                    # Model's preferred action with terminal density awareness
                    action_idx = torch.argmax(action_probs, dim=1).item()
                    
                    # If terminal density is low, encourage more movement
                    if terminal_density < 3 and action_idx == 0:  # If no movement and low density
                        action_idx = np.random.choice([1, 2, 3, 4])  # Force horizontal movement
                        print(f"  Encouraging movement: Action {action_idx} (low terminal density)")
                
                # Increased sensitivity and anti-stagnation mechanism
                sensitivity = 30.0  # Increased sensitivity for more significant movement
                dx, dy, dz = 0, 0, 0
                
                # Add anti-stagnation: if terminal density is low, increase movement step
                if terminal_density < 2:
                    sensitivity = 40.0  # Move more when in low-density areas
                
                if action_idx == 1: dx = -1
                elif action_idx == 2: dx = 1
                elif action_idx == 3: dy = -1
                elif action_idx == 4: dy = 1
                elif action_idx == 5: dz = -1
                elif action_idx == 6: dz = 1
                
                # Ensure movement happens even with small actions
                if action_idx == 0 and terminal_density < 3:  # No movement but low density
                    # Force small random movement
                    dx = np.random.choice([-1, 1]) * 0.5
                    dy = np.random.choice([-1, 1]) * 0.5
                    print(f"  Anti-stagnation: Forced movement ({dx}, {dy})")
                
                new_model_x = max(0, min(TRAIN_DIM, model_x + dx * sensitivity))
                new_model_y = max(0, min(TRAIN_DIM, model_y + dy * sensitivity))
                new_z = max(100.0, min(300.0, gps_alt + dz * sensitivity))
                
                new_node = node.copy()
                new_node['longitude'] = "{:.22f}".format(to_real_lon(new_model_x))
                new_node['latitude'] = "{:.22f}".format(to_real_lat(new_model_y))
                new_node['altitude'] = "{:.1f}".format(new_z)
                new_nodes.append(new_node)
        
        current_nodes = new_nodes
        if (step + 1) % 100 == 0:
            print(f"Step {step+1}/{steps} completed...")

    # 4. Save and Plot
    with open(output_nodes_path, 'w') as f:
        json.dump(current_nodes, f, indent=4)
    print(f"Saved final results to {output_nodes_path}")

    # Plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Improved plotting logic for stems
    lons = [float(t['longitude']) for t in terminals]
    lats = [float(t['latitude']) for t in terminals]
    ax.scatter(lons, lats, [0]*len(terminals), c='blue', s=10, alpha=0.3, label='Terminals (Irregular)')
    
    for n in current_nodes:
        lon, lat, alt = float(n['longitude']), float(n['latitude']), float(n['altitude'])
        ax.scatter(lon, lat, alt, c='red', marker='^', s=100)
        ax.plot([lon, lon], [lat, lat], [0, alt], color='red', linestyle='--', alpha=0.4)
        ax.text(lon, lat, alt+10, n['name'], color='black', fontsize=8)
    
    ax.set_xlabel('Lon')
    ax.set_ylabel('Lat')
    ax.set_zlabel('Alt')
    plt.legend()
    plt.savefig(output_image_path)
    print(f"Saved plot to {output_image_path}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Simulate UAV deployment for 1000 steps')
    parser.add_argument('--input_nodes', type=str, required=True, help='Path to input aerial nodes JSON')
    parser.add_argument('--input_terminals', type=str, required=True, help='Path to input terminals JSON')
    parser.add_argument('--output_nodes', type=str, required=True, help='Path to output nodes JSON')
    parser.add_argument('--output_image', type=str, required=True, help='Path to output visualization image')
    
    args = parser.parse_args()
    
    # Run the simulation
    simulate(args.input_nodes, args.input_terminals, args.output_nodes, args.output_image)
