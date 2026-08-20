"""
world_memory.py — Procedural world memory, entirely separate from Aurion's personal memory.

The world has its OWN TinyDB (data/world_memory.db). Aurion discovers/experiences
the world through play — she does not pre-know everything.

World reasoning uses Voice 6 (qwen3-reason) via Ollama locally. Zero cost.

Storage layout:
  world_memory.db / regions   — per-region state (ecology, events, discovered %)
  world_memory.db / entities  — NPCs, aliens, objects with individual histories
  world_memory.db / events    — timestamped world events (battles, discoveries, etc.)
  world_memory.db / seeds     — procedural generation seeds per region
"""

from __future__ import annotations

import os
import time
import json
import logging
import hashlib
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger("aurion.world_memory")

try:
    from joi_companion.core.sacred_geometry import (
        PHI_CONJUGATE, TRINITY, HARMONY, UNITY,
    )
except Exception:
    PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9

DATA_DIR = os.environ.get("AURION_DATA_DIR", "data")
WORLD_DB_PATH = os.path.join(DATA_DIR, "world_memory.db")


# ── Region state ───────────────────────────────────────────────────────────────

@dataclass
class RegionState:
    region_id: str
    name: str
    discovered_pct: float = 0.0      # 0.0–1.0 how much Aurion has explored
    ecology_health: float = 1.0      # 0.0 = dead, 1.0 = thriving
    population: int = 0
    active_events: List[str] = field(default_factory=list)
    dominant_alien_species: Optional[str] = None
    last_tick_ts: float = field(default_factory=time.time)
    tick_count: int = 0
    seed: int = 0                    # procedural generation seed
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldEntity:
    entity_id: str
    entity_type: str          # "npc" | "alien" | "object" | "boss"
    region_id: str
    name: str
    level: int = 1
    health: float = 1.0       # 0.0–1.0
    caught: bool = False
    evolution_stage: int = 1  # 1–3
    xp: int = 0
    traits: List[str] = field(default_factory=list)
    memory_snippets: List[str] = field(default_factory=list)
    last_seen_ts: float = field(default_factory=time.time)


@dataclass
class WorldEvent:
    event_id: str
    event_type: str           # "battle" | "discovery" | "ecology" | "alien_spawn" | "tournament"
    region_id: str
    description: str
    participants: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    ts: float = field(default_factory=time.time)
    tick: int = 0


def _make_seed(region_id: str) -> int:
    return int(hashlib.md5(region_id.encode()).hexdigest()[:8], 16)


