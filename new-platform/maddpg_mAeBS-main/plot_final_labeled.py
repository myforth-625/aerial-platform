import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def final_plot():
    terminals = json.load(open('过程快照/-1/terminalSnapshot.json'))
    nodes = json.load(open('过程快照/-1/aerialNodeResult_1000steps.json'))
    orig = json.load(open('过程快照/-1/aerialNode.json'))
    orig_map = {n['id']: n for n in orig}

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    # Terminals
    ax.scatter([float(t['longitude']) for t in terminals], 
               [float(t['latitude']) for t in terminals], 
               [0]*len(terminals), c='blue', s=5, alpha=0.2, label='Terminals')

    # Initial positions (gray)
    ax.scatter([float(n['longitude']) for n in orig], 
               [float(n['latitude']) for n in orig], 
               [float(n['altitude']) for n in orig], c='gray', marker='x', s=50, alpha=0.5, label='Initial Position')

    # Final positions
    for n in nodes:
        lon, lat, alt = float(n['longitude']), float(n['latitude']), float(n['altitude'])
        color = 'red' if n['type'] == 'TestUAV' else 'orange'
        
        # Plot the UAV point
        ax.scatter(lon, lat, alt, c=color, marker='^', s=100)
        
        # Add vertical stem line to the ground (Z=0)
        ax.plot([lon, lon], [lat, lat], [0, alt], color=color, linestyle='--', alpha=0.4)
        
        # Determine if it moved significantly
        o = orig_map[n['id']]
        dist = ((lon-float(o['longitude']))**2 + (lat-float(o['latitude']))**2 + (alt-float(o['altitude']))**2)**0.5
        status = "(Moved)" if dist > 0.0001 else "(Static/HAP)"
        
        ax.text(lon, lat, alt+10, f"{n['name']} {status}", color='black', fontsize=8)

    ax.set_xlabel('Lon')
    ax.set_ylabel('Lat')
    ax.set_zlabel('Alt')
    ax.set_title("1000 Steps Deployment Verification")
    plt.legend()
    plt.savefig('过程快照/-1/final_verification_labeled.png')
    print("Saved plot to 过程快照/-1/final_verification_labeled.png")

if __name__ == "__main__":
    final_plot()
