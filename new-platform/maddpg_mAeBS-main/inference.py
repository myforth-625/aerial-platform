import os
import sys
import json
import argparse
import torch
import numpy as np
import math
from sklearn.cluster import KMeans

# add current directory to sys.path to ensure model classes can be loaded
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import model classes - CRITICAL for torch.load of full objects
try:
    from model import openai_actor, openai_critic
except ImportError:
    # If standard import fails, try relative import assuming we are in the package
    pass


class GeoConverter:
    """
    Simple Geographic Converter to project GPS coordinates to a local Cartesian plane (meters).
    """
    def __init__(self, origin_lon, origin_lat):
        self.origin_lon = origin_lon
        self.origin_lat = origin_lat
        self.R = 6371000.0  # Earth radius in meters

    def gps_to_metric(self, lon, lat):
        """
        Convert (lon, lat) to (x, y) in meters relative to origin.
        """
        x = math.radians(lon - self.origin_lon) * self.R * math.cos(math.radians(self.origin_lat))
        y = math.radians(lat - self.origin_lat) * self.R
        return x, y

    def metric_to_gps(self, x, y):
        """
        Convert (x, y) in meters to (lon, lat).
        """
        lat_rad = y / self.R + math.radians(self.origin_lat)
        lat = math.degrees(lat_rad)
        
        lon_rad = x / (self.R * math.cos(math.radians(self.origin_lat))) + math.radians(self.origin_lon)
        lon = math.degrees(lon_rad)
        
        return lon, lat

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def run_inference(args):
    work_dir = args.work_dir
    
    # Resolve paths
    if work_dir:
        input_nodes_path = os.path.join(work_dir, args.input_nodes)
        input_terminals_path = os.path.join(work_dir, args.input_terminals)
        output_path = os.path.join(work_dir, args.output_nodes)
    else:
        input_nodes_path = args.input_nodes
        input_terminals_path = args.input_terminals
        output_path = args.output_nodes

    model_dir = args.model_path 
    
    # Load inputs
    print(f"Loading inputs...")
    try:
        aerial_nodes = load_json(input_nodes_path)
    except FileNotFoundError:
        print(f"Error: Could not find {input_nodes_path}")
        return

    # Attempt to load terminals (ground users), might be needed for observation
    terminals = []
    try:
        terminals = load_json(input_terminals_path)
    except FileNotFoundError:
        print(f"Warning: Could not find {input_terminals_path}, proceeding without user data.")

    # Prepare data for model
    # Sort nodes by ID to ensure consistent assignment to agents
    # Assuming IDs are strings like "1", "2" or "UAV1", etc. 
    # We need a consistent ordering.
    aerial_nodes.sort(key=lambda x: x.get('id', ''))
    
    # Check if we have enough agents in the model for the nodes provided
    # MADDPG trains a specific number of agents. We need to match them.
    # We will try to load agent 0 to N-1
    
    updated_nodes = []
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # Use dynamic coordinate mapping to adapt to actual terminal distribution
    # while ensuring consistent scaling with training environment
    
    # Find bounding box of all nodes (UAVs and Terminals)
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
    
    print(f"Dynamic Scene Bounds:")
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

    # Normalization Helpers - map GPS coordinates to scaled model space
    def to_model_x(lon):
        dist_x = (lon - ref_lon) * SCALE_X
        # Apply scaling factor that preserves relative positions
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

    # Check if we should use K-means deployment instead of model inference
    if args.deployment_mode == 'kmeans':
        print("\nUsing K-means Clustering Deployment...")
        
        # Separate UAVs and HAPs
        uavs = [n for n in aerial_nodes if n['type'] != 'HAP']
        haps = [n for n in aerial_nodes if n['type'] == 'HAP']
        
        if not uavs:
            print("Warning: No UAVs found in input nodes.")
            updated_nodes = aerial_nodes
        else:
            # Extract terminal coordinates
            terminal_coords = np.array([[float(t['longitude']), float(t['latitude'])] for t in terminals])
            
            if len(terminal_coords) == 0:
                print("Warning: No terminals found, using original UAV positions.")
                updated_nodes = aerial_nodes
            else:
                # Use K-means to find cluster centers
                n_clusters = len(uavs)
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                cluster_labels = kmeans.fit_predict(terminal_coords)
                cluster_centers = kmeans.cluster_centers_
                
                print(f"\nK-means Deployment Results:")
                print(f"- Terminals: {len(terminals)}")
                print(f"- Clusters: {n_clusters}")
                for i, center in enumerate(cluster_centers):
                    cluster_size = np.sum(cluster_labels == i)
                    print(f"  Cluster {i+1}: {cluster_size} terminals at ({center[0]:.6f}, {center[1]:.6f})")
                
                # Assign UAVs to cluster centers based on current positions
                # Calculate distances from each UAV to each cluster center
                uav_positions = []
                for uav in uavs:
                    uav_lon = float(uav['longitude'])
                    uav_lat = float(uav['latitude'])
                    uav_positions.append((uav_lon, uav_lat))
                
                # Create distance matrix: uav_count x cluster_count
                n_uavs = len(uavs)
                n_clusters = len(cluster_centers)
                distance_matrix = np.zeros((n_uavs, n_clusters))
                
                for i in range(n_uavs):
                    for j in range(n_clusters):
                        # Calculate Euclidean distance in GPS coordinates
                        dist = ((uav_positions[i][0] - cluster_centers[j][0])**2 + 
                                (uav_positions[i][1] - cluster_centers[j][1])**2)**0.5
                        distance_matrix[i, j] = dist
                
                # Greedy assignment: assign each UAV to its nearest unassigned cluster
                assigned_clusters = set()
                uav_cluster_assignment = {}
                
                # Sort all possible (uav, cluster) pairs by distance
                all_pairs = []
                for i in range(n_uavs):
                    for j in range(n_clusters):
                        all_pairs.append((distance_matrix[i, j], i, j))
                
                # Sort by distance (ascending)
                all_pairs.sort(key=lambda x: x[0])
                
                # Assign greedily
                for dist, uav_idx, cluster_idx in all_pairs:
                    if uav_idx not in uav_cluster_assignment and cluster_idx not in assigned_clusters:
                        uav_cluster_assignment[uav_idx] = cluster_idx
                        assigned_clusters.add(cluster_idx)
                        print(f"  Assignment: UAV{uav_idx+1} -> Cluster{cluster_idx+1} (distance: {dist:.6f})")
                
                # Deploy UAVs to assigned cluster centers
                manual_uavs = []
                for uav_idx, cluster_idx in uav_cluster_assignment.items():
                    uav = uavs[uav_idx]
                    new_uav = uav.copy()
                    # Place UAV at assigned cluster center
                    new_uav['longitude'] = "{:.22f}".format(cluster_centers[cluster_idx][0])
                    new_uav['latitude'] = "{:.22f}".format(cluster_centers[cluster_idx][1])
                    
                    # Calculate geometric constraints for valid coverage
                    signal_radius = float(new_uav.get('signalRadius', 210.0))
                    max_ground_angle = float(new_uav.get('maxGroundSignalAngle', 60.0))
                    
                    # Calculate maximum valid altitude based on maxGroundSignalAngle
                    # max altitude = signal_radius * sin(max_ground_angle)
                    max_valid_altitude = signal_radius * math.sin(math.radians(max_ground_angle))
                    
                    # Set altitude based on terminal density in cluster, but within valid range
                    cluster_terminal_count = np.sum(cluster_labels == cluster_idx)
                    # Base altitude with density adjustment, then clamp to valid range
                    base_altitude = 150.0 + min(cluster_terminal_count * 2, 100.0)
                    altitude = max(100.0, min(base_altitude, max_valid_altitude))
                    
                    new_uav['altitude'] = "{:.1f}".format(altitude)
                    manual_uavs.append(new_uav)
                    print(f"  UAV{uav_idx+1} deployed at ({cluster_centers[cluster_idx][0]:.6f}, {cluster_centers[cluster_idx][1]:.6f}), Altitude: {altitude:.1f}m (valid max: {max_valid_altitude:.1f}m)")
                
                # Combine HAPs and new UAVs
                updated_nodes = manual_uavs + haps
        
        # Save output and return
        print(f"\nSaving K-means deployment results to {output_path}...")
        save_json(output_path, updated_nodes)
        print("K-means deployment completed successfully.")
        return
    
    # Continue with model inference if K-means not selected
    print("\nUsing Model Inference Deployment...")
    
    for i, node in enumerate(aerial_nodes):
        # Construct model path for this agent
        # Adjust naming convention based on file listing: 'a_c_{i}.pt'
        model_file = os.path.join(model_dir, f'a_c_{i}.pt')
        
        if not os.path.exists(model_file):
            print(f"Warning: No model found for agent index {i} at {model_file}. Skipping inference for this node.")
            updated_nodes.append(node) # Keep original state
            continue
            
        try:
            # Load model
            # map_location='cpu' is safer for inference
            if torch.cuda.is_available():
                 actor = torch.load(model_file, map_location=device, weights_only=False)
            else:
                 actor = torch.load(model_file, map_location=torch.device('cpu'))

            actor.eval()
            
            # Construct Input (Observation)
            # We need to determine what the model expects.
            # Based on environment.py analysis:
            # simple observation might be just [x, y, z] (3 dims)
            # complex observation might be [pos_uav, pos_users...]
            
            # Let's check the first layer weight shape to guess input dimension
            input_dim = 3 # Default minimum (x,y,z)
            if hasattr(actor, 'linear_a1'):
                input_dim = actor.linear_a1.in_features
            
            print(f"Agent {i}: Model expects input dim {input_dim}")
            
            # 1. Get UAV GPS Position
            gps_lon = float(node.get('longitude', 0))
            gps_lat = float(node.get('latitude', 0))
            gps_alt = float(node.get('altitude', 100))
            
            # 2. Convert to Model Coordinates (in range 0-TRAIN_DIM)
            model_x = to_model_x(gps_lon)
            model_y = to_model_y(gps_lat)
            
            # Clamp to bounds just in case
            model_x = max(0, min(TRAIN_DIM, model_x))
            model_y = max(0, min(TRAIN_DIM, model_y))
            
            # Normalize for Neural Network Observation ([0, 1] range) exactly like environment.py
            norm_x = model_x / TRAIN_DIM
            norm_y = model_y / TRAIN_DIM
            norm_z = gps_alt / 300.0
            
            pos_obs = [norm_x, norm_y, norm_z]
            
            obs = []
            obs.extend(pos_obs)
            
            # If model expects more data (users), fill it
            if input_dim > 3:
                # Add user positions (Real -> Model -> Normalized)
                user_obs = []
                for t in terminals:
                    t_lon = float(t.get('longitude', 0))
                    t_lat = float(t.get('latitude', 0))
                    
                    # Direct mapping to model space without scaling
                    t_model_x = to_model_x(t_lon)
                    t_model_y = to_model_y(t_lat)
                    
                    # Normalize based on the actual model space dimensions
                    # This preserves the relative distribution of users
                    user_obs.extend([t_model_x / (TRAIN_DIM), t_model_y / (TRAIN_DIM)])
                
                # If we have users, add them
                if user_obs:
                     # Truncate or pad to match input_dim
                     needed = input_dim - 3
                     current_user_obs_len = len(user_obs)
                     
                     if current_user_obs_len >= needed:
                         obs.extend(user_obs[:needed])
                     else:
                         obs.extend(user_obs)
                         # Pad with zeros if not enough users
                         obs.extend([0.0] * (needed - current_user_obs_len))
                else:
                    # No user data but model needs it -> pad with zeros
                    obs.extend([0.0] * (input_dim - 3))
            
            # Convert to tensor
            obs_tensor = torch.tensor([obs], dtype=torch.float32).to(device)
            
            # Inference with exploration
            with torch.no_grad():
                action_probs = actor(obs_tensor)
                
                # Add small exploration chance (10%) to avoid deterministic behavior
                exploration_rate = 0.1
                if np.random.rand() < exploration_rate:
                    # Random action (0-6, assuming 7 actions)
                    action_idx = np.random.randint(0, 7)
                    print(f"Agent {i} (Exploring): Action Index: {action_idx}")
                else:
                    # Best action from model
                    action_idx = torch.argmax(action_probs, dim=1).item()
                    print(f"Agent {i}: Action Index: {action_idx}")
            
            sensitivity = 200.0 # Increased speed to make actions more noticeable
            
            dx, dy, dz = 0, 0, 0
            if action_idx == 1: dx = -1
            elif action_idx == 2: dx = 1
            elif action_idx == 3: dy = -1
            elif action_idx == 4: dy = 1
            elif action_idx == 5: dz = -1
            elif action_idx == 6: dz = 1
            
            dx *= sensitivity
            dy *= sensitivity
            dz *= sensitivity
            
            # Update position in MODEL SPACE (Meters)
            new_model_x = max(0, min(TRAIN_DIM, model_x + dx))
            new_model_y = max(0, min(TRAIN_DIM, model_y + dy))
            # environment.py limit 100-300 for height
            new_z = max(100.0, min(300.0, gps_alt + dz))
            
            # Convert back to GPS SPACE
            new_lon = to_real_lon(new_model_x)
            new_lat = to_real_lat(new_model_y)
            
            # Construct result node
            res_node = node.copy()
            
            # Update with new GPS coordinates, formatted as high-precision strings to match input
            # Input had ~22 decimal places, e.g., "116.35687983557841611370"
            res_node['longitude'] = "{:.22f}".format(new_lon)
            res_node['latitude'] = "{:.22f}".format(new_lat)
            res_node['altitude'] = "{:.1f}".format(new_z)
            
            # Clean up legacy fields if they exist to avoid confusion
            if 'x' in res_node: del res_node['x']
            if 'y' in res_node: del res_node['y']
            if 'z' in res_node: del res_node['z']
            
            updated_nodes.append(res_node)
            
        except Exception as e:
            print(f"Error executing model for agent {i}: {e}")
            import traceback
            traceback.print_exc()
            updated_nodes.append(node)

    # Save output
    print(f"Saving results to {output_path}...")
    save_json(output_path, updated_nodes)
    print("Inference completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MADDPG Inference for UAV Platform')
    parser.add_argument('--work_dir', type=str, default=None, help='Directory containing snapshot files (Optional)')
    parser.add_argument('--input_nodes', type=str, default='aerialNode.json', help='Input UAV nodes JSON')
    parser.add_argument('--input_terminals', type=str, default='terminalSnapshot.json', help='Input Terminal nodes JSON')
    parser.add_argument('--output_nodes', type=str, default='aerialNodeResult.json', help='Output UAV nodes JSON')
    parser.add_argument('--model_path', type=str, default='models', help='Path to trained models directory')
    # Extra args to match the Java call signature if needed, though we can ignore unused ones
    parser.add_argument('--input_links', type=str, help='Ignored')
    parser.add_argument('--output_links', type=str, help='Ignored')
    parser.add_argument('--steps', type=str, help='Ignored')

    parser.add_argument('--ref_lon', type=float, default=116.355, help='Reference longitude (origin)')
    parser.add_argument('--ref_lat', type=float, default=39.962, help='Reference latitude (origin)')

    # Parse scene dimensions (default to training environment size)
    parser.add_argument('--scene_width', type=float, default=6000.0, help='Width of the actual scenario')
    parser.add_argument('--scene_height', type=float, default=6000.0, help='Height of the actual scenario')
    
    # Add deployment mode option
    parser.add_argument('--deployment_mode', type=str, choices=['model', 'kmeans'], default='kmeans',
                       help='Deployment mode: model (use trained model) or kmeans (use K-means clustering)')

    args = parser.parse_args()
    
    # Store dimensions in global or pass them
    run_inference(args)
