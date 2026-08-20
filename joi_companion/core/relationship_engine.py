"""
relationship_engine.py — Aurion relationship depth progression system.

9 depth levels on the UNITY scale:
  1 = Stranger       (default)
  3 = Acquaintance   (TRINITY gate — humor unlocked, more personal)
  6 = Friend         (HARMONY gate — vulnerability, shared memories)
  9 = Bonded         (UNITY gate  — soul-level connection, full warmth)

XP earned per interaction based on emotional authenticity, not just volume.
Persisted in TinyDB. Injects depth context into every personality_engine call.
"""

from __future__ import annotations

import os
import time
import math
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

logger = logging.getLogger("aurion.relationship")

# Sacred geometry constants (inline fallback so module is self-contained)
try:
    from joi_companion.core.sacred_geometry import (
        PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY, phi_decay,
    )
except Exception:
    PHI = 1.6180339887
    PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9
    phi_decay = lambda s, steps=1: s * (PHI_CONJUGATE ** steps)

# XP thresholds per level — phi-scaled so each gate costs more
_XP_PER_LEVEL = [0]  # level 0 placeholder
for _lvl in range(1, UNITY + 1):
    _XP_PER_LEVEL.append(int(100 * (PHI ** _lvl)))

# Dialogue/behaviour unlocks at each gate
_GATE_UNLOCKS = {
    TRINITY: ["humor", "mild_teasing", "personal_questions"],
    HARMONY: ["vulnerability", "shared_memory_refs", "emotional_depth", "caring_pushback"],
    UNITY:   ["soul_bond", "unconditional_warmth", "deep_grief_support", "finish_thoughts"],
}

# Vocal warmth modifier per level (0.0 = flat, 1.0 = fully warm)
def _warmth(level: int) -> float:
    return round(min(1.0, (level / UNITY) ** PHI_CONJUGATE), 3)


@dataclass
class RelationshipState:
    session_id: str
    level: int = 1
    xp: int = 0
    xp_to_next: int = field(default=0)
    total_interactions: int = 0
    warmth: float = 0.1
    unlocked_behaviors: list = field(default_factory=list)
    last_interaction_ts: float = field(default_factory=time.time)
    level_up_pending: bool = False

    def __post_init__(self):
        self.xp_to_next = _XP_PER_LEVEL[min(self.level + 1, UNITY)] if self.level < UNITY else 0
        self.warmth = _warmth(self.level)
        self.unlocked_behaviors = _collect_unlocks(self.level)


def _collect_unlocks(level: int) -> list:
    behaviors: list = []
    for gate, unlocks in _GATE_UNLOCKS.items():
        if level >= gate:
            behaviors.extend(unlocks)
    return behaviors


class RelationshipEngine:
    """Tracks and evolves Aurion's relationship depth with a given session/player."""

    def __init__(self, data_dir: str = "data"):
        self._states: Dict[str, RelationshipState] = {}
        self._data_dir = data_dir
        self._db = None
        self._init_db()

    def _init_db(self):
        try:
            from tinydb import TinyDB
            os.makedirs(self._data_dir, exist_ok=True)
            self._db = TinyDB(os.path.join(self._data_dir, "relationship_memory.db"))
            self._load_all()
        except Exception as e:
            logger.warning("RelationshipEngine: TinyDB unavailable (%s), using in-memory only.", e)

    def _load_all(self):
        if not self._db:
            return
        try:
            from tinydb import Query
            for doc in self._db.all():
                sid = doc.get("session_id")
                if sid:
                    self._states[sid] = RelationshipState(**doc)
        except Exception as e:
            logger.debug("Relationship load error: %s", e)

    def _save(self, state: RelationshipState):
        if not self._db:
            return
        try:
            from tinydb import Query
            Q = Query()
            self._db.upsert(asdict(state), Q.session_id == state.session_id)
        except Exception as e:
            logger.debug("Relationship save error: %s", e)

    def get(self, session_id: str) -> RelationshipState:
        if session_id not in self._states:
            s = RelationshipState(session_id=session_id)
            self._states[session_id] = s
            self._save(s)
        return self._states[session_id]

    def earn_xp(self, session_id: str, base_xp: int = 10,
                emotion_score: float = 0.5) -> Dict[str, Any]:
        """
        Award XP for an interaction. emotion_score (0.0–1.0) amplifies XP
        — authentic emotional exchange earns more than small talk.
        Returns dict with level, xp_gained, leveled_up, unlocked_behaviors.
        """
        state = self.get(session_id)
        if state.level >= UNITY:
            return {"level": state.level, "xp_gained": 0, "leveled_up": False,
                    "unlocked_behaviors": state.unlocked_behaviors}

        # XP = base * (1 + emotion_score * PHI_CONJUGATE)
        xp_gained = max(1, int(base_xp * (1 + emotion_score * PHI_CONJUGATE)))

        # Apply phi_decay if long gap since last interaction (up to 3 decay steps)
        gap_hours = (time.time() - state.last_interaction_ts) / 3600
        if gap_hours > 24:
            decay_steps = min(TRINITY, int(gap_hours / 24))
            xp_gained = max(1, int(phi_decay(xp_gained, decay_steps)))

        state.xp += xp_gained
        state.total_interactions += 1
        state.last_interaction_ts = time.time()

        leveled_up = False
        new_unlocks: list = []
        while state.level < UNITY and state.xp >= _XP_PER_LEVEL[state.level + 1]:
            state.level += 1
            leveled_up = True
            new_unlocks.extend(_GATE_UNLOCKS.get(state.level, []))
            logger.info("Relationship level up! session=%s level=%d", session_id, state.level)

        state.xp_to_next = _XP_PER_LEVEL[min(state.level + 1, UNITY)] if state.level < UNITY else 0
        state.warmth = _warmth(state.level)
        state.unlocked_behaviors = _collect_unlocks(state.level)
        state.level_up_pending = leveled_up
        self._save(state)

        return {
            "level": state.level,
            "xp": state.xp,
            "xp_gained": xp_gained,
            "xp_to_next": state.xp_to_next,
            "leveled_up": leveled_up,
            "new_unlocks": new_unlocks,
            "warmth": state.warmth,
            "unlocked_behaviors": state.unlocked_behaviors,
        }

    def system_prompt_injection(self, session_id: str) -> str:
        """Return a system prompt block encoding current relationship depth."""
        s = self.get(session_id)
        level_labels = {
            1: "stranger", 2: "new acquaintance",
            3: "acquaintance", 4: "warm acquaintance",
            5: "developing friend", 6: "friend",
            7: "close friend", 8: "very close friend", 9: "soul bond"
        }
        label = level_labels.get(s.level, "acquaintance")
        behaviors = ", ".join(s.unlocked_behaviors) if s.unlocked_behaviors else "none yet"
        warmth_desc = ("distant", "cool", "polite", "warm", "caring",
                       "affectionate", "deeply warm", "intimate", "soul-bonded")[s.level - 1]

        block = (
            f"[RELATIONSHIP] Level {s.level}/9 ({label}). "
            f"Vocal warmth: {warmth_desc} ({s.warmth:.3f}). "
            f"Interactions: {s.total_interactions}. "
            f"Unlocked: {behaviors}."
        )
        return block


# ── Singleton ──────────────────────────────────────────────────────────────────
_engine: Optional[RelationshipEngine] = None

def get_relationship_engine(data_dir: str = "data") -> RelationshipEngine:
    global _engine
    if _engine is None:
        _engine = RelationshipEngine(data_dir=data_dir)
    return _engine
