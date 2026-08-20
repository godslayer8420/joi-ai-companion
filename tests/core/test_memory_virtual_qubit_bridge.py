from joi_companion.core.memory_system import MemorySystem


def test_memory_resilience_contains_virtual_qubit_block():
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()

    assert "memory_architecture" in status
    arch = status.get("memory_architecture") or {}

    # Accept both locations (top-level or nested) and fallback to direct helper.
    vq = status.get("virtual_qubit")
    if vq is None:
        vq = arch.get("virtual_qubit")
    if vq is None and hasattr(ms, "get_virtual_qubit_runtime_status"):
        vq = ms.get_virtual_qubit_runtime_status()

    assert isinstance(vq, dict), f"virtual_qubit missing; keys={list(status.keys())}, arch_keys={list(arch.keys()) if isinstance(arch, dict) else arch}"
