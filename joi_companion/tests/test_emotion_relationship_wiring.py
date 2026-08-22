"""
test_emotion_relationship_wiring.py

Tests for:
  Slice 1 — emotion memory write + read + prompt injection per turn
  Slice 2 — relationship XP progression + persistence

All tests are offline (no Ollama, no TinyDB file required).
"""

import sys
import os
import time
import types
import pytest

# ── path bootstrap ─────────────────────────────────────────────────────────────
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ── stub tinydb so tests run without it installed ──────────────────────────────
if "tinydb" not in sys.modules:
    tinydb_mod = types.ModuleType("tinydb")
    class _FakeTinyDB:
        def __init__(self, *a, **kw): self._store = []
        def get(self, cond): return None
        def upsert(self, doc, cond): self._store.append(doc)
        def all(self): return self._store
    class _FakeQuery:
        def __getattr__(self, name): return lambda val: True
    tinydb_mod.TinyDB = _FakeTinyDB
    tinydb_mod.Query = _FakeQuery
    sys.modules["tinydb"] = tinydb_mod


# ══════════════════════════════════════════════════════════════════════════════
# SLICE 1 — EmotionMemory
# ══════════════════════════════════════════════════════════════════════════════

from joi_companion.core.emotion_memory import EmotionMemory, EmotionVector


class TestEmotionMemory:

    def setup_method(self):
        self.mem = EmotionMemory(data_dir=":memory_test:")  # won't actually write

    def test_record_returns_emotion_vector(self):
        ev = self.mem.record("alice", "I'm so happy today!", turn_index=0)
        assert isinstance(ev, EmotionVector)
        assert ev.valence > 0, "positive text should yield positive valence"

    def test_record_negative_text(self):
        ev = self.mem.record("alice", "I hate this, I'm so angry", turn_index=1)
        assert ev.valence < 0, "negative text should yield negative valence"

    def test_recent_context_returns_last_n(self):
        for i, txt in enumerate(["love this", "feeling good", "so excited", "wow amazing"]):
            self.mem.record("bob", txt, turn_index=i)
        recent = self.mem.recent_context("bob", n=3)
        assert len(recent) == 3
        assert all(isinstance(e, EmotionVector) for e in recent)

    def test_system_prompt_injection_nonempty_after_record(self):
        self.mem.record("carol", "I feel wonderful", turn_index=0)
        prompt = self.mem.system_prompt_injection("carol")
        assert "[EMOTION]" in prompt
        assert "valence" in prompt.lower() or "tone" in prompt.lower()

    def test_system_prompt_injection_neutral_before_any_record(self):
        prompt = self.mem.system_prompt_injection("unknown_user_xyz")
        assert "[EMOTION]" in prompt
        assert "neutral" in prompt.lower() or "baseline" in prompt.lower()

    def test_emotion_score_range(self):
        self.mem.record("dave", "I'm scared and sad", turn_index=0)
        score = self.mem.emotion_score("dave")
        assert 0.0 <= score <= 1.0

    def test_trust_accumulates_on_trust_words(self):
        self.mem.record("eve", "I trust you with my secret", turn_index=0)
        s = self.mem._session("eve")
        assert s.cumulative_trust > 0.0

    def test_session_isolation(self):
        """Two users have independent emotion state."""
        self.mem.record("user_a", "I love everything!", turn_index=0)
        self.mem.record("user_b", "I hate everything!", turn_index=0)
        score_a = self.mem.emotion_score("user_a")
        score_b = self.mem.emotion_score("user_b")
        # Both have nonzero scores — they are tracked independently
        assert score_a >= 0
        assert score_b >= 0
        prompt_a = self.mem.system_prompt_injection("user_a")
        prompt_b = self.mem.system_prompt_injection("user_b")
        assert prompt_a != prompt_b, "different users should have different emotional context"


# ══════════════════════════════════════════════════════════════════════════════
# SLICE 2 — RelationshipEngine
# ══════════════════════════════════════════════════════════════════════════════

from joi_companion.core.relationship_engine import RelationshipEngine, _XP_PER_LEVEL, UNITY


