"""
battle_arena.py — Fight Arena system (Basement Layer 3).

5 tournament tiers (Bronze → Silver → Gold → Platinum → Void).
Bracket-style tournaments, spectator system, alien vs alien battles.
All state in world_memory.db. Zero API cost.
"""

from __future__ import annotations

import uuid
import time
import random
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger("aurion.arena")

try:
    from joi_companion.core.sacred_geometry import PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY
except Exception:
    PHI = 1.6180339887; PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9

TIERS = ["Bronze", "Silver", "Gold", "Platinum", "Void"]
TIER_LEVEL_REQ = [1, 15, 30, 50, 80]  # min player level per tier
TIER_PRIZE_MULTIPLIER = [1, 3, 6, 9, 27]


@dataclass
class ArenaMatch:
    match_id: str
    tier: str
    fighter_a: str   # catch_id or NPC name
    fighter_b: str
    winner: Optional[str] = None
    round_log: List[str] = field(default_factory=list)
    spectator_count: int = 0
    prize_credits: int = 0
    ts: float = field(default_factory=time.time)


@dataclass
class Tournament:
    tournament_id: str
    tier: str
    participants: List[str] = field(default_factory=list)  # catch_ids
    bracket: List[List[str]] = field(default_factory=list)
    current_round: int = 0
    champion: Optional[str] = None
    prize_credits: int = 0
    ts: float = field(default_factory=time.time)
    complete: bool = False


