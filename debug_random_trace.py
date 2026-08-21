"""Debug script to trace ALL random calls during simulation."""
import os
import sys
import random
import traceback
from collections import defaultdict

# Patch random module to trace all calls
_original_random = random.random
_original_randint = random.randint
_original_choice = random.choice
_original_uniform = random.uniform
_original_seed = random.seed

call_log = defaultdict(list)
current_sim = None

def traced_seed(a):
    global current_sim
    call_log[current_sim].append(f"SEED({a})")
    return _original_seed(a)

def traced_random():
    global current_sim
    val = _original_random()
    call_log[current_sim].append(f"random()={val:.6f}")
    return val

def traced_randint(a, b):
    global current_sim
    val = _original_randint(a, b)
    call_log[current_sim].append(f"randint({a},{b})={val}")
    return val

def traced_choice(seq):
    global current_sim
    val = _original_choice(seq)
    call_log[current_sim].append(f"choice(len={len(seq)})={val}")
    return val

def traced_uniform(a, b):
    global current_sim
    val = _original_uniform(a, b)
    call_log[current_sim].append(f"uniform({a},{b})={val:.6f}")
    return val

# Monkey-patch
random.seed = traced_seed
random.random = traced_random
random.randint = traced_randint
random.choice = traced_choice
random.uniform = traced_uniform

# Now import after patching
from joi_companion.core.world_simulation import WorldSimulation, TRINITY
from joi_companion.core.world_memory import WorldMemory
import tempfile

def test_trace():
    global current_sim
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        mem1 = WorldMemory(os.path.join(tmpdir, "mem1.db"))
        mem2 = WorldMemory(os.path.join(tmpdir, "mem2.db"))
        
        current_sim = "sim1"
        sim1 = WorldSimulation(world_memory=mem1, seed=42)
        init_calls_sim1 = len(call_log["sim1"])
        
        current_sim = "sim2"
        sim2 = WorldSimulation(world_memory=mem2, seed=42)
        init_calls_sim2 = len(call_log["sim2"])
        
        print("=" * 80)
        print("INIT PHASE")
        print("=" * 80)
        print(f"\nSim1 init calls ({init_calls_sim1}):")
        for call in call_log["sim1"][:20]:
            print(f"  {call}")
        print("\nSim2 init calls ({})".format(init_calls_sim2))
        for call in call_log["sim2"][:20]:
            print(f"  {call}")
        
        # Run tick
        current_sim = "sim1"
        tick_start_1 = len(call_log["sim1"])
        tick1 = sim1.tick()
        tick_calls_1 = len(call_log["sim1"]) - tick_start_1
        
        current_sim = "sim2"
        tick_start_2 = len(call_log["sim2"])
        tick2 = sim2.tick()
        tick_calls_2 = len(call_log["sim2"]) - tick_start_2
        
        print("\n" + "=" * 80)
        print("TICK 1 PHASE")
        print("=" * 80)
        print(f"\nSim1 spawns: {tick1.spawns_generated}")
        print(f"Sim1 tick calls ({tick_calls_1}):")
        for i, call in enumerate(call_log["sim1"][tick_start_1:]):
            print(f"  {i:2d}: {call}")
            if i > 50:
                print(f"  ... ({tick_calls_1 - 51} more)")
                break
        
        print(f"\nSim2 spawns: {tick2.spawns_generated}")
        print(f"Sim2 tick calls ({tick_calls_2}):")
        for i, call in enumerate(call_log["sim2"][tick_start_2:]):
            print(f"  {i:2d}: {call}")
            if i > 50:
                print(f"  ... ({tick_calls_2 - 51} more)")
                break
        
        # Find divergence point
        print("\n" + "=" * 80)
        print("FINDING DIVERGENCE")
        print("=" * 80)
        min_calls = min(tick_calls_1, tick_calls_2)
        for i in range(min_calls):
            call1 = call_log["sim1"][tick_start_1 + i]
            call2 = call_log["sim2"][tick_start_2 + i]
            if call1 != call2:
                print(f"\nDIVERGENCE AT CALL {i}:")
                print(f"  Sim1: {call1}")
                print(f"  Sim2: {call2}")
                print(f"\nContext (calls {max(0, i-3)} to {i+3}):")
                print(f"  Sim1:")
                for j in range(max(0, i-3), min(i+4, tick_calls_1)):
                    prefix = ">>>" if j == i else "   "
                    print(f"  {prefix} {j}: {call_log['sim1'][tick_start_1 + j]}")
                print(f"  Sim2:")
                for j in range(max(0, i-3), min(i+4, tick_calls_2)):
                    prefix = ">>>" if j == i else "   "
                    print(f"  {prefix} {j}: {call_log['sim2'][tick_start_2 + j]}")
                break
        else:
            if tick_calls_1 != tick_calls_2:
                print(f"\nNo divergence in first {min_calls} calls, but counts differ:")
                print(f"  Sim1: {tick_calls_1} calls")
                print(f"  Sim2: {tick_calls_2} calls")
            else:
                print("\nNo divergence found! Both sims executed identically.")

if __name__ == "__main__":
    test_trace()
