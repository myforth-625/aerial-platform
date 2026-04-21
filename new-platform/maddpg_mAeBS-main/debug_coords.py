
import json

def test_logic():
    # Mock data from aerialNode.json (UAV1)
    node = {
        "longitude" : "116.35687983557841611370",
        "latitude" : "39.96404761945006492866",
        "altitude" : "100.0"
    }

    # Parameters from inference.py
    real_w = 6000.0
    real_h = 6000.0
    TRAIN_DIM = 6000.0
    sensitivity = 100.0

    def to_model_x(val): return (float(val) / real_w) * TRAIN_DIM
    def to_model_y(val): return (float(val) / real_h) * TRAIN_DIM
    
    def to_real_x(val): return (float(val) / TRAIN_DIM) * real_w
    def to_real_y(val): return (float(val) / TRAIN_DIM) * real_h

    real_x = float(node.get('longitude'))
    real_y = float(node.get('latitude'))
    
    print(f"Original Real X: {real_x}")
    print(f"Original Real Y: {real_y}")

    model_x = to_model_x(real_x)
    model_y = to_model_y(real_y)
    
    print(f"Model X: {model_x}")
    print(f"Model Y: {model_y}")

    # Simulate Action: Move Left and Down
    # Action index 1 -> dx = -1
    # Action index 3 -> dy = -1
    
    # Try all movements
    moves = [
        ("Left", -100, 0),
        ("Right", 100, 0),
        ("Down", 0, -100),
        ("Up", 0, 100)
    ]

    for name, dx, dy in moves:
        new_model_x = max(0, min(TRAIN_DIM, model_x + dx))
        new_model_y = max(0, min(TRAIN_DIM, model_y + dy))
        
        new_real_x = to_real_x(new_model_x)
        new_real_y = to_real_y(new_model_y)
        
        print(f"--- Move {name} ---")
        print(f"New Model X: {new_model_x}")
        print(f"New Model Y: {new_model_y}")
        print(f"New Real X: {new_real_x}")
        print(f"New Real Y: {new_real_y}")

if __name__ == "__main__":
    test_logic()
