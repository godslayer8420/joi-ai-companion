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
# Observability: /healthz + structured logging setup.
# ---------------------------------------------------------------------------

def test_healthz_endpoint_reports_security_and_runtime_posture():
    client = web_ui.app.test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "ok"
    assert payload["runtime"]["autonomy_threads_enabled"] is False
    assert payload["runtime"]["test_run"] is True
    assert payload["security"]["code_exec_enabled"] is False
    assert payload["security"]["self_edit_enabled"] is False
    assert payload["security"]["code_editor_enabled"] is False
    assert "failure_count" in payload["code_autonomy"]
    assert "ffmpeg_available" in payload["codec"]
    assert set(payload["llm_providers_configured"].keys()) == {
        "openai", "anthropic", "cohere", "openrouter", "groq", "ollama_cloud",
    }


def test_healthz_is_rate_limit_exempt():
    assert "/healthz" in web_ui._RATE_LIMIT_EXEMPT_PATHS


def test_structured_logger_uses_json_formatter():
    assert web_ui.logger.name == "aurion"
    assert len(web_ui.logger.handlers) >= 1
    formatter = web_ui.logger.handlers[0].formatter
    assert isinstance(formatter, web_ui._JsonLogFormatter)


def test_json_log_formatter_produces_parseable_json():
    import json as _json
    import logging as _logging
    record = _logging.LogRecord(
        name="aurion.test", level=_logging.WARNING, pathname=__file__, lineno=1,
        msg="blocked %s", args=("thing",), exc_info=None,
    )
    line = web_ui._JsonLogFormatter().format(record)
    parsed = _json.loads(line)
    assert parsed["level"] == "WARNING"
    assert parsed["message"] == "blocked thing"
    assert parsed["logger"] == "aurion.test"


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

def test_mutate_code_autonomy_runtime_increments_counter_atomically():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["code_autonomy_runtime"] = {"success_count": 2, "keep_me": "yes"}

    def _bump(runtime):
        runtime["success_count"] = int(runtime.get("success_count", 0) or 0) + 1

    result = web_ui._mutate_code_autonomy_runtime(_bump)
    assert result["success_count"] == 3
    assert result["keep_me"] == "yes"
    assert web_ui.app_state["code_autonomy_runtime"] == result


def test_update_code_autonomy_runtime_merges_without_clobbering():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["code_autonomy_runtime"] = {"existing_field": "keep-me"}
    result = web_ui._update_code_autonomy_runtime(last_tick_at="2026-01-01T00:00:00")
    assert result["existing_field"] == "keep-me"
    assert result["last_tick_at"] == "2026-01-01T00:00:00"
    assert web_ui.app_state["code_autonomy_runtime"] == result


# ---------------------------------------------------------------------------
# world_continuity locking (first reviewed batch: world_builder + guardian
# presence + special-ability grant/revoke). See ARCHITECTURE.md / session
# todos for the remaining ~28 sites still tracked as follow-up.
# ---------------------------------------------------------------------------

def test_update_world_continuity_merges_without_clobbering():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"unrelated_field": "keep-me"}
    result = web_ui._update_world_continuity(some_field="value")
    assert result["unrelated_field"] == "keep-me"
    assert result["some_field"] == "value"
    assert web_ui.app_state["world_continuity"] == result


def test_mutate_world_continuity_preserves_concurrent_top_level_keys():
    # Simulate the exact hazard the helper fixes: caller A takes a stale
    # snapshot, caller B updates an unrelated key in between, caller A's
    # mutate_fn should still only touch its own key.
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"other_key": "from-someone-else"}

    def _apply(wc):
        wc["my_key"] = "mine"

    result = web_ui._mutate_world_continuity(_apply)
    assert result["my_key"] == "mine"
    assert result["other_key"] == "from-someone-else"


def test_save_world_builder_state_merges_into_world_continuity():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"guardian_presence": {"summons_enabled": True}}
    web_ui._save_world_builder_state({"phase": "testing"})
    wc = web_ui.app_state["world_continuity"]
    # _save_world_builder_state hands off to _resolve_world_builder_state,
    # which normalizes/expands the raw dict against defaults -- our custom
    # field must survive that merge, not be replaced wholesale.
    assert wc["world_builder"]["phase"] == "testing"
    assert "synced_at" in wc
    # Unrelated key from before the call must survive the merge-write.
    assert wc["guardian_presence"] == {"summons_enabled": True}


def test_resolve_guardian_presence_state_defaults_and_merge():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"world_builder": {"phase": "keep-me"}}
    state = web_ui._resolve_guardian_presence_state()
    assert state["summons_enabled"] is True
    assert state["active_guardians"] == []
    wc = web_ui.app_state["world_continuity"]
    assert wc["guardian_presence"] == state
    # Unrelated key must survive.
    assert wc["world_builder"] == {"phase": "keep-me"}


