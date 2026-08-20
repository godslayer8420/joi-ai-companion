"""
emotion_memory.py — Per-turn emotional state tracking for Aurion.

Tracks valence (positive/negative), arousal (calm/intense), and trust across
every conversation turn. Feeds last TRINITY turns of emotion context into
inference. Stores emotion vectors alongside message history in TinyDB.

All decay follows phi_decay() from sacred geometry.
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional

logger = logging.getLogger("aurion.emotion")

try:
    from joi_companion.core.sacred_geometry import (
        PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY, phi_decay,
    )
except Exception:
    PHI = 1.6180339887
    PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9
    phi_decay = lambda s, steps=1: s * (PHI_CONJUGATE ** steps)

# Emotion keywords → (valence_delta, arousal_delta)
_KEYWORD_SIGNALS: Dict[str, tuple] = {
    # positive
    "love": (0.8, 0.3), "happy": (0.6, 0.2), "excited": (0.5, 0.7),
    "thank": (0.4, 0.1), "great": (0.4, 0.2), "wonderful": (0.5, 0.1),
    "amazing": (0.6, 0.4), "good": (0.3, 0.1), "nice": (0.3, 0.1),
    "fun": (0.4, 0.4), "glad": (0.4, 0.1), "proud": (0.5, 0.2),
    # negative
    "sad": (-0.5, -0.2), "angry": (-0.6, 0.8), "frustrated": (-0.4, 0.5),
    "hate": (-0.7, 0.6), "hurt": (-0.5, 0.2), "lonely": (-0.4, -0.3),
    "scared": (-0.4, 0.6), "depressed": (-0.7, -0.4), "terrible": (-0.6, 0.2),
    "awful": (-0.6, 0.3), "bad": (-0.3, 0.1), "wrong": (-0.3, 0.2),
    # trust signals
    "trust": (0.3, 0.0), "honest": (0.3, 0.0), "secret": (0.2, 0.1),
    "personal": (0.2, 0.1), "private": (0.2, 0.1),
}


@dataclass
class EmotionVector:
    """One turn's emotional snapshot."""
    valence: float = 0.0      # -1.0 (very negative) to +1.0 (very positive)
    arousal: float = 0.0      # -1.0 (calm/sleepy) to +1.0 (intense/excited)
    trust: float = 0.0        # 0.0 (neutral) to +1.0 (deep trust)
    timestamp: float = field(default_factory=time.time)
    turn_index: int = 0
    text_snippet: str = ""    # first 60 chars for debugging


@dataclass
class EmotionSession:
    session_id: str
    turns: List[dict] = field(default_factory=list)  # list of EmotionVector dicts
    cumulative_valence: float = 0.0
    cumulative_trust: float = 0.0


def _detect_emotion(text: str) -> EmotionVector:
    """Heuristic emotion detection from text — no API calls, pure local."""
    text_lower = text.lower()
    valence = 0.0
    arousal = 0.0
    trust = 0.0
    hits = 0
    for kw, (v, a) in _KEYWORD_SIGNALS.items():
        if kw in text_lower:
            valence += v
            arousal += a
            if kw in ("trust", "honest", "secret", "personal", "private"):
                trust += 0.2
            hits += 1
    if hits > 0:
        valence = max(-1.0, min(1.0, valence / hits))
        arousal = max(-1.0, min(1.0, arousal / hits))
        trust = max(0.0, min(1.0, trust))
    # Question marks → slightly higher arousal (engagement)
    if text.count("?") > 0:
        arousal = min(1.0, arousal + 0.1)
    # Exclamation marks → arousal + valence boost
    if text.count("!") > 1:
        arousal = min(1.0, arousal + 0.15)
        valence = min(1.0, valence + 0.1)
    return EmotionVector(
        valence=round(valence, 3),
        arousal=round(arousal, 3),
        trust=round(trust, 3),
        text_snippet=text[:60],
    )


