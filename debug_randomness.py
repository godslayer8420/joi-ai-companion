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

print("=== Testing reproducible randomness ===\n")

with tempfile.TemporaryDirectory() as tmpdir:
    mem1 = WorldMemory(os.path.join(tmpdir, "mem1.db"))
    mem2 = WorldMemory(os.path.join(tmpdir, "mem2.db"))
    
    print("Creating sim1 with seed=42")
    sim1 = WorldSimulation(world_memory=mem1, seed=42)
    print(f"sim1.regions keys: {list(sim1.regions.keys())}\n")
    
    print("Creating sim2 with seed=42")
    sim2 = WorldSimulation(world_memory=mem2, seed=42)
    print(f"sim2.regions keys: {list(sim2.regions.keys())}\n")
    
    # Check if the region orders are the same
    print(f"Region orders match: {list(sim1.regions.keys()) == list(sim2.regions.keys())}")
    print(f"sim1 and sim2 regions identical: {sim1.regions.keys() == sim2.regions.keys()}\n")
    
    # Now run tick and compare
    print("Running tick 1...")
    tick1 = sim1.tick()
    tick2 = sim2.tick()
    
    print(f"tick1.spawns_generated: {tick1.spawns_generated}")
    print(f"tick2.spawns_generated: {tick2.spawns_generated}")
    print(f"tick1.regions_affected: {tick1.regions_affected}")
    print(f"tick2.regions_affected: {tick2.regions_affected}")
    
    print("\nNorth region spawns:")
    print(f"sim1 north pending_spawns: {sim1.regions['north'].pending_spawns}")
    print(f"sim2 north pending_spawns: {sim2.regions['north'].pending_spawns}")
    
    print("\nAll regions pending_spawns:")
    for rid in sim1.regions:
        s1_spawns = len(sim1.regions[rid].pending_spawns)
        s2_spawns = len(sim2.regions[rid].pending_spawns)
        if s1_spawns > 0 or s2_spawns > 0:
            print(f"  {rid}: sim1={s1_spawns}, sim2={s2_spawns}")
    
    mem1._db.close()
    mem2._db.close()
    gc.collect()
    time.sleep(0.5)

print("\nDone")
