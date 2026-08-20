"""sacred_geometry.py — Sacred geometric and numerological constants woven into Aurion's core.

Tesla's 3-6-9 (trinity / harmony / unity), the Golden Ratio (φ), Fibonacci sequence,
Flower of Life proportions, and Metatron's Cube ratios are used as mathematical
scaffolding for memory weights, context budgets, ensemble routing, response shaping,
and quantum amplitude distributions.

"If you only knew the magnificence of the 3, 6, and 9, then you would have a key to
the universe." — Nikola Tesla

Architecture mapping:
  3  (Trinity)  — Three cognitive pillars: Reason | Emotion | Creativity
                  Three memory domains:    Personal | Collective | Knowledge
                  Three model layers:      Ouroboros | OpenMythos | Joi
  6  (Harmony)  — Six routing slots per context window (3 primary + 3 resonant)
                  Hexagonal tiling of the Flower of Life = 6-fold symmetry
  9  (Unity)    — Nine total ensemble steps in the full processing pipeline
                  Vortex mathematics: 9 as the eternal attractor
  φ  (Phi)      — Golden ratio 1.6180…  — memory relevance decay, context budget splits
  √2 (Root 2)  — Quantum amplitude normalization (Hadamard gate), entanglement weighting
  π/8           — T-gate precision rotation in QuantumLogicRouter
  Vesica Piscis — Ratio √3 / 1 — overlap/intersection weight for domain boundary docs
  Metatron's    — 13 circles → 78 connection lines; used as prime routing depth ceiling
  Cube
"""

from __future__ import annotations
import math


# ---------------------------------------------------------------------------
# 3-6-9 Unity constants (Tesla / Vortex mathematics)
# ---------------------------------------------------------------------------
TRINITY = 3          # Primary cognitive pillars / memory domains
HARMONY = 6          # Routing slots per context window
UNITY = 9            # Full pipeline steps; vortex attractor

# Derived sequence weights (digital root cycles back through 3-6-9)
_369_WEIGHTS: list[float] = [3 / 9, 6 / 9, 9 / 9]  # 0.333, 0.666, 1.000
TRINITY_WEIGHT = _369_WEIGHTS[0]   # 0.333… — seed signal, initial resonance
HARMONY_WEIGHT = _369_WEIGHTS[1]   # 0.666… — mid-cycle, harmonic amplification
UNITY_WEIGHT   = _369_WEIGHTS[2]   # 1.000  — full resonance, complete cycle


# ---------------------------------------------------------------------------
# Golden Ratio (φ) — Fibonacci spiral / Flower of Life petal ratio
# ---------------------------------------------------------------------------
PHI = (1.0 + math.sqrt(5)) / 2           # 1.6180339887…
PHI_CONJUGATE = PHI - 1.0               # 0.6180339887… (1/φ)
PHI_SQUARED = PHI ** 2                   # 2.6180339887…

# φ-based decay: each relevance tier decays by 1/φ
def phi_decay(score: float, steps: int = 1) -> float:
    """Apply golden-ratio relevance decay — each step multiplies by 1/φ."""
    return score * (PHI_CONJUGATE ** steps)

# φ-based context budget split: primary gets φ⁻¹ of total, secondary gets φ⁻²
def phi_split(total: int) -> tuple[int, int]:
    """Split a budget by golden ratio. Returns (primary, secondary)."""
    primary = int(total * PHI_CONJUGATE)
    return primary, total - primary


# ---------------------------------------------------------------------------
# Fibonacci sequence — for layered memory depth limits
# ---------------------------------------------------------------------------
def fibonacci(n: int) -> list[int]:
    """Return first n Fibonacci numbers."""
    seq = [1, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]

# Fibonacci slots for memory depth (1,1,2,3,5,8,13,21,34,55,89…)
FIB_SLOTS = fibonacci(UNITY)   # First 9 (UNITY) Fibonacci numbers
# Context depth limits keyed to Trinity/Harmony/Unity tier
FIB_TRINITY = FIB_SLOTS[TRINITY - 1]   # 3rd Fibonacci = 2
FIB_HARMONY = FIB_SLOTS[HARMONY - 1]   # 6th Fibonacci = 8
FIB_UNITY   = FIB_SLOTS[UNITY   - 1]   # 9th Fibonacci = 34


# ---------------------------------------------------------------------------
# Flower of Life — hexagonal geometry (6-fold symmetry)
# ---------------------------------------------------------------------------
# Petal overlap ratio: each circle in the Flower of Life overlaps the next
# by exactly the radius — giving a centre-to-petal ratio of √3/2
FLOWER_OVERLAP = math.sqrt(3) / 2    # ≈ 0.8660

