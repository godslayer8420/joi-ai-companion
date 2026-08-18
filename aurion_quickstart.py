#!/usr/bin/env python3
"""
aurion_quickstart.py — local AI stack launcher
Run this to bring up Aurion's free-first model stack before using Copilot tokens.

Usage:
    python aurion_quickstart.py            # Check what's available
    python aurion_quickstart.py --start    # Start available services
    python aurion_quickstart.py --jupyter  # Start WSL JupyterLab
"""
import os
import sys
import subprocess
import socket
import argparse

LMSTUDIO_PORT = 1234
OLLAMA_PORT = 11434
JUPYTER_PORT = 8888

def port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False

def check_lmstudio():
    alive = port_open("localhost", LMSTUDIO_PORT)
    print(f"  LM Studio  (localhost:{LMSTUDIO_PORT}): {'✓ RUNNING' if alive else '✗ not running'}")
    if not alive:
        print("    → Open LM Studio, load a model (Saturn-7B or Ouroboros-Next-9B), and enable the server.")
    return alive

def check_ollama():
    alive = port_open("localhost", OLLAMA_PORT)
    print(f"  Ollama     (localhost:{OLLAMA_PORT}): {'✓ RUNNING' if alive else '✗ not running'}")
    if not alive:
        print("    → Run: ollama serve  (in a separate terminal)")
    return alive

def check_jupyter():
    alive = port_open("localhost", JUPYTER_PORT)
    print(f"  JupyterLab (localhost:{JUPYTER_PORT}): {'✓ RUNNING' if alive else '✗ not running'}")
    if not alive:
        print("    → Run: wsl jupyter lab --no-browser --port=8888")
    return alive

def start_ollama():
    print("  Starting Ollama…")
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_jupyter():
    print("  Starting WSL JupyterLab on port 8888…")
    subprocess.Popen(
        ["wsl", "-d", "Ubuntu", "--", "bash", "-c",
         "jupyter lab --no-browser --port=8888 --ip=0.0.0.0 --NotebookApp.token='' &"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print("  JupyterLab: http://localhost:8888")

def print_model_inventory():
    lmstudio_base = r"D:\bzimm\.lmstudio\models"
    print("\n  Key local models (serve via LM Studio or Ollama):")
    models = [
        ("Ouroboros-Next-9B", r"mradermacher\Ouroboros-Next-9B-GGUF\Ouroboros-Next-9B-Q4_K_M.gguf"),
        ("13B-Ouroboros",     r"mradermacher\13B-Ouroboros-GGUF\13B-Ouroboros.Q3_K_S.gguf"),
        ("Saturn-7B",        r"mradermacher\Saturn-7B.Q4_K_S.gguf"),
        ("EVA-Qwen2.5-7B",   r"mmnga\EVA-Qwen2.5-7B-v0.1-gguf\EVA-Qwen2.5-7B-v0.1.Q8_0.gguf"),
        ("Gemma-4-26B",      r"bartowski\gemma-4-26B-A4B-it-GGUF\gemma-4-26B-A4B-it-Q8_0.gguf"),
        ("Gemma-3-12B",      r"bartowski\gemma-3-12b-it-GGUF\gemma-3-12b-it-Q4_K_M.gguf"),
    ]
    for alias, rel in models:
        full = os.path.join(lmstudio_base, rel)
        status = "✓" if os.path.exists(full) else "?"
        print(f"    {status} {alias:<22} alias in personality_engine: see ALIASES section")

    print("\n  Ollama Modelfiles (ai_core/):")
    for mf in ["gemma_modelfile.txt", "ouroboros_next_modelfile.txt", "saturn_modelfile.txt", "eva_modelfile.txt"]:
        path = os.path.join("ai_core", mf)
        status = "✓" if os.path.exists(path) else "?"
        name = mf.replace("_modelfile.txt", "").replace("_", "-")
        print(f"    {status} ollama create {name} -f {path}")

def main():
    parser = argparse.ArgumentParser(description="Aurion local AI stack launcher")
    parser.add_argument("--start", action="store_true", help="Start available services (Ollama)")
    parser.add_argument("--jupyter", action="store_true", help="Start WSL JupyterLab")
    args = parser.parse_args()

    print("═══════════════════════════════════════")
    print("  Aurion — Local AI Stack Status")
    print("═══════════════════════════════════════")
    lm = check_lmstudio()
    ol = check_ollama()
    jl = check_jupyter()

    if args.start:
        print()
        if not ol:
            start_ollama()
    if args.jupyter:
        print()
        if not jl:
            start_jupyter()

    print_model_inventory()

    print("\n  Free provider priority (env: AURION_PROVIDER_PRIORITY):")
    print("    1. custom_local  (LM Studio localhost:1234)")
    print("    2. ollama        (localhost:11434)")
    print("    3. gemini        (gemini-3-flash-preview — free, confirmed working)")
    print("\n  Set AURION_CUSTOM_LOCAL_BASE_URL=http://localhost:1234 to activate LM Studio.")
    print("═══════════════════════════════════════")

if __name__ == "__main__":
    main()
