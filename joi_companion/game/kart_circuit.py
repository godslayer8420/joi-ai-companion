"""
kart_circuit.py — Kart racing system (Basement Layer 4).

9 tracks, alien kart riders, ghost replay system, drift boost zones.
All state in world_memory.db. Zero API cost.
Tracks have unique themes tied to world regions.
"""

from __future__ import annotations

import uuid
import time
import random
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger("aurion.kart")

try:
    from joi_companion.core.sacred_geometry import PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY
except Exception:
    PHI = 1.6180339887; PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9

# ── 9 tracks ──────────────────────────────────────────────────────────────────
TRACKS: Dict[str, Dict[str, Any]] = {
    "neon_highway":       {"name": "Neon Highway",        "laps": 3, "difficulty": 1, "theme": "cyberpunk", "drift_zones": 6, "shortcut": True},
    "crystal_caverns":    {"name": "Crystal Caverns",     "laps": 3, "difficulty": 2, "theme": "underground","drift_zones": 4, "shortcut": True},
    "void_circuit":       {"name": "Void Circuit",        "laps": 2, "difficulty": 7, "theme": "dimensional","drift_zones": 9, "shortcut": False},
    "festival_loop":      {"name": "Festival Loop",       "laps": 4, "difficulty": 1, "theme": "festive",   "drift_zones": 3, "shortcut": False},
    "alien_preserve_run": {"name": "Alien Preserve Run",  "laps": 3, "difficulty": 4, "theme": "wilderness","drift_zones": 5, "shortcut": True},
    "deep_wild_rush":     {"name": "Deep Wild Rush",      "laps": 2, "difficulty": 6, "theme": "jungle",    "drift_zones": 6, "shortcut": True},
    "smog_street":        {"name": "Smog Street",         "laps": 3, "difficulty": 3, "theme": "urban",     "drift_zones": 7, "shortcut": True},
    "arena_blitz":        {"name": "Arena Blitz",         "laps": 1, "difficulty": 8, "theme": "combat",    "drift_zones": 9, "shortcut": False},
    "grand_prix_omega":   {"name": "Grand Prix Omega",    "laps": 5, "difficulty": 9, "theme": "ultimate",  "drift_zones": 9, "shortcut": True},
}

# Alien kart riders (each has unique speed/handling/boost stats)
ALIEN_RACERS: Dict[str, Dict[str, int]] = {
    "speed_demon":    {"speed": 95, "handling": 60, "boost": 90, "weight": 40},
    "neon_leech":     {"speed": 70, "handling": 85, "boost": 75, "weight": 35},
    "glitch_sprite":  {"speed": 80, "handling": 90, "boost": 65, "weight": 25},
    "turbo_imp":      {"speed": 85, "handling": 70, "boost": 80, "weight": 30},
    "plasma_mantis":  {"speed": 88, "handling": 65, "boost": 85, "weight": 50},
    "void_strider":   {"speed": 78, "handling": 88, "boost": 70, "weight": 35},
    "crystal_wyvern": {"speed": 65, "handling": 75, "boost": 95, "weight": 80},
    "echo_serpent":   {"speed": 82, "handling": 80, "boost": 72, "weight": 40},
    "festival_imp":   {"speed": 72, "handling": 92, "boost": 68, "weight": 28},
}


@dataclass
class RaceResult:
    race_id: str
    track_id: str
    player_position: int
    total_racers: int
    lap_times: List[float]         # seconds per lap
    best_lap: float
    total_time: float
    prize_credits: int
    ghost_saved: bool
    ts: float = field(default_factory=time.time)
    session_id: str = ""


@dataclass
class GhostRecord:
    ghost_id: str
    track_id: str
    session_id: str
    total_time: float
    lap_times: List[float]
    ts: float = field(default_factory=time.time)


