from joi_companion.core.memory_system import MemorySystem


def test_memory_resilience_payload_has_architecture_contract():
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()

    assert isinstance(status, dict)
    assert "memory_architecture" in status

    arch = status.get("memory_architecture")
    assert isinstance(arch, dict)

    # Contract-level checks that are stable across runtime modes.
    expected_arch_keys = {
        "policy",
        "active_runtime_role",
        "active_runtime_path",
        "active_runtime_drive",
        "long_term_role",
        "long_term_path",
        "long_term_drive",
        "backup_role",
        "backup_dir",
        "backup_drive",
    }
    missing = expected_arch_keys.difference(set(arch.keys()))
    assert not missing, f"missing memory_architecture keys: {sorted(missing)}"
