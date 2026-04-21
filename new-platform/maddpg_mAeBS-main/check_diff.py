import json
import math

def calculate_displacement(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            nodes_in = json.load(f)
        with open(output_file, 'r', encoding='utf-8') as f:
            nodes_out = json.load(f)
            
        print("UAV Movements (Real geographic difference):")
        for n_in in nodes_in:
            if n_in['type'] == 'TestUAV':
                n_out = next((n for n in nodes_out if n['id'] == n_in['id']), None)
                if n_out:
                    in_lon = float(n_in['longitude'])
                    in_lat = float(n_in['latitude'])
                    in_alt = float(n_in['altitude'])
                    
                    out_lon = float(n_out['longitude'])
                    out_lat = float(n_out['latitude'])
                    out_alt = float(n_out.get('altitude', in_alt))
                    
                    # Rough meters approximation for Beijing latitude (cos(40 deg) * 111320)
                    SCALE_X = 111320.0 * math.cos(math.radians(39.96))
                    SCALE_Y = 110574.0
                    
                    dx_m = (out_lon - in_lon) * SCALE_X
                    dy_m = (out_lat - in_lat) * SCALE_Y
                    dz_m = out_alt - in_alt
                    
                    dist_3d = math.sqrt(dx_m**2 + dy_m**2 + dz_m**2)
                    
                    print(f"  {n_in['name']} (ID {n_in['id']}):")
                    print(f"    Moved: dx={dx_m:.2f}m, dy={dy_m:.2f}m, dz={dz_m:.2f}m (Total 3D Shift: {dist_3d:.2f}m)")
                    
    except Exception as e:
        print(f"Error checking displacement: {e}")

if __name__ == '__main__':
    calculate_displacement('过程快照/-1/aerialNode.json', '过程快照/-1/aerialNodeResult_fixed_verification.json')
