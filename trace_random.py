import os
import sys
import tempfile
import random
import time
import gc
import copy
from pathlib import Path

sys.path.insert(0, r"D:\bzimm\GitHub Copilot\copilot-worktrees\joi-ai-companion\godslayer8420-fuzzy-meme")

from joi_companion.core.sacred_geometry import TRINITY
from joi_companion.core.world_memory import WorldMemory
from joi_companion.core.world_simulation import WorldSimulation
from joi_companion.core.world_regions import get_regions

print("=== Tracing random value consumption ===\n")

# Monkey-patch random.random() to track calls
original_random = random.random
random_calls = []
def traced_random():
    val = original_random()
    random_calls.append(val)
    return val
random.random = traced_random

# Also patch randint
original_randint = random.randint
def traced_randint(a, b):
    val = original_randint(a, b)
    random_calls.append(f"randint({a},{b})={val}")
    return val
random.randint = traced_randint

with tempfile.TemporaryDirectory() as tmpdir:
    # First simulation
    print("=" * 60)
    print("SIM1 with seed=42")
    print("=" * 60)
    random_calls = []
    mem1 = WorldMemory(os.path.join(tmpdir, "mem1.db"))
    random.seed(42)
    sim1 = WorldSimulation(world_memory=mem1, seed=42)
    
    print(f"\nAfter __init__: {len(random_calls)} random calls")
    for i, val in enumerate(random_calls[:15]):
        print(f"  {i}: {val}")
    if len(random_calls) > 15:
        print(f"  ... and {len(random_calls) - 15} more")
    
    # Record the state after init
    init_calls_1 = len(random_calls)
    
    # Reset for tick
    random_calls = []
    tick1 = sim1.tick()
    print(f"\nTick 1: {len(random_calls)} new random calls")
    for i, val in enumerate(random_calls[:20]):
        print(f"  {i}: {val}")
    
    print(f"\nTick1 spawns: {tick1.spawns_generated}")
    print(f"Regions affected: {tick1.regions_affected}")
    
    mem1._db.close()
    
    # Second simulation
    print("\n" + "=" * 60)
    print("SIM2 with seed=42")
    print("=" * 60)
    random_calls = []
    mem2 = WorldMemory(os.path.join(tmpdir, "mem2.db"))
    random.seed(42)
    sim2 = WorldSimulation(world_memory=mem2, seed=42)
    
    print(f"\nAfter __init__: {len(random_calls)} random calls")
    for i, val in enumerate(random_calls[:15]):
        print(f"  {i}: {val}")
    if len(random_calls) > 15:
        print(f"  ... and {len(random_calls) - 15} more")
    
    init_calls_2 = len(random_calls)
    
    # Reset for tick
    random_calls = []
    tick2 = sim2.tick()
    print(f"\nTick 1: {len(random_calls)} new random calls")
    for i, val in enumerate(random_calls[:20]):
        print(f"  {i}: {val}")
    
    print(f"\nTick2 spawns: {tick2.spawns_generated}")
    print(f"Regions affected: {tick2.regions_affected}")
    
    mem2._db.close()
    
    print(f"\nInit random calls same: {init_calls_1 == init_calls_2}")
    print(f"Init calls: sim1={init_calls_1}, sim2={init_calls_2}")

gc.collect()
time.sleep(0.5)
print("\nDone")
