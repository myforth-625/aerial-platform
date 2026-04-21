import json
import torch
import numpy as np

# Debug script to understand why models produce repetitive actions

def analyze_model_behavior():
    # Load the model for UAV1
    model_path = 'models/a_c_0.pt'
    try:
        actor = torch.load(model_path, map_location=torch.device('cpu'))
        actor.eval()
        print(f"Successfully loaded model: {model_path}")
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    # Test different scenarios
    scenarios = [
        "Initial state (100m altitude)",
        "After 1 step (200m altitude)", 
        "At max altitude (300m altitude)"
    ]
    
    altitudes = [100.0, 200.0, 300.0]
    
    for i, (scenario, altitude) in enumerate(zip(scenarios, altitudes)):
        # Create observation similar to what the model receives during simulation
        obs = torch.zeros(1, 203)
        
        # Position in the middle of the map (normalized)
        obs[:, 0] = 0.5  # x (longitude)
        obs[:, 1] = 0.5  # y (latitude)
        obs[:, 2] = altitude / 300.0  # altitude normalized to [0, 1]
        
        # Add some terminal positions (this part is critical!)
        # The model has been trained with terminal positions, so we need to include them
        # Even random positions will help us see if the model is responsive
        for j in range(100):  # First 100 terminal positions
            # Random terminal positions
            obs[:, 3 + j*2] = np.random.rand()  # terminal x
            obs[:, 4 + j*2] = np.random.rand()  # terminal y
        
        # Run inference
        with torch.no_grad():
            action_probs = actor(obs)
            action_idx = torch.argmax(action_probs, dim=1).item()
            
        # Print results
        print(f"\n=== {scenario} ===")
        print(f"Input altitude: {altitude}m")
        print(f"Selected action index: {action_idx}")
        print(f"Action probabilities: {action_probs[0].tolist()}")
        
        # Map action index to description
        action_desc = ""
        if action_idx == 1:
            action_desc = "Move west"
        elif action_idx == 2:
            action_desc = "Move east"
        elif action_idx == 3:
            action_desc = "Move south"
        elif action_idx == 4:
            action_desc = "Move north"
        elif action_idx == 5:
            action_desc = "Decrease altitude"
        elif action_idx == 6:
            action_desc = "Increase altitude"
        else:
            action_desc = "No movement"
        
        print(f"Action description: {action_desc}")
    
    # Now let's check what happens with real terminal data
    print("\n=== TEST WITH REAL TERMINAL DATA ===")
    try:
        with open('过程快照/-1/70新终端纯still.json', 'r', encoding='utf-8') as f:
            terminals = json.load(f)
        
        # Create observation with real terminal positions
        obs_real = torch.zeros(1, 203)
        obs_real[:, 0] = 0.5  # x
        obs_real[:, 1] = 0.5  # y
        obs_real[:, 2] = 100.0 / 300.0  # initial altitude
        
        # Add real terminal positions (normalized)
        for j, term in enumerate(terminals[:100]):
            # For real data, we need to normalize like in the simulation
            # But since we don't have the dynamic bounds here, use relative normalization
            term_lon = float(term['longitude'])
            term_lat = float(term['latitude'])
            
            # Normalize roughly around the center
            norm_lon = (term_lon - 116.358) / 0.003  # Simple normalization around center
            norm_lat = (term_lat - 39.9645) / 0.003  # Adjust based on actual terminal range
            
            # Clamp to [0, 1]
            norm_lon = max(0.0, min(1.0, 0.5 + norm_lon / 2))
            norm_lat = max(0.0, min(1.0, 0.5 + norm_lat / 2))
            
            obs_real[:, 3 + j*2] = norm_lon
            obs_real[:, 4 + j*2] = norm_lat
        
        # Run inference with real terminal data
        with torch.no_grad():
            action_probs = actor(obs_real)
            action_idx = torch.argmax(action_probs, dim=1).item()
        
        print(f"With real terminal data:")
        print(f"Selected action index: {action_idx}")
        
    except Exception as e:
        print(f"Error using real terminal data: {e}")

if __name__ == "__main__":
    analyze_model_behavior()
