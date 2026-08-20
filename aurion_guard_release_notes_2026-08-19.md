# Aurion Guardrail Rollup (2026-08-19)

## Scope
- Enforced fail-closed paid-provider authorization.
- Added local-first shell guard operations (safe start, timed unlock, lock, panic lock).
- Added diagnostics and reliability metadata coverage.

## Key outcomes
- Default runtime remains local (ollama) unless explicit, time-bounded paid unlock is active.
- Paid unlock now has dual-confirm flow and explicit operator intent.
- Panic-lock path force-resets to local and records a forensic snapshot.
- Guard status and help output now have regression tests.
- Memory resilience payload includes richer reliability metadata for observability.

## New/updated ops commands
- urion-start
- urion-safe-start
- urion-status
- urion-status-verbose
- urion-paid-enable
- urion-paid-30
- urion-lock
- urion-paid-disable
- urion-panic-lock
- urion-help

## Verification snapshots
Run:
- urion-start
- urion-status
Expected:
- env=ollama
- chosen=ollama
- paid_valid=no

Optional paid window:
1. urion-paid-enable
2. urion-paid-30
3. urion-status (shows paid window active)
4. urion-lock then urion-status (returns to local/no paid auth)

## Recent commit heads (for PR context)
- d39a3aed test: add guard e2e workflow smoke coverage
- 45494d3a test: add quiet guard status output regression coverage
- 28f2b585 test: add aurion-help output regression coverage
- 790f9c54 feat: add reliability summary string to memory resilience payload
- a1f9676c feat: add reliability tier classification to memory resilience payload
- 1e5dc84e feat: add bounded reliability score to memory resilience payload
- 2210e50c feat: enrich memory resilience payload with reliability metadata
