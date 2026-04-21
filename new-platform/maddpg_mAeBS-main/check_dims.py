import torch
import os
import sys

def check_model():
    try:
        model_path = os.path.join("models", "a_c_0.pt")
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}")
            return

        # Load the model
        # Note: Since the model was saved as a full object, we need the class definitions available.
        # They should be imported by 'from model import openai_actor' in the original context.
        # Here we rely on the fact that torch.load might need the class definition.
        # However, if the class structure changed, this might fail.
        
        # We need to add the current directory to sys.path so it can find 'model' module if needed by pickle
        sys.path.append(os.getcwd())
        
        model = torch.load(model_path, map_location=torch.device('cpu'))
        print(f"Model loaded successfully: {model}")
        
        # Check the first layer
        # Usually looking at model structure or finding the first Linear layer
        for name, param in model.named_parameters():
             if 'weight' in name:
                 print(f"Layer {name}: shape {param.shape}")
                 # usually shape is (out_features, in_features) for Linear
                 break
                 
    except Exception as e:
        print(f"Error loading model: {e}")

if __name__ == "__main__":
    check_model()
