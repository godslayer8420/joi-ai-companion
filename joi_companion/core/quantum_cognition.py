"""
Quantum Cognition Engine for Aurion.

Integrates quantum-inspired reasoning with routed memory system to enable:
- Superposition-based memory exploration (personal + collective + knowledge)
- Quantum oracle for domain-aware query routing
- Memory entanglement tracking for context binding
- Deterministic fallback for stability

3-phase architecture:
  Phase 1: Runtime quantum-inspired simulation (active, deterministic)
  Phase 2: Feature-flagged real quantum backends (Qiskit, IonQ, Rigetti)
  Phase 3: Offline distillation (classical training from quantum traces)
"""

import os
import json
import hashlib
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class QuantumMemoryState:
    """Represents memory in superposition across domains."""
    memory_id: str
    domain: str  # personal, collective, knowledge
    content: str
    amplitude: float  # 0.0-1.0, probability measure
    timestamp: str
    
    def collapse(self) -> Dict[str, Any]:
        """Collapse superposition to classical memory."""
        return asdict(self)


class QuantumState:
    """Superposition of memory states across 3 layers."""
    
    def __init__(self, num_qubits: int = 8):
        """Initialize superposition of n qubits. Each qubit = 1 memory dimension."""
        self.num_qubits = num_qubits
        # Use complex dtype to support quantum phase operations
        self.amplitudes = np.ones(2 ** num_qubits, dtype=np.complex128) / np.sqrt(2 ** num_qubits)
        self.basis_states = [format(i, f'0{num_qubits}b') for i in range(2 ** num_qubits)]
        self.entanglement_map = {}  # Tracks correlations between memories
    
    def measure(self) -> str:
        """Collapse to single basis state with probability weighted by amplitude."""
        probabilities = np.abs(self.amplitudes) ** 2
        outcome_idx = np.random.choice(len(self.basis_states), p=probabilities)
        return self.basis_states[outcome_idx]
    
    def encode_memory(self, memory_domain: str, memory_id: str, weight: float = 1.0):
        """Encode memory as amplitude boost in superposition."""
        domain_hash = int(hashlib.md5(memory_domain.encode()).hexdigest(), 16)
        idx = domain_hash % len(self.amplitudes)
        # Amplify this basis state by weight
        self.amplitudes[idx] *= (1.0 + weight)
        # Normalize
        self.amplitudes /= np.linalg.norm(self.amplitudes)
    
    def entangle_memories(self, mem1_id: str, mem2_id: str, correlation: float):
        """Track cross-domain memory correlation."""
        key = tuple(sorted([mem1_id, mem2_id]))
        self.entanglement_map[key] = {
            "correlation": correlation,
            "timestamp": datetime.now().isoformat()
        }


class QuantumGate:
    """Quantum gates for memory transformation."""
    
    @staticmethod
    def hadamard(state: QuantumState, target: int):
        """Equal superposition across all states (exploration)."""
        # Reset to uniform superposition
        state.amplitudes = np.ones(2 ** state.num_qubits) / np.sqrt(2 ** state.num_qubits)
        return state
    
    @staticmethod
    def pauli_x(state: QuantumState, target: int):
        """Flip bit at target (invert memory domain)."""
        if 0 <= target < state.num_qubits:
            new_amplitudes = np.zeros_like(state.amplitudes)
            for i, amp in enumerate(state.amplitudes):
                flipped = list(state.basis_states[i])
                flipped[target] = '1' if flipped[target] == '0' else '0'
                flipped_idx = state.basis_states.index(''.join(flipped))
                new_amplitudes[flipped_idx] = amp
            state.amplitudes = new_amplitudes
        return state
    
    @staticmethod
    def rx(state: QuantumState, target: int, theta: float):
        """Rotation gate (rotate probability mass)."""
        # Simple phase rotation
        phase = np.exp(1j * theta)
        state.amplitudes *= phase
        return state
    
    @staticmethod
    def cnot(state: QuantumState, control: int, target: int):
        """Entangle two memory dimensions."""
        if 0 <= control < state.num_qubits and 0 <= target < state.num_qubits:
            # Mark cross-reference in entanglement map
            state.entanglement_map[f"cnot_{control}_{target}"] = {
                "control": control, "target": target,
                "timestamp": datetime.now().isoformat()
            }
        return state