class EmotionMemory:
    """Records and retrieves emotional state across conversation turns."""

    def __init__(self, data_dir: str = "data"):
        self._sessions: Dict[str, EmotionSession] = {}
        self._data_dir = data_dir
        self._db = None
        self._init_db()

    def _init_db(self):
        try:
            from tinydb import TinyDB
            os.makedirs(self._data_dir, exist_ok=True)
            self._db = TinyDB(os.path.join(self._data_dir, "emotion_memory.db"))
        except Exception as e:
            logger.warning("EmotionMemory: TinyDB unavailable (%s)", e)

    def _session(self, sid: str) -> EmotionSession:
        if sid not in self._sessions:
            # Try load from DB
            if self._db:
                try:
                    from tinydb import Query
                    doc = self._db.get(Query().session_id == sid)
                    if doc:
                        s = EmotionSession(session_id=sid,
                                           turns=doc.get("turns", []),
                                           cumulative_valence=doc.get("cumulative_valence", 0.0),
                                           cumulative_trust=doc.get("cumulative_trust", 0.0))
                        self._sessions[sid] = s
                        return s
                except Exception:
                    pass
            self._sessions[sid] = EmotionSession(session_id=sid)
        return self._sessions[sid]

    def record(self, session_id: str, user_text: str, turn_index: int = 0) -> EmotionVector:
        """Analyse user_text and store emotion vector. Returns the vector."""
        ev = _detect_emotion(user_text)
        ev.turn_index = turn_index
        s = self._session(session_id)
        s.turns.append(asdict(ev))
        # Cumulative with phi_decay on older values
        s.cumulative_valence = round(
            phi_decay(s.cumulative_valence) + ev.valence * PHI_CONJUGATE, 3)
        s.cumulative_trust = round(
            min(1.0, s.cumulative_trust + ev.trust * 0.1), 3)
        # Persist (keep last UNITY*UNITY turns to bound DB size)
        s.turns = s.turns[-(UNITY * UNITY):]
        if self._db:
            try:
                from tinydb import Query
                self._db.upsert({
                    "session_id": sid,
                    "turns": s.turns,
                    "cumulative_valence": s.cumulative_valence,
                    "cumulative_trust": s.cumulative_trust,
                }, Query().session_id == session_id)
            except Exception:
                pass
        return ev

    def recent_context(self, session_id: str, n: int = TRINITY) -> List[EmotionVector]:
        """Return last n emotion vectors for context injection."""
        s = self._session(session_id)
        recent = s.turns[-n:]
        return [EmotionVector(**t) for t in recent]

    def system_prompt_injection(self, session_id: str) -> str:
        """Return system prompt block encoding recent emotional tone."""
        s = self._session(session_id)
        recent = self.recent_context(session_id, TRINITY)
        if not recent:
            return "[EMOTION] Neutral baseline. No prior emotional signals."

        avg_valence = sum(e.valence for e in recent) / len(recent)
        avg_arousal = sum(e.arousal for e in recent) / len(recent)

        valence_label = (
            "very positive" if avg_valence > 0.5 else
            "positive" if avg_valence > 0.2 else
            "neutral" if avg_valence > -0.2 else
            "negative" if avg_valence > -0.5 else "very negative"
        )
        arousal_label = (
            "highly engaged" if avg_arousal > 0.5 else
            "engaged" if avg_arousal > 0.1 else
            "calm" if avg_arousal > -0.2 else "subdued"
        )
        trust_note = (
            f" Trust level: {s.cumulative_trust:.2f}/1.0."
            if s.cumulative_trust > 0.1 else ""
        )
        return (
            f"[EMOTION] Recent tone: {valence_label}, {arousal_label}."
            f" Valence={avg_valence:.2f}, Arousal={avg_arousal:.2f}.{trust_note}"
            f" Respond with matching emotional attunement."
        )

    def emotion_score(self, session_id: str) -> float:
        """0.0–1.0 score of emotional richness — used for XP multiplier."""
        recent = self.recent_context(session_id, TRINITY)
        if not recent:
            return 0.3
        intensity = sum(abs(e.valence) + abs(e.arousal) for e in recent) / (len(recent) * 2)
        return round(min(1.0, intensity), 3)


# ── Singleton ──────────────────────────────────────────────────────────────────
_mem: Optional[EmotionMemory] = None

def get_emotion_memory(data_dir: str = "data") -> EmotionMemory:
    global _mem
    if _mem is None:
        _mem = EmotionMemory(data_dir=data_dir)
    return _mem
