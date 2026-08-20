"""
aurion_unified_model.py  —  UNITY: Nine Voices, One Mind.

    LAYER 1 · SOUL   (φ⁰=1.000)   Voice 1 Ouroboros-9B  · Voice 2 Saturn-7B  · Voice 3 EVA-Qwen-7B
    LAYER 2 · REASON (φ⁻¹=0.618)  Voice 4 OpenMythos-9B · Voice 5 Gemma3-12B · Voice 6 Gemma4-26B
    LAYER 3 · HEART  (φ⁻²=0.382)  Voice 7 Nuro-7B       · Voice 8 Joi-Gemma-1B· Voice 9 Gemma4-Voice

    Temperatures  : 0.333 / 0.666 / 0.888 / 1.000
    Token ratios  : 0.333 / 0.666 / 0.999  (applied to TOKEN_BUDGET)
    Retries       : 3 s → 6 s → 9 s
    Memory gates  : 6 (HARMONY)
"""

from __future__ import annotations

import os, json, hashlib, logging, threading, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aurion.unified")

# ── Sacred geometry ──────────────────────────────────────────────────────────
try:
    from joi_companion.core.sacred_geometry import (
        PHI, PHI_CONJUGATE,
        TRINITY, HARMONY, UNITY,
        TEMP_ANCHOR, TEMP_HARMONIC, TEMP_CREATIVE, TEMP_PEAK,
        vortex_weight, phi_decay,
    )
    _SG = True
except Exception:
    PHI, PHI_CONJUGATE = 1.6180339887, 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9
    TEMP_ANCHOR, TEMP_HARMONIC, TEMP_CREATIVE, TEMP_PEAK = 0.333, 0.666, 0.888, 1.000
    vortex_weight = lambda n: (n % 9) / 9 or 1.0
    phi_decay = lambda s, steps=1: s * (PHI_CONJUGATE ** steps)
    _SG = False

# Sacred numeric constants — nothing arbitrary
# Token ratios: 0.333 / 0.666 / 0.999 applied to TOKEN_BUDGET to get integer counts
TOKEN_BUDGET   = int(os.getenv("AURION_TOKEN_BUDGET", "2000"))  # total budget per call
_R333, _R666, _R999 = 0.333, 0.666, 0.999                       # sacred ratios
_T333 = max(1, round(TOKEN_BUDGET * _R333))                      # ~666 at budget=2000
_T666 = max(1, round(TOKEN_BUDGET * _R666))                      # ~1332
_T999 = max(1, round(TOKEN_BUDGET * _R999))                      # ~1998
_RETRIES = (TRINITY, HARMONY, UNITY)                             # 3→6→9 s back-off
_TIMEOUT = UNITY * 10                                            # 90 s per call

# Nine-voice φ-decay weights: LayerMult × VoiceMult
_L1, _L2, _L3 = 1.0, PHI_CONJUGATE, PHI_CONJUGATE**2
NINE_VOICE_WEIGHTS = {
    "ouroboros":   _L1,
    "saturn":      _L1 * PHI_CONJUGATE,
    "eva":         _L1 * PHI_CONJUGATE**2,
    "openmythos":  _L2,
    "gemma3_12b":  _L2 * PHI_CONJUGATE,
    "gemma4_26b":  _L2 * PHI_CONJUGATE**2,
    "nuro":        _L3,
    "joi":         _L3 * PHI_CONJUGATE,
    "gemma4_voice":_L3 * PHI_CONJUGATE**2,
}


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class VoiceLayer:
    name: str           # key into NINE_VOICE_WEIGHTS
    model_key: str      # Ollama tag or remote model id
    layer_idx: int      # 1/2/3 — Soul/Reason/Heart
    voice_pos: int      # 1/2/3 within layer
    temperature: float  # sacred temperature (0.333/0.666/0.888)
    max_tokens: int     # sacred ceiling (333/666/999)
    provider: str = "ollama"   # "ollama" | "lmstudio" | "gemini"
    available: bool = False
    call_count: int = 0
    error_count: int = 0
    last_latency_ms: float = 0.0

    @property
    def weight(self) -> float:
        return NINE_VOICE_WEIGHTS.get(self.name, PHI_CONJUGATE**UNITY)

    @property
    def phi_weight(self) -> float:
        pos = (self.layer_idx - 1) * TRINITY + self.voice_pos  # 1..9
        return self.weight * vortex_weight(pos)


