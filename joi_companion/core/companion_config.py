"""
Aurion Companion Config — UI parameter defaults and sampling config.
Original architecture by Billy — integrated into joi_companion core.

These values mirror the React CompanionConfigDashboard (5.js) defaults
so the Python backend and frontend stay in sync.

Sacred geometry numerology applied throughout:
  - Token limits: 0.333, 0.666, 0.999 fractions (never hit round 333/666/999)
  - Context: 9999, 6666, 3333
  - Sacred ratios: 0.333 = devotion, 0.666 = harmony, 0.999 = completion
"""

from dataclasses import dataclass, field
from typing import Dict, Any


# ---------------------------------------------------------------------------
# Sampling / AI Engine defaults
# ---------------------------------------------------------------------------

SAMPLING_DEFAULTS: Dict[str, Any] = {
    # Sacred decimal fractions — never exactly 333/666/999
    "temperature":          0.666,
    "min_p":                0.033,
    "top_p":                0.999,
    "dry_multiplier":       0.333,
    "xtc_probability":      0.099,
    "repetition_penalty":   1.12,
    "repetition_range":     1333,
    "max_response_tokens":  1333,     # 1+3+3+3 = 10 → 1
    "presence_penalty":     0.033,
    "frequency_penalty":    0.066,
}


# ---------------------------------------------------------------------------
# Aurion persona sliders (0–100)
# ---------------------------------------------------------------------------

@dataclass
class PersonaConfig:
    warmth:         int = 85
    dominance:      int = 40
    verbosity:      int = 60
    explicit_bias:  int = 75
    sarcasm:        int = 30
    volatility:     int = 20


# ---------------------------------------------------------------------------
# Memory & context
# ---------------------------------------------------------------------------

@dataclass
class MemoryConfig:
    context_size:           int   = 9999     # 9+9+9+9 = 36 → 9
    system_prompt_pinned:   bool  = True
    auto_summary_interval:  int   = 15       # every 15 turns → 1+5 = 6
    rag_top_k:              int   = 6        # 6 = harmony
    rag_similarity_cutoff:  float = 0.666    # 0.666 = harmonic fraction


# ---------------------------------------------------------------------------
# Voice / TTS
# ---------------------------------------------------------------------------

@dataclass
class VoiceConfig:
    speech_speed:    float = 1.0
    voice_pitch:     float = 1.0
    emotion_weight:  int   = 66      # 6+6 = 12 → 3
    tts_stability:   float = 0.666
    auto_tts:        bool  = True


# ---------------------------------------------------------------------------
# Visual / image gen
# ---------------------------------------------------------------------------

@dataclass
class VisualConfig:
    visual_sensitivity:  int   = 2     # 0:Off 1:Low 2:Medium 3:EveryTurn
    denoising_strength:  float = 0.333
    cfg_scale:           float = 6.66  # 6.66 = harmonic


# ---------------------------------------------------------------------------
# 3D/2D Avatar
# ---------------------------------------------------------------------------

@dataclass
class AvatarConfig:
    # Body morphs
    body_height_cm:     float = 165.0
    body_weight_kg:     float = 55.0
    bust_size:          float = 0.666
    waist_size:         float = 0.333
    hip_size:           float = 0.666
    muscle_definition:  float = 0.25
    shoulder_width:     float = 0.50
    leg_to_torso_ratio: float = 0.55

    # Facial blendshapes (Live2D / VRM)
    eye_size:               float = 0.50
    eye_tilt:               float = 0.00
    nose_bridge_width:      float = 0.333
    lip_fullness:           float = 0.666
    jawline_sharpness:      float = 0.333
    cheekbone_height:       float = 0.50
    expression_bias_smile:  float = 0.333

    # Skin & texture
    skin_tone:              float = 0.30
    skin_gloss_specular:    float = 0.333
    blush_intensity:        float = 0.333
    freckles_blemishes:     float = 0.099

    # Physics
    softbody_physics_jiggle:    float = 0.666
    hair_physics_stiffness:     float = 0.50
    gravity_influence:          float = 0.50

    # Outfit
    clothing_tightness:     float = 0.666
    outfit_reveal_factor:   float = 0.50


# ---------------------------------------------------------------------------
# Master config container
# ---------------------------------------------------------------------------

@dataclass
class AurionConfig:
    sampling:  Dict[str, Any]  = field(default_factory=lambda: dict(SAMPLING_DEFAULTS))
    persona:   PersonaConfig   = field(default_factory=PersonaConfig)
    memory:    MemoryConfig    = field(default_factory=MemoryConfig)
    voice:     VoiceConfig     = field(default_factory=VoiceConfig)
    visual:    VisualConfig    = field(default_factory=VisualConfig)
    avatar:    AvatarConfig    = field(default_factory=AvatarConfig)


# Singleton default config (importable directly)
DEFAULT_CONFIG = AurionConfig()
