# Architecture: code-program vs. game-program

This repository contains two intentionally separate tracks. Keep ownership,
tests, and CI scoped to the right one — cross-cutting changes should be rare
and called out explicitly in the PR description.

## Code-program (AI companion runtime)

The operator-facing application: startup, HTTP surface, LLM providers,
memory, personality, media I/O, and packaging.

- `run_web_ui.py` / `web_ui.py` — primary entrypoint (Flask app, HTTP API,
  security guard, self-edit/exec endpoints).
- `main.py` — legacy standalone pygame desktop loop (secondary entrypoint).
- `joi_companion/core/` — personality engine, memory system, vision/audio
  processing, content generation, intent parsing.
- `joi_companion/data/` — runtime data (e.g. `aurion_personality.json`).
- `Aurion.spec` — PyInstaller packaging.
- `requirements.txt` — code-program's third-party dependencies.

Tests for this track should live under `tests/code_program/` (to be created)
and stay independent from the game-program tests below.

## Game-program (world/lore simulation)

The in-world simulation content Aurion's game surfaces: regions, festivals,
the city atlas, and narrative continuity/consequence systems.

- `joi_companion/aurion_runtime/` — `world_atlas.py`, `world_regions.py`,
  `world_simulation.py`, `world_continuity.py`, `world_consequences.py`,
  `world_journey.py`, `lumen_city.py`, `regional_*.py`, `festival_*.py`,
  `durable_io.py`, `aurion_self_edits.py` (autonomy log, not executable
  code — see the code-program's exec-surface hardening workstream).
- `android/` and the Unreal Engine bridge (`aurion_unreal_bridge.py`) —
  external game-client surfaces that consume this simulation state.
- `game_design/` — design docs for this track.

Existing tests under `tests/` (`test_world_*`, `test_regional_*`,
`test_festival_*`, `test_lumen_city.py`) already cover this track exclusively
(142 tests passing as of this writing) and should stay there.

## Why the split matters

`joi_companion/aurion_runtime/` is imported by `web_ui.py` for rendering game
state to the operator UI, but its correctness, pacing, and content design are
owned independently from the runtime's security/reliability/packaging work.
Do not let game-content changes block code-program releases, and do not let
code-program refactors (e.g. modularizing `web_ui.py`) silently change
game-program behavior — cover any shared surface with an explicit contract
test on both sides before refactoring.
