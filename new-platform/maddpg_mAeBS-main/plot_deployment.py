import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def plot_deployment():
    # Load data
    terminals = load_json(r'过程快照\-1\terminalSnapshot.json')
    uavs_original = load_json(r'过程快照\-1\aerialNode.json')
    uavs_fixed = load_json(r'过程快照\-1\aerialNodeResult_fixed_verification.json')

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    # 1. Plot Terminals (Ground Users)
    term_lons = [float(t['longitude']) for t in terminals]
    term_lats = [float(t['latitude']) for t in terminals]
    term_alts = [float(t['altitude']) for t in terminals]
    ax.scatter(term_lons, term_lats, term_alts, c='blue', marker='o', alpha=0.3, label='Ground Users')

    # 2. Plot Original UAV Positions (Light Red, dashed drop lines)
    orig_lons = []
    orig_lats = []
    orig_alts = []
    for node in uavs_original:
        lon = float(node['longitude'])
        lat = float(node['latitude'])
        alt = float(node['altitude'])
        orig_lons.append(lon)
        orig_lats.append(lat)
        orig_alts.append(alt)
        ax.plot([lon, lon], [lat, lat], [0, alt], color='gray', linestyle='--', alpha=0.3)
    ax.scatter(orig_lons, orig_lats, orig_alts, c='salmon', marker='^', s=100, alpha=0.5, label='Original UAV Positions')

    # 3. Plot Fixed Model Inference UAV Positions (Bright Green, solid drop lines)
    fixed_lons = []
    fixed_lats = []
    fixed_alts = []
    for node in uavs_fixed:
        lon = float(node['longitude'])
        lat = float(node['latitude'])
        # Some outputs might not cast altitude changes if fixed in script, using 100 as base or parsing it
        alt = float(node.get('altitude', 100.0))
        fixed_lons.append(lon)
        fixed_lats.append(lat)
        fixed_alts.append(alt)
        name = node.get('name', 'UAV')
        
        ax.plot([lon, lon], [lat, lat], [0, alt], color='green', linestyle='-', alpha=0.6)
        # Add labels to the new positions
        ax.text(lon, lat, alt, f" {name}", color='darkgreen', fontsize=9, fontweight='bold')
        
        # Plot a line connecting old position to new position
        orig_node = next((n for n in uavs_original if n['id'] == node['id']), None)
        if orig_node:
            o_lon = float(orig_node['longitude'])
            o_lat = float(orig_node['latitude'])
            o_alt = float(orig_node['altitude'])
            ax.plot([o_lon, lon], [o_lat, lat], [o_alt, alt], color='black', linestyle=':', alpha=0.8)

    ax.scatter(fixed_lons, fixed_lats, fixed_alts, c='lightgreen', edgecolors='green', marker='^', s=130, alpha=1.0, label='Fixed Model Positions')

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_zlabel('Altitude (m)')
    ax.set_title('UAV Deployment: Original vs Fixed AI Inference')
    ax.legend()
    
    # Set view angle for better 3D perspective
    ax.view_init(elev=20., azim=-45)

    plt.tight_layout()
    save_path = r'过程快照\-1\visualization_fixed_comparison.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {save_path}")

if __name__ == '__main__':
    plot_deployment()
