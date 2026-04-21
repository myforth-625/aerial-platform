import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def plot_final_deployment():
    terminals = load_json(r'过程快照\-1\terminalSnapshot.json')
    uavs_original = load_json(r'过程快照\-1\aerialNode.json')
    uavs_final = load_json(r'过程快照\-1\aerialNodeResult_50steps.json')

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    # 1. Plot Terminals (Ground Users)
    term_lons = [float(t['longitude']) for t in terminals]
    term_lats = [float(t['latitude']) for t in terminals]
    term_alts = [float(t.get('altitude', 0)) for t in terminals]
    ax.scatter(term_lons, term_lats, term_alts, c='blue', marker='o', alpha=0.3, label='Ground Users')

    # 2. Plot Original UAV Positions (Light Red)
    orig_lons, orig_lats, orig_alts = [], [], []
    for node in uavs_original:
        if node['type'] in ('TestUAV', 'UAV', 'HAP'):
            lon, lat, alt = float(node['longitude']), float(node['latitude']), float(node.get('altitude', 100))
            orig_lons.append(lon)
            orig_lats.append(lat)
            orig_alts.append(alt)
            # drop line
            ax.plot([lon, lon], [lat, lat], [0, alt], color='gray', linestyle='--', alpha=0.3)
    ax.scatter(orig_lons, orig_lats, orig_alts, c='salmon', marker='x', s=100, alpha=0.6, label='Initial Spawn Positions')

    # 3. Plot Final Deployed UAV Positions (Bright Green)
    final_lons, final_lats, final_alts = [], [], []
    for node in uavs_final:
        if node['type'] in ('TestUAV', 'UAV', 'HAP'):
            lon, lat, alt = float(node['longitude']), float(node['latitude']), float(node.get('altitude', 100))
            final_lons.append(lon)
            final_lats.append(lat)
            final_alts.append(alt)
            name = node.get('name', f"ID:{node['id']}")
            
            # solid drop line
            ax.plot([lon, lon], [lat, lat], [0, alt], color='green', linestyle='-', alpha=0.6)
            ax.text(lon, lat, alt, f"  {name} (Final)", color='darkgreen', fontsize=10, fontweight='bold')
            
            # Draw movement vector from original to final
            orig_node = next((n for n in uavs_original if n['id'] == node['id']), None)
            if orig_node:
                o_lon, o_lat, o_alt = float(orig_node['longitude']), float(orig_node['latitude']), float(orig_node.get('altitude', 100))
                ax.plot([o_lon, lon], [o_lat, lat], [o_alt, alt], color='black', linestyle=':', alpha=0.8)

    ax.scatter(final_lons, final_lats, final_alts, c='limegreen', edgecolors='green', marker='^', s=200, alpha=1.0, label='Optimal Deployed Positions (Step 50)')

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_zlabel('Altitude (m)')
    ax.set_title('UAV Deployment: 50-Step AI Convergence Result')
    ax.legend()
    
    ax.view_init(elev=30., azim=-55)

    plt.tight_layout()
    save_path = r'过程快照\-1\visualization_final_50steps.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Final deployment visualization saved to {save_path}")

if __name__ == '__main__':
    plot_final_deployment()
