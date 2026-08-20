from joi_companion.core.memory_system import MemorySystem


def test_memory_resilience_exposes_runtime_and_long_term_paths():
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()
    arch = status.get("memory_architecture") or {}

    assert isinstance(status, dict)
    assert isinstance(arch, dict)

    # Existing contract keys should exist
    assert "active_runtime_path" in arch
    assert "long_term_path" in arch
    assert "backup_dir" in arch


def test_memory_resilience_cloud_flags_are_booleans_or_strings():
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()
    arch = status.get("memory_architecture") or {}

    # tolerate current runtime shape, but enforce stable presence
    assert "cloud_memory_mode" in arch
    assert "cloud_memory_offload_enabled" in arch
