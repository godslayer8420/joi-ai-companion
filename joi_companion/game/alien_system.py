"""
alien_system.py — Alien catch, contain, battle, and evolution for Aurion's world.

27 alien species across 3 tiers (3×3×3 = TRINITY³ = 27).
9 combat stats on the UNITY scale.
3 evolution stages (TRINITY gates: level 3, 6, 9).

All data stored in world_memory.db (NOT Aurion's personal memory).
Battle uses local logic — zero API calls, zero cost.
Unreal mesh swap triggered via unreal_bridge on evolution.
"""

from __future__ import annotations

import os
import uuid
import time
import random
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger("aurion.alien")

try:
    from joi_companion.core.sacred_geometry import (
        PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY,
    )
except Exception:
    PHI = 1.6180339887
    PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9

# ── 27 species catalogue (3 tiers × 9 per tier) ───────────────────────────────
# Format: name → (tier, element, base_power, catch_difficulty, description)
SPECIES_CATALOGUE: Dict[str, Dict[str, Any]] = {
    # Tier 1 — Common (levels 1–15)
    "glitch_sprite":     {"tier": 1, "element": "electric", "base_power": 30,  "catch_rate": 0.7, "desc": "Small digital entity that corrupts tech nearby."},
    "smog_crawler":      {"tier": 1, "element": "poison",   "base_power": 28,  "catch_rate": 0.75,"desc": "Toxic crawling lifeform born from polluted air."},
    "neon_leech":        {"tier": 1, "element": "energy",   "base_power": 32,  "catch_rate": 0.65,"desc": "Drains power from neon signs and tech."},
    "confetti_wisp":     {"tier": 1, "element": "light",    "base_power": 22,  "catch_rate": 0.85,"desc": "Festive, harmless spirit that spreads joy."},
    "festival_imp":      {"tier": 1, "element": "chaos",    "base_power": 35,  "catch_rate": 0.6, "desc": "Mischievous trickster from the festival grounds."},
    "cavern_shade":      {"tier": 1, "element": "dark",     "base_power": 33,  "catch_rate": 0.65,"desc": "Shadow creature lurking in cave systems."},
    "crystal_grub":      {"tier": 1, "element": "earth",    "base_power": 40,  "catch_rate": 0.55,"desc": "Armored grub that eats mineral deposits."},
    "speed_demon":       {"tier": 1, "element": "wind",     "base_power": 38,  "catch_rate": 0.6, "desc": "Lightning-fast sprinter, impossible to outrun on foot."},
    "turbo_imp":         {"tier": 1, "element": "fire",     "base_power": 36,  "catch_rate": 0.6, "desc": "Obsessed with karts and race tracks."},

    # Tier 2 — Uncommon (levels 15–40)
    "data_wraith":       {"tier": 2, "element": "electric", "base_power": 65,  "catch_rate": 0.45,"desc": "Digital ghost that haunts corrupted networks."},
    "neon_mimic":        {"tier": 2, "element": "psychic",  "base_power": 70,  "catch_rate": 0.4, "desc": "Shapeshifter that copies the appearance of tech."},
    "root_titan":        {"tier": 2, "element": "earth",    "base_power": 80,  "catch_rate": 0.35,"desc": "Ancient tree-beast, slow but nearly indestructible."},
    "plasma_mantis":     {"tier": 2, "element": "fire",     "base_power": 75,  "catch_rate": 0.4, "desc": "Superheated insectoid predator with blade arms."},
    "echo_serpent":      {"tier": 2, "element": "sound",    "base_power": 68,  "catch_rate": 0.45,"desc": "Sonic vibrations shatter glass when it screams."},
    "spore_wraith":      {"tier": 2, "element": "poison",   "base_power": 72,  "catch_rate": 0.4, "desc": "Fungal phantom that releases paralytic spores."},
    "ruin_stalker":      {"tier": 2, "element": "dark",     "base_power": 78,  "catch_rate": 0.38,"desc": "Camouflaged ambush predator in ancient ruins."},
    "void_strider":      {"tier": 2, "element": "void",     "base_power": 85,  "catch_rate": 0.35,"desc": "Partially dimensional — phases through solid walls."},
    "circuit_beast":     {"tier": 2, "element": "electric", "base_power": 73,  "catch_rate": 0.42,"desc": "Cybernetically enhanced predator, fused with scrap."},

    # Tier 3 — Rare / Alpha (levels 40+)
    "alpha_luminar":     {"tier": 3, "element": "light",    "base_power": 130, "catch_rate": 0.15,"desc": "Radiant apex predator of the Alien Preserve."},
    "crystal_wyvern":    {"tier": 3, "element": "earth",    "base_power": 140, "catch_rate": 0.12,"desc": "Dragon-class crystalline flying beast."},
    "gravity_bear":      {"tier": 3, "element": "gravity",  "base_power": 145, "catch_rate": 0.1, "desc": "Bends gravity around itself — standing near it is dangerous."},
    "void_wraith":       {"tier": 3, "element": "void",     "base_power": 150, "catch_rate": 0.1, "desc": "Near-incorporeal entity from dimensional rifts."},
    "phase_stalker":     {"tier": 3, "element": "void",     "base_power": 155, "catch_rate": 0.08,"desc": "Apex predator that hunts across multiple dimensions."},
    "rift_colossus":     {"tier": 3, "element": "void",     "base_power": 200, "catch_rate": 0.05,"desc": "Boss-tier dimensional titan. Extremely dangerous."},
    "ancient_guardian":  {"tier": 3, "element": "earth",    "base_power": 180, "catch_rate": 0.07,"desc": "Primordial protector of the Deep Wild ruins."},
    "moss_colossus":     {"tier": 3, "element": "earth",    "base_power": 160, "catch_rate": 0.1, "desc": "Ancient living mountain covered in primordial moss."},
    "jungle_titan":      {"tier": 3, "element": "nature",   "base_power": 170, "catch_rate": 0.09,"desc": "Apex predator of the primordial jungle."},
}

