import torch
import os
import sys

# Ensure model class can be loaded
sys.path.append(os.getcwd())

try:
    from model import openai_actor, openai_critic
except ImportError:
    pass

def inspect_model():
    model_path = os.path.join("models", "a_c_0.pt")
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        return

    try:
        # Load model
        if torch.cuda.is_available():
            actor = torch.load(model_path, map_location=torch.device('cuda:0'))
        else:
            actor = torch.load(model_path, map_location=torch.device('cpu'))
        
        print(f"Model loaded: {model_path}")
        
        # Check input dimension
        if hasattr(actor, 'linear_a1'):
            input_dim = actor.linear_a1.in_features
            print(f"Actor Input Dimension: {input_dim}")
            
            if input_dim == 3:
                print("CONCLUSION: Model is BLIND. It only accepts [x, y, z]. It CANNOT see users.")
            elif input_dim > 3:
                print(f"CONCLUSION: Model SEEING. It accepts {input_dim} inputs (likely [x,y,z] + users).")
        else:
            print("Unknown model structure.")
            print(actor)

    except Exception as e:
        print(f"Error loading model: {e}")

if __name__ == "__main__":
    inspect_model()
