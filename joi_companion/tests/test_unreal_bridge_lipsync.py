from joi_companion.core.unreal_bridge import UnrealIntegration


def test_build_lip_sync_data_empty_text():
    integration = UnrealIntegration(enabled=False)
    payload = integration._build_lip_sync_data("", speed=1.0)
    assert payload["source"] == "heuristic_text"
    assert payload["duration_sec"] == 0.0
    assert payload["phonemes"] == []
    assert payload["visemes"] == []


def test_build_lip_sync_data_generates_phonemes_and_visemes():
    integration = UnrealIntegration(enabled=False)
    payload = integration._build_lip_sync_data("Aurion speaks clearly", speed=1.0)
    phonemes = payload["phonemes"]
    visemes = payload["visemes"]

    assert payload["duration_sec"] > 0.0
    assert payload["sample_rate_hz"] == 60
    assert len(phonemes) > 0
    assert len(visemes) > 0
    assert any(v.get("viseme") == "closed" for v in visemes)
    assert any(v.get("viseme") == "rest" for v in visemes)
    assert all(float(p["end"]) >= float(p["start"]) for p in phonemes)
    assert all(float(v["end"]) >= float(v["start"]) for v in visemes)

