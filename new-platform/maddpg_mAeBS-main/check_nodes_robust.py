import json

def check_nodes_robust():
    input_file = r"d:\maddpg_mAeBS-main\过程快照\-1\aerialNode.json"
    output_file = r"d:\maddpg_mAeBS-main\过程快照\-1\aerialNodeResult.json"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data_in = json.load(f)
    with open(output_file, 'r', encoding='utf-8') as f:
        data_out = json.load(f)
        
    # Sort both by ID to match inference.py logic
    data_in.sort(key=lambda x: str(x.get('id', '')))
    data_out.sort(key=lambda x: str(x.get('id', '')))
    
    print(f"{'Idx':<4} {'ID':<6} {'Type':<10} {'Alt(In)':<8} {'Alt(Out)':<8} {'Moved?':<6}")
    print("-" * 60)
    
    for i, node_in in enumerate(data_in):
        node_out = data_out[i] if i < len(data_out) else {}
        
        nid = str(node_in.get('id', 'N/A'))
        ntype = str(node_in.get('type', 'N/A'))
        alt_in = str(node_in.get('altitude', 'N/A'))
        alt_out = str(node_out.get('altitude', 'N/A'))
        
        # Check movement
        lat_in = float(node_in.get('latitude', 0))
        lat_out = float(node_out.get('latitude', 0))
        moved = abs(lat_in - lat_out) > 1e-9
        
        print(f"{i:<4} {nid:<6} {ntype:<10} {alt_in:<8} {alt_out:<8} {moved:<6}")

if __name__ == "__main__":
    check_nodes_robust()
