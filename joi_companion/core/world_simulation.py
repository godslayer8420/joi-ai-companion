"""world_simulation.py — World tick engine for Phase 5.

Handles:
- Per-region ecology evolution (spawn queue, NPC movement, event generation)
- Weather cycling and Lumen energy fluctuation
- Encounter probability per tick (tick = 9 seconds, UNITY interval)
- Integration with WorldMemory for persistent state

The simulation is designed to run synchronously on a 9-second tick
via GameLauncher's main loop (no threading), with reproducible
randomness via sacred geometry seeding.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import time
import random
import copy
from enum import Enum

from joi_companion.core.sacred_geometry import (
    PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY,
    digital_root, is_369, vortex_weight
)
from joi_companion.core.world_memory import WorldMemory, WorldEvent, RegionState
from joi_companion.core.world_regions import (
    Region, get_regions, WeatherPattern, EconomyType, BiomeType
)


# ─────────────────────────────────────────────────────────────────────────────
# Simulation constants
# ─────────────────────────────────────────────────────────────────────────────
TICK_INTERVAL = UNITY  # 9 seconds between ticks
TICKS_PER_MOON_CYCLE = 9 * UNITY  # 81 ticks = ~12 minutes (compressed lunar month)
SPAWN_BASE_RATE = 0.05  # Base probability per region per tick
WEATHER_CHANGE_RATE = 0.08  # Probability weather shifts each tick
LUMEN_DRIFT_RATE = 0.02  # Lumen energy drifts by ±2% per tick


# ─────────────────────────────────────────────────────────────────────────────
# Simulation state machine
# ─────────────────────────────────────────────────────────────────────────────
class SimulationPhase(str, Enum):
    """Which phase of the tick cycle we're in."""
    SPAWN = "spawn"        # 1. Encounters spawn
    MOVE = "move"          # 2. NPCs/creatures move
    WEATHER = "weather"    # 3. Weather shifts
    ENERGY = "energy"      # 4. Lumen drifts
    EFFECT = "effect"      # 5. Regional effects trigger
    CLEANUP = "cleanup"    # 6. Expired events decay


@dataclass
class SimulationTick:
    """Record of a single simulation tick."""
    tick_number: int
    timestamp: float
    phase: SimulationPhase
    regions_affected: List[str]
    spawns_generated: int
    encounters_resolved: int
    weather_events: int
    lumen_shifts: Dict[str, float]  # region_id -> new lumen_energy


