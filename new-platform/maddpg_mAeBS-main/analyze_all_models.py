import torch
import numpy as np
import json

# Debug script to analyze all UAV models
def analyze_all_models():
    # Check first 4 UAV models
    for model_idx in range(4):
        model_path = f'models/a_c_{model_idx}.pt'
        try:
            # Load the model
            actor = torch.load(model_path, map_location=torch.device('cpu'))
            actor.eval()
            print(f"\n=== Analyzing Model {model_idx} ({model_path}) ===")
            
            # Test with multiple different observations
            test_cases = [
                {"name": "Center position, low altitude", "x": 0.5, "y": 0.5, "z": 100.0},
                {"name": "Center position, mid altitude", "x": 0.5, "y": 0.5, "z": 200.0},
                {"name": "Center position, high altitude", "x": 0.5, "y": 0.5, "z": 300.0},
                {"name": "Edge position, low altitude", "x": 0.1, "y": 0.1, "z": 100.0},
                {"name": "Edge position, mid altitude", "x": 0.9, "y": 0.9, "z": 200.0},
            ]
            
            for test_case in test_cases:
                # Create observation
                obs = torch.zeros(1, 203)
                obs[:, 0] = test_case["x"]
                obs[:, 1] = test_case["y"]
                obs[:, 2] = test_case["z"] / 300.0  # normalize altitude
                
                # Add realistic terminal positions from our data
                try:
                    with open('过程快照/-1/70新终端纯still.json', 'r', encoding='utf-8') as f:
                        terminals = json.load(f)
                    
                    for i, term in enumerate(terminals[:100]):
                        term_lon = float(term['longitude'])
                        term_lat = float(term['latitude'])
                        
                        # Normalize terminal positions based on known range
                        # From previous analysis: Lon ~ 116.355-116.362, Lat ~ 39.961-39.968
                        norm_lon = (term_lon - 116.355) / (116.362 - 116.355)
                        norm_lat = (term_lat - 39.961) / (39.968 - 39.961)
                        
                        obs[:, 3 + i*2] = max(0.0, min(1.0, norm_lon))
                        obs[:, 4 + i*2] = max(0.0, min(1.0, norm_lat))
                except Exception:
                    # Fallback to random positions if terminal data not available
                    for i in range(100):
                        obs[:, 3 + i*2] = np.random.rand()
                        obs[:, 4 + i*2] = np.random.rand()
                
                # Run inference
                with torch.no_grad():
                    action_probs = actor(obs)
                    action_idx = torch.argmax(action_probs, dim=1).item()
                    
                    # Calculate entropy to measure decision randomness
                    entropy = -torch.sum(action_probs * torch.log(action_probs + 1e-10)).item()
                
                # Map action index to description
                action_desc = {
                    1: "West",
                    2: "East", 
                    3: "South",
                    4: "North",
                    5: "Down",
                    6: "Up"
                }.get(action_idx, "None")
                
                print(f"{test_case['name']}:")
                print(f"  Action: {action_idx} ({action_desc})")
                print(f"  Entropy: {entropy:.4f}")
                
                # Check if the action is deterministic (very low entropy)
                if entropy < 0.1:
                    print("  WARNING: Deterministic action selection!")
            
        except Exception as e:
            print(f"Error analyzing model {model_idx}: {e}")
            continue

if __name__ == "__main__":
    analyze_all_models()
