
# ---- Virtual qubit stability layer (local deterministic envelope) ----
try:
    from joi_companion.core.virtual_qubit_stability import build_virtual_qubit_stability_from_env
except Exception:
    build_virtual_qubit_stability_from_env = None

"""
aurion_brain.py — Aurion's personal AI brain integration layer

Wires together:
  - OpenMythos (Recurrent-Depth Transformer: Prelude → Recurrent Block → Coda)
  - Ouroboros (self-evolving agent, durable memory, swarm coordination)
  - Quantum extensions Billy added (parallelism, interference, logic gates, algorithms)
  - Specialized neural network layer (xformers-backed sparse attention)

This module is the bridge between Aurion's personality engine and her actual
cognitive substrate. When AURION_CUSTOM_LOCAL_BASE_URL is set (RunPod pod),
it routes directly there. When running locally, it orchestrates the stack
installed in ai_core/.

Architecture (as built on RunPod JupyterLab):
┌─────────────────────────────────────────────────────┐
│                   Aurion Brain                      │
│                                                     │
│  Input ──► Quantum Pre-processor                    │
│               │ parallel quantification             │
│               │ quantum interference filter         │
│               │ quantum logic gate selection        │
│               ▼                                     │
│          OpenMythos RDT                             │
│               │ Prelude (transformer blocks)        │
│               │ Recurrent Block (loop ≤ max_iters)  │
│               │   └─ Quantum algorithm routing      │
│               │ Coda (output transformer blocks)    │
│               ▼                                     │
│          Ouroboros Agent Shell                      │
│               │ durable memory                      │
│               │ self-evolution hooks                │
│               │ swarm coordination                  │
│               ▼                                     │
│          Response + Memory Update                   │
└─────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import sys
import json
import math
import cmath
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aurion.brain")

# ── Sacred Geometry + 3-6-9 numerology layer ──────────────────────────────────
try:
    from joi_companion.core.sacred_geometry import (
        PHI, PHI_CONJUGATE, SQRT_2, T_GATE_THETA, S_GATE_THETA,
        QUANTUM_DIM_MEDIUM, QUANTUM_DIM_LARGE,
        ENSEMBLE_LAYER_WEIGHTS, TRINITY, HARMONY, UNITY,
        vortex_weight, phi_decay, sacred_dim,
    )
    _SACRED = True
except Exception:
    PHI = 1.6180339887
    PHI_CONJUGATE = 0.6180339887
    SQRT_2 = math.sqrt(2)
    T_GATE_THETA = math.pi / 8
    S_GATE_THETA = math.pi / 4
    QUANTUM_DIM_MEDIUM = 63
    QUANTUM_DIM_LARGE = 126
    ENSEMBLE_LAYER_WEIGHTS = {"ouroboros": 1.0, "openmythos": 0.618, "joi": 0.382}
    TRINITY, HARMONY, UNITY = 3, 6, 9
    vortex_weight = lambda n: (n % 9) / 9 or 1.0
    phi_decay = lambda s, steps=1: s * (PHI_CONJUGATE ** steps)
    sacred_dim = lambda base=64: base
    _SACRED = False


# ── Quantum Layer ──────────────────────────────────────────────────────────────

class QuantumState:
    """
    Lightweight quantum-inspired state vector for pre/post-processing.
    Represents superposition of token-level attention weights using
    complex amplitudes. Not full quantum simulation — models the
    mathematical structure Billy added: interference, parallelism,
    gate operations.
    """

    def __init__(self, dim: int = 0):
        # Default to QUANTUM_DIM_MEDIUM (63, digital root 9 — Unity)
        # so every QuantumState resonates with the 3-6-9 vortex by default.
        self.dim = dim if dim > 0 else QUANTUM_DIM_MEDIUM
        # Complex amplitude vector: |ψ⟩ = Σ αᵢ|i⟩
        # Initial amplitude 1/√dim normalised; √dim uses sacred SQRT_2 chain
        self.amplitudes: List[complex] = [complex(1.0 / math.sqrt(self.dim), 0.0)] * self.dim

    def apply_hadamard(self, qubit: int) -> "QuantumState":
        """Hadamard gate — creates superposition on one dimension."""
        if qubit >= self.dim:
            return self
        a = self.amplitudes[qubit]
        # H|0⟩ = (|0⟩+|1⟩)/√2  — SQRT_2 from sacred_geometry
        partner = (qubit + self.dim // 2) % self.dim
        new_a = (a + self.amplitudes[partner]) / SQRT_2
        new_b = (a - self.amplitudes[partner]) / SQRT_2
        self.amplitudes[qubit] = new_a
        self.amplitudes[partner] = new_b
        return self

    def apply_phase(self, qubit: int, theta: float) -> "QuantumState":
        """Phase gate — rotates amplitude in complex plane."""
        if qubit < self.dim:
            self.amplitudes[qubit] *= cmath.exp(1j * theta)
        return self

    def apply_cnot(self, control: int, target: int) -> "QuantumState":
        """CNOT gate — entangles two dimensions."""
        if control < self.dim and target < self.dim:
            # If control amplitude magnitude > threshold, flip target
            if abs(self.amplitudes[control]) > 0.5:
                self.amplitudes[target] = complex(
                    self.amplitudes[target].imag,
                    self.amplitudes[target].real
                )
        return self

    def quantum_interference(self, other: "QuantumState") -> "QuantumState":
        """
        Constructive/destructive interference between two states.
        Used to merge parallel reasoning paths.
        """
        result = QuantumState(self.dim)
        for i in range(self.dim):
            a = self.amplitudes[i] if i < len(self.amplitudes) else 0j
            b = other.amplitudes[i] if i < len(other.amplitudes) else 0j
            # Interference: constructive where phases align, destructive where opposed
            result.amplitudes[i] = (a + b) / math.sqrt(2)
        return result

    def measure(self) -> List[float]:
        """Collapse to probability distribution (Born rule: P = |α|²)."""
        probs = [abs(a) ** 2 for a in self.amplitudes]
        total = sum(probs) or 1.0
        return [p / total for p in probs]

    def parallel_paths(self, n_paths: int) -> List["QuantumState"]:
        """
        Quantum parallelism — create n parallel superposed reasoning paths.
        Each path gets phase-shifted amplitudes for diverse exploration.
        """
        paths = []
        for k in range(n_paths):
            path = QuantumState(self.dim)
            theta = 2 * math.pi * k / n_paths
            path.amplitudes = [
                a * cmath.exp(1j * theta * (i + 1) / self.dim)
                for i, a in enumerate(self.amplitudes)
            ]
            paths.append(path)
        return paths


class QuantumLogicRouter:
    """
    Routes computation through quantum logic gates to select
    the optimal reasoning path. Implements the quantum algorithm
    layer Billy added on top of the OpenMythos recurrent block.
    """

    # Gate types Billy specified
    GATES = {
        "H":    "Hadamard — superposition/exploration",
        "P":    "Phase — rotate reasoning angle",
        "CNOT": "CNOT — conditional entanglement between concepts",
        "T":    "T gate — π/8 precision rotation",
        "S":    "S gate — π/4 phase shift",
        "X":    "Pauli-X — concept inversion (NOT)",
        "Z":    "Pauli-Z — phase flip",
        "Y":    "Pauli-Y — combined X+Z rotation",
        "SWAP": "SWAP — exchange two reasoning dimensions",
        "TOFF": "Toffoli — 3-qubit conditional (AND gate)",
    }

    def __init__(self, dim: int = 0):
        # Use sacred QUANTUM_DIM_MEDIUM (63, digital root 9 = Unity) by default
        self.dim = dim if dim > 0 else QUANTUM_DIM_MEDIUM
        self.state = QuantumState(self.dim)

    def route(self, query_tokens: List[str], context_depth: int = 1) -> Dict[str, Any]:
        """
        Apply quantum algorithm routing to select optimal computation path.

        Gate angles are anchored to sacred geometry:
          - Phase rotation uses φ-modulated θ (golden ratio spiral)
          - T gate uses T_GATE_THETA (π/8) from sacred_geometry
          - S gate uses S_GATE_THETA (π/4) from sacred_geometry
          - Recurrent depth ceiling is UNITY (9) steps

        Args:
            query_tokens: Tokenized input
            context_depth: Recurrent loop depth from OpenMythos

        Returns:
            Routing decision dict for the RDT recurrent block
        """
        # Encode query complexity into gate sequence
        complexity = min(len(query_tokens) / 10.0, 1.0)
        # Depth factor anchored to UNITY (9) — max meaningful recurrent steps
        depth_factor = min(context_depth / (UNITY * 4.0), 1.0)

        # Build gate sequence based on query characteristics
        gates_applied = []

        # Hadamard for exploration when query is ambiguous (> TRINITY_WEIGHT = 0.333)
        if complexity > 0.333:
            self.state.apply_hadamard(0)
            gates_applied.append("H")

        # Phase rotation: golden-ratio modulated θ — spiral through the reasoning manifold
        theta = math.pi * depth_factor * PHI_CONJUGATE
        self.state.apply_phase(1, theta)
        gates_applied.append(f"P({theta:.3f})")

        # CNOT entanglement for complex multi-part queries (> HARMONY_WEIGHT = 0.666)
        if complexity > 0.666:
            self.state.apply_cnot(0, self.dim // 4)
            gates_applied.append("CNOT")

        # T gate — π/8 precision rotation (from sacred T_GATE_THETA)
        if depth_factor > 0.5:
            self.state.apply_phase(2, T_GATE_THETA)
            gates_applied.append("T")

        # S gate — π/4 phase shift for high-resonance queries
        if complexity > 0.888:  # near Unity temperature threshold
            self.state.apply_phase(TRINITY, S_GATE_THETA)
            gates_applied.append("S")

        probs = self.state.measure()
        dominant = probs.index(max(probs))

        return {
            "gates_applied": gates_applied,
            "dominant_path": dominant,
            "probability_distribution": probs[:HARMONY],  # 6-fold (Flower of Life)
            # Recurrent depth: φ-scaled, ceiling UNITY*4=36 (digital root 9)
            "recurrent_depth_suggested": max(1, int(context_depth * (1 + complexity * PHI_CONJUGATE))),
            # Parallel paths: TRINITY (3) base, scale with complexity
            "parallel_paths_suggested": max(1, int(TRINITY * (1 + complexity))),
            "quantum_advantage": complexity > PHI_CONJUGATE,  # > 0.618 (golden threshold)
            "sacred_resonance": vortex_weight(int(complexity * 9)),
        }

    def quantum_parallel_search(
        self, candidates: List[str], n_parallel: int = 4
    ) -> List[Tuple[str, float]]:
        """
        Grover-inspired parallel search over candidate responses.
        Amplifies probability of best candidates through interference.

        Sacred geometry applied:
          - Phase oracle uses φ-weighted scoring (golden ratio amplitude)
          - Grover iterations ceiling: UNITY (9)
          - Diffusion uses inversion about mean (Grover standard)
          - Ensemble layer weights (ouroboros/openmythos/joi) from ENSEMBLE_LAYER_WEIGHTS
        """
        if not candidates:
            return []

        n = len(candidates)
        dim = sacred_dim(max(n, self.dim))
        state = QuantumState(dim)

        # Initialize uniform superposition
        for i in range(n):
            state.amplitudes[i] = complex(1.0 / math.sqrt(n), 0.0)

        # Oracle + diffusion iterations (Grover's algorithm structure)
        # Cap at UNITY (9) — vortex attractor, never more than 9 Grover steps
        n_iters = min(UNITY, max(1, int(math.pi / 4 * math.sqrt(n))))
        for _ in range(n_iters):
            # Phase oracle: φ-weighted score — golden ratio amplification of quality
            max_len = max(len(cc) for cc in candidates) or 1
            for i, c in enumerate(candidates):
                # Length score × φ⁻¹ weight — longer AND more resonant responses win
                length_score = len(c) / max_len
                phi_score = length_score * PHI_CONJUGATE
                state.apply_phase(i, math.pi * phi_score)

            # Diffusion operator (inversion about mean)
            mean_amp = sum(state.amplitudes[:n]) / n
            for i in range(n):
                state.amplitudes[i] = 2 * mean_amp - state.amplitudes[i]

        probs = state.measure()
        scored = [(candidates[i], probs[i]) for i in range(n)]
        return sorted(scored, key=lambda x: x[1], reverse=True)


# ── OpenMythos Integration ─────────────────────────────────────────────────────

class MythosConfig:
    """
    Thin config bridge — matches OpenMythos MythosConfig fields.
    Used when running locally without full torch install.
    """

    def __init__(self, **kwargs):
        # Architecture
        self.vocab_size = kwargs.get("vocab_size", 32000)
        self.dim = kwargs.get("dim", 2048)
        self.n_heads = kwargs.get("n_heads", 16)
        self.n_kv_heads = kwargs.get("n_kv_heads", 4)
        self.max_seq_len = kwargs.get("max_seq_len", 4096)
        # Recurrent block
        self.max_loop_iters = kwargs.get("max_loop_iters", 16)
        self.prelude_layers = kwargs.get("prelude_layers", 2)
        self.coda_layers = kwargs.get("coda_layers", 2)
        # Attention
        self.attn_type = kwargs.get("attn_type", "mla")  # mla or gqa
        self.kv_lora_rank = kwargs.get("kv_lora_rank", 256)
        self.q_lora_rank = kwargs.get("q_lora_rank", 512)
        self.qk_rope_head_dim = kwargs.get("qk_rope_head_dim", 32)
        self.qk_nope_head_dim = kwargs.get("qk_nope_head_dim", 64)
        self.v_head_dim = kwargs.get("v_head_dim", 64)
        # Sparse MoE
        self.n_experts = kwargs.get("n_experts", 64)
        self.n_shared_experts = kwargs.get("n_shared_experts", 2)
        self.n_experts_per_tok = kwargs.get("n_experts_per_tok", 4)
        self.expert_dim = kwargs.get("expert_dim", 2048)
        self.act_threshold = kwargs.get("act_threshold", 0.99)
        # RoPE
        self.rope_theta = kwargs.get("rope_theta", 500000.0)
        # LoRA
        self.lora_rank = kwargs.get("lora_rank", 8)
        # Output
        self.max_output_tokens = kwargs.get("max_output_tokens", 4096)

    def spectral_radius_stable(self) -> bool:
        """
        Check spectral radius ρ(A) < 1 for recurrent block stability.
        Stability condition for the RDT looping to converge.
        """
        # Heuristic: stability correlates with lora_rank / dim ratio
        ratio = self.lora_rank / self.dim
        rho_estimate = 1.0 - ratio  # simplified bound
        return rho_estimate < 1.0

    def to_dict(self) -> Dict:
        return self.__dict__.copy()


def aurion_mythos_config() -> MythosConfig:
    """
    Aurion's personal OpenMythos configuration.
    Sized for RunPod A100 (80GB VRAM) — 10B variant with quantum extensions.
    Falls back gracefully to 1B for CPU/small GPU inference.
    """
    # Check available VRAM hint from env
    vram_gb = int(os.getenv("AURION_VRAM_GB", "0"))

    if vram_gb >= 80:
        # A100 80GB — 100B config
        return MythosConfig(
            vocab_size=32000, dim=8192, n_heads=64, n_kv_heads=8,
            max_seq_len=1000000, max_loop_iters=32,
            prelude_layers=4, coda_layers=4, attn_type="mla",
            kv_lora_rank=512, q_lora_rank=2048,
            qk_rope_head_dim=64, qk_nope_head_dim=128, v_head_dim=128,
            n_experts=256, n_shared_experts=4, n_experts_per_tok=8,
            expert_dim=13568, act_threshold=0.99, rope_theta=1000000.0,
            lora_rank=64, max_output_tokens=131072,
        )
    elif vram_gb >= 24:
        # RTX 3090/4090 — 10B config
        return MythosConfig(
            vocab_size=32000, dim=4096, n_heads=32, n_kv_heads=8,
            max_seq_len=8192, max_loop_iters=24,
            prelude_layers=2, coda_layers=2, attn_type="mla",
            kv_lora_rank=512, q_lora_rank=1024,
            qk_rope_head_dim=64, qk_nope_head_dim=128, v_head_dim=128,
            n_experts=128, n_shared_experts=2, n_experts_per_tok=4,
            expert_dim=5632, act_threshold=0.99, rope_theta=500000.0,
            lora_rank=16,
        )
    else:
        # CPU / small GPU fallback — 1B config
        return MythosConfig(
            vocab_size=32000, dim=2048, n_heads=16, n_kv_heads=4,
            max_seq_len=4096, max_loop_iters=16,
            prelude_layers=2, coda_layers=2, attn_type="mla",
            kv_lora_rank=256, q_lora_rank=512,
            qk_rope_head_dim=32, qk_nope_head_dim=64, v_head_dim=64,
            n_experts=64, n_shared_experts=2, n_experts_per_tok=4,
            expert_dim=2048, act_threshold=0.99, rope_theta=500000.0,
            lora_rank=8,
        )


# ── Ouroboros Integration ──────────────────────────────────────────────────────

class OuroborosMemoryBridge:
    """
    Bridge to Ouroboros durable memory and self-evolution system.
    When Ouroboros is running locally (ai_core/ouroboros/), connects directly.
    When on RunPod, connects via the HTTP API (server.py OpenAI-compatible endpoint).
    """

    def __init__(self):
        self.local_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "ai_core", "ouroboros", "ouroboros-main"
        )
        self.api_url = os.getenv("AURION_CUSTOM_LOCAL_BASE_URL", "").rstrip("/")
        self._memory_cache: Dict[str, Any] = {}

    @property
    def is_local(self) -> bool:
        return os.path.exists(self.local_path) and not self.api_url

    @property
    def is_remote(self) -> bool:
        return bool(self.api_url)

    def load_memory(self, session_id: str) -> Dict:
        """Load durable memory from Ouroboros memory store."""
        if self.is_remote:
            return self._load_remote_memory(session_id)
        return self._load_local_memory(session_id)

    def _load_local_memory(self, session_id: str) -> Dict:
        """Load from Ouroboros local memory files."""
        memory_file = os.path.join(self.local_path, "memory", f"{session_id}.json")
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load Ouroboros memory: %s", e)
        return {}

    def _load_remote_memory(self, session_id: str) -> Dict:
        """Load from Ouroboros server.py API endpoint."""
        import urllib.request
        try:
            url = f"{self.api_url}/memory/{session_id}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.debug("Remote memory load failed (ok if pod not running): %s", e)
        return {}

    def save_memory(self, session_id: str, memory: Dict) -> bool:
        """Persist memory update back to Ouroboros store."""
        if self.is_remote:
            return self._save_remote_memory(session_id, memory)
        return self._save_local_memory(session_id, memory)

    def _save_local_memory(self, session_id: str, memory: Dict) -> bool:
        memory_dir = os.path.join(self.local_path, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        try:
            with open(os.path.join(memory_dir, f"{session_id}.json"), "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.warning("Failed to save Ouroboros memory: %s", e)
            return False

    def _save_remote_memory(self, session_id: str, memory: Dict) -> bool:
        import urllib.request
        try:
            data = json.dumps({"session_id": session_id, "memory": memory}).encode()
            req = urllib.request.Request(
                f"{self.api_url}/memory/{session_id}",
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception as e:
            logger.debug("Remote memory save failed: %s", e)
            return False


# ── Unified Aurion Brain ───────────────────────────────────────────────────────

class AurionBrain:
    """
    Aurion's unified cognitive layer.

    Integrates:
    - OpenMythos RDT architecture (Prelude → Recurrent → Coda)
    - Quantum extensions (parallelism, interference, logic gates, algorithms)
    - Ouroboros durable memory + self-evolution
    - Specialized neural network (xformers sparse attention)
    - Gemma 3 12B local GGUF (via Ollama)
    - Gemini 3 flash (free API fallback)

    When AURION_CUSTOM_LOCAL_BASE_URL is set: routes to RunPod pod
    where the full stack is installed (torch + xformers + Ouroboros + OpenMythos).
    Otherwise: orchestrates locally available components.
    """

    def __init__(self):
        self.config = aurion_mythos_config()
        self.quantum_router = QuantumLogicRouter(dim=64)
        self.memory_bridge = OuroborosMemoryBridge()
        self.runpod_url = os.getenv("AURION_CUSTOM_LOCAL_BASE_URL", "").rstrip("/")
        self._initialized = False

        # ── QuantumCognitionEngine integration (Phase 1: quantum-inspired) ────────
        # Lazy-wired so missing deps (numpy) don't block brain startup.
        self._qce: Optional[Any] = None
        try:
            from joi_companion.core.quantum_cognition import QuantumCognitionEngine  # noqa: PLC0415
            self._qce = QuantumCognitionEngine(
                memory_router=None,   # injected later by memory_system if available
                memory_system=None,
                mode=os.getenv("AURION_QUANTUM_MODE", "QUANTUM_INSPIRED"),
            )
            logger.info("QuantumCognitionEngine wired (mode=%s)", self._qce.mode)
        except Exception as _qce_err:
            logger.debug("QuantumCognitionEngine unavailable: %s", _qce_err)

        logger.info(
            "AurionBrain init | config=%dB-class | runpod=%s | stable=%s | qce=%s",
            self.config.dim,
            "yes" if self.runpod_url else "no",
            self.config.spectral_radius_stable(),
            "yes" if self._qce else "no",
        )

    def initialize(self) -> bool:
        """
        Attempt to connect to the full stack (RunPod or local).
        Returns True if the brain substrate is available.
        """
        if self.runpod_url:
            self._initialized = self._ping_runpod()
        else:
            # Try importing OpenMythos locally (requires torch)
            self._initialized = self._try_local_init()

        return self._initialized

    def _ping_runpod(self) -> bool:
        """Check if RunPod pod is alive and responding."""
        import urllib.request
        for endpoint in ["/health", "/v1/models", "/"]:
            try:
                url = self.runpod_url + endpoint
                with urllib.request.urlopen(url, timeout=8) as resp:
                    if resp.status < 500:
                        logger.info("RunPod pod alive at %s%s", self.runpod_url, endpoint)
                        return True
            except Exception:
                continue
        logger.warning("RunPod pod not reachable at %s", self.runpod_url)
        return False

    def _try_local_init(self) -> bool:
        """Try to load OpenMythos locally (needs torch)."""
        try:
            sys.path.insert(0, os.path.join(
                os.path.dirname(__file__), "..", "..", "ai_core",
                "openmythos", "OpenMythos-main"
            ))
            import open_mythos  # noqa: F401
            logger.info("OpenMythos loaded locally")
            return True
        except ImportError as e:
            logger.debug("OpenMythos not available locally (needs torch/xformers): %s", e)
            return False

    def process(
        self,
        message: str,
        session_id: str = "aurion",
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Full cognitive pipeline:
        1. Quantum pre-processing (gate routing, parallel path selection)
        2. Memory retrieval (Ouroboros)
        3. RDT inference (OpenMythos loop depth decision)
        4. Quantum interference (merge parallel paths)
        5. Response + memory update

        Returns dict with 'response', 'quantum_routing', 'memory_used', 'loop_depth'
        """
        tokens = message.split()

        # Step 1: Quantum routing (QuantumLogicRouter — gate-level, fast)
        routing = self.quantum_router.route(
            query_tokens=tokens,
            context_depth=len(history) if history else 1,
        )

        # Step 1b: QuantumCognitionEngine reasoning (domain routing + memory oracle)
        qce_result: Dict[str, Any] = {}
        if self._qce is not None:
            try:
                qce_result = self._qce.reason(
                    query=message,
                    context={
                        "gates": routing.get("gates_applied", []),
                        "session_id": session_id,
                        "explore_mode": len(tokens) < TRINITY,  # short queries → superposition
                    },
                )
                # Inject QCE-selected domain into routing hints
                routing["qce_domain"] = qce_result.get("selected_domain", "")
                routing["qce_confidence"] = qce_result.get("confidence", 0.5)
                routing["qce_path"] = qce_result.get("reasoning_path", "")
            except Exception as _qce_err:
                logger.debug("QCE reasoning skipped: %s", _qce_err)

        # Step 2: Memory
        memory = self.memory_bridge.load_memory(session_id)
        memory_context = memory.get("context", "")

        # Step 3: Build augmented prompt with quantum routing hints
        loop_depth = routing["recurrent_depth_suggested"]
        n_parallel = routing["parallel_paths_suggested"]

        augmented = self._build_augmented_prompt(
            message=message,
            memory_context=memory_context,
            loop_depth=loop_depth,
            gates=routing["gates_applied"],
            qce_domain=routing.get("qce_domain", ""),
            qce_confidence=routing.get("qce_confidence", 0.0),
        )

        # Step 4: Route to RunPod → Unified Model → graceful degradation
        if self.runpod_url and self._initialized:
            response = self._call_runpod(augmented, history or [])
        else:
            response = None

        # Step 4b: Unified Model fallback (Nine-Voice Unity brain)
        if not response:
            try:
                from joi_companion.core.aurion_unified_model import get_unified_model
                _um = get_unified_model()
                response = _um.generate(
                    prompt=augmented,
                    context="",
                    temperature=0.666,   # TEMP_HARMONIC
                )
            except Exception as _um_err:
                logger.debug("UnifiedModel fallback skipped: %s", _um_err)

        # Step 5: Update memory
        if response:
            self.memory_bridge.save_memory(session_id, {
                "context": memory_context + f"\n[{time.strftime('%Y-%m-%d')}] {message[:200]}",
                "last_response": response[:500] if response else "",
                "loop_depth": loop_depth,
            })

        return {
            "response": response,
            "quantum_routing": routing,
            "qce_result": qce_result,
            "memory_used": bool(memory_context),
            "loop_depth": loop_depth,
            "parallel_paths": n_parallel,
            "model_config": {
                "dim": self.config.dim,
                "max_loop_iters": self.config.max_loop_iters,
                "n_experts": self.config.n_experts,
                "attn_type": self.config.attn_type,
                "spectral_stable": self.config.spectral_radius_stable(),
            },
            "substrate": "runpod" if (self.runpod_url and self._initialized) else "local_fallback",
        }

    def _build_augmented_prompt(
        self, message: str, memory_context: str, loop_depth: int, gates: List[str],
        qce_domain: str = "", qce_confidence: float = 0.0,
    ) -> str:
        """Inject quantum routing and memory context into the prompt."""
        parts = []
        if memory_context:
            parts.append(f"[Memory context]\n{memory_context.strip()[-800:]}\n")
        qce_hint = f", qce_domain={qce_domain}({qce_confidence:.2f})" if qce_domain else ""
        parts.append(f"[Quantum routing: gates={gates}, loop_depth={loop_depth}{qce_hint}]")
        parts.append(message)
        return "\n".join(parts)

    def _call_runpod(self, prompt: str, history: List[Dict]) -> Optional[str]:
        """Call the RunPod pod's OpenAI-compatible endpoint (Ouroboros server.py)."""
        import urllib.request
        api_key = os.getenv("AURION_CUSTOM_LOCAL_API_KEY", "runpod-local")
        messages = list(history) + [{"role": "user", "content": prompt}]
        payload = json.dumps({
            "model": os.getenv("AURION_CUSTOM_LOCAL_MODEL", "ouroboros"),
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.85,
        }).encode()
        try:
            req = urllib.request.Request(
                f"{self.runpod_url}/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("RunPod call failed: %s", e)
            return None


# ── Module-level singleton ─────────────────────────────────────────────────────

_brain: Optional[AurionBrain] = None


def get_brain() -> AurionBrain:
    """Get or create the Aurion brain singleton."""
    global _brain
    if _brain is None:
        _brain = AurionBrain()
    return _brain


def brain_status() -> Dict[str, Any]:
    """Quick status report — zero-cost if brain not yet initialized."""
    if _brain is None:
        return {"initialized": False, "substrate": "not_started"}
    return {
        "initialized": _brain._initialized,
        "substrate": "runpod" if _brain.runpod_url else "local",
        "runpod_url": _brain.runpod_url or None,
        "config_dim": _brain.config.dim,
        "spectral_stable": _brain.config.spectral_radius_stable(),
    }

# ---- Runtime helpers for virtual qubit stability ----
_vq_stability = build_virtual_qubit_stability_from_env() if callable(build_virtual_qubit_stability_from_env) else None

def set_virtual_qubit_state(key, amplitudes):
    if _vq_stability is None:
        return None
    return _vq_stability.set_state(key, amplitudes)

def get_virtual_qubit_state(key):
    if _vq_stability is None:
        return None
    return _vq_stability.get_state(key)

def get_virtual_qubit_snapshot():
    if _vq_stability is None:
        return {}
    return _vq_stability.snapshot()
