import json
import subprocess
import sys

# Run inference for irregular distribution
print("Running inference for irregular distribution...")
irr_cmd = [
    sys.executable, "inference.py",
    "--input_nodes", "过程快照/-1/aerialNode.json",
    "--input_terminals", "过程快照/-1/terminalSnapshot_irregular.json",
    "--output_nodes", "过程快照/-1/aerialNodeResult_irr_test.json"
]
irr_result = subprocess.run(irr_cmd, capture_output=True, text=True)
print(irr_result.stdout)

# Run inference for new distribution
print("\nRunning inference for new distribution...")
new_cmd = [
    sys.executable, "inference.py",
    "--input_nodes", "过程快照/-1/aerialNode.json",
    "--input_terminals", "过程快照/-1/terminalSnapshot_new.json",
    "--output_nodes", "过程快照/-1/aerialNodeResult_new_test.json"
]
new_result = subprocess.run(new_cmd, capture_output=True, text=True)
print(new_result.stdout)

# Extract action indices
print("\nExtracting action indices...")
irr_actions = []
for line in irr_result.stdout.split('\n'):
    if "Action Index" in line:
        irr_actions.append(line)

new_actions = []
for line in new_result.stdout.split('\n'):
    if "Action Index" in line:
        new_actions.append(line)

# Compare actions
print("\nComparing actions:")
print("-" * 60)
for i, (irr_act, new_act) in enumerate(zip(irr_actions, new_actions)):
    print(f"Agent {i}:")
    print(f"  Irregular: {irr_act}")
    print(f"  New:       {new_act}")
    if irr_act == new_act:
        print("  Same action for both distributions!")
    else:
        print("  Different actions for different distributions!")
    print("-" * 60)