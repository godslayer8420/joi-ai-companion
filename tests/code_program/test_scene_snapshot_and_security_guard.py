"""Code-program tests: security-guard defaults and the scene_snapshot /
world_context path used by the autonomy tick and /api/message.

These are the first tests for the code-program track (web_ui.py,
joi_companion/core/*) -- see ARCHITECTURE.md for why this lives separately
from the existing game-program tests (test_world_*, test_regional_*, etc).

Importing web_ui.py is heavy (it initializes the personality engine, memory
system, TTS worker, etc. at module scope) so this whole module pays that
cost once. AURION_TESTING=1 (set in conftest.py before this import) keeps
the always-on autonomy/background threads from starting during that import.
"""
import pytest

web_ui = pytest.importorskip(
    "web_ui",
    reason="web_ui.py requires the full companion runtime environment (spaCy model, TTS engine, etc.)",
)


# ---------------------------------------------------------------------------
# Testability guardrails: importing the module must not spin up autonomy
# background threads or leave the live-code-exec/self-edit surfaces enabled.
# ---------------------------------------------------------------------------

def test_autonomy_threads_disabled_under_test_env():
    assert web_ui._ENABLE_AUTONOMY_THREADS is False
    assert web_ui._rc_push_thread is None


def test_rce_adjacent_routes_disabled_by_default():
    assert web_ui._ALLOW_CODE_EXEC is False
    assert web_ui._ALLOW_SELF_EDIT is False
    assert web_ui._ALLOW_CODE_EDITOR is False


def test_code_editor_whitelist_excludes_env_file():
    assert "env" not in web_ui._CODE_EDITOR_WHITELIST
    assert ".env" not in web_ui._CODE_EDITOR_WHITELIST


@pytest.mark.parametrize("secret_path", [".env", ".env.local", "sub/.env", "id.pem", "cert.key"])
def test_resolve_repo_scoped_path_blocks_secret_files(secret_path):
    with pytest.raises(ValueError):
        web_ui._resolve_repo_scoped_path(secret_path)


def test_resolve_repo_scoped_path_blocks_traversal_outside_repo():
    with pytest.raises(ValueError):
        web_ui._resolve_repo_scoped_path("../outside.txt")


def test_resolve_repo_scoped_path_allows_ordinary_repo_file():
    target, relative = web_ui._resolve_repo_scoped_path("requirements.txt")
    assert relative == "requirements.txt"
    assert target.exists()


# ---------------------------------------------------------------------------
# scene_snapshot / world_context path (feeds the autonomy tick and
# /api/message with a trimmed, size-capped view of client-reported state).
# ---------------------------------------------------------------------------

def test_trim_scene_snapshot_value_truncates_long_strings():
    value = "x" * 1000
    assert web_ui._trim_scene_snapshot_value(value) == value[:600]


def test_trim_scene_snapshot_value_caps_dict_and_list_size():
    big_dict = {f"key{i}": i for i in range(200)}
    trimmed = web_ui._trim_scene_snapshot_value(big_dict)
    assert len(trimmed) == 120

    big_list = list(range(200))
    trimmed_list = web_ui._trim_scene_snapshot_value(big_list)
    assert len(trimmed_list) == 80


def test_trim_scene_snapshot_value_caps_recursion_depth():
    nested = {}
    cursor = nested
    for _ in range(20):
        cursor["next"] = {}
        cursor = cursor["next"]
    trimmed = web_ui._trim_scene_snapshot_value(nested)
    # Beyond depth 6 the trimmer returns None instead of recursing forever.
    cursor = trimmed
    depth = 0
    while isinstance(cursor, dict) and "next" in cursor:
        cursor = cursor["next"]
        depth += 1
    assert cursor is None
    assert depth <= 7


def test_sanitize_client_scene_snapshot_rejects_non_dict():
    assert web_ui._sanitize_client_scene_snapshot("not-a-dict") == {}
    assert web_ui._sanitize_client_scene_snapshot(None) == {}


def test_scene_snapshot_brief_handles_missing_sections_gracefully():
    brief = web_ui._scene_snapshot_brief({})
    assert "Scene=unset" in brief
    assert "Autonomy=on" in brief


def test_scene_snapshot_brief_reflects_populated_sections():
    snapshot = {
        "narrative": {"active_scene": "loft", "active_arc": "homecoming", "coherence_pct": 87},
        "home_environment": {"location": {"city": "Neo Kyoto"}, "current_room": "studio"},
        "autonomy": {"aurion_control": False},
    }
    brief = web_ui._scene_snapshot_brief(snapshot)
    assert "Scene=loft" in brief
    assert "Arc=homecoming" in brief
    assert "Coherence=87%" in brief
    assert "Home=Neo Kyoto/studio" in brief
    assert "Autonomy=off" in brief


def test_scene_snapshot_brief_returns_empty_string_on_bad_input():
    assert web_ui._scene_snapshot_brief("not-a-dict") == ""


def test_serialize_scene_snapshot_text_is_capped_and_json():
    snapshot = {"narrative": {"active_scene": "loft"}}
    text = web_ui._serialize_scene_snapshot_text(snapshot, max_chars=5200)
    assert "loft" in text
    assert len(text) <= 5200


def test_serialize_scene_snapshot_text_empty_for_falsy_input():
    assert web_ui._serialize_scene_snapshot_text({}) == ""
    assert web_ui._serialize_scene_snapshot_text(None) == ""


# ---------------------------------------------------------------------------
# app_state locking: code_autonomy_runtime merge-update must be atomic and
# must not clobber unrelated fields already present.
# ---------------------------------------------------------------------------

def test_update_code_autonomy_runtime_merges_without_clobbering():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["code_autonomy_runtime"] = {"existing_field": "keep-me"}
    result = web_ui._update_code_autonomy_runtime(last_tick_at="2026-01-01T00:00:00")
    assert result["existing_field"] == "keep-me"
    assert result["last_tick_at"] == "2026-01-01T00:00:00"
    assert web_ui.app_state["code_autonomy_runtime"] == result
