import json

def compare_results():
    input_file = "过程快照/-1/aerialNode.json"
    output_file = "过程快照/-1/aerialNodeResult_fixed.json"
    
    with open(input_file, 'r') as f:
        in_nodes = json.load(f)
        
    with open(output_file, 'r') as f:
        out_nodes = json.load(f)
        
    in_dict = {n['id']: n for n in in_nodes}
    
    print(f"{'ID':<4} {'Type':<8} {'Input (Lon, Lat, Alt)':<40} {'Output (Lon, Lat, Alt)':<40}")
    print("-" * 95)
    
    for out_n in out_nodes:
        idx = out_n['id']
        in_n = in_dict.get(idx)
        
        in_lon = float(in_n['longitude'])
        in_lat = float(in_n['latitude'])
        in_alt = float(in_n['altitude'])
        
        out_lon = float(out_n['longitude'])
        out_lat = float(out_n['latitude'])
        out_alt = float(out_n['altitude'])
        
        print(f"{idx:<4} {out_n['type']:<8} "
              f"({in_lon:.5f}, {in_lat:.5f}, {in_alt})".ljust(40) +
              f"({out_lon:.5f}, {out_lat:.5f}, {out_alt})")

if __name__ == '__main__':
    compare_results()
