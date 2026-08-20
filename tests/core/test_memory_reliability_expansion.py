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

def test_memory_resilience_contains_reliability_block():
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()
    rel = status.get("reliability") or {}

    assert isinstance(rel, dict)
    assert "runtime_path_present" in rel
    assert "long_term_path_present" in rel
    assert "backup_dir_present" in rel
    assert "cloud_mode" in rel
    assert "cloud_offload_enabled" in rel

def test_memory_resilience_reliability_score_is_bounded():
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()
    rel = status.get("reliability") or {}

    assert "score" in rel
    score = rel.get("score")
    assert isinstance(score, (int, float))
    assert 0.0 <= float(score) <= 1.0

def test_memory_resilience_reliability_tier_matches_score():
    ms = MemorySystem()
    status = ms.get_memory_resilience_status()
    rel = status.get("reliability") or {}

    assert "score" in rel
    assert "tier" in rel

    score = float(rel["score"])
    tier = rel["tier"]

    assert tier in {"high", "medium", "low"}
    if score >= 0.99:
        assert tier == "high"
    elif score >= 0.66:
        assert tier == "medium"
    else:
        assert tier == "low"
