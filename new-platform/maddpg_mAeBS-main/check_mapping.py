import os
import json

def check_mapping():
    model_dir = "models"
    input_nodes_path = "过程快照/-1/aerialNode.json"
    
    with open(input_nodes_path, 'r', encoding='utf-8') as f:
        aerial_nodes = json.load(f)
    
    aerial_nodes.sort(key=lambda x: x.get('id', ''))
    
    print(f"Total nodes in JSON: {len(aerial_nodes)}")
    for i, node in enumerate(aerial_nodes):
        model_file = os.path.join(model_dir, f'a_c_{i}.pt')
        exists = os.path.exists(model_file)
        print(f"Node {i} (ID: {node['id']}, Name: {node['name']}): Model {model_file} exists? {exists}")
        if exists:
            # check file size
            print(f"  Size: {os.path.getsize(model_file)} bytes")

if __name__ == "__main__":
    check_mapping()