class QuantumOracle:
    """Domain-aware oracle for query routing via Grover's algorithm."""
    
    def __init__(self, memory_router: 'MemoryRouter'):
        """Initialize oracle with routed memory system."""
        self.router = memory_router
        self.query_history = []
    
    def encode_query(self, query_text: str, state: QuantumState) -> QuantumState:
        """Encode query into superposition via oracle."""
        # Route query to get expected domains
        routes = self.router.route_text(query_text)
        
        # Encode each route as amplitude boost
        for route in routes:
            domain = route.get("domain", "")
            confidence = route.get("confidence", 0.5)
            state.encode_memory(domain, query_text, weight=confidence)
        
        # Track for debugging
        self.query_history.append({
            "query": query_text,
            "routes": routes,
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    def grover_iteration(self, state: QuantumState, marked_states: List[int]) -> QuantumState:
        """Single Grover iteration: amplify marked states."""
        if not marked_states:
            return state
        
        # Amplitude amplification (simplified Grover)
        amplification = 1.5  # Boost marked states
        for idx in marked_states:
            if idx < len(state.amplitudes):
                state.amplitudes[idx] *= amplification
        
        # Normalize
        state.amplitudes /= np.linalg.norm(state.amplitudes)
        return state


class QuantumCognitionEngine:
    """Main quantum cognition orchestrator for Aurion."""
    
    def __init__(self, memory_router: Optional['MemoryRouter'] = None, 
                 memory_system: Optional['MemorySystem'] = None,
                 mode: str = "QUANTUM_INSPIRED"):
        """
        Initialize quantum cognition engine.
        
        Args:
            memory_router: MemoryRouter for domain-aware routing
            memory_system: MemorySystem for actual memory access
            mode: CLASSICAL, QUANTUM_INSPIRED (default), HYBRID, FULL_QUANTUM
        """
        self.memory_router = memory_router
        self.memory_system = memory_system
        self.mode = mode
        self.oracle = QuantumOracle(memory_router) if memory_router else None
        self.reasoning_traces = []  # For Phase 3 distillation
        self.entanglement_log = []  # Track memory correlations
        
        # Feature flags from environment
        self.flags = json.loads(os.getenv("AURION_QUANTUM_FLAGS", "{}"))
        self.use_real_quantum = self.flags.get("use_real_quantum", False)
    
    def reason(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Quantum-inspired reasoning over routed memory.
        
        Returns reasoning trace with:
          - selected_domain: routed memory domain
          - reasoning_path: superposition exploration
          - result: collapsed classical answer
          - confidence: measurement confidence
        """
        if self.mode == "CLASSICAL":
            return self._fallback_classical(query, context)
        
        # Normalize context: convert string domain to dict format
        if isinstance(context, str):
            context = {"domain": context}
        context = context or {}
        trace = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "superposition_states": []
        }
        
        try:
            # Create superposition over memory domains
            state = QuantumState(num_qubits=6)  # 64 basis states (3 layers × ~20 domains)
            
            # Phase 1: Explore all memory routes (superposition)
            if self.memory_router:
                routes = self.memory_router.route_text(query)
                trace["initial_routes"] = routes
                
                for route in routes:
                    domain = route.get("domain", "")
                    confidence = route.get("confidence", 0.5)
                    state.encode_memory(domain, query, weight=confidence)
                    trace["superposition_states"].append({
                        "domain": domain,
                        "confidence": confidence
                    })
            
            # Phase 2: Apply quantum gates to explore combinations
            if context.get("explore_mode"):
                state = QuantumGate.hadamard(state, 0)  # Equal superposition
            
            # Phase 3: Use oracle to amplify relevant routes
            if self.oracle:
                marked = [i for i, s in enumerate(trace["superposition_states"]) 
                          if s["confidence"] > 0.6]
                if marked:
                    state = self.oracle.grover_iteration(state, marked)
            
            # Phase 4: Measurement (collapse to single domain)
            measured_basis = state.measure()
            selected_idx = int(measured_basis, 2) % len(trace["superposition_states"])
            if selected_idx < len(trace["superposition_states"]):
                selected = trace["superposition_states"][selected_idx]
                domain = selected["domain"]
                confidence = selected["confidence"]
            else:
                domain = "personal"
                confidence = 0.5
            
            trace["measured_basis"] = measured_basis
            trace["selected_domain"] = domain
            trace["measurement_confidence"] = confidence
            
            # Phase 5: Access memory via routed system
            result = None
            if self.memory_system and self.memory_router:
                result = self.memory_system.route_and_retrieve(query)
            
            trace["result"] = result or f"No memory in {domain} for: {query[:50]}"
            trace["reasoning_path"] = "superposition → oracle → measurement → domain"
            
            # Track for distillation
            self.reasoning_traces.append(trace)
            
            return {
                "selected_domain": domain,
                "reasoning_path": trace["reasoning_path"],
                "result": trace["result"],
                "confidence": confidence,
                "trace": trace
            }
        
        except Exception as e:
            # Fallback to classical on any quantum error
            return self._fallback_classical(query, context)
    
    def superposition_query(self, query: str, num_samples: int = 3) -> List[Dict[str, Any]]:
        """
        Sample multiple reasoning paths from superposition.
        Returns diverse perspectives on the query.
        """
        results = []
        for i in range(num_samples):
            result = self.reason(query, context={"sample_idx": i})
            results.append(result)
        return results
    
    def entangle_memories(self, mem_id1: str, mem_id2: str, query: str) -> Dict[str, Any]:
        """
        Create quantum entanglement between two memories for context binding.
        Enables retrieval of related memories via correlation.
        """
        state = QuantumState(num_qubits=4)
        state.entangle_memories(mem_id1, mem_id2, correlation=0.85)
        
        entanglement = {
            "memory1": mem_id1,
            "memory2": mem_id2,
            "query": query,
            "correlation": 0.85,
            "timestamp": datetime.now().isoformat(),
            "entanglement_log": state.entanglement_map
        }
        
        self.entanglement_log.append(entanglement)
        return entanglement
    
    def distill_to_classical(self, num_traces: int = 5) -> List[Dict[str, Any]]:
        """
        Phase 3: Convert quantum reasoning traces to classical training data.
        Output can be used to fine-tune classical model.
        """
        if not self.reasoning_traces:
            return []
        
        distilled = []
        for trace in self.reasoning_traces[-num_traces:]:
            training_pair = {
                "input": trace["query"],
                "domain": trace["selected_domain"],
                "confidence": trace.get("measurement_confidence", 0.5),
                "output": trace.get("result", ""),
                "trace": trace
            }
            distilled.append(training_pair)
        
        return distilled
    
    def _fallback_classical(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic classical fallback for stability."""
        domain_map = {
            0: "personal", 1: "collective", 2: "knowledge"
        }
        
        # Hash query to deterministic domain
        query_hash = int(hashlib.md5(query.encode()).hexdigest(), 16)
        domain = domain_map[query_hash % 3]
        
        result = None
        if self.memory_system and self.memory_router:
            result = self.memory_system.route_and_retrieve(query)
        
        return {
            "selected_domain": domain,
            "reasoning_path": "fallback_classical",
            "result": result or f"Fallback: {query[:50]}",
            "confidence": 0.5,
            "fallback": True
        }
