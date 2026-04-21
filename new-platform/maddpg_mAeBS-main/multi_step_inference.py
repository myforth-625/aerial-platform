import os
import sys
import copy
import argparse
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

import torch

# Ensure inference.py can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from inference import run_inference

def main():
    steps = 50
    
    input_nodes = r"过程快照\-1\aerialNode.json"
    input_terms = r"过程快照\-1\terminalSnapshot.json"
    
    # { id: [(lon, lat, alt), ... ] }
    trajectories = {}
    
    with open(input_nodes, 'r', encoding='utf-8') as f:
        initial_nodes = json.load(f)
        for n in initial_nodes:
            if n['type'] in ('TestUAV', 'UAV'):
                trajectories[n['id']] = [(float(n['longitude']), float(n['latitude']), float(n.get('altitude', 100)))]
                
    curr_input = input_nodes
    for i in range(steps):
        print(f"--- Running Step {i+1}/{steps} ---")
        curr_output = rf"过程快照\-1\temp_nodes_step{i}.json"
        
        args = argparse.Namespace(
            work_dir=None,
            input_nodes=curr_input,
            input_terminals=input_terms,
            output_nodes=curr_output,
            model_path='models',
            input_links=None,
            output_links=None,
            steps=None,
            ref_lon=116.355,
            ref_lat=39.962,
            scene_width=6000.0,
            scene_height=6000.0
        )
        
        # Suppress the heavy stdout for each step except the start
        run_inference(args)
        
        with open(curr_output, 'r', encoding='utf-8') as f:
            out_nodes = json.load(f)
            
        for n in out_nodes:
            if n['type'] in ('TestUAV', 'UAV') and n['id'] in trajectories:
                trajectories[n['id']].append((float(n['longitude']), float(n['latitude']), float(n.get('altitude', 100))))
                
        curr_input = curr_output
        # Clean up temporary file to avoid clutter
        if i > 0 and i < steps - 1:
            try:
                os.remove(rf"过程快照\-1\temp_nodes_step{i-1}.json")
            except Exception:
                pass
                
    # Final cleanup rename
    final_dest = rf"过程快照\-1\aerialNodeResult_{steps}steps.json"
    try:
        os.rename(curr_output, final_dest)
    except Exception:
        pass
        
    print(f"Inference loop finished. Final positions saved to {final_dest}\nPlotting trajectories...")
    
    # ----------- PLOT -----------
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    with open(input_terms, 'r', encoding='utf-8') as f:
        terms = json.load(f)
    term_lons = [float(t['longitude']) for t in terms]
    term_lats = [float(t['latitude']) for t in terms]
    term_alts = [float(t.get('altitude', 0)) for t in terms]
    ax.scatter(term_lons, term_lats, term_alts, c='blue', alpha=0.1, label='Ground Users')
    
    colors = ['red', 'green', 'orange', 'purple', 'cyan']
    c_idx = 0
    for uid, traj in trajectories.items():
        lons = [p[0] for p in traj]
        lats = [p[1] for p in traj]
        alts = [p[2] for p in traj]
        
        ax.plot(lons, lats, alts, color=colors[c_idx % len(colors)], marker='.', markersize=2, label=f'UAV {uid} path')
        ax.scatter([lons[0]], [lats[0]], [alts[0]], color='black', marker='x', s=100) # Start points
        ax.scatter([lons[-1]], [lats[-1]], [alts[-1]], color=colors[c_idx % len(colors)], marker='^', s=150) # End points
        
        c_idx += 1
        
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_zlabel('Altitude (m)')
    ax.set_title(f'UAV Real Displacement Trajectory over {steps} steps')
    ax.legend()
    
    ax.view_init(elev=40., azim=-45)
    plt.tight_layout()
    try:
        save_path = r'过程快照\-1\visualization_multistep.png'
        plt.savefig(save_path, dpi=300)
        print(f"Saved plot to {save_path}")
        # Copy to artifacts for AI access
        import shutil
        shutil.copy(save_path, r"C:\Users\LENOVO\.gemini\antigravity\brain\5860daff-4453-4fe5-9ded-8c13d1767299\artifacts\visualization_multistep.png")
    except Exception as e:
        print(f"Error saving plot: {e}")
    
if __name__ == '__main__':
    main()