# Evolution chain — species → (stage2_name, stage3_name, level_thresholds)
EVOLUTION_CHAINS: Dict[str, Dict] = {
    "glitch_sprite":  {"s2": "glitch_phantom",    "s3": "glitch_god",      "lvl": (TRINITY, HARMONY)},
    "smog_crawler":   {"s2": "smog_wraith",        "s3": "smog_colossus",   "lvl": (TRINITY, HARMONY)},
    "neon_leech":     {"s2": "neon_vampire",       "s3": "neon_overlord",   "lvl": (TRINITY, HARMONY)},
    "crystal_grub":   {"s2": "crystal_beetle",     "s3": "crystal_dragon",  "lvl": (TRINITY, UNITY)},
    "data_wraith":    {"s2": "data_spectre",        "s3": "data_lich",       "lvl": (HARMONY, UNITY)},
    "void_strider":   {"s2": "void_hunter",         "s3": "void_harbinger",  "lvl": (HARMONY, UNITY)},
    "plasma_mantis":  {"s2": "plasma_warlord",      "s3": "plasma_god",      "lvl": (HARMONY, UNITY)},
    "alpha_luminar":  {"s2": "luminar_sovereign",   "s3": "luminar_deity",   "lvl": (UNITY, UNITY*3)},
}


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class CaughtAlien:
    catch_id: str
    species: str
    nickname: str
    level: int = 1
    xp: int = 0
    evolution_stage: int = 1
    hp: int = 100
    max_hp: int = 100
    # 9 stats (UNITY)
    power: int = 10
    defense: int = 10
    speed: int = 10
    stamina: int = 10
    energy: int = 10
    accuracy: int = 10
    evasion: int = 10
    luck: int = 10
    will: int = 10
    # Meta
    owner_session: str = ""
    caught_at_region: str = ""
    caught_ts: float = field(default_factory=time.time)
    battles_won: int = 0
    battles_total: int = 0
    traits: List[str] = field(default_factory=list)


@dataclass
class ContainmentPod:
    pod_id: str
    owner_session: str
    capacity: int = TRINITY       # starts at 3, upgrades to 6 → 9
    slots: List[str] = field(default_factory=list)  # list of catch_ids


# ── Stat generator ─────────────────────────────────────────────────────────────

def _generate_stats(species: str, level: int) -> Dict[str, int]:
    spec = SPECIES_CATALOGUE.get(species, {})
    base = spec.get("base_power", 50)
    seed = int(hashlib.md5(species.encode()).hexdigest()[:4], 16) if False else hash(species) % 100
    rng = random.Random(seed + level)
    scale = 1 + (level - 1) * 0.15
    return {
        "power":    max(5, int(base * scale * rng.uniform(0.8, 1.2))),
        "defense":  max(5, int(base * 0.7 * scale * rng.uniform(0.8, 1.2))),
        "speed":    max(5, int(base * 0.9 * scale * rng.uniform(0.8, 1.2))),
        "stamina":  max(5, int(base * 0.8 * scale * rng.uniform(0.8, 1.2))),
        "energy":   max(5, int(base * 0.75 * scale * rng.uniform(0.8, 1.2))),
        "accuracy": max(5, int(base * 0.85 * scale * rng.uniform(0.8, 1.2))),
        "evasion":  max(5, int(base * 0.6 * scale * rng.uniform(0.8, 1.2))),
        "luck":     max(5, int(base * 0.5 * scale * rng.uniform(0.7, 1.3))),
        "will":     max(5, int(base * 0.65 * scale * rng.uniform(0.8, 1.2))),
        "max_hp":   max(20, int(base * 2.5 * scale)),
    }


