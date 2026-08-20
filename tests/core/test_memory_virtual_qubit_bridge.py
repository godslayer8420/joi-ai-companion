def test_memory_resilience_contains_virtual_qubit_block():
    from joi_companion.core.memory_system import MemorySystem
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()

    assert "memory_architecture" in status
    arch = status.get("memory_architecture") or {}

    # Accept either location so test matches current runtime contract.
    vq = status.get("virtual_qubit")
    if vq is None:
        vq = arch.get("virtual_qubit")

    assert isinstance(vq, dict)
    assert "enabled" in vq
    assert "active_states" in vq