class WorldMemory:
    """
    The world's own persistent memory — decoupled from Aurion's soul.
    All writes are local TinyDB (no network, no cost).
    """

    def __init__(self, db_path: str = WORLD_DB_PATH):
        self._db = None
        self._regions: Dict[str, TinyDB_table] = {}  # type: ignore
        self._init_db(db_path)

    def _init_db(self, db_path: str):
        try:
            from tinydb import TinyDB
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self._db = TinyDB(db_path)
            self._tbl_regions = self._db.table("regions")
            self._tbl_entities = self._db.table("entities")
            self._tbl_events = self._db.table("events")
            self._tbl_seeds = self._db.table("seeds")
            logger.info("WorldMemory: DB opened at %s", db_path)
        except Exception as e:
            logger.warning("WorldMemory: TinyDB unavailable (%s)", e)
            self._db = None

    # ── Region helpers ─────────────────────────────────────────────────────────

    def get_region(self, region_id: str, name: str = "") -> RegionState:
        if self._db:
            try:
                from tinydb import Query
                doc = self._tbl_regions.get(Query().region_id == region_id)
                if doc:
                    return RegionState(**{k: v for k, v in doc.items()
                                         if k in RegionState.__dataclass_fields__})
            except Exception:
                pass
        return RegionState(region_id=region_id, name=name or region_id,
                           seed=_make_seed(region_id))

    def save_region(self, r: RegionState):
        if not self._db:
            return
        try:
            from tinydb import Query
            self._tbl_regions.upsert(asdict(r), Query().region_id == r.region_id)
        except Exception as e:
            logger.debug("WorldMemory save_region error: %s", e)

    def tick_region(self, region_id: str, delta: Dict[str, Any] = None) -> RegionState:
        """
        Advance the world simulation for one region by one tick.
        Called every UNITY (9) seconds by WorldSimulation.
        """
        r = self.get_region(region_id)
        r.tick_count += 1
        r.last_tick_ts = time.time()

        # Ecology drifts slowly toward balance
        if r.ecology_health < 1.0:
            r.ecology_health = round(min(1.0, r.ecology_health + 0.001), 4)

        if delta:
            for k, v in delta.items():
                if hasattr(r, k):
                    setattr(r, k, v)

        self.save_region(r)
        return r

    def update_discovery(self, region_id: str, amount: float = 0.01):
        """Player explored more of a region."""
        r = self.get_region(region_id)
        r.discovered_pct = round(min(1.0, r.discovered_pct + amount), 4)
        self.save_region(r)

    # ── Entity helpers ─────────────────────────────────────────────────────────

    def get_entity(self, entity_id: str) -> Optional[WorldEntity]:
        if not self._db:
            return None
        try:
            from tinydb import Query
            doc = self._tbl_entities.get(Query().entity_id == entity_id)
            if doc:
                return WorldEntity(**{k: v for k, v in doc.items()
                                      if k in WorldEntity.__dataclass_fields__})
        except Exception:
            pass
        return None

    def save_entity(self, e: WorldEntity):
        if not self._db:
            return
        try:
            from tinydb import Query
            self._tbl_entities.upsert(asdict(e), Query().entity_id == e.entity_id)
        except Exception as e2:
            logger.debug("WorldMemory save_entity error: %s", e2)

    def entities_in_region(self, region_id: str) -> List[WorldEntity]:
        if not self._db:
            return []
        try:
            from tinydb import Query
            docs = self._tbl_entities.search(Query().region_id == region_id)
            return [WorldEntity(**{k: v for k, v in d.items()
                                   if k in WorldEntity.__dataclass_fields__}) for d in docs]
        except Exception:
            return []

    # ── Event log ─────────────────────────────────────────────────────────────

    def log_event(self, event: WorldEvent):
        if not self._db:
            return
        try:
            self._tbl_events.insert(asdict(event))
        except Exception as e:
            logger.debug("WorldMemory log_event error: %s", e)

    def recent_events(self, region_id: str = None, n: int = HARMONY) -> List[WorldEvent]:
        if not self._db:
            return []
        try:
            from tinydb import Query
            if region_id:
                docs = self._tbl_events.search(Query().region_id == region_id)
            else:
                docs = self._tbl_events.all()
            docs = sorted(docs, key=lambda d: d.get("ts", 0), reverse=True)[:n]
            return [WorldEvent(**{k: v for k, v in d.items()
                                  if k in WorldEvent.__dataclass_fields__}) for d in docs]
        except Exception:
            return []

    # ── World summary (for Aurion context) ────────────────────────────────────

    def world_summary(self) -> str:
        """Short narrative world state — injected into Aurion's context sparingly."""
        if not self._db:
            return "[WORLD] Memory offline."
        try:
            regions = [RegionState(**{k: v for k, v in d.items()
                                      if k in RegionState.__dataclass_fields__})
                       for d in self._tbl_regions.all()]
            if not regions:
                return "[WORLD] Unexplored — no regions discovered yet."
            parts = []
            for r in sorted(regions, key=lambda x: x.discovered_pct, reverse=True)[:TRINITY]:
                parts.append(
                    f"{r.name} ({r.discovered_pct*100:.0f}% explored, "
                    f"ecology {r.ecology_health*100:.0f}%)"
                )
            events = self.recent_events(n=TRINITY)
            ev_str = "; ".join(e.description[:60] for e in events) if events else "quiet"
            return f"[WORLD] Active regions: {', '.join(parts)}. Recent: {ev_str}."
        except Exception as e:
            return f"[WORLD] Error: {e}"


# ── Singleton ──────────────────────────────────────────────────────────────────
_world_mem: Optional[WorldMemory] = None

def get_world_memory(db_path: str = WORLD_DB_PATH) -> WorldMemory:
    global _world_mem
    if _world_mem is None:
        _world_mem = WorldMemory(db_path=db_path)
    return _world_mem