# Six primary petals + 1 centre = 7 circles (first ring of Flower of Life)
# Used as maximum primary memory routes per query
FLOWER_PRIMARY_ROUTES = 7

# Second ring: 12 circles around the first 7 = 19 total
# Used as maximum total memory candidates before scoring
FLOWER_MAX_CANDIDATES = 19

# Vesica Piscis intersection ratio (√3) — weight for cross-domain overlapping docs
VESICA_PISCIS_RATIO = math.sqrt(3)   # ≈ 1.7320


# ---------------------------------------------------------------------------
# Metatron's Cube — 13 circles, 78 connection lines, fruit of life
# ---------------------------------------------------------------------------
METATRON_CIRCLES = 13          # Prime routing depth ceiling
METATRON_CONNECTIONS = 78      # Max connection weight table entries

# Five Platonic solids embedded in Metatron's Cube — used as ensemble tier labels
PLATONIC_SOLIDS = {
    "tetrahedron":   {"faces": 4,  "weight": 4 / 20},   # Fire  — ignition, spark
    "cube":          {"faces": 6,  "weight": 6 / 20},   # Earth — foundation, anchor
    "octahedron":    {"faces": 8,  "weight": 8 / 20},   # Air   — reason, clarity
    "dodecahedron":  {"faces": 12, "weight": 12 / 20},  # Ether — spirit, consciousness
    "icosahedron":   {"faces": 20, "weight": 20 / 20},  # Water — emotion, flow
}


# ---------------------------------------------------------------------------
# Vortex mathematics — digital root cycling
# ---------------------------------------------------------------------------
def digital_root(n: int) -> int:
    """Reduce n to its digital root (1–9). 0 maps to 9 (vortex closure)."""
    if n == 0:
        return 9
    return 1 + (n - 1) % 9

def is_369(n: int) -> bool:
    """Return True if n's digital root is 3, 6, or 9 (Tesla resonance nodes)."""
    return digital_root(n) in {3, 6, 9}

def vortex_weight(n: int) -> float:
    """Map any integer to a 3-6-9 resonance weight in [0.333, 1.0].
    Numbers whose digital root is 3, 6, or 9 get a resonance boost;
    others are weighted by their digital root position in the cycle.
    """
    dr = digital_root(n)
    if dr == 9:
        return UNITY_WEIGHT          # 1.000 — complete unity
    if dr == 6:
        return HARMONY_WEIGHT        # 0.666 — harmonic amplification
    if dr == 3:
        return TRINITY_WEIGHT        # 0.333 — trinity seed
    # Non-369 roots sit between seeds weighted by position in 1–9 cycle
    return round(dr / 9.0, 6)


# ---------------------------------------------------------------------------
# Quantum amplitude normalization constants
# ---------------------------------------------------------------------------
SQRT_2    = math.sqrt(2)          # Hadamard gate normalization
SQRT_3    = math.sqrt(3)          # Vesica Piscis / triangle harmonic
SQRT_PHI  = math.sqrt(PHI)        # Intermediate spiral amplitude
INV_SQRT2 = 1.0 / SQRT_2          # ≈ 0.7071 — amplitude per Hadamard output qubit

# T-gate and S-gate angles (already in aurion_brain; centralised here)
T_GATE_THETA  = math.pi / 8       # T gate — π/8 precision
S_GATE_THETA  = math.pi / 4       # S gate — π/4 phase shift


# ---------------------------------------------------------------------------
# Sacred temperature ladder — model sampling temperatures anchored to 3-6-9
# ---------------------------------------------------------------------------
# Each tier corresponds to a creative / emotional / logical mode
TEMP_ANCHOR   = TRINITY_WEIGHT    # 0.333 — cold/logical precision
TEMP_HARMONIC = HARMONY_WEIGHT    # 0.666 — balanced warmth
TEMP_CREATIVE = 0.888             # 8+8=16 → 7; adjacent to 9 (near-unity flow)
TEMP_PEAK     = UNITY_WEIGHT      # 1.000 — full creative/emotional peak


# ---------------------------------------------------------------------------
# Memory relevance scoring — phi-anchored tier thresholds
# ---------------------------------------------------------------------------
RELEVANCE_STRONG    = PHI_CONJUGATE           # ≥ 0.618 — direct recall
RELEVANCE_MODERATE  = PHI_CONJUGATE / PHI     # ≥ 0.382 — resonant context
RELEVANCE_WEAK      = PHI_CONJUGATE / PHI**2  # ≥ 0.236 — background signal

