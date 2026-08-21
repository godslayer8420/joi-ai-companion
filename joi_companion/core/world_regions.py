"""world_regions.py — Nine canonical regions of Aurion's procedural world.

Each region has:
- Biome type (jungle, void, ruins, crystal caverns, etc.)
- Ecology scale (biodiversity index, 0–1)
- Economy type (scavenging, trading, ritual-based)
- Native alien tier (T1/T2/T3) and spawn rates
- Lumen energy signature (0–1, affects evolution conditions)
- Regional effects (weather, time dilation, vision range modifiers)
- Discovery state (player must explore to unlock)

The 9 regions form a 3×3 spatial grid (TRINITY×TRINITY=HARMONY),
organized around Aurion's Cathedral (the central hub).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import math

from joi_companion.core.sacred_geometry import (
    PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY,
    digital_root, is_369, vortex_weight
)


# ─────────────────────────────────────────────────────────────────────────────
# Region biome types
# ─────────────────────────────────────────────────────────────────────────────
class BiomeType(str, Enum):
    """Available biome archetypes."""
    JUNGLE = "jungle"           # Overgrown, humid, dense vegetation
    VOID = "void"               # Empty, dark, anti-light; high Lumen drain
    RUINS = "ruins"             # Ancient structures, half-submerged
    CRYSTAL_CAVERNS = "crystal_caverns"  # Resonant geometry, light-bending
    SWAMP = "swamp"             # Murky, slow movement, disease risk
    TUNDRA = "tundra"           # Frozen, sparse resources, survival focus
    VOLCANIC = "volcanic"       # Magma flows, extreme heat, volatility
    LUMINOUS_FOREST = "luminous_forest"  # Glowing flora, high ambient Lumen
    ABYSSAL_TRENCH = "abyssal_trench"    # Deep pressure, bioluminescence, isolation


class EconomyType(str, Enum):
    """How aliens and NPCs exchange resources in each region."""
    SCAVENGING = "scavenging"   # Gathering debris, trading found items
    TRADING = "trading"          # Merchants, bartering, price-based
    RITUAL = "ritual"            # Ceremony-driven, favour/debt system
    HUNT = "hunt"                # Resource scarcity, predator/prey dynamics
    CULTIVATION = "cultivation"  # Farming/breeding aliens, slow accumulation


class WeatherPattern(str, Enum):
    """Cyclical weather affecting encounter rates and evolution triggers."""
    STORM = "storm"              # Increased water alien spawns, reduced visibility
    FULL_MOON = "full_moon"      # Evolution triggers, nocturnal spawns surge
    ECLIPSE = "eclipse"          # Void energy spike, rare spawns
    CLEAR = "clear"              # Normal rates
    SEASONAL_BLOOM = "seasonal_bloom"  # Flora-based aliens surge


# ─────────────────────────────────────────────────────────────────────────────
# Region spawn rates and ecology
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class AlienSpawnRates:
    """Spawn probabilities for each alien tier in a region."""
    tier1_rate: float = 0.6    # T1 common spawn (level 1–15)
    tier2_rate: float = 0.3    # T2 uncommon (15–40)
    tier3_rate: float = 0.1    # T3 rare (40+)
    
    def get_random_tier(self, roll: float) -> int:
        """Given a random roll (0–1), return 1, 2, or 3."""
        if roll < self.tier1_rate:
            return 1
        elif roll < self.tier1_rate + self.tier2_rate:
            return 2
        else:
            return 3


@dataclass
class RegionSpawnTable:
    """Which alien species can spawn in this region, grouped by tier."""
    tier1_species: List[str] = field(default_factory=list)
    tier2_species: List[str] = field(default_factory=list)
    tier3_species: List[str] = field(default_factory=list)
    
    def get_species_for_tier(self, tier: int) -> List[str]:
        """Return the list of species for the given tier (1–3)."""
        if tier == 1:
            return self.tier1_species
        elif tier == 2:
            return self.tier2_species
        elif tier == 3:
            return self.tier3_species
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Region definition
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Region:
    """A canonical procedurally-generated region of the world."""
    region_id: str
    name: str
    description: str
    
    # Geography
    biome: BiomeType
    position: tuple[int, int]  # (x, y) grid position in 3×3 world
    
    # Ecology
    ecology_scale: float  # 0.0 (barren) to 1.0 (maximal biodiversity)
    economy_type: EconomyType
    lumen_energy: float  # 0.0 (drained) to 1.0 (fully charged); affects evolution & discovery
    
    # Spawning
    spawn_rates: AlienSpawnRates
    spawn_table: RegionSpawnTable
    encounter_rate: float  # 0.0–1.0; probability of alien encounter per walk tick
    
    # Regional effects
    weather: WeatherPattern = WeatherPattern.CLEAR
    vision_range_mod: float = 1.0  # Multiplier on player vision distance
    movement_speed_mod: float = 1.0  # Terrain friction
    alien_evolution_conditions: List[str] = field(default_factory=list)  # e.g., ["full_moon", "high_lumen"]
    
    # Discovery
    discovered: bool = False
    discovery_xp: int = 100  # XP grant when first entered
    discovery_ts: Optional[float] = None
    
    # Sim state (updated each tick)
    last_tick: float = 0.0
    pending_spawns: List[Dict[str, Any]] = field(default_factory=list)
    active_npcs: List[str] = field(default_factory=list)  # NPC IDs
    active_events: List[str] = field(default_factory=list)  # Event IDs
    
    def __hash__(self):
        return hash(self.region_id)


# ─────────────────────────────────────────────────────────────────────────────
# Canonical 9 regions (3×3 grid around Aurion's Cathedral)
# ─────────────────────────────────────────────────────────────────────────────
def build_canonical_regions() -> Dict[str, Region]:
    """
    Construct the 9 canonical regions arranged in a 3×3 grid.
    
    Grid layout (cathedral at centre):
        NW (-1,-1)  | N (0,-1)  | NE (1,-1)
        ─────────────────────────────────
        W (-1,0)    | CENTRE    | E (1,0)
        ─────────────────────────────────
        SW (-1,1)   | S (0,1)   | SE (1,1)
    
    Returns a dict keyed by region_id.
    """
    regions = {}
    
    # ────────────────────────────────────────────────────────────────────────
    # NORTH (0, -1) — Luminous Forest
    # ────────────────────────────────────────────────────────────────────────
    regions["north"] = Region(
        region_id="north",
        name="Luminous Forest",
        description="Glowing flora illuminates the canopy. Ambient Lumen hums through the air.",
        biome=BiomeType.LUMINOUS_FOREST,
        position=(0, -1),
        ecology_scale=0.95,
        economy_type=EconomyType.CULTIVATION,
        lumen_energy=0.90,
        spawn_rates=AlienSpawnRates(tier1_rate=0.5, tier2_rate=0.35, tier3_rate=0.15),
        spawn_table=RegionSpawnTable(
            tier1_species=["Glow_Sprite", "Flower_Moth", "Light_Pixel"],
            tier2_species=["Luminant_Hound", "Prism_Drake"],
            tier3_species=["Radiant_Guardian"],
        ),
        encounter_rate=0.08,
        vision_range_mod=1.3,
        movement_speed_mod=0.9,
        alien_evolution_conditions=["high_lumen", "daylight"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # NORTHEAST (1, -1) — Crystal Caverns
    # ────────────────────────────────────────────────────────────────────────
    regions["northeast"] = Region(
        region_id="northeast",
        name="Crystal Caverns",
        description="Resonant geometry fractures light. Echoes distort time and space.",
        biome=BiomeType.CRYSTAL_CAVERNS,
        position=(1, -1),
        ecology_scale=0.65,
        economy_type=EconomyType.RITUAL,
        lumen_energy=0.75,
        spawn_rates=AlienSpawnRates(tier1_rate=0.55, tier2_rate=0.30, tier3_rate=0.15),
        spawn_table=RegionSpawnTable(
            tier1_species=["Quartz_Mite", "Refract_Pup", "Chime_Spirit"],
            tier2_species=["Prism_Drake", "Resonant_Beast"],
            tier3_species=["Crystal_Titan"],
        ),
        encounter_rate=0.06,
        vision_range_mod=0.85,
        movement_speed_mod=1.1,
        alien_evolution_conditions=["geometric_harmony", "full_moon"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # EAST (1, 0) — Volcanic Wastes
    # ────────────────────────────────────────────────────────────────────────
    regions["east"] = Region(
        region_id="east",
        name="Volcanic Wastes",
        description="Magma flows carve new paths. The ground trembles with buried rage.",
        biome=BiomeType.VOLCANIC,
        position=(1, 0),
        ecology_scale=0.45,
        economy_type=EconomyType.HUNT,
        lumen_energy=0.50,
        spawn_rates=AlienSpawnRates(tier1_rate=0.50, tier2_rate=0.35, tier3_rate=0.15),
        spawn_table=RegionSpawnTable(
            tier1_species=["Magma_Newt", "Ash_Wraith", "Flame_Creeper"],
            tier2_species=["Magma_Behemoth", "Lava_Wyrm"],
            tier3_species=["Infernal_Lord"],
        ),
        encounter_rate=0.10,
        vision_range_mod=0.8,
        movement_speed_mod=0.7,
        alien_evolution_conditions=["extreme_heat", "combat_victory"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # SOUTHEAST (1, 1) — Abyssal Trench
    # ────────────────────────────────────────────────────────────────────────
    regions["southeast"] = Region(
        region_id="southeast",
        name="Abyssal Trench",
        description="Crushing depths. Bioluminescent creatures drift through eternal night.",
        biome=BiomeType.ABYSSAL_TRENCH,
        position=(1, 1),
        ecology_scale=0.70,
        economy_type=EconomyType.SCAVENGING,
        lumen_energy=0.30,
        spawn_rates=AlienSpawnRates(tier1_rate=0.50, tier2_rate=0.35, tier3_rate=0.15),
        spawn_table=RegionSpawnTable(
            tier1_species=["Deep_Fish", "Pressure_Slug", "Void_Squid_Jr"],
            tier2_species=["Leviathan_Calf", "Anglerfish_Phantom"],
            tier3_species=["Abyssal_Leviathan"],
        ),
        encounter_rate=0.07,
        vision_range_mod=0.6,
        movement_speed_mod=0.85,
        alien_evolution_conditions=["low_lumen", "water_present"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # SOUTH (0, 1) — Swamp Mire
    # ────────────────────────────────────────────────────────────────────────
    regions["south"] = Region(
        region_id="south",
        name="Swamp Mire",
        description="Murky water and rotting vegetation. Life persists in slow decay.",
        biome=BiomeType.SWAMP,
        position=(0, 1),
        ecology_scale=0.75,
        economy_type=EconomyType.SCAVENGING,
        lumen_energy=0.35,
        spawn_rates=AlienSpawnRates(tier1_rate=0.60, tier2_rate=0.30, tier3_rate=0.10),
        spawn_table=RegionSpawnTable(
            tier1_species=["Bog_Crawler", "Moss_Sprite", "Fungal_Pup"],
            tier2_species=["Vine_Beast", "Plague_Toad"],
            tier3_species=["Rot_Sovereign"],
        ),
        encounter_rate=0.09,
        vision_range_mod=0.7,
        movement_speed_mod=0.6,
        alien_evolution_conditions=["disease_resistance", "water_submerged"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # SOUTHWEST (-1, 1) — Tundra Expanse
    # ────────────────────────────────────────────────────────────────────────
    regions["southwest"] = Region(
        region_id="southwest",
        name="Tundra Expanse",
        description="Frozen wasteland. Survival is a constant struggle against cold.",
        biome=BiomeType.TUNDRA,
        position=(-1, 1),
        ecology_scale=0.40,
        economy_type=EconomyType.HUNT,
        lumen_energy=0.55,
        spawn_rates=AlienSpawnRates(tier1_rate=0.50, tier2_rate=0.35, tier3_rate=0.15),
        spawn_table=RegionSpawnTable(
            tier1_species=["Frost_Hare", "Ice_Spirit", "Snow_Flake_Bug"],
            tier2_species=["Blizzard_Wolf", "Glacier_Drake"],
            tier3_species=["Frost_Monarch"],
        ),
        encounter_rate=0.06,
        vision_range_mod=1.0,
        movement_speed_mod=0.8,
        alien_evolution_conditions=["extreme_cold", "low_energy_expenditure"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # WEST (-1, 0) — Ruins of Echoes
    # ────────────────────────────────────────────────────────────────────────
    regions["west"] = Region(
        region_id="west",
        name="Ruins of Echoes",
        description="Crumbling monuments. Ancient technology hums faintly beneath stone.",
        biome=BiomeType.RUINS,
        position=(-1, 0),
        ecology_scale=0.50,
        economy_type=EconomyType.RITUAL,
        lumen_energy=0.65,
        spawn_rates=AlienSpawnRates(tier1_rate=0.55, tier2_rate=0.30, tier3_rate=0.15),
        spawn_table=RegionSpawnTable(
            tier1_species=["Stone_Golem_Jr", "Ruin_Rat", "Echo_Bat"],
            tier2_species=["Construct_Guardian", "Memory_Phantom"],
            tier3_species=["Ancient_Sentinel"],
        ),
        encounter_rate=0.05,
        vision_range_mod=0.9,
        movement_speed_mod=1.0,
        alien_evolution_conditions=["ancient_tech_proximity", "lumen_channeling"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # NORTHWEST (-1, -1) — Jungle Canopy
    # ────────────────────────────────────────────────────────────────────────
    regions["northwest"] = Region(
        region_id="northwest",
        name="Jungle Canopy",
        description="Primal vegetation chokes the sky. Life competes for sunlight.",
        biome=BiomeType.JUNGLE,
        position=(-1, -1),
        ecology_scale=0.92,
        economy_type=EconomyType.CULTIVATION,
        lumen_energy=0.70,
        spawn_rates=AlienSpawnRates(tier1_rate=0.60, tier2_rate=0.30, tier3_rate=0.10),
        spawn_table=RegionSpawnTable(
            tier1_species=["Vine_Snake", "Leaf_Hopper", "Petal_Bird"],
            tier2_species=["Jungle_Prowler", "Canopy_Drake"],
            tier3_species=["Primordial_Beast"],
        ),
        encounter_rate=0.08,
        vision_range_mod=0.75,
        movement_speed_mod=0.9,
        alien_evolution_conditions=["dense_foliage", "natural_selection"],
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # VOID RIFTS (centre-adjacent) — Dark Matter Nexus
    # ────────────────────────────────────────────────────────────────────────
    # This region exists "between" the others; accessible only through portals
    # or late-game progression. Highest rarity, extreme conditions.
    regions["void_rifts"] = Region(
        region_id="void_rifts",
        name="Void Rifts",
        description="Reality fractures. Alien geometries hint at dimensions beyond.",
        biome=BiomeType.VOID,
        position=(0, 0),  # Centre, but overlaid
        ecology_scale=0.20,
        economy_type=EconomyType.RITUAL,
        lumen_energy=0.05,
        spawn_rates=AlienSpawnRates(tier1_rate=0.25, tier2_rate=0.40, tier3_rate=0.35),
        spawn_table=RegionSpawnTable(
            tier1_species=["Void_Mote", "Shadow_Imp"],
            tier2_species=["Void_Wyvern", "Entropy_Construct"],
            tier3_species=["Void_Sovereign", "Cosmic_Horror"],
        ),
        encounter_rate=0.02,
        vision_range_mod=0.4,
        movement_speed_mod=1.2,
        alien_evolution_conditions=["void_energy", "no_lumen"],
    )
    
    return regions


# ─────────────────────────────────────────────────────────────────────────────
# Global singleton cache
# ─────────────────────────────────────────────────────────────────────────────
_REGIONS_CACHE: Optional[Dict[str, Region]] = None

def get_regions() -> Dict[str, Region]:
    """Lazy-load the canonical regions."""
    global _REGIONS_CACHE
    if _REGIONS_CACHE is None:
        _REGIONS_CACHE = build_canonical_regions()
    return _REGIONS_CACHE

def get_region(region_id: str) -> Optional[Region]:
    """Fetch a single region by ID, or None if not found."""
    return get_regions().get(region_id)

def list_region_ids() -> List[str]:
    """Return all region IDs in spatial order."""
    return [
        "northwest", "north", "northeast",
        "west", "void_rifts", "east",
        "southwest", "south", "southeast",
    ]
