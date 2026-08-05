# Aurion memory/profile substrate

This folder is the dedicated home for Aurion's runtime memory and
persona/profile data, separate from source code (`joi_companion/core/`,
`joi_companion/aurion_runtime/`) and from packaging/build artifacts.

## Contents

- `aurion_notes.jsonl` — autonomous continuity notes (self-fix checkpoints
  and "auto tick" insights), one JSON object per line. Replaces the old
  design where these notes were appended as executable-looking Python
  functions to `joi_companion/aurion_runtime/aurion_self_edits.py` (a file
  that grew unbounded and was never actually imported/executed as code —
  see `p1-aurion-self-edits-redesign` in the session history). This file
  is bounded (oldest entries are trimmed once it exceeds a configured
  line count) and is genuinely just data, not source.
- `aurion_personality.json` — Aurion's persona/profile configuration.

## Notes for future work

- This folder is intentionally separate from `joi_companion/aurion_runtime/`
  (the game-program's world-simulation layer) and from
  `joi_companion/core/` (the code-program's runtime modules) — see
  `ARCHITECTURE.md` at the repo root for the code-program/game-program
  split.
- The autonomous "code edit" tick can still be pointed at a real repo
  source file (e.g. if a user's chat message names an existing `.py`
  file to fix) — that path is unaffected by this folder and continues to
  go through the existing repo-scoped code-edit machinery
  (`_apply_repo_code_edit`). Only the *default*, no-target-specified case
  (previously `aurion_self_edits.py`) now lands here as structured data.
- Richer persona personalization (expanding `aurion_personality.json`'s
  schema/content) is a content/design decision for whoever owns Aurion's
  character, not something authored by the code-program infrastructure
  pass that created this folder.
