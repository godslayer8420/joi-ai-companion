"""
world_simulation.py — Live world simulation engine for Aurion's game world.

Ticks every UNITY (9) seconds. Each tick:
  1. Advances ecology for each region
  2. Spawns / despawns aliens per region spawn tables
  3. Generates random world events (battles, discoveries, weather)
  4. Updates NPC schedules
  5. Logs events to world_memory.db (separate from Aurion's memory)
  6. Pushes diffs to Unreal via unreal_bridge if connected

All reasoning uses Voice 6 (qwen3-reason / Ollama) — free, local.
World has its own memory — Aurion experiences it, doesn't pre-know it.
"""

from __future__ import annotations

import os
import time
import uuid
import random
import logging
import threading
from typing import Dict, List, Optional, Any

logger = logging.getLogger("aurion.world_sim")

try:
    from joi_companion.core.sacred_geometry import (
        PHI_CONJUGATE, TRINITY, HARMONY, UNITY,
    )
except Exception:
    PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9

TICK_INTERVAL = float(os.environ.get("WORLD_TICK_INTERVAL", UNITY))  # 9s default

# ── Random event templates ─────────────────────────────────────────────────────
_EVENT_TEMPLATES = {
    "alien_spawn": [
        "A {alien} emerged from the shadows in {region}.",
        "Strange energy signatures detected — a {alien} materialized in {region}.",
        "The ecology shifted: a {alien} staked territory in {region}.",
    ],
    "ecology": [
        "The ecosystem in {region} shifted — flora density increased.",
        "A bioluminescent bloom swept through {region}.",
        "Resource nodes regenerated in {region} after the last harvest.",
    ],
    "discovery": [
        "An unexplored passage was revealed in {region}.",
        "Ancient ruins surfaced in {region} after a tremor.",
        "A hidden cache of rare materials appeared in {region}.",
    ],
    "weather": [
        "Acid rain rolled into {region} — visibility low.",
        "A void storm crackled through {region}, empowering alien spawns.",
        "Calm descended over {region}; NPCs moved more freely.",
    ],
}


def _random_event(event_type: str, region_id: str, alien: str = "unknown alien") -> str:
    templates = _EVENT_TEMPLATES.get(event_type, ["{event_type} event in {region}."])
    t = random.choice(templates)
    return t.format(region=region_id.replace("_", " ").title(), alien=alien, event_type=event_type)


