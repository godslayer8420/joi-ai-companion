"""
world_regions.py — 9 canonical world regions for Aurion's game world.

Each region has:
  - Unique biome, atmosphere, ecology
  - Spawn tables for aliens and NPCs
  - Loot / resource nodes
  - Unreal level reference
  - Sacred geometry seed (3/6/9 aligned)

Basement layers (multi-level underground):
  Layer 1 — The Deep Nexus (general underground hub)
  Layer 2 — Neon District (cyberpunk market)
  Layer 3 — Fight Arena  (battle tournaments)
  Layer 4 — Kart Circuit  (racing track)

Procedural content uses its own world_memory.db — not Aurion's personal memory.
"""

from __future__ import annotations
from typing import Dict, List, Any

# ── Region ID constants ────────────────────────────────────────────────────────
R_SURFACE_CITY    = "surface_city"
R_UNDERGROUND     = "underground_nexus"
R_NEON_DISTRICT   = "neon_district"
R_VOID_LAYER      = "void_layer"
R_FESTIVAL        = "festival_grounds"
R_ALIEN_PRESERVE  = "alien_preserve"
R_BASEMENT_ARENA  = "basement_arena"
R_KART_CIRCUIT    = "kart_circuit"
R_DEEP_WILD       = "deep_wild"


def _region(
    rid: str,
    name: str,
    biome: str,
    atmosphere: str,
    level_range: tuple,
    unreal_level: str,
    alien_spawns: List[str],
    npc_density: str,
    loot_tier: int,
    ecology_type: str,
    ambient_music: str,
    seed: int,
    special: Dict[str, Any] = None,
) -> Dict[str, Any]:
    return {
        "id": rid,
        "name": name,
        "biome": biome,
        "atmosphere": atmosphere,
        "level_range": level_range,
        "unreal_level": unreal_level,
        "alien_spawns": alien_spawns,
        "npc_density": npc_density,
        "loot_tier": loot_tier,
        "ecology_type": ecology_type,
        "ambient_music": ambient_music,
        "seed": seed,
        "special": special or {},
    }


