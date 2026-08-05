"""Test config for the code-program suite (see ARCHITECTURE.md for the
code-program vs game-program split).

Setting AURION_TESTING here, before web_ui is ever imported by any test in
this package, ensures the module-level autonomy background threads never
start as a side effect of `import web_ui` (see web_ui._ENABLE_AUTONOMY_THREADS).
"""
import os
import tempfile

os.environ.setdefault("AURION_TESTING", "1")

# Isolate the persistent memory/profile store from the real one.
#
# Discovered while testing world_continuity locking: MemorySystem() (used by
# web_ui.py) defaults to a real, persistent TinyDB JSON file (normally
# %LOCALAPPDATA%\Aurion\memory\aurion_memory.json, falling back to
# ./aurion_memory.json in this environment). Without this override, running
# the test suite reads AND WRITES that real file -- test runs were polluting
# real app data, and killing a slow test process mid-write once corrupted it
# (recovered by MemorySystem's own self-repair, but should never happen from
# a test run). AURION_MEMORY_DB_PATH already existed as a supported override;
# point it at a fresh temp file for the life of the test session.
os.environ.setdefault(
    "AURION_MEMORY_DB_PATH",
    os.path.join(tempfile.mkdtemp(prefix="aurion_code_program_tests_"), "test_aurion_memory.json"),
)