class WorldSimulation:
    """
    Runs the world tick loop in a background thread.
    Interacts with WorldMemory (world_memory.db) and optionally with UnrealBridge.
    """

    def __init__(
        self,
        tick_interval: float = TICK_INTERVAL,
        data_dir: str = "data",
        unreal_bridge=None,
    ):
        self._interval = tick_interval
        self._data_dir = data_dir
        self._bridge = unreal_bridge
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_count = 0
        self._world_mem = None
        self._regions_cache: Dict[str, Any] = {}
        self._init_world()

    def _init_world(self):
        try:
            from joi_companion.core.world_memory import get_world_memory
            self._world_mem = get_world_memory()
        except Exception as e:
            logger.warning("WorldSim: WorldMemory unavailable (%s)", e)

        try:
            from joi_companion.aurion_runtime.world_regions import region_catalog
            self._regions_cache = region_catalog()
            logger.info("WorldSim: %d regions loaded.", len(self._regions_cache))
        except Exception as e:
            logger.warning("WorldSim: region_catalog unavailable (%s)", e)

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="WorldSim")
        self._thread.start()
        logger.info("WorldSim: started (tick=%.1fs)", self._interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._interval + 1)
        logger.info("WorldSim: stopped after %d ticks.", self._tick_count)

    def force_tick(self):
        """Manually trigger one tick (useful for testing)."""
        self._tick()

    def get_state(self) -> Dict[str, Any]:
        """Current snapshot of the world — sent to Unreal on demand."""
        if not self._world_mem:
            return {"running": self._running, "ticks": self._tick_count}
        try:
            from joi_companion.core.world_memory import RegionState
            regions_out = {}
            for rid in self._regions_cache:
                r = self._world_mem.get_region(rid, self._regions_cache[rid]["name"])
                regions_out[rid] = {
                    "name": r.name,
                    "discovered_pct": r.discovered_pct,
                    "ecology_health": r.ecology_health,
                    "population": r.population,
                    "active_events": r.active_events,
                    "tick_count": r.tick_count,
                }
            events = self._world_mem.recent_events(n=HARMONY)
            return {
                "running": self._running,
                "ticks": self._tick_count,
                "regions": regions_out,
                "recent_events": [
                    {"type": e.event_type, "region": e.region_id, "desc": e.description}
                    for e in events
                ],
            }
        except Exception as e:
            logger.debug("WorldSim get_state error: %s", e)
            return {"running": self._running, "ticks": self._tick_count, "error": str(e)}

    # ── Tick loop ──────────────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error("WorldSim tick error: %s", e)
            time.sleep(self._interval)

    def _tick(self):
        self._tick_count += 1
        t = self._tick_count

        for rid, rdef in self._regions_cache.items():
            try:
                self._tick_region(rid, rdef, t)
            except Exception as e:
                logger.debug("WorldSim region tick error %s: %s", rid, e)

        # Every HARMONY (6) ticks push world state to Unreal
        if t % HARMONY == 0 and self._bridge:
            self._push_to_unreal()

    def _tick_region(self, rid: str, rdef: Dict[str, Any], tick: int):
        if not self._world_mem:
            return

        from joi_companion.core.world_memory import WorldEvent

        # Advance region state
        r = self._world_mem.tick_region(rid)

        # Random events — probability scales with tick (more active over time)
        roll = random.random()

        # Alien spawn event — 15% chance per tick
        if roll < 0.15 and rdef.get("alien_spawns"):
            alien = random.choice(rdef["alien_spawns"])
            desc = _random_event("alien_spawn", rid, alien)
            r.active_events = ([desc] + r.active_events)[:TRINITY]
            self._world_mem.save_region(r)
            self._world_mem.log_event(WorldEvent(
                event_id=str(uuid.uuid4())[:8],
                event_type="alien_spawn",
                region_id=rid,
                description=desc,
                tick=tick,
            ))

        # Ecology event — 8% chance
        elif roll < 0.23:
            desc = _random_event("ecology", rid)
            self._world_mem.log_event(WorldEvent(
                event_id=str(uuid.uuid4())[:8],
                event_type="ecology",
                region_id=rid,
                description=desc,
                tick=tick,
            ))

        # Discovery event — 5% chance
        elif roll < 0.28:
            desc = _random_event("discovery", rid)
            self._world_mem.log_event(WorldEvent(
                event_id=str(uuid.uuid4())[:8],
                event_type="discovery",
                region_id=rid,
                description=desc,
                tick=tick,
            ))

        # Weather — 5% chance
        elif roll < 0.33:
            desc = _random_event("weather", rid)
            self._world_mem.log_event(WorldEvent(
                event_id=str(uuid.uuid4())[:8],
                event_type="weather",
                region_id=rid,
                description=desc,
                tick=tick,
            ))

    def _push_to_unreal(self):
        try:
            state = self.get_state()
            self._bridge.broadcast({"type": "WORLD_STATE_UPDATE", "payload": state})
        except Exception as e:
            logger.debug("WorldSim Unreal push error: %s", e)


# ── Flask API endpoint helper ──────────────────────────────────────────────────
def resolve_world_simulation(*args, **kwargs) -> Dict[str, Any]:
    """Legacy shim — returns world state from running simulation or empty."""
    global _sim
    if _sim and _sim._running:
        return _sim.get_state()
    return {"running": False, "ticks": 0, "regions": {}}


# ── Singleton ──────────────────────────────────────────────────────────────────
_sim: Optional[WorldSimulation] = None

def get_world_simulation(**kwargs) -> WorldSimulation:
    global _sim
    if _sim is None:
        _sim = WorldSimulation(**kwargs)
    return _sim

