import numpy as np
import json

def check_data():
    # Check Training User Locations
    try:
        train_locs = np.load("d:/maddpg_mAeBS-main/user_locations_3_100.npy")
        print(f"Training Data (user_locations_3_100.npy) Shape: {train_locs.shape}")
        print(f"Sample Train Data (First 5): \n{train_locs[:5]}")
        print(f"Train Data Range: X [{np.min(train_locs[:,0]):.1f}, {np.max(train_locs[:,0]):.1f}], Y [{np.min(train_locs[:,1]):.1f}, {np.max(train_locs[:,1]):.1f}]")
    except Exception as e:
        print(f"Error loading npy: {e}")

    # Check Inference Terminal Data
    try:
        with open("d:/maddpg_mAeBS-main/过程快照/-1/terminalSnapshot.json", 'r', encoding='utf-8') as f:
            terminals = json.load(f)
        
        lons = [float(t['longitude']) for t in terminals]
        lats = [float(t['latitude']) for t in terminals]
        
        print(f"\nInference Data (terminalSnapshot.json) Count: {len(terminals)}")
        print(f"Inference Lat Range: {min(lats)} - {max(lats)}")
        print(f"Inference Lon Range: {min(lons)} - {max(lons)}")
        
    except Exception as e:
        print(f"Error loading json: {e}")

if __name__ == "__main__":
    check_data()