# ── 9 canonical regions ───────────────────────────────────────────────────────
REGIONS: Dict[str, Dict[str, Any]] = {

    R_SURFACE_CITY: _region(
        rid=R_SURFACE_CITY,
        name="Surface City",
        biome="urban_megacity",
        atmosphere="smoggy neon dusk, perpetual twilight, rain-slicked streets",
        level_range=(1, 15),
        unreal_level="/Game/Levels/SurfaceCity/SurfaceCity_Main",
        alien_spawns=["glitch_sprite", "smog_crawler", "neon_leech"],
        npc_density="high",
        loot_tier=2,
        ecology_type="urban_decay",
        ambient_music="ambient_city_rain_loop",
        seed=369,
        special={
            "shops": ["tech_bazaar", "black_market", "aurion_lounge"],
            "fast_travel_hub": True,
            "vertical_zones": 9,
        },
    ),

    R_UNDERGROUND: _region(
        rid=R_UNDERGROUND,
        name="Underground Nexus",
        biome="subterranean_cavern",
        atmosphere="bioluminescent fungi, dripping water, echo-heavy, warm geothermal air",
        level_range=(5, 25),
        unreal_level="/Game/Levels/Underground/Underground_Nexus",
        alien_spawns=["cavern_shade", "crystal_grub", "root_titan"],
        npc_density="medium",
        loot_tier=3,
        ecology_type="fungal_network",
        ambient_music="ambient_underground_deep",
        seed=636,
        special={
            "mining_nodes": True,
            "secret_passages": 6,
            "gateway_to_basement": True,
        },
    ),

    R_NEON_DISTRICT: _region(
        rid=R_NEON_DISTRICT,
        name="Neon District",
        biome="cyberpunk_underground",
        atmosphere="holographic ads, synthetic music, crowded bazaars, black market energy",
        level_range=(8, 30),
        unreal_level="/Game/Levels/NeonDistrict/NeonDistrict_Main",
        alien_spawns=["data_wraith", "neon_mimic", "circuit_beast"],
        npc_density="very_high",
        loot_tier=4,
        ecology_type="synthetic_sprawl",
        ambient_music="ambient_neon_cyberpunk",
        seed=999,
        special={
            "hacking_minigame": True,
            "alien_smuggler_npc": True,
            "underground_casino": True,
        },
    ),

    R_VOID_LAYER: _region(
        rid=R_VOID_LAYER,
        name="Void Layer",
        biome="dimensional_rift",
        atmosphere="gravity-warped space, floating debris, dimensional tears, silence",
        level_range=(20, 50),
        unreal_level="/Game/Levels/VoidLayer/VoidLayer_Main",
        alien_spawns=["void_wraith", "phase_stalker", "rift_colossus"],
        npc_density="sparse",
        loot_tier=7,
        ecology_type="dimensional_chaos",
        ambient_music="ambient_void_rift",
        seed=333,
        special={
            "zero_gravity_zones": True,
            "dimensional_echoes": True,
            "boss_rift_colossus": True,
        },
    ),

    R_FESTIVAL: _region(
        rid=R_FESTIVAL,
        name="Festival Grounds",
        biome="open_air_celebration",
        atmosphere="lanterns, music, food stalls, carnival energy, multispecies crowd",
        level_range=(1, 10),
        unreal_level="/Game/Levels/Festival/Festival_Main",
        alien_spawns=["confetti_wisp", "festival_imp", "balloon_beast"],
        npc_density="very_high",
        loot_tier=2,
        ecology_type="cultural_hub",
        ambient_music="ambient_festival_celebration",
        seed=666,
        special={
            "mini_games": ["ring_toss", "alien_parade", "dance_battle"],
            "seasonal_events": True,
            "aurion_stage_performance": True,
        },
    ),

    R_ALIEN_PRESERVE: _region(
        rid=R_ALIEN_PRESERVE,
        name="Alien Preserve",
        biome="alien_wilderness",
        atmosphere="exotic alien flora, twin moons visible, bioluminescent rivers",
        level_range=(15, 45),
        unreal_level="/Game/Levels/AlienPreserve/AlienPreserve_Main",
        alien_spawns=[
            "alpha_luminar", "void_strider", "crystal_wyvern",
            "plasma_mantis", "gravity_bear", "echo_serpent",
        ],
        npc_density="low",
        loot_tier=6,
        ecology_type="alien_ecosystem",
        ambient_music="ambient_alien_wilderness",
        seed=963,
        special={
            "rare_alien_spawns": True,
            "catch_bonus_zone": True,
            "ecology_tracking": True,
            "alpha_boss_spawns": True,
        },
    ),

    R_BASEMENT_ARENA: _region(
        rid=R_BASEMENT_ARENA,
        name="Fight Arena",
        biome="underground_combat_arena",
        atmosphere="roaring crowd, spotlights, blood-stained sand, alien battle energy",
        level_range=(10, 99),
        unreal_level="/Game/Levels/Basement/Layer3_FightArena",
        alien_spawns=["arena_gladiator", "champion_beast", "tournament_titan"],
        npc_density="medium",
        loot_tier=8,
        ecology_type="combat_colosseum",
        ambient_music="ambient_arena_battle",
        seed=396,
        special={
            "tournament_tiers": 5,
            "spectator_system": True,
            "bracket_mode": True,
            "alien_battle_enabled": True,
            "basement_layer": 3,
        },
    ),

    R_KART_CIRCUIT: _region(
        rid=R_KART_CIRCUIT,
        name="Kart Circuit",
        biome="underground_race_track",
        atmosphere="exhaust fumes, cheering fans, neon track lighting, engine roar",
        level_range=(1, 99),
        unreal_level="/Game/Levels/Basement/Layer4_KartCircuit",
        alien_spawns=["speed_demon", "turbo_imp", "track_guardian"],
        npc_density="medium",
        loot_tier=5,
        ecology_type="motorsport_underground",
        ambient_music="ambient_kart_race",
        seed=693,
        special={
            "track_count": 9,
            "alien_kart_riders": True,
            "ghost_system": True,
            "drift_boost_zones": True,
            "basement_layer": 4,
        },
    ),

    R_DEEP_WILD: _region(
        rid=R_DEEP_WILD,
        name="The Deep Wild",
        biome="primordial_jungle",
        atmosphere="ancient trees, howling winds, ruins of forgotten civilizations",
        level_range=(30, 70),
        unreal_level="/Game/Levels/DeepWild/DeepWild_Main",
        alien_spawns=[
            "ancient_guardian", "ruin_stalker", "jungle_titan",
            "moss_colossus", "spore_wraith",
        ],
        npc_density="very_low",
        loot_tier=9,
        ecology_type="primordial_ecosystem",
        ambient_music="ambient_deep_wild",
        seed=999,
        special={
            "ancient_ruins": True,
            "hidden_boss_lairs": 3,
            "legendary_alien_spawns": True,
        },
    ),
}


# ── Node graph (fast-travel connections) ──────────────────────────────────────
NODES: Dict[str, List[str]] = {
    R_SURFACE_CITY:   [R_UNDERGROUND, R_FESTIVAL, R_NEON_DISTRICT],
    R_UNDERGROUND:    [R_SURFACE_CITY, R_NEON_DISTRICT, R_BASEMENT_ARENA, R_KART_CIRCUIT],
    R_NEON_DISTRICT:  [R_SURFACE_CITY, R_UNDERGROUND, R_VOID_LAYER],
    R_VOID_LAYER:     [R_NEON_DISTRICT, R_ALIEN_PRESERVE, R_DEEP_WILD],
    R_FESTIVAL:       [R_SURFACE_CITY, R_ALIEN_PRESERVE],
    R_ALIEN_PRESERVE: [R_FESTIVAL, R_VOID_LAYER, R_DEEP_WILD],
    R_BASEMENT_ARENA: [R_UNDERGROUND, R_KART_CIRCUIT],
    R_KART_CIRCUIT:   [R_UNDERGROUND, R_BASEMENT_ARENA],
    R_DEEP_WILD:      [R_VOID_LAYER, R_ALIEN_PRESERVE],
}


def region_catalog() -> Dict[str, Dict[str, Any]]:
    """Return all regions keyed by ID."""
    return dict(REGIONS)


def get_region(region_id: str) -> Dict[str, Any]:
    """Return a single region definition or empty dict if unknown."""
    return REGIONS.get(region_id, {})


def neighbors(region_id: str) -> List[str]:
    """Return connected region IDs (fast-travel graph)."""
    return NODES.get(region_id, [])


def regions_by_level(player_level: int) -> List[Dict[str, Any]]:
    """Return regions appropriate for a given player level."""
    return [
        r for r in REGIONS.values()
        if r["level_range"][0] <= player_level <= r["level_range"][1]
    ]