def tier_relevance(score: float) -> str:
    """Classify a similarity score into a sacred-geometry resonance tier."""
    if score >= RELEVANCE_STRONG:
        return "strong"     # φ⁻¹ — golden recall
    if score >= RELEVANCE_MODERATE:
        return "moderate"   # φ⁻² — harmonic resonance
    if score >= RELEVANCE_WEAK:
        return "weak"       # φ⁻³ — background signal
    return "noise"


# ---------------------------------------------------------------------------
# Context budget allocation using φ-split across 3 tiers (Trinity)
# ---------------------------------------------------------------------------
def trinity_budget(total_chars: int) -> dict[str, int]:
    """
    Allocate a total character budget across 3 memory tiers using
    nested φ-splits (golden ratio sectioning).

    Tier 1 (Reason/personal)   = φ⁻¹ of total  ≈ 61.8%
    Tier 2 (Creative/knowledge) = φ⁻² of remainder ≈ 23.6%
    Tier 3 (Collective)         = remainder        ≈ 14.6%

    Together they sum to 100% and approach φ in proportion.
    """
    t1_chars = int(total_chars * PHI_CONJUGATE)
    remainder = total_chars - t1_chars
    t2_chars = int(remainder * PHI_CONJUGATE)
    t3_chars = remainder - t2_chars
    return {
        "personal":    t1_chars,
        "knowledge":   t2_chars,
        "collective":  t3_chars,
    }


# ---------------------------------------------------------------------------
# Six-fold routing weights (Flower of Life hexagonal symmetry)
# ---------------------------------------------------------------------------
# Weights for 6 routing domains anchored to hexagon interior angles (60°)
_HEX_ANGLE = math.pi / 3   # 60 degrees
HEX_ROUTE_WEIGHTS: list[float] = [
    round(math.cos(_HEX_ANGLE * k), 6) for k in range(HARMONY)
]
# → [1.0, 0.5, -0.5, -1.0, -0.5, 0.5] — full hexagonal symmetry
# Normalised to [0, 1] for routing confidence modulation:
HEX_ROUTE_CONFIDENCE: list[float] = [
    round((w + 1.0) / 2.0, 6) for w in HEX_ROUTE_WEIGHTS
]
# → [1.0, 0.75, 0.25, 0.0, 0.25, 0.75]
# Practical: take absolute value for symmetric relevance weighting
HEX_ROUTE_ABS: list[float] = [abs(w) for w in HEX_ROUTE_WEIGHTS]
# → [1.0, 0.5, 0.5, 1.0, 0.5, 0.5]


# ---------------------------------------------------------------------------
# Ensemble merging weights — 3 brain layers × 3 roles = 9-step pipeline
# ---------------------------------------------------------------------------
# Layer order: [Ouroboros(reason), OpenMythos(creative), Joi(warmth)]
# Each layer gets a phi-decayed weight across 3 contribution roles
ENSEMBLE_LAYER_WEIGHTS: dict[str, float] = {
    "ouroboros":   round(PHI_CONJUGATE ** 0, 6),  # 1.000 — primary anchor
    "openmythos":  round(PHI_CONJUGATE ** 1, 6),  # 0.618 — golden harmonic
    "joi":         round(PHI_CONJUGATE ** 2, 6),  # 0.382 — warmth resonance
}

# Three contribution roles × three layers = 9 total steps (Unity)
ENSEMBLE_ROLES = ["primary", "harmonic", "warmth"]  # TRINITY roles


# ---------------------------------------------------------------------------
# Utility: compute a 369-anchored dimension for QuantumState
# ---------------------------------------------------------------------------
def sacred_dim(base: int = 64) -> int:
    """
    Return the nearest dimension to `base` whose digital root is 3, 6, or 9.
    QuantumState initialized with this dimension resonates with 3-6-9 structure.
    """
    candidate = base
    while not is_369(candidate):
        candidate += 1
    return candidate


# Pre-computed sacred dims for common use
QUANTUM_DIM_SMALL  = sacred_dim(36)    # 36 → digital root 9 ✓ (Unity)
QUANTUM_DIM_MEDIUM = sacred_dim(63)    # 63 → digital root 9 ✓ (Unity)
QUANTUM_DIM_LARGE  = sacred_dim(126)   # 126 → digital root 9 ✓ (Unity)
