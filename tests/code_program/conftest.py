"""Test config for the code-program suite (see ARCHITECTURE.md for the
code-program vs game-program split).

Setting AURION_TESTING here, before web_ui is ever imported by any test in
this package, ensures the module-level autonomy background threads never
start as a side effect of `import web_ui` (see web_ui._ENABLE_AUTONOMY_THREADS).
"""
import os

os.environ.setdefault("AURION_TESTING", "1")