def test_resolve_special_ability_registry_defaults_and_merge():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"world_builder": {"phase": "keep-me"}}
    registry = web_ui._resolve_special_ability_registry()
    assert registry["enabled"] is True
    assert registry["entities"] == {}
    wc = web_ui.app_state["world_continuity"]
    assert wc["special_ability_registry"] == registry
    # Unrelated key must survive the merge-write.
    assert wc["world_builder"] == {"phase": "keep-me"}


def test_world_force_state_round_trips_through_world_continuity():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"guardian_presence": {"summons_enabled": True}}
    saved = web_ui._save_world_force_state([{"id": "storm", "name": "Storm Front", "summary": "A rolling storm."}])
    assert len(saved) == 1
    assert saved[0]["name"] == "Storm Front"
    wc = web_ui.app_state["world_continuity"]
    assert wc["world_forces"] == saved
    assert "synced_at" in wc
    # Unrelated key must survive.
    assert wc["guardian_presence"] == {"summons_enabled": True}
    # A second resolve call should be idempotent (same normalized shape).
    assert web_ui._resolve_world_force_state() == saved


def test_time_control_state_round_trips_through_world_continuity():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"guardian_presence": {"summons_enabled": True}}
    state = web_ui._save_time_control_state({"active": True, "owner_name": "Billy"})
    assert state["active"] is True
    assert "Billy" in state["controller_entities"]
    assert "Aurion" in state["controller_entities"]
    wc = web_ui.app_state["world_continuity"]
    assert wc["time_control"] == state
    # Unrelated key must survive.
    assert wc["guardian_presence"] == {"summons_enabled": True}


def test_resolve_special_ability_registry_round_trip_via_grant():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"guardian_presence": {"summons_enabled": True}}
    result = web_ui._grant_special_ability(
        entity_id="test-npc", entity_name="Test NPC", entity_type="world_entity",
        ability_name="Test Ability", description="A test-only ability.",
    )
    assert result["ability"]["name"] == "Test Ability"
    wc = web_ui.app_state["world_continuity"]
    assert "test-npc" in wc["special_ability_registry"]["entities"]
    # Unrelated key must survive.
    assert wc["guardian_presence"] == {"summons_enabled": True}


def test_offscreen_life_route_locks_world_continuity_without_clobbering():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"guardian_presence": {"summons_enabled": True}}
    client = web_ui.app.test_client()
    resp = client.post("/api/world/offscreen-life", json={"enabled": True, "procedural_density": "ultra"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    assert payload["offscreen_simulation"]["procedural_density"] == "ultra"
    wc = web_ui.app_state["world_continuity"]
    assert wc["offscreen_simulation"]["procedural_density"] == "ultra"
    assert "synced_at" in wc
    # Unrelated key from before the request must survive the merge-write.
    assert wc["guardian_presence"] == {"summons_enabled": True}


def test_spacefaring_load_screen_route_locks_world_continuity_without_clobbering():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["world_continuity"] = {"guardian_presence": {"summons_enabled": True}}
    client = web_ui.app.test_client()
    resp = client.post("/api/world/spacefaring/load-screen", json={"active": True, "label": "Testing"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    assert payload["spacefaring"]["load_screen"]["label"] == "Testing"
    wc = web_ui.app_state["world_continuity"]
    assert wc["spacefaring"]["load_screen"]["label"] == "Testing"
    # Unrelated key from before the request must survive the merge-write.
    assert wc["guardian_presence"] == {"summons_enabled": True}


# ---------------------------------------------------------------------------
# home_environment locking (second-highest-traffic key; first reviewed
# batch covers the simple single-route mutators). See session todos for
# the remaining sites (core _update_home_environment tick + a few routes).
# ---------------------------------------------------------------------------

def test_update_home_environment_state_merges_without_clobbering():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["home_environment"] = {"unrelated_field": "keep-me"}
    result = web_ui._update_home_environment_state(some_field="value")
    assert result["unrelated_field"] == "keep-me"
    assert result["some_field"] == "value"
    assert web_ui.app_state["home_environment"] == result


def test_mutate_home_environment_state_preserves_concurrent_top_level_keys():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state["home_environment"] = {"other_key": "from-someone-else"}

    def _apply(home):
        home["my_key"] = "mine"

    result = web_ui._mutate_home_environment_state(_apply)
    assert result["my_key"] == "mine"
    assert result["other_key"] == "from-someone-else"


def test_mutate_home_environment_state_falls_back_to_default_when_unset():
    with web_ui._APP_STATE_LOCK:
        web_ui.app_state.pop("home_environment", None)

    def _apply(home):
        home["touched"] = True

    result = web_ui._mutate_home_environment_state(_apply)
    assert result["touched"] is True
    # _default_home_state() should have populated other baseline keys.
    assert len(result) > 1