class BattleArena:
    """Manages Fight Arena matches and tournaments."""

    def __init__(self, data_dir: str = "data"):
        self._alien_system = None
        self._db = None
        self._init_db(data_dir)
        self._init_deps()

    def _init_db(self, data_dir: str):
        try:
            import os
            from tinydb import TinyDB
            os.makedirs(data_dir, exist_ok=True)
            self._db = TinyDB(os.path.join(data_dir, "world_memory.db"))
            self._tbl_matches = self._db.table("arena_matches")
            self._tbl_tournaments = self._db.table("arena_tournaments")
        except Exception as e:
            logger.warning("BattleArena: TinyDB unavailable (%s)", e)

    def _init_deps(self):
        try:
            from joi_companion.game.alien_system import get_alien_system
            self._alien_system = get_alien_system()
        except Exception:
            pass

    # ── Quick match ───────────────────────────────────────────────────────────

    def quick_match(
        self,
        player_catch_id: str,
        tier_name: str = "Bronze",
        session_id: str = "",
    ) -> Dict[str, Any]:
        """Challenge an arena NPC with your alien. Returns full result."""
        tier_idx = TIERS.index(tier_name) if tier_name in TIERS else 0
        base_credits = 50 * TIER_PRIZE_MULTIPLIER[tier_idx]

        if not self._alien_system:
            return {"error": "Alien system not available."}

        player_alien = self._alien_system._load_alien(player_catch_id)
        if not player_alien:
            return {"error": f"Alien {player_catch_id} not found."}

        # Generate NPC opponent scaled to tier
        npc_level = TIER_LEVEL_REQ[tier_idx] + random.randint(0, 10)
        npc_species = random.choice(list(self._alien_system.SPECIES_CATALOGUE
                                         if hasattr(self._alien_system, 'SPECIES_CATALOGUE')
                                         else ["glitch_sprite"]))
        from joi_companion.game.alien_system import SPECIES_CATALOGUE, _generate_stats, CaughtAlien
        npc_spec = SPECIES_CATALOGUE.get(npc_species, {})
        npc_stats = _generate_stats(npc_species, npc_level)
        npc_alien = CaughtAlien(
            catch_id=f"npc_{uuid.uuid4().hex[:6]}",
            species=npc_species,
            nickname=f"Arena {npc_species.replace('_',' ').title()}",
            level=npc_level,
            owner_session="arena",
            **npc_stats,
            hp=npc_stats["max_hp"],
        )
        self._alien_system._save_alien(npc_alien)

        result = self._alien_system.battle(player_catch_id, npc_alien.catch_id, rounds=TRINITY)
        won = result.get("winner") == player_alien.nickname

        prize = base_credits if won else base_credits // TRINITY
        spectators = random.randint(10, 500) * TIER_PRIZE_MULTIPLIER[tier_idx]

        match = ArenaMatch(
            match_id=str(uuid.uuid4())[:8],
            tier=tier_name,
            fighter_a=player_catch_id,
            fighter_b=npc_alien.catch_id,
            winner=player_catch_id if won else npc_alien.catch_id,
            round_log=result.get("log", []),
            spectator_count=spectators,
            prize_credits=prize,
        )
        if self._db:
            try:
                self._tbl_matches.insert(asdict(match))
            except Exception:
                pass

        return {
            "result": "Victory! 🏆" if won else "Defeat 💀",
            "prize_credits": prize,
            "spectators": spectators,
            "battle_log": result,
            "match_id": match.match_id,
        }

    # ── Tournament ────────────────────────────────────────────────────────────

    def create_tournament(
        self, tier_name: str, participant_catch_ids: List[str]
    ) -> Dict[str, Any]:
        """Create and run a bracket tournament. Min 4 participants."""
        if len(participant_catch_ids) < 4:
            return {"error": "Need at least 4 aliens to start a tournament."}

        tier_idx = TIERS.index(tier_name) if tier_name in TIERS else 0
        prize = 500 * TIER_PRIZE_MULTIPLIER[tier_idx]

        tourney = Tournament(
            tournament_id=str(uuid.uuid4())[:8],
            tier=tier_name,
            participants=list(participant_catch_ids),
            prize_credits=prize,
        )

        # Build bracket
        random.shuffle(tourney.participants)
        current_round = tourney.participants[:]
        tourney.bracket = [current_round[:]]
        all_logs: List[str] = []

        while len(current_round) > 1:
            next_round: List[str] = []
            for i in range(0, len(current_round) - 1, 2):
                a, b = current_round[i], current_round[i + 1]
                if not self._alien_system:
                    break
                res = self._alien_system.battle(a, b, rounds=TRINITY)
                winner_name = res.get("winner")
                a_alien = self._alien_system._load_alien(a)
                b_alien = self._alien_system._load_alien(b)
                if a_alien and b_alien:
                    winner_id = a if winner_name == a_alien.nickname else b
                else:
                    winner_id = a
                next_round.append(winner_id)
                all_logs.extend(res.get("log", []))
            if len(current_round) % 2 == 1:
                next_round.append(current_round[-1])  # bye
            current_round = next_round
            tourney.bracket.append(current_round[:])

        tourney.champion = current_round[0] if current_round else None
        tourney.complete = True

        if self._db:
            try:
                self._tbl_tournaments.insert(asdict(tourney))
            except Exception:
                pass

        champion_alien = self._alien_system._load_alien(tourney.champion) if self._alien_system and tourney.champion else None
        return {
            "tournament_id": tourney.tournament_id,
            "tier": tier_name,
            "champion": champion_alien.nickname if champion_alien else tourney.champion,
            "prize_credits": prize,
            "rounds_played": len(tourney.bracket) - 1,
            "battle_log": all_logs[:30],  # truncate for readability
        }

    def leaderboard(self, tier_name: str = None, top: int = UNITY) -> List[Dict]:
        """Return top fighters by wins."""
        if not self._db:
            return []
        try:
            from tinydb import Query
            docs = self._tbl_matches.all()
            wins: Dict[str, int] = {}
            for d in docs:
                if tier_name and d.get("tier") != tier_name:
                    continue
                w = d.get("winner")
                if w:
                    wins[w] = wins.get(w, 0) + 1
            sorted_wins = sorted(wins.items(), key=lambda x: x[1], reverse=True)[:top]
            return [{"catch_id": cid, "wins": w} for cid, w in sorted_wins]
        except Exception:
            return []


# ── Singleton ──────────────────────────────────────────────────────────────────
_arena: Optional[BattleArena] = None

def get_battle_arena(data_dir: str = "data") -> BattleArena:
    global _arena
    if _arena is None:
        _arena = BattleArena(data_dir=data_dir)
    return _arena
