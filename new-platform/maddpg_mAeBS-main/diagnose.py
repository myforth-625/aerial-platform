import json

def diagnose():
    orig = json.load(open('过程快照/-1/aerialNode.json'))
    fix1 = json.load(open('过程快照/-1/aerialNodeResult_fixed.json')) # 1 step
    fix1000 = json.load(open('过程快照/-1/aerialNodeResult_1000steps.json')) # 1000 steps

    orig_map = {n['id']: n for n in orig}
    
    print(f"{'ID':<4} {'Name':<8} {'Type':<8} {'Moved (1000 steps)?'}")
    print("-" * 40)
    
    for n in fix1000:
        oid = n['id']
        o = orig_map[oid]
        
        dx = float(n['longitude']) - float(o['longitude'])
        dy = float(n['latitude']) - float(o['latitude'])
        dz = float(n['altitude']) - float(o['altitude'])
        
        moved = abs(dx) > 1e-9 or abs(dy) > 1e-9 or abs(dz) > 1e-9
        print(f"{oid:<4} {n['name']:<8} {n['type']:<8} {moved}")
        if moved:
            print(f"  Delta: dLon={dx:.6f}, dLat={dy:.6f}, dAlt={dz:.1f}")

if __name__ == "__main__":
    diagnose()
