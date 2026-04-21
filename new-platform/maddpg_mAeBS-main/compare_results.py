import json
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os

# 1. Compare JSON results to find position differences
def compare_json_results():
    print("=== Comparing JSON Results ===")
    
    # Load both JSON files
    with open('过程快照/-1/aerialNodeResult_irregular_final.json', 'r', encoding='utf-8') as f:
        irr_result = json.load(f)
    
    with open('过程快照/-1/aerialNodeResult_new_final.json', 'r', encoding='utf-8') as f:
        new_result = json.load(f)
    
    # Sort both by ID to ensure proper comparison
    irr_result.sort(key=lambda x: x.get('id', ''))
    new_result.sort(key=lambda x: x.get('id', ''))
    
    print(f"Irregular result has {len(irr_result)} nodes")
    print(f"New result has {len(new_result)} nodes")
    
    # Compare each node
    for i, (irr_node, new_node) in enumerate(zip(irr_result, new_result)):
        irr_lon = float(irr_node['longitude'])
        irr_lat = float(irr_node['latitude'])
        irr_alt = float(irr_node['altitude'])
        
        new_lon = float(new_node['longitude'])
        new_lat = float(new_node['latitude'])
        new_alt = float(new_node['altitude'])
        
        # Calculate differences
        diff_lon = abs(irr_lon - new_lon)
        diff_lat = abs(irr_lat - new_lat)
        diff_alt = abs(irr_alt - new_alt)
        
        # Convert to meters for better understanding
        scale_x = 111320.0 * np.cos(np.radians((irr_lat + new_lat) / 2))
        scale_y = 110574.0
        diff_m_x = diff_lon * scale_x
        diff_m_y = diff_lat * scale_y
        diff_m_total = np.sqrt(diff_m_x**2 + diff_m_y**2)
        
        print(f"\nNode {i} ({irr_node['id']}):")
        print(f"  Irregular: Lon={irr_lon:.8f}, Lat={irr_lat:.8f}, Alt={irr_alt:.1f}")
        print(f"  New:       Lon={new_lon:.8f}, Lat={new_lat:.8f}, Alt={new_alt:.1f}")
        print(f"  Differences: Lon={diff_lon:.8f}, Lat={diff_lat:.8f}, Alt={diff_alt:.1f}")
        print(f"  Distance apart: {diff_m_total:.1f} meters")

# 2. Compare images
def compare_images():
    print("\n=== Comparing Visualization Images ===")
    
    # Check if images exist
    irr_img_path = '过程快照/-1/visualization_irregular_final.png'
    new_img_path = '过程快照/-1/visualization_new_final.png'
    
    if not os.path.exists(irr_img_path):
        print(f"Error: {irr_img_path} not found")
        return
    
    if not os.path.exists(new_img_path):
        print(f"Error: {new_img_path} not found")
        return
    
    print(f"Irregular image: {irr_img_path}")
    print(f"New image: {new_img_path}")
    
    # Load images
    try:
        irr_img = Image.open(irr_img_path)
        new_img = Image.open(new_img_path)
        
        print(f"Irregular image size: {irr_img.size}")
        print(f"New image size: {new_img.size}")
        
        # Check if images are identical
        if irr_img.size == new_img.size:
            irr_pixels = np.array(irr_img)
            new_pixels = np.array(new_img)
            
            # Calculate percentage of different pixels
            diff_pixels = np.sum(irr_pixels != new_pixels)
            total_pixels = np.prod(irr_img.size)
            diff_percentage = (diff_pixels / total_pixels) * 100
            
            print(f"Percentage of different pixels: {diff_percentage:.2f}%")
            print(f"Number of different pixels: {diff_pixels:,} / {total_pixels:,}")
            
            if diff_percentage > 5:
                print("Images have significant differences - different deployment strategies detected!")
            elif diff_percentage > 1:
                print("Images have noticeable differences - deployment strategies differ.")
            else:
                print("Images are very similar - deployment strategies may be the same.")
        else:
            print("Images have different sizes - cannot directly compare pixels.")
            print("But they are separate files, so deployment strategies likely differ.")
            
    except Exception as e:
        print(f"Error comparing images: {e}")

# 3. Create comparison report
def create_comparison_report():
    print("\n" + "="*50)
    print("COMPARISON REPORT")
    print("="*50)
    
    compare_json_results()
    compare_images()
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print("The simulations for the two different terminal distributions have been completed.")
    print("Check the output files for detailed results:")
    print("- Irregular: aerialNodeResult_irregular_final.json")
    print("- New: aerialNodeResult_new_final.json")
    print("\nVisualization images:")
    print("- Irregular: visualization_irregular_final.png")
    print("- New: visualization_new_final.png")

if __name__ == "__main__":
    create_comparison_report()