# ── AlienSystem ────────────────────────────────────────────────────────────────

class AlienSystem:
    """Manages catching, containment, battle, and evolution for all aliens."""

    def __init__(self, data_dir: str = "data"):
        self._pods: Dict[str, ContainmentPod] = {}
        self._aliens: Dict[str, CaughtAlien] = {}
        self._world_mem = None
        self._bridge = None
        self._init_db(data_dir)
        self._init_deps()

    def _init_db(self, data_dir: str):
        try:
            from tinydb import TinyDB
            os.makedirs(data_dir, exist_ok=True)
            self._db = TinyDB(os.path.join(data_dir, "world_memory.db"))
            self._tbl_aliens = self._db.table("caught_aliens")
            self._tbl_pods = self._db.table("containment_pods")
        except Exception as e:
            logger.warning("AlienSystem: TinyDB unavailable (%s)", e)
            self._db = None

    def _init_deps(self):
        try:
            from joi_companion.core.world_memory import get_world_memory
            self._world_mem = get_world_memory()
        except Exception:
            pass
        try:
            from joi_companion.core.unreal_bridge import get_bridge
            self._bridge = get_bridge()
        except Exception:
            pass

    # ── Catch ──────────────────────────────────────────────────────────────────

    def attempt_catch(
        self,
        session_id: str,
        species: str,
        alien_level: int,
        player_level: int,
        pod_upgrade: int = 0,
    ) -> Dict[str, Any]:
        """
        Attempt to catch a wild alien.
        Returns {"success": bool, "alien": CaughtAlien|None, "message": str}
        """
        spec = SPECIES_CATALOGUE.get(species)
        if not spec:
            return {"success": False, "alien": None, "message": f"Unknown species: {species}"}

        pod = self._get_or_create_pod(session_id, pod_upgrade)
        if len(pod.slots) >= pod.capacity:
            return {"success": False, "alien": None,
                    "message": f"Containment pod full ({pod.capacity} slots). Upgrade or release an alien."}

        # Catch probability: base_rate * (player_level / alien_level) * PHI_CONJUGATE
        catch_rate = spec["catch_rate"]
        level_bonus = (player_level / max(1, alien_level)) * PHI_CONJUGATE
        final_rate = min(0.95, catch_rate * (1 + level_bonus))
        roll = random.random()

        if roll > final_rate:
            return {
                "success": False, "alien": None,
                "message": f"The {species} broke free! (roll={roll:.2f} > rate={final_rate:.2f})"
            }

        # Create caught alien
        stats = _generate_stats(species, alien_level)
        alien = CaughtAlien(
            catch_id=str(uuid.uuid4())[:8],
            species=species,
            nickname=species.replace("_", " ").title(),
            level=alien_level,
            evolution_stage=1,
            hp=stats["max_hp"],
            max_hp=stats["max_hp"],
            owner_session=session_id,
            caught_at_region="unknown",
            **{k: v for k, v in stats.items() if k != "max_hp"},
        )
        self._save_alien(alien)
        pod.slots.append(alien.catch_id)
        self._save_pod(pod)

        # Log world event
        if self._world_mem:
            from joi_companion.core.world_memory import WorldEvent
            self._world_mem.log_event(WorldEvent(
                event_id=str(uuid.uuid4())[:8],
                event_type="catch",
                region_id="unknown",
                description=f"{species} was caught by session {session_id[:8]}.",
                participants=[alien.catch_id],
            ))

        return {
            "success": True,
            "alien": asdict(alien),
            "message": f"{alien.nickname} was caught! (rate={final_rate:.0%})"
        }

    # ── Containment ────────────────────────────────────────────────────────────

    def _get_or_create_pod(self, session_id: str, upgrade: int = 0) -> ContainmentPod:
        if session_id in self._pods:
            return self._pods[session_id]
        if self._db:
            try:
                from tinydb import Query
                doc = self._tbl_pods.get(Query().owner_session == session_id)
                if doc:
                    p = ContainmentPod(**{k: v for k, v in doc.items()
                                          if k in ContainmentPod.__dataclass_fields__})
                    self._pods[session_id] = p
                    return p
            except Exception:
                pass
        # New pod
        capacity = TRINITY + upgrade * TRINITY
        p = ContainmentPod(
            pod_id=str(uuid.uuid4())[:8],
            owner_session=session_id,
            capacity=capacity,
        )
        self._pods[session_id] = p
        self._save_pod(p)
        return p

    def get_pod(self, session_id: str) -> Dict[str, Any]:
        pod = self._get_or_create_pod(session_id)
        aliens = [asdict(self._load_alien(cid)) for cid in pod.slots
                  if self._load_alien(cid)]
        return {"pod_id": pod.pod_id, "capacity": pod.capacity,
                "slots": len(pod.slots), "aliens": aliens}

    def release_alien(self, session_id: str, catch_id: str) -> str:
        pod = self._get_or_create_pod(session_id)
        if catch_id in pod.slots:
            pod.slots.remove(catch_id)
            self._save_pod(pod)
            return f"Alien {catch_id} released back to the wild."
        return "Alien not found in your pod."

    def upgrade_pod(self, session_id: str) -> Dict[str, Any]:
        pod = self._get_or_create_pod(session_id)
        if pod.capacity >= UNITY:
            return {"capacity": pod.capacity, "message": "Pod already at max capacity (9)."}
        pod.capacity = min(UNITY, pod.capacity + TRINITY)
        self._save_pod(pod)
        return {"capacity": pod.capacity, "message": f"Pod upgraded to {pod.capacity} slots!"}

    # ── Battle ─────────────────────────────────────────────────────────────────

    def battle(
        self,
        attacker_catch_id: str,
        defender_catch_id: str,
        rounds: int = TRINITY,
    ) -> Dict[str, Any]:
        """
        Run a turn-based battle between two caught aliens.
        3-round structure (TRINITY). Returns full battle log.
        """
        atk = self._load_alien(attacker_catch_id)
        dfn = self._load_alien(defender_catch_id)
        if not atk or not dfn:
            return {"error": "One or both aliens not found."}

        log: List[str] = []
        atk_hp = atk.max_hp
        dfn_hp = dfn.max_hp

        for rnd in range(1, rounds + 1):
            # Attacker goes first if faster
            first, second = (atk, dfn) if atk.speed >= dfn.speed else (dfn, atk)
            f_hp = atk_hp if first is atk else dfn_hp
            s_hp = dfn_hp if first is atk else atk_hp

            for (striker, target, is_first) in [(first, second, True), (second, first, False)]:
                if f_hp <= 0 or s_hp <= 0:
                    break
                # Damage = power * PHI_CONJUGATE * (1 - defense/200) * luck modifier
                luck_mod = 1.0 + (striker.luck / 100) * 0.3
                dmg = max(1, int(
                    striker.power * PHI_CONJUGATE
                    * max(0.1, 1 - target.defense / 200)
                    * luck_mod
                    * random.uniform(0.85, 1.15)
                ))
                # Evasion check
                if random.random() < target.evasion / 150:
                    log.append(f"  Round {rnd}: {target.nickname} evaded {striker.nickname}'s attack!")
                    continue

                if is_first:
                    s_hp = max(0, s_hp - dmg)
                else:
                    f_hp = max(0, f_hp - dmg)

                log.append(
                    f"  Round {rnd}: {striker.nickname} hits {target.nickname} for {dmg} dmg "
                    f"(HP remaining: {s_hp if is_first else f_hp})"
                )

            if first is atk:
                atk_hp, dfn_hp = f_hp, s_hp
            else:
                dfn_hp, atk_hp = f_hp, s_hp

            if atk_hp <= 0 or dfn_hp <= 0:
                break

        winner = atk if atk_hp > dfn_hp else dfn
        loser  = dfn if winner is atk else atk

        # XP award — winner gets more, HARMONY bonus for close fights
        base_xp = 30
        if abs(atk_hp - dfn_hp) < (winner.max_hp * 0.2):
            base_xp = HARMONY * 10  # Close fight bonus
        self._award_xp(winner, base_xp)
        self._award_xp(loser, base_xp // TRINITY)

        winner.battles_won += 1
        winner.battles_total += 1
        loser.battles_total += 1
        self._save_alien(winner)
        self._save_alien(loser)

        evolution_msg = ""
        evo_result = self._check_evolution(winner)
        if evo_result:
            evolution_msg = f" 🌟 {evo_result}"

        return {
            "winner": winner.nickname,
            "loser": loser.nickname,
            "attacker_hp_remaining": atk_hp,
            "defender_hp_remaining": dfn_hp,
            "log": log,
            "xp_awarded": base_xp,
            "evolution": evolution_msg,
        }

    # ── Evolution ──────────────────────────────────────────────────────────────

    def _check_evolution(self, alien: CaughtAlien) -> Optional[str]:
        chain = EVOLUTION_CHAINS.get(alien.species)
        if not chain:
            return None
        lvl_s2, lvl_s3 = chain["lvl"]

        if alien.evolution_stage == 1 and alien.level >= lvl_s2:
            old_name = alien.nickname
            alien.species = chain["s2"]
            alien.nickname = chain["s2"].replace("_", " ").title()
            alien.evolution_stage = 2
            alien.power = int(alien.power * PHI)
            alien.defense = int(alien.defense * PHI)
            alien.max_hp = int(alien.max_hp * PHI)
            alien.hp = alien.max_hp
            self._save_alien(alien)
            self._notify_unreal_evolution(alien)
            return f"{old_name} evolved into {alien.nickname}!"

        if alien.evolution_stage == 2 and alien.level >= lvl_s3:
            old_name = alien.nickname
            alien.species = chain["s3"]
            alien.nickname = chain["s3"].replace("_", " ").title()
            alien.evolution_stage = 3
            alien.power = int(alien.power * PHI)
            alien.defense = int(alien.defense * PHI)
            alien.max_hp = int(alien.max_hp * PHI)
            alien.hp = alien.max_hp
            self._save_alien(alien)
            self._notify_unreal_evolution(alien)
            return f"{old_name} achieved final evolution: {alien.nickname}!"

        return None

    def _notify_unreal_evolution(self, alien: CaughtAlien):
        if self._bridge:
            try:
                self._bridge.broadcast({
                    "type": "ALIEN_EVOLUTION",
                    "payload": {
                        "catch_id": alien.catch_id,
                        "species": alien.species,
                        "stage": alien.evolution_stage,
                        "nickname": alien.nickname,
                    }
                })
            except Exception:
                pass

    # ── XP + levelling ────────────────────────────────────────────────────────

    def _award_xp(self, alien: CaughtAlien, xp: int):
        alien.xp += xp
        xp_needed = int(100 * PHI ** alien.level)
        while alien.xp >= xp_needed:
            alien.xp -= xp_needed
            alien.level += 1
            # Scale all stats on level up
            alien.power   = int(alien.power   * 1.1)
            alien.defense = int(alien.defense * 1.1)
            alien.speed   = int(alien.speed   * 1.05)
            alien.max_hp  = int(alien.max_hp  * 1.15)
            alien.hp      = alien.max_hp
            xp_needed     = int(100 * PHI ** alien.level)
            logger.info("Alien %s leveled up to %d!", alien.nickname, alien.level)

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _save_alien(self, alien: CaughtAlien):
        if not self._db:
            self._aliens[alien.catch_id] = alien
            return
        try:
            from tinydb import Query
            self._tbl_aliens.upsert(asdict(alien), Query().catch_id == alien.catch_id)
            self._aliens[alien.catch_id] = alien
        except Exception as e:
            logger.debug("AlienSystem save_alien error: %s", e)

    def _load_alien(self, catch_id: str) -> Optional[CaughtAlien]:
        if catch_id in self._aliens:
            return self._aliens[catch_id]
        if not self._db:
            return None
        try:
            from tinydb import Query
            doc = self._tbl_aliens.get(Query().catch_id == catch_id)
            if doc:
                a = CaughtAlien(**{k: v for k, v in doc.items()
                                   if k in CaughtAlien.__dataclass_fields__})
                self._aliens[catch_id] = a
                return a
        except Exception:
            pass
        return None

    def _save_pod(self, pod: ContainmentPod):
        if not self._db:
            self._pods[pod.owner_session] = pod
            return
        try:
            from tinydb import Query
            self._tbl_pods.upsert(asdict(pod), Query().owner_session == pod.owner_session)
        except Exception as e:
            logger.debug("AlienSystem save_pod error: %s", e)


# ── Singleton ──────────────────────────────────────────────────────────────────
_system: Optional[AlienSystem] = None

def get_alien_system(data_dir: str = "data") -> AlienSystem:
    global _system
    if _system is None:
        _system = AlienSystem(data_dir=data_dir)
    return _system
