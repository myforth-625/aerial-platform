import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def generate_3d_plot():
    # Load Terminals
    with open('过程快照/-1/terminalSnapshot.json', 'r') as f:
        terminals = json.load(f)
        
    term_lons = [float(t['longitude']) for t in terminals]
    term_lats = [float(t['latitude']) for t in terminals]
    term_alts = [0.0 for _ in terminals] # Ground terminals

    # Load UAVs
    with open('过程快照/-1/aerialNodeResult_fixed.json', 'r') as f:
        uavs = json.load(f)
        
    uav_lons = [float(u['longitude']) for u in uavs]
    uav_lats = [float(u['latitude']) for u in uavs]
    uav_alts = [float(u['altitude']) for u in uavs]
    uav_labels = [u['name'] for u in uavs]

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot Ground Terminals
    ax.scatter(term_lons, term_lats, term_alts, c='blue', marker='o', s=10, alpha=0.5, label='Ground Terminals')

    # Plot UAVs
    ax.scatter(uav_lons, uav_lats, uav_alts, c='red', marker='^', s=100, label='UAVs / HAPs')
    
    # Add text labels for UAVs
    for i in range(len(uav_lons)):
        ax.text(uav_lons[i], uav_lats[i], uav_alts[i] + 5, uav_labels[i], color='red', fontsize=9)

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_zlabel('Altitude (m)')
    ax.set_title('3D UAV Deployment vs Ground Terminals')
    
    # Optional: Format the axes tick labels to not use scientific notation for coordinates
    ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))
    ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))

    plt.legend()
    plt.tight_layout()
    plt.savefig('过程快照/-1/3d_deployment_fixed.png')
    print("Saved 3D plot to 过程快照/-1/3d_deployment_fixed.png")
    # plt.show() # Uncomment if running interactively

if __name__ == '__main__':
    generate_3d_plot()
