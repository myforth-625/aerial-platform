import json

def check_nodes():
    input_file = r"d:\maddpg_mAeBS-main\过程快照\-1\aerialNode.json"
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    data.sort(key=lambda x: x.get('id', ''))
    
    print(f"{'Idx':<4} {'ID':<10} {'Type':<12} {'Alt':<8} {'Lon':<12} {'Lat':<10}")
    print("-" * 60)
    for i, node in enumerate(data):
        print(f"{i:<4} {node.get('id', 'N/A'):<10} {node.get('type', 'N/A'):<12} {node.get('altitude', 'N/A'):<8} {node.get('longitude')[:8]:<12} {node.get('latitude')[:8]:<10}")

if __name__ == "__main__":
    check_nodes()
