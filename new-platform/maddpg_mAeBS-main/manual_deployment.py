import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Load input files
input_nodes_path = "d:\\maddpg_mAeBS-main\\过程快照\\-1\\aerialNode.json"
input_terminals_path = "d:\\maddpg_mAeBS-main\\过程快照\\-1\\70新终端纯still.json"
output_nodes_path = "d:\\maddpg_mAeBS-main\\过程快照\\-1\\output_aerialNode_manual.json"
output_image_path = "d:\\maddpg_mAeBS-main\\过程快照\\-1\\visualization_manual.png"

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

aerial_nodes = load_json(input_nodes_path)
terminals = load_json(input_terminals_path)

# Separate UAVs and HAPs
uavs = [n for n in aerial_nodes if n['type'] != 'HAP']
haps = [n for n in aerial_nodes if n['type'] == 'HAP']

# Extract terminal coordinates
terminal_coords = np.array([[float(t['longitude']), float(t['latitude'])] for t in terminals])

# Simple clustering: divide terminals into clusters based on UAV count
n_clusters = len(uavs)

# Calculate cluster centers using K-means
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
cluster_labels = kmeans.fit_predict(terminal_coords)
cluster_centers = kmeans.cluster_centers_

# Assign UAVs to cluster centers
manual_uavs = []
for i, uav in enumerate(uavs):
    new_uav = uav.copy()
    # Place UAV at cluster center
    new_uav['longitude'] = "{:.22f}".format(cluster_centers[i][0])
    new_uav['latitude'] = "{:.22f}".format(cluster_centers[i][1])
    # Set altitude based on terminal density in cluster
    cluster_terminal_count = np.sum(cluster_labels == i)
    # Higher density = higher altitude for better coverage
    altitude = 150.0 + min(cluster_terminal_count * 2, 100.0)
    new_uav['altitude'] = "{:.1f}".format(altitude)
    manual_uavs.append(new_uav)

# Combine HAPs and new UAVs
new_nodes = manual_uavs + haps

# Save results
with open(output_nodes_path, 'w') as f:
    json.dump(new_nodes, f, indent=4)
print(f"Saved manual deployment results to {output_nodes_path}")

# Plot results
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')

# Plot terminals
lons = [float(t['longitude']) for t in terminals]
lats = [float(t['latitude']) for t in terminals]
ax.scatter(lons, lats, [0]*len(terminals), c='blue', s=10, alpha=0.3, label='Terminals')

# Plot UAVs
for n in manual_uavs:
    lon, lat, alt = float(n['longitude']), float(n['latitude']), float(n['altitude'])
    ax.scatter(lon, lat, alt, c='red', marker='^', s=150, label=n['name'])
    ax.plot([lon, lon], [lat, lat], [0, alt], color='red', linestyle='--', alpha=0.6)
    ax.text(lon, lat, alt+15, n['name'], color='black', fontsize=10, weight='bold')

# Plot HAPs
for n in haps:
    lon, lat, alt = float(n['longitude']), float(n['latitude']), float(n['altitude'])
    ax.scatter(lon, lat, alt, c='green', marker='*', s=200, label=n['name'])
    ax.plot([lon, lon], [lat, lat], [0, alt], color='green', linestyle='--', alpha=0.6)
    ax.text(lon, lat, alt+15, n['name'], color='black', fontsize=10, weight='bold')

ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_zlabel('Altitude (m)')
plt.title('Manual UAV Deployment Based on Terminal Clusters')
plt.legend()
plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
print(f"Saved visualization to {output_image_path}")
print("\nDeployment Summary:")
print(f"- Number of terminals: {len(terminals)}")
print(f"- Number of UAVs: {len(manual_uavs)}")
print(f"- Number of HAPs: {len(haps)}")
for i, center in enumerate(cluster_centers):
    cluster_size = np.sum(cluster_labels == i)
    print(f"  Cluster {i+1}: {cluster_size} terminals, center at ({center[0]:.6f}, {center[1]:.6f})")