@dataclass
class UnifiedResponse:
    text: str
    fused: bool
    voices: Dict[str, str] = field(default_factory=dict)
    weights_used: Dict[str, float] = field(default_factory=dict)
    domain: str = "personal"
    temperature_used: float = TEMP_HARMONIC
    tokens_used: int = 0
    latency_ms: float = 0.0
    voices_active: int = 0
    sacred_signature: str = ""  # 9-char φ-hash (UNITY)


# ── Backend callers ───────────────────────────────────────────────────────────

def _post(url: str, payload: dict, headers: dict, timeout: int) -> Optional[str]:
    import urllib.request
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _enrich_with_soul(messages: list, ouroboros_base: str) -> list:
    """Inject Ouroboros soul context into the system prompt for Voice 1.

    Tries the live sidecar's /api/state endpoint first (reads identity/memory),
    then falls back to the local SQLite soul bridge. Returns messages unchanged
    on any error so inference always continues.
    """
    soul_block: Optional[str] = None

    # 1. Try live Ouroboros sidecar state
    try:
        raw = _post(
            f"{ouroboros_base}/api/state",
            {},
            {"Content-Type": "application/json"},
            TRINITY,  # 3 s fast timeout — don't stall inference
        )
        if isinstance(raw, dict):
            identity = raw.get("identity") or {}
            memory   = raw.get("recent_memory") or []
            parts = []
            if identity.get("name"):
                parts.append(f"[SOUL] Identity: {identity['name']}")
            if identity.get("core_values"):
                parts.append(f"[SOUL] Values: {identity['core_values']}")
            if memory:
                mem_str = " | ".join(str(m) for m in memory[-TRINITY:])
                parts.append(f"[SOUL] Recent: {mem_str}")
            if parts:
                soul_block = "\n".join(parts)
    except Exception:
        pass

    # 2. Fallback: local SQLite soul bridge
    if not soul_block:
        try:
            from ai_core.ouroboros_soul_bridge import get_soul
            soul_block = get_soul().to_system_block()
        except Exception:
            pass

    if not soul_block:
        return messages

    # Inject as first system message (or prepend to existing system message)
    msgs = list(messages)
    if msgs and msgs[0].get("role") == "system":
        msgs[0] = {"role": "system", "content": f"{soul_block}\n\n{msgs[0]['content']}"}
    else:
        msgs.insert(0, {"role": "system", "content": soul_block})
    return msgs


