import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import argparse
import os
import sys

def load_json(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found {file_path}")
        sys.exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def plot_scene_3d(uav_file, terminal_file, output_file=None):
    uavs = load_json(uav_file)
    terminals = load_json(terminal_file)
    
    # Extract UAV Data
    uav_lons = []
    uav_lats = []
    uav_alts = []
    uav_ids = []
    
    for u in uavs:
        uav_lons.append(float(u.get('longitude', 0)))
        uav_lats.append(float(u.get('latitude', 0)))
        uav_alts.append(float(u.get('altitude', 0)))
        uav_ids.append(u.get('name', u.get('id')))

    # Extract Terminal Data
    term_lons = []
    term_lats = []
    term_alts = []
    
    for t in terminals:
        term_lons.append(float(t.get('longitude', 0)))
        term_lats.append(float(t.get('latitude', 0)))
        term_alts.append(float(t.get('altitude', 0)))

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot Terminals (Ground Users)
    # Usually z=0, color blue, lower opacity
    ax.scatter(term_lons, term_lats, term_alts, c='blue', alpha=0.3, s=20, label='Ground Users')
    
    # Plot UAVs (Aerial Nodes)
    # Color red, different marker
    ax.scatter(uav_lons, uav_lats, uav_alts, c='red', marker='^', s=100, label='UAVs/HAPs')
    
    # Connect UAVs to ground projection lines for depth perception
    for u_lon, u_lat, u_alt in zip(uav_lons, uav_lats, uav_alts):
        ax.plot([u_lon, u_lon], [u_lat, u_lat], [0, u_alt], 'k--', alpha=0.2)

    # Annotate UAV IDs
    for i, txt in enumerate(uav_ids):
        ax.text(uav_lons[i], uav_lats[i], uav_alts[i], txt, size=9, zorder=1, color='black') 
        
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_zlabel('Altitude (m)')
    ax.set_title('3D UAV and Terminal Position View')
    
    ax.legend()
    
    # Adjust view angle for better perspective
    ax.view_init(elev=20., azim=-45)
    
    if output_file:
        plt.savefig(output_file)
        print(f"3D Plot saved to {output_file}")
    else:
        plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Visualize Scene in 3D')
    parser.add_argument('--uav_file', type=str, required=True, help='Path to aerialNodeResult.json')
    parser.add_argument('--terminal_file', type=str, required=True, help='Path to terminalSnapshot.json')
    parser.add_argument('--output', type=str, default='scene_visualization_3d.png', help='Output image file path')
    
    args = parser.parse_args()
    
    plot_scene_3d(args.uav_file, args.terminal_file, args.output)