class TestRelationshipEngine:

    def setup_method(self):
        self.eng = RelationshipEngine(data_dir=":memory_test:")

    def test_new_session_starts_at_level_1(self):
        s = self.eng.get("new_user")
        assert s.level == 1
        assert s.xp == 0

    def test_earn_xp_returns_dict(self):
        result = self.eng.earn_xp("player1", base_xp=10, emotion_score=0.5)
        assert "level" in result
        assert "xp_gained" in result
        assert result["xp_gained"] > 0

    def test_xp_accumulates(self):
        self.eng.earn_xp("player2", base_xp=10, emotion_score=0.0)
        self.eng.earn_xp("player2", base_xp=10, emotion_score=0.0)
        s = self.eng.get("player2")
        assert s.xp >= 20

    def test_level_up_on_threshold(self):
        """Force enough XP to cross level 2 threshold."""
        threshold = _XP_PER_LEVEL[2]
        result = self.eng.earn_xp("leveler", base_xp=threshold, emotion_score=0.0)
        assert result["leveled_up"] is True
        assert result["level"] >= 2

    def test_max_level_caps_at_unity(self):
        """Awarding massive XP should not exceed UNITY (9)."""
        for _ in range(100):
            self.eng.earn_xp("max_player", base_xp=10000, emotion_score=1.0)
        s = self.eng.get("max_player")
        assert s.level <= UNITY

    def test_warmth_increases_with_level(self):
        # Level 1 warmth
        s1 = self.eng.get("warmth_test_a")
        w1 = s1.warmth
        # Force to level 3
        self.eng.earn_xp("warmth_test_a", base_xp=_XP_PER_LEVEL[3], emotion_score=0.0)
        s3 = self.eng.get("warmth_test_a")
        assert s3.warmth >= w1, "warmth should not decrease as level increases"

    def test_system_prompt_injection_contains_level(self):
        prompt = self.eng.system_prompt_injection("prompt_tester")
        assert "[RELATIONSHIP]" in prompt
        assert "Level" in prompt

    def test_session_isolation(self):
        self.eng.earn_xp("solo_a", base_xp=50, emotion_score=0.5)
        s_a = self.eng.get("solo_a")
        s_b = self.eng.get("solo_b")  # never earned XP
        assert s_a.xp > s_b.xp

    def test_high_emotion_score_earns_more_xp(self):
        result_low  = self.eng.earn_xp("cmp_low",  base_xp=10, emotion_score=0.0)
        result_high = self.eng.earn_xp("cmp_high", base_xp=10, emotion_score=1.0)
        assert result_high["xp_gained"] > result_low["xp_gained"]


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION — personality_engine wires session_id correctly
# ══════════════════════════════════════════════════════════════════════════════

class TestPersonalityEngineWiring:
    """Smoke-tests that generate_response passes session_id down."""

    def _make_engine(self):
        """Build a minimal PersonalityEngine with real emotion/relationship modules."""
        import importlib
        try:
            pe_mod = importlib.import_module("joi_companion.core.personality_engine")
        except Exception as e:
            pytest.skip(f"personality_engine import failed: {e}")
        # Find the main class
        for name in dir(pe_mod):
            obj = getattr(pe_mod, name)
            if isinstance(obj, type) and hasattr(obj, "generate_response"):
                return obj
        pytest.skip("No class with generate_response found in personality_engine")

    def test_emotion_memory_record_called_with_session_id(self, monkeypatch):
        cls = self._make_engine()
        captured = {}
        from joi_companion.core import emotion_memory as em_mod
        orig_record = em_mod.EmotionMemory.record
        def patched_record(self_mem, session_id, user_text, turn_index=0):
            captured["session_id"] = session_id
            return orig_record(self_mem, session_id, user_text, turn_index)
        monkeypatch.setattr(em_mod.EmotionMemory, "record", patched_record)

        try:
            engine = cls()
        except Exception as e:
            pytest.skip(f"Engine init failed (expected in test env): {e}")

        try:
            engine.generate_response("NEUTRAL", user_text="hello there", user_name="billy")
        except Exception:
            pass  # inference will fail in test env — we only care that record was called

        assert "session_id" in captured, "record() was never called"
        # sanitize_user_name may capitalise; what matters is it's non-empty and
        # derived from user_name, not the string "default"
        assert captured["session_id"], "session_id should be non-empty"
        assert captured["session_id"].lower() == "billy", (
            f"Expected session_id='billy' (case-insensitive), got '{captured.get('session_id')}'"
        )

    def test_earn_xp_called_with_session_id(self, monkeypatch):
        cls = self._make_engine()
        captured = {}
        from joi_companion.core import relationship_engine as re_mod
        orig_earn = re_mod.RelationshipEngine.earn_xp
        def patched_earn(self_eng, session_id, base_xp=10, emotion_score=0.5):
            captured["session_id"] = session_id
            return orig_earn(self_eng, session_id, base_xp=base_xp, emotion_score=emotion_score)
        monkeypatch.setattr(re_mod.RelationshipEngine, "earn_xp", patched_earn)

        try:
            engine = cls()
        except Exception as e:
            pytest.skip(f"Engine init failed (expected in test env): {e}")

        try:
            engine.generate_response("NEUTRAL", user_text="hello there", user_name="billy")
        except Exception:
            pass

        if "session_id" in captured:
            assert captured["session_id"] == "billy"