def _call_voice(
    voice: VoiceLayer,
    messages: list,
    temp: float,
    tokens: int,
    ollama_base: str,
    lms_base: str,
    ouroboros_base: str = "",
) -> Optional[str]:
    """Single dispatcher -- all providers share one path."""
    temp_r = round(temp, TRINITY)
    try:
        if voice.provider == "ouroboros":
            # Voice 1 (SOUL layer): enrich messages with live Ouroboros soul
            # context, then run inference via Ollama using the ouroboros-next model.
            # Ouroboros sidecar acts as memory/identity layer, not a completion API.
            enriched = _enrich_with_soul(messages, ouroboros_base or "http://127.0.0.1:8765")
            raw = _post(
                f"{ollama_base}/api/chat",
                {"model": voice.model_key, "messages": enriched, "stream": False,
                 "options": {"temperature": temp_r, "num_predict": tokens}},
                {"Content-Type": "application/json"},
                _TIMEOUT,
            )
            return str(raw.get("message", {}).get("content") or "").strip() or None

        if voice.provider == "ollama":
            raw = _post(
                f"{ollama_base}/api/chat",
                {"model": voice.model_key, "messages": messages, "stream": False,
                 "options": {"temperature": temp_r, "num_predict": tokens}},
                {"Content-Type": "application/json"},
                _TIMEOUT,
            )
            return str(raw.get("message", {}).get("content") or "").strip() or None

        if voice.provider == "lmstudio":
            raw = _post(
                f"{lms_base}/v1/chat/completions",
                {"model": voice.model_key, "messages": messages, "stream": False,
                 "temperature": temp_r, "max_tokens": tokens},
                {"Content-Type": "application/json", "Authorization": "Bearer lmstudio"},
                _TIMEOUT,
            )
            return str((raw.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip() or None

        if voice.provider == "gemini":
            key = os.getenv("GEMINI_API_KEY", "").strip()
            if not key:
                return None
            base = os.getenv("GEMINI_BASE_URL",
                             "https://generativelanguage.googleapis.com/v1beta/openai")
            raw = _post(
                f"{base}/chat/completions",
                {"model": voice.model_key, "messages": messages,
                 "temperature": temp_r, "max_tokens": tokens},
                {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                _TIMEOUT,
            )
            return str((raw.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip() or None

    except Exception as e:
        logger.debug("Voice %s [%s] failed: %s", voice.name, voice.provider, e)
    return None


# ── Unified model ─────────────────────────────────────────────────────────────

class AurionUnifiedModel:
    """3 layers × 3 voices = 9 = UNITY.  One inference entry-point for all of Aurion."""

    def __init__(self):
        self._lock = threading.Lock()
        self._ollama_base     = os.getenv("AURION_OLLAMA_BASE_URL",     "http://localhost:11434").rstrip("/")
        self._lms_base        = os.getenv("AURION_LMS_BASE_URL",        "http://localhost:1234").rstrip("/")
        self._ouroboros_base  = os.getenv("AURION_OUROBOROS_BASE_URL",  "http://127.0.0.1:8765").rstrip("/")

        # ── 9 voices across 3 layers (3-6-9) ──────────────────────────────────
        self.voices: List[VoiceLayer] = [
            # LAYER 1 — SOUL  (temp 0.333 · tokens ×0.999)
            VoiceLayer("ouroboros",   os.getenv("AURION_VOICE_1", "ouroboros-next"),     1, 1, TEMP_ANCHOR,   _T999, provider="ouroboros"),
            VoiceLayer("saturn",      os.getenv("AURION_VOICE_2", "saturn-7b"),          1, 2, TEMP_ANCHOR,   _T666),
            VoiceLayer("eva",         os.getenv("AURION_VOICE_3", "eva-7b"),             1, 3, TEMP_ANCHOR,   _T333),
            # LAYER 2 — REASON (temp 0.666 · tokens ×0.666)
            VoiceLayer("openmythos",  os.getenv("AURION_VOICE_4", "openmythos"),         2, 1, TEMP_HARMONIC, _T999),
            VoiceLayer("gemma3_12b",  os.getenv("AURION_VOICE_5", "gemma3-voice"),       2, 2, TEMP_HARMONIC, _T666),
            VoiceLayer("gemma4_26b",  os.getenv("AURION_VOICE_6", "qwen3-reason"),        2, 3, TEMP_HARMONIC, _T333),
            # LAYER 3 — HEART (temp 0.888 · tokens ×0.333)
            VoiceLayer("nuro",        os.getenv("AURION_VOICE_7", "nuro-voice"),         3, 1, TEMP_CREATIVE, _T666),
            VoiceLayer("joi",         os.getenv("AURION_VOICE_8", "joi"),                3, 2, TEMP_CREATIVE, _T333),
            VoiceLayer("gemma4_voice",os.getenv("AURION_VOICE_9", "gemma-3-12b-voice"),  3, 3, TEMP_CREATIVE, _T333),
        ]
        assert len(self.voices) == UNITY, "Must have exactly 9 voices"

        # ── 6 memory-routing domains (HARMONY gates) ──────────────────────────
        _s = ["ouroboros", "saturn", "eva"]
        _r = ["openmythos", "gemma3_12b", "gemma4_26b"]
        _h = ["nuro", "joi", "gemma4_voice"]
        self._domain_gate: Dict[str, List[str]] = {
            "personal":    _s + _h + _r,
            "memory":      _s + _r + _h,
            "knowledge":   _r + _s + _h,
            "collective":  _r + _h + _s,
            "creative":    _h + _s + _r,
            "exploration": _h + _r + _s,
        }
        assert len(self._domain_gate) == HARMONY, "Must have exactly 6 gates"

        # ── QCE ───────────────────────────────────────────────────────────────
        self._qce: Optional[Any] = None
        try:
            from joi_companion.core.quantum_cognition import QuantumCognitionEngine
            self._qce = QuantumCognitionEngine(mode=os.getenv("AURION_QUANTUM_MODE", "QUANTUM_INSPIRED"))
        except Exception:
            pass

        self._initialized = False
        logger.info("AurionUnifiedModel ready | voices=9 | SG=%s | QCE=%s", _SG, bool(self._qce))

    # ── Probe ─────────────────────────────────────────────────────────────────

    def probe(self) -> Dict[str, bool]:
        results = {}
        for v in self.voices:
            resp = _call_voice(v, [{"role": "user", "content": "ping"}],
                               TEMP_ANCHOR, TRINITY, self._ollama_base, self._lms_base,
                               self._ouroboros_base)
            v.available = resp is not None
            results[v.name] = v.available
        self._initialized = any(results.values())
        logger.info("Probe: %s", results)
        return results

    # ── Generate ──────────────────────────────────────────────────────────────

    def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        domain: str = "personal",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        session_id: str = "aurion",
    ) -> UnifiedResponse:
        t0 = time.time()
        user_text = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")

        # QCE domain routing
        qce_domain = domain
        if self._qce and user_text:
            try:
                qr = self._qce.reason(user_text, context={"session_id": session_id})
                qce_domain = qr.get("selected_domain", domain) or domain
            except Exception:
                pass

        # Domain gate → ordered voice names
        gate_order = self._domain_gate.get(qce_domain, self._domain_gate["personal"])
        ordered = sorted(self.voices, key=lambda v: gate_order.index(v.name) if v.name in gate_order else UNITY)

        base_temp   = temperature if temperature is not None else self._domain_temp(qce_domain)
        base_tokens = max_tokens  if max_tokens  is not None else _T666

        raw_voices: Dict[str, str] = {}
        weights_used: Dict[str, float] = {}

        for voice in ordered:
            # Per-voice sacred temperature: L1=0.333×base, L2=0.666×base, L3=1.0×base
            v_temp   = round(max(0.01, min(1.0, base_temp * voice.layer_idx / TRINITY)), TRINITY)
            v_tokens = min(voice.max_tokens, base_tokens)
            t_v = time.time()
            text: Optional[str] = None

            for attempt in range(TRINITY):  # retry 3 times, 3→6→9 s
                text = _call_voice(voice, messages, v_temp, v_tokens,
                                    self._ollama_base, self._lms_base,
                                    self._ouroboros_base)
                if text:
                    break
                if attempt < TRINITY - 1:
                    time.sleep(_RETRIES[attempt])

            voice.last_latency_ms = (time.time() - t_v) * 1000
            voice.call_count += 1
            if text:
                raw_voices[voice.name] = text
                gate_pos = gate_order.index(voice.name) if voice.name in gate_order else HARMONY
                weights_used[voice.name] = phi_decay(voice.phi_weight, gate_pos)
            else:
                voice.error_count += 1

        fused_text, is_fused = self._fuse(raw_voices, weights_used)
        latency = (time.time() - t0) * 1000

        resp = UnifiedResponse(
            text=fused_text,
            fused=is_fused and len(raw_voices) > 1,
            voices=raw_voices,
            weights_used=weights_used,
            domain=qce_domain,
            temperature_used=base_temp,
            tokens_used=sum(len(v.split()) for v in raw_voices.values()),
            latency_ms=round(latency, 1),
            voices_active=len(raw_voices),
            sacred_signature=hashlib.sha256(fused_text.encode()).hexdigest()[:UNITY],
        )
        logger.info("generate: domain=%s active=%d/%d fused=%s latency=%.0fms sig=%s",
                    qce_domain, resp.voices_active, UNITY, resp.fused, latency, resp.sacred_signature)
        return resp

    # ── φ-fusion ──────────────────────────────────────────────────────────────

    def _fuse(self, voices: Dict[str, str], weights: Dict[str, float]) -> Tuple[str, bool]:
        if not voices:
            return "", False
        if len(voices) == 1:
            return next(iter(voices.values())), False

        total_w = sum(weights.values()) or 1.0
        ranked  = sorted(voices.items(), key=lambda kv: weights.get(kv[0], 0.0), reverse=True)
        _, primary = ranked[0]
        primary_paras = [p.strip() for p in primary.split("\n\n") if p.strip()]

        # Collect secondary sentences with normalized weight
        secondary: List[Tuple[float, str]] = []
        for name, text in ranked[1:]:
            w = weights.get(name, 0.0) / total_w
            for s in text.replace("\n\n", " ").split(". "):
                s = s.strip()
                if s:
                    secondary.append((w, s if s.endswith(".") else s + "."))

        # Inject into primary paragraphs — only above φ⁻³ floor (0.236)
        floor = PHI_CONJUGATE ** TRINITY
        fused, sec_i = [], 0
        inject = max(0, round(len(secondary) * PHI_CONJUGATE / max(len(primary_paras), 1)))
        for para in primary_paras:
            fused.append(para)
            for _ in range(inject):
                if sec_i < len(secondary):
                    w, sent = secondary[sec_i]
                    if w >= floor:
                        fused[-1] = fused[-1].rstrip() + " " + sent
                    sec_i += 1

        return ("\n\n".join(fused).strip() or primary), True

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _domain_temp(self, domain: str) -> float:
        return {
            "personal": TEMP_ANCHOR, "memory": TEMP_ANCHOR,
            "knowledge": TEMP_HARMONIC, "collective": TEMP_HARMONIC,
            "creative": TEMP_CREATIVE, "exploration": TEMP_PEAK,
        }.get(domain, TEMP_HARMONIC)

    def status(self) -> Dict[str, Any]:
        return {
            "voices": UNITY,
            "active": sum(1 for v in self.voices if v.available),
            "sacred_geometry": _SG,
            "qce": bool(self._qce),
            "constants": {"3": TRINITY, "6": HARMONY, "9": UNITY, "phi": PHI},
            "voice_table": [
                {"name": v.name, "layer": v.layer_idx, "pos": v.voice_pos,
                 "weight": round(v.weight, TRINITY), "provider": v.provider,
                 "available": v.available, "calls": v.call_count, "errors": v.error_count}
                for v in self.voices
            ],
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[AurionUnifiedModel] = None
_lock = threading.Lock()


def get_unified_model() -> AurionUnifiedModel:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = AurionUnifiedModel()
    return _instance


def unified_generate(
    messages: List[Dict[str, str]],
    *,
    domain: str = "personal",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    session_id: str = "aurion",
) -> UnifiedResponse:
    return get_unified_model().generate(
        messages, domain=domain, temperature=temperature,
        max_tokens=max_tokens, session_id=session_id,
    )