# ─────────────────────────────────────────────────────────────────────────────
# World Simulation Engine
# ─────────────────────────────────────────────────────────────────────────────
class WorldSimulation:
    """
    Orchestrates procedural world generation and tick-by-tick evolution.
    
    Tight integration with WorldMemory (persists state via TinyDB)
    and World Regions (spatial/biome layout).
    """
    
    def __init__(self, world_memory: WorldMemory, seed: Optional[int] = None):
        """
        Initialize the simulation.
        
        Args:
            world_memory: WorldMemory instance for persistent state
            seed: Optional random seed; if None, uses sacred geometry hash
        """
        self.world_memory = world_memory
        self.regions = copy.deepcopy(get_regions())
        self.tick_count = 0
        self.last_tick_time = time.time()
        self.simulation_time = 0.0  # Simulated seconds (not wall clock)
        self.moon_phase = 0  # 0–8 (TRINITY×TRINITY cycle, with 9th as transition)
        
        # Set random seed for reproducibility
        if seed is None:
            seed = sum(ord(c) for c in "AURION") * int(PHI)
            seed = int(seed) % (2**31 - 1)
        self.rng_seed = seed
        # Use instance-level RNG instead of global random module for determinism
        self.rng = random.Random(seed)
        
        # Initialize region weather
        self._init_weather()
        
        # Tick history (last N ticks for debugging)
        self.tick_history: List[SimulationTick] = []
        self.max_history = TRINITY * HARMONY  # Keep 18 ticks
    
    def _init_weather(self):
        """Initialize random weather for each region."""
        for region_id, region in sorted(self.regions.items()):
            weather_roll = self.rng.random()
            if weather_roll < 0.15:
                region.weather = WeatherPattern.FULL_MOON
            elif weather_roll < 0.30:
                region.weather = WeatherPattern.STORM
            elif weather_roll < 0.40:
                region.weather = WeatherPattern.ECLIPSE
            else:
                region.weather = WeatherPattern.CLEAR
    
    def tick(self, dt: float = TICK_INTERVAL) -> SimulationTick:
        """
        Execute one full simulation cycle (9 seconds of game time).
        
        Called by GameLauncher main loop at regular intervals.
        
        Args:
            dt: Delta time since last tick (default = 9 sec)
        
        Returns:
            SimulationTick record with changes made during this tick
        """
        self.tick_count += 1
        self.simulation_time += dt
        
        # Track changes across all phases
        tick_record = SimulationTick(
            tick_number=self.tick_count,
            timestamp=time.time(),
            phase=SimulationPhase.SPAWN,
            regions_affected=[],
            spawns_generated=0,
            encounters_resolved=0,
            weather_events=0,
            lumen_shifts={},
        )
        
        # Phase 1: Spawn encounters in each region
        for region_id in sorted(self.regions):
            spawns = self._phase_spawn(region_id)
            tick_record.spawns_generated += spawns
            if spawns > 0:
                tick_record.regions_affected.append(region_id)
        
        # Phase 2: Move NPCs (stub for now)
        self._phase_move()
        
        # Phase 3: Cycle weather
        weather_changes = self._phase_weather()
        tick_record.weather_events = weather_changes
        
        # Phase 4: Drift Lumen energy
        lumen_changes = self._phase_energy()
        tick_record.lumen_shifts = lumen_changes
        
        # Phase 5: Trigger regional effects (based on weather, Lumen, etc.)
        self._phase_effects()
        
        # Phase 6: Cleanup expired events
        self._phase_cleanup()
        
        # Update moon phase (cycles 0–8 repeatedly)
        self.moon_phase = int(self.tick_count % TICKS_PER_MOON_CYCLE / 9)
        
        # Record tick
        self.tick_history.append(tick_record)
        if len(self.tick_history) > self.max_history:
            self.tick_history.pop(0)
        
        self.last_tick_time = time.time()
        return tick_record
    
    # ─────────────────────────────────────────────────────────────────────────
    # Simulation phases
    # ─────────────────────────────────────────────────────────────────────────
    
    def _phase_spawn(self, region_id: str) -> int:
        """
        Spawn encounters in a region if conditions are met.
        
        Encounter probability depends on:
        - Base spawn rate
        - Region ecology_scale
        - Weather pattern
        - Lumen energy
        
        Returns: Number of spawns generated
        """
        region = self.regions[region_id]
        
        # Modulate spawn rate based on conditions
        spawn_prob = SPAWN_BASE_RATE * region.ecology_scale
        
        # Weather boost
        if region.weather == WeatherPattern.STORM:
            spawn_prob *= 1.3
        elif region.weather == WeatherPattern.FULL_MOON:
            spawn_prob *= 1.5
        elif region.weather == WeatherPattern.ECLIPSE:
            spawn_prob *= 1.1
        
        # Lumen modulation (low Lumen = fewer spawns in some biomes)
        if region.biome == BiomeType.LUMINOUS_FOREST and region.lumen_energy < 0.3:
            spawn_prob *= 0.5
        
        # Roll for spawn
        if self.rng.random() > spawn_prob:
            return 0
        
        # Spawn 1–TRINITY (1–3) encounters
        num_spawns = self.rng.randint(1, TRINITY)
        
        for _ in range(num_spawns):
            # Determine tier and species based on region spawn table
            tier_roll = self.rng.random()
            tier = region.spawn_rates.get_random_tier(tier_roll)
            species_list = region.spawn_table.get_species_for_tier(tier)
            
            if not species_list:
                continue
            
            species = self.rng.choice(species_list)
            
            # Create spawn record
            import uuid
            from joi_companion.core.world_memory import WorldEvent
            
            spawn_event = {
                "species": species,
                "tier": tier,
                "level": self._calculate_spawn_level(region, tier),
                "timestamp": self.simulation_time,
            }
            region.pending_spawns.append(spawn_event)
            
            # Log to world memory
            event = WorldEvent(
                event_id=str(uuid.uuid4()),
                event_type="alien_spawn",
                region_id=region_id,
                description=f"{species} (T{tier}) appeared in {region.name}",
                participants=[species],
                tick=self.tick_count,
                ts=self.simulation_time,
            )
            self.world_memory.log_event(event)
        
        return num_spawns
    
    def _phase_move(self):
        """Move NPCs, age existing encounters, etc. (Stub for now)."""
        # TODO: Implement NPC pathfinding, encounter expiration
        pass
    
    def _phase_weather(self) -> int:
        """
        Cycle weather each tick.
        Returns: Number of weather changes
        """
        changes = 0
        for region_id, region in sorted(self.regions.items()):
            if self.rng.random() > WEATHER_CHANGE_RATE:
                continue
            
            # Shift to new weather
            old_weather = region.weather
            weather_roll = self.rng.random()
            if weather_roll < 0.15:
                region.weather = WeatherPattern.FULL_MOON
            elif weather_roll < 0.30:
                region.weather = WeatherPattern.STORM
            elif weather_roll < 0.40:
                region.weather = WeatherPattern.ECLIPSE
            else:
                region.weather = WeatherPattern.CLEAR
            
            if region.weather != old_weather:
                changes += 1
                import uuid
                event = WorldEvent(
                    event_id=str(uuid.uuid4()),
                    event_type="weather_shift",
                    region_id=region_id,
                    description=f"Weather changed from {old_weather.value} to {region.weather.value}",
                    participants=[],
                    ts=self.simulation_time,
                    tick=self.tick_count
                )
                self.world_memory.log_event(event)
        
        return changes
    
    def _phase_energy(self) -> Dict[str, float]:
        """
        Drift Lumen energy levels.
        Returns: Dict of region_id -> new_lumen_energy
        """
        changes = {}
        for region_id, region in sorted(self.regions.items()):
            # Lumen drifts toward the biome's "natural" level
            natural_level = self._get_natural_lumen(region)
            
            # Drift toward natural with some randomness
            drift = (natural_level - region.lumen_energy) * LUMEN_DRIFT_RATE
            drift += self.rng.uniform(-0.01, 0.01)  # ±1% noise
            
            new_lumen = region.lumen_energy + drift
            new_lumen = max(0.0, min(1.0, new_lumen))
            
            if abs(new_lumen - region.lumen_energy) > 0.01:
                changes[region_id] = new_lumen
                region.lumen_energy = new_lumen
        
        return changes
    
    def _phase_effects(self):
        """
        Trigger region-specific effects based on weather, Lumen, etc.
        
        Examples:
        - Full moon in jungle: evolution triggers
        - Void rifts low Lumen: void spawn surge
        - Crystal caverns high Lumen: harmonic resonance event
        """
        for region_id, region in sorted(self.regions.items()):
            # Full moon + forest = evolution surge
            if (region.weather == WeatherPattern.FULL_MOON and
                region.biome == BiomeType.LUMINOUS_FOREST):
                from joi_companion.core.world_memory import WorldEvent
                event = WorldEvent(
                    event_id=f"effect_{self.tick_count}_{region_id}",
                    event_type="effect_trigger",
                    region_id=region_id,
                    description="Lunar energy swells—evolutions surge under moonlight!",
                    participants=[],
                    tick=self.tick_count,
                )
                self.world_memory.log_event(event)
            
            # Void rifts degrade Lumen
            if region.biome == BiomeType.VOID and self.rng.random() < 0.1:
                region.lumen_energy = max(0.0, region.lumen_energy - 0.05)
    
    def _phase_cleanup(self):
        """
        Expire old events, clear resolved spawns, etc.
        """
        for region_id, region in sorted(self.regions.items()):
            # Clear expired spawns (TODO: define expiration threshold)
            region.pending_spawns = [
                s for s in region.pending_spawns
                if self.simulation_time - s["timestamp"] < TICKS_PER_MOON_CYCLE
            ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────
    
    def _calculate_spawn_level(self, region: Region, tier: int) -> int:
        """Determine level of a spawned alien based on tier and region."""
        if tier == 1:
            return self.rng.randint(1, 15)
        elif tier == 2:
            base = 15 + int((region.ecology_scale) * 25)
            return base + self.rng.randint(-3, 3)
        else:  # tier 3
            base = 40 + int((region.lumen_energy) * 20)
            return base + self.rng.randint(-5, 5)
    
    def _get_natural_lumen(self, region: Region) -> float:
        """
        Return the "natural" Lumen level for a region based on biome.
        
        High-Lumen: Luminous Forest, Crystal Caverns, Ruins
        Mid-Lumen: Jungle, Tundra, Volcanic
        Low-Lumen: Void, Abyssal Trench, Swamp
        """
        if region.biome == BiomeType.LUMINOUS_FOREST:
            return 0.85
        elif region.biome == BiomeType.CRYSTAL_CAVERNS:
            return 0.70
        elif region.biome == BiomeType.RUINS:
            return 0.65
        elif region.biome == BiomeType.VOLCANIC:
            return 0.50
        elif region.biome == BiomeType.JUNGLE:
            return 0.70
        elif region.biome == BiomeType.TUNDRA:
            return 0.55
        elif region.biome == BiomeType.SWAMP:
            return 0.35
        elif region.biome == BiomeType.ABYSSAL_TRENCH:
            return 0.25
        else:  # VOID
            return 0.05
    
    def get_tick_summary(self) -> Dict[str, Any]:
        """Return summary of last tick for debugging."""
        if not self.tick_history:
            return {}
        
        last = self.tick_history[-1]
        return {
            "tick": last.tick_number,
            "spawns": last.spawns_generated,
            "weather_changes": last.weather_events,
            "moon_phase": self.moon_phase,
            "regions_active": last.regions_affected,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Global singleton
# ─────────────────────────────────────────────────────────────────────────────
_SIMULATION: Optional[WorldSimulation] = None

def init_simulation(world_memory: WorldMemory, seed: Optional[int] = None) -> WorldSimulation:
    """Initialize or return the global simulation instance."""
    global _SIMULATION
    if _SIMULATION is None:
        _SIMULATION = WorldSimulation(world_memory, seed)
    return _SIMULATION

def get_simulation() -> Optional[WorldSimulation]:
    """Return the current simulation instance, or None if not initialized."""
    return _SIMULATION

def tick_world(dt: float = TICK_INTERVAL) -> SimulationTick:
    """Convenience: tick the global simulation."""
    sim = get_simulation()
    if sim is None:
        raise RuntimeError("Simulation not initialized; call init_simulation() first")
    return sim.tick(dt)
