import torch
import os

model_dir = "models"
for file in os.listdir(model_dir):
    if file.endswith('.pt'):
        print(f"\nModel: {file}")
        try:
            model = torch.load(os.path.join(model_dir, file), map_location=torch.device('cpu'))
            print(f"Input dimensions: {model.linear_a1.in_features}")
            print(f"Action size: {model.linear_a.out_features}")
        except Exception as e:
            print(f"Error loading model: {e}")
