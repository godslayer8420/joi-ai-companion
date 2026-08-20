# -*- mode: python ; coding: utf-8 -*-
"""
Aurion.spec  --  PyInstaller packaging spec for Aurion.
Entry point: main.py (pygame/voice/vision desktop runtime)
Web entry:   web_ui.py (Flask companion surface)

Build commands:
  pyinstaller Aurion.spec                  # desktop runtime
  pyinstaller --add-data "static;static" Aurion.spec

Sacred geometry token budget is enforced externally -- not baked into build.

Dependencies covered by requirements.txt as of 2026-08-20:
  flask, flask-cors, python-dotenv, cryptography, openai, anthropic, cohere,
  ollama, vosk, pyttsx3, sounddevice, PyAudio, opencv-contrib-python, pygame,
  mediapipe, spacy (en_core_web_sm), matplotlib, scipy, jax, jaxlib,
  websockets, requests, pillow, tinydb, rich, tqdm
"""

import os, sys, shutil as _shutil
from PyInstaller.utils.hooks import collect_all as _collect_all

block_cipher = None

_is_windows = sys.platform == "win32"
_is_macos   = sys.platform == "darwin"

# ---- Icon ----------------------------------------------------------------
if _is_windows:
    _icon = "static/favicon.ico" if os.path.exists("static/favicon.ico") else None
elif _is_macos:
    _icon = "static/favicon.icns" if os.path.exists("static/favicon.icns") else None
else:
    _icon = None

# ---- Extra collections for packages with native binaries ----------------
_extra_datas      = []
_extra_binaries   = []
_extra_hiddenimports = []

_native_pkgs = [
    "cv2",          # opencv
    "mediapipe",    # mediapipe tasks
    "sounddevice",  # portaudio bindings
    "vosk",         # VOSK STT
    "spacy",        # spacy + en_core_web_sm
    "en_core_web_sm",
]

for _pkg in _native_pkgs:
    try:
        _d, _b, _h = _collect_all(_pkg)
        _extra_datas      += _d
        _extra_binaries   += _b
        _extra_hiddenimports += _h
    except Exception as _exc:
        print(f"WARNING: could not collect {_pkg}: {_exc}")

# ---- Vosk model (offline STT) -------------------------------------------
_vosk_src = os.path.join("model", "vosk-model-small-en-us-0.15")
if os.path.isdir(_vosk_src):
    _extra_datas.append((_vosk_src, os.path.join("model", "vosk-model-small-en-us-0.15")))
else:
    print("WARNING: vosk model not found at model/vosk-model-small-en-us-0.15 -- "
          "STT will not work in built app. Run: python -c \"import vosk; vosk.MODEL_PATH\"")

# ---- Aurion avatar models ------------------------------------------------
if os.path.isdir("static/models"):
    _extra_datas.append(("static/models", "static/models"))

# ---- Flask templates + static -------------------------------------------
if os.path.isdir("static"):
    _extra_datas.append(("static", "static"))
if os.path.isdir("templates"):
    _extra_datas.append(("templates", "templates"))

# ---- .env (optional, user-provided) -------------------------------------
if os.path.exists(".env"):
    _extra_datas.append((".env", "."))

# ---- Analysis ------------------------------------------------------------
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=_extra_binaries,
    datas=[
        ("requirements.txt", "."),
        ("joi_companion", "joi_companion"),
        ("ai_core", "ai_core"),
    ] + _extra_datas,
    hiddenimports=[
        # Flask + runtime
        "flask", "flask_cors", "dotenv", "cryptography",
        # LLM providers
        "openai", "anthropic", "cohere", "ollama",
        # Audio/voice
        "pyttsx3", "pyttsx3.drivers", "pyttsx3.drivers.sapi5",
        "sounddevice", "vosk", "PyAudio",
        # Vision
        "cv2", "mediapipe",
        # NLP
        "spacy", "en_core_web_sm",
        # Aurion core
        "joi_companion.core.context_manager",
        "joi_companion.core.llm_router",
        "joi_companion.core.companion_config",
        "joi_companion.core.aurion_unified_model",
        "joi_companion.core.sacred_geometry",
        "joi_companion.core.personality_engine",
        "joi_companion.core.memory_system",
        "joi_companion.core.speech_handler",
        "joi_companion.core.vision_processor",
        "joi_companion.core.intent_parser",
        "joi_companion.core.ui_manager",
        # Numerics
        "scipy", "numpy", "matplotlib",
        # Misc
        "tinydb", "websockets", "requests", "PIL",
    ] + _extra_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude large training-only / non-runtime deps
        "jax", "jaxlib", "torch", "tensorflow",
        "IPython", "jupyter", "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Aurion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,          # set False for windowed-only release
    disable_windowed_traceback=False,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Aurion",
)

if _is_macos:
    app = BUNDLE(
        coll,
        name="Aurion.app",
        icon=_icon,
        bundle_identifier="com.aurion.companion",
    )