class KartCircuit:
    """Manages kart races, ghost records, and lap times."""

    def __init__(self, data_dir: str = "data"):
        self._db = None
        self._init_db(data_dir)

    def _init_db(self, data_dir: str):
        try:
            import os
            from tinydb import TinyDB
            os.makedirs(data_dir, exist_ok=True)
            self._db = TinyDB(os.path.join(data_dir, "world_memory.db"))
            self._tbl_races = self._db.table("kart_races")
            self._tbl_ghosts = self._db.table("kart_ghosts")
        except Exception as e:
            logger.warning("KartCircuit: TinyDB unavailable (%s)", e)

    # ── Race simulation ────────────────────────────────────────────────────────

    def race(
        self,
        session_id: str,
        track_id: str,
        player_speed: int = 70,
        player_handling: int = 70,
        player_boost: int = 70,
        ai_count: int = HARMONY,
    ) -> Dict[str, Any]:
        """
        Simulate a kart race. Returns placement, lap times, prize.
        Player stats (speed/handling/boost) fed from player's kart upgrades.
        """
        track = TRACKS.get(track_id)
        if not track:
            return {"error": f"Unknown track: {track_id}. Available: {list(TRACKS.keys())}"}

        laps = track["laps"]
        difficulty = track["difficulty"]
        drift_bonus = track["drift_zones"] * 0.5  # seconds saved per drift zone mastered

        # Simulate player lap times
        base_lap = 60.0 + difficulty * 5.0  # base seconds per lap
        player_laps: List[float] = []
        for i in range(laps):
            # Lower times = better; speed reduces, handling smooths, boost cuts
            time_s = (
                base_lap
                - (player_speed / 100) * 12
                - (player_handling / 100) * 8
                - (player_boost / 100) * 5
                + random.uniform(-2.0, 2.0)
            )
            # Drift zone bonus (random partial capture)
            drift_capture = random.uniform(0.3, 1.0) * (player_handling / 100)
            time_s -= drift_bonus * drift_capture
            player_laps.append(max(15.0, round(time_s, 2)))

        player_total = round(sum(player_laps), 2)
        player_best  = min(player_laps)

        # Simulate AI opponents
        ai_times: List[float] = []
        ai_racers = random.sample(list(ALIEN_RACERS.keys()), min(ai_count, len(ALIEN_RACERS)))
        for ai_species in ai_racers:
            stats = ALIEN_RACERS[ai_species]
            ai_lap = (
                base_lap
                - (stats["speed"] / 100) * 12
                - (stats["handling"] / 100) * 8
                - (stats["boost"] / 100) * 5
                + random.uniform(-3.0, 3.0)
            )
            ai_total = max(15.0 * laps, round(ai_lap * laps, 2))
            ai_times.append(ai_total)

        # Placement
        all_times = sorted(ai_times)
        position = 1
        for t in all_times:
            if t < player_total:
                position += 1

        # Prize — 1st pays most, scales with difficulty
        base_prize = 100 * difficulty
        prize_table = {1: base_prize * UNITY, 2: base_prize * TRINITY,
                       3: base_prize * 2, 4: base_prize}
        prize = prize_table.get(position, base_prize // 2)

        # Save ghost if personal best
        ghost_saved = self._maybe_save_ghost(session_id, track_id, player_total, player_laps)

        result = RaceResult(
            race_id=str(uuid.uuid4())[:8],
            track_id=track_id,
            player_position=position,
            total_racers=len(ai_racers) + 1,
            lap_times=player_laps,
            best_lap=player_best,
            total_time=player_total,
            prize_credits=prize,
            ghost_saved=ghost_saved,
            session_id=session_id,
        )
        if self._db:
            try:
                self._tbl_races.insert(asdict(result))
            except Exception:
                pass

        pos_label = {1: "🥇 1st", 2: "🥈 2nd", 3: "🥉 3rd"}.get(position, f"{position}th")
        return {
            "position": pos_label,
            "total_time": f"{player_total:.2f}s",
            "best_lap": f"{player_best:.2f}s",
            "lap_times": [f"{t:.2f}s" for t in player_laps],
            "prize_credits": prize,
            "ghost_saved": ghost_saved,
            "track": track["name"],
            "racers": len(ai_racers) + 1,
        }

    def _maybe_save_ghost(
        self, session_id: str, track_id: str, total_time: float, lap_times: List[float]
    ) -> bool:
        """Save ghost if it beats the player's personal best."""
        best = self.get_personal_best(session_id, track_id)
        if best is None or total_time < best:
            ghost = GhostRecord(
                ghost_id=str(uuid.uuid4())[:8],
                track_id=track_id,
                session_id=session_id,
                total_time=total_time,
                lap_times=lap_times,
            )
            if self._db:
                try:
                    from tinydb import Query
                    self._tbl_ghosts.upsert(asdict(ghost),
                                            (Query().track_id == track_id) &
                                            (Query().session_id == session_id))
                except Exception:
                    pass
            return True
        return False

    def get_personal_best(self, session_id: str, track_id: str) -> Optional[float]:
        if not self._db:
            return None
        try:
            from tinydb import Query
            doc = self._tbl_ghosts.get(
                (Query().track_id == track_id) & (Query().session_id == session_id)
            )
            return doc["total_time"] if doc else None
        except Exception:
            return None

    def global_leaderboard(self, track_id: str, top: int = UNITY) -> List[Dict]:
        """Top times for a track across all players."""
        if not self._db:
            return []
        try:
            from tinydb import Query
            docs = self._tbl_ghosts.search(Query().track_id == track_id)
            docs = sorted(docs, key=lambda d: d.get("total_time", 9999))[:top]
            return [
                {"position": i + 1, "session_id": d["session_id"][:8],
                 "time": f"{d['total_time']:.2f}s"}
                for i, d in enumerate(docs)
            ]
        except Exception:
            return []

    def track_list(self) -> List[Dict[str, Any]]:
        return [{"id": k, **v} for k, v in TRACKS.items()]


# ── Singleton ──────────────────────────────────────────────────────────────────
_circuit: Optional[KartCircuit] = None

def get_kart_circuit(data_dir: str = "data") -> KartCircuit:
    global _circuit
    if _circuit is None:
        _circuit = KartCircuit(data_dir=data_dir)
    return _circuit
