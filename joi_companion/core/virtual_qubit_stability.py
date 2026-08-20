import json
import math
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

@dataclass
class VirtualQubitConfig:
    enabled: bool = True
    temperature: float = 0.01            # near-zero drift by default
    max_amplitude: float = 1.0
    decoherence_threshold: float = 0.02
    correction_interval_sec: float = 5.0
    max_states_in_memory: int = 256
    offload_dir: str = r"D:\AurionData\CloudMemory\qubit_cache"
    paging_enabled: bool = True

@dataclass
class VirtualQubitState:
    key: str
    amplitudes: List[float]
    last_corrected_ts: float
    temperature: float

class VirtualQubitStability:
    """
    Software 'virtual qubit' envelope:
    - bounded amplitudes
    - deterministic renormalization
    - decoherence guard + correction cadence
    - optional paging/offload to disk (RAM pressure control)
    """

    def __init__(self, config: VirtualQubitConfig | None = None):
        self.config = config or VirtualQubitConfig()
        self._states: Dict[str, VirtualQubitState] = {}
        self._offload_dir = Path(self.config.offload_dir)
        if self.config.paging_enabled:
            self._offload_dir.mkdir(parents=True, exist_ok=True)

    def _normalize(self, amps: List[float]) -> List[float]:
        if not amps:
            return [1.0]
        clamped = [max(-self.config.max_amplitude, min(self.config.max_amplitude, float(a))) for a in amps]
        norm = math.sqrt(sum(a * a for a in clamped))
        if norm <= 1e-12:
            return [1.0] + [0.0] * (len(clamped) - 1)
        return [a / norm for a in clamped]

    def _decoherence_score(self, amps: List[float]) -> float:
        # deterministic score proxy from amplitude spread + temperature
        if not amps:
            return 0.0
        mean = sum(amps) / len(amps)
        var = sum((a - mean) ** 2 for a in amps) / len(amps)
        return min(1.0, var + self.config.temperature)

    def _should_correct(self, state: VirtualQubitState) -> bool:
        elapsed = time.time() - state.last_corrected_ts
        if elapsed >= self.config.correction_interval_sec:
            return True
        return self._decoherence_score(state.amplitudes) >= self.config.decoherence_threshold

    def _state_path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return self._offload_dir / f"{safe}.json"

    def set_state(self, key: str, amplitudes: List[float]) -> VirtualQubitState:
        amps = self._normalize(amplitudes)
        st = VirtualQubitState(key=key, amplitudes=amps, last_corrected_ts=time.time(), temperature=self.config.temperature)
        self._states[key] = st
        self._enforce_memory_cap()
        return st

    def get_state(self, key: str) -> VirtualQubitState | None:
        st = self._states.get(key)
        if st:
            if self._should_correct(st):
                st.amplitudes = self._normalize(st.amplitudes)
                st.last_corrected_ts = time.time()
            return st

        # load from disk if paged out
        if self.config.paging_enabled:
            p = self._state_path(key)
            if p.exists():
                obj = json.loads(p.read_text(encoding="utf-8"))
                st = VirtualQubitState(**obj)
                if self._should_correct(st):
                    st.amplitudes = self._normalize(st.amplitudes)
                    st.last_corrected_ts = time.time()
                self._states[key] = st
                self._enforce_memory_cap()
                return st
        return None

    def snapshot(self) -> Dict[str, dict]:
        return {k: asdict(v) for k, v in self._states.items()}

    def _enforce_memory_cap(self) -> None:
        if not self.config.paging_enabled:
            return
        if len(self._states) <= self.config.max_states_in_memory:
            return

        # oldest first
        victims: List[Tuple[str, VirtualQubitState]] = sorted(
            self._states.items(), key=lambda kv: kv[1].last_corrected_ts
        )
        over = len(self._states) - self.config.max_states_in_memory
        for i in range(over):
            key, st = victims[i]
            p = self._state_path(key)
            p.write_text(json.dumps(asdict(st), ensure_ascii=False), encoding="utf-8")
            self._states.pop(key, None)

def build_virtual_qubit_stability_from_env() -> VirtualQubitStability:
    cfg = VirtualQubitConfig(
        enabled=os.getenv("AURION_VQ_ENABLED", "1") not in ("0", "false", "False"),
        temperature=float(os.getenv("AURION_VQ_TEMPERATURE", "0.01")),
        max_amplitude=float(os.getenv("AURION_VQ_MAX_AMPLITUDE", "1.0")),
        decoherence_threshold=float(os.getenv("AURION_VQ_DECOHERENCE_THRESHOLD", "0.02")),
        correction_interval_sec=float(os.getenv("AURION_VQ_CORRECTION_INTERVAL_SEC", "5")),
        max_states_in_memory=int(os.getenv("AURION_VQ_MAX_STATES_IN_MEMORY", "256")),
        offload_dir=os.getenv("AURION_VQ_OFFLOAD_DIR", r"D:\AurionData\CloudMemory\qubit_cache"),
        paging_enabled=os.getenv("AURION_VQ_PAGING_ENABLED", "1") not in ("0", "false", "False"),
    )
    return VirtualQubitStability(cfg)
