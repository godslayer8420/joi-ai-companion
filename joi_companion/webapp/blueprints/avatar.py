"""Avatar blueprint — extracted from web_ui.py.

Handles all /api/avatar/* routes:
  - Model management (default, list, upload)
  - Portrait serving
  - Reference image management (latest, sources, palette)
  - Unreal Engine identity contract sync
  - Body state (get, apply, preset)
  - Selfies (get, post)

Helper functions (_resolve_runtime_avatar_model_path, etc.) remain in web_ui.py
during the incremental migration. This blueprint imports them from the global
module namespace at request time to avoid circular imports.

Sacred geometry note:
  All avatar domain limits use TRINITY (3) or HARMONY (6) where applicable.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

# ── Blueprint definition ──────────────────────────────────────────────────────
avatar_bp = Blueprint("avatar", __name__, url_prefix="")


def _web_ui():
    """Lazy import of web_ui module to access shared helpers and app_state."""
    return sys.modules.get("__main__") or importlib.import_module("web_ui")


def _h(name):
    """Get a helper function from web_ui by name."""
    mod = _web_ui()
    fn = getattr(mod, name, None)
    if fn is None:
        raise RuntimeError(f"web_ui helper '{name}' not found — is web_ui.py loaded?")
    return fn


def _state():
    """Get the shared app_state dict from web_ui."""
    mod = _web_ui()
    return getattr(mod, "app_state", {})


# ── Avatar model routes ───────────────────────────────────────────────────────

@avatar_bp.route("/api/avatar/model/default", methods=["GET"])
def api_avatar_model_default():
    resolve = _h("_resolve_runtime_avatar_model_path")
    find_default = _h("_find_aurion_default_model_path")
    make_url = _h("_make_aurion_default_model_url")
    resolve_wardrobe = _h("_resolve_wardrobe_state")

    model_path = resolve() or find_default()
    if not model_path:
        return jsonify({"success": True, "exists": False, "url": "", "filename": "", "label": "No 3D avatar model"})

    wardrobe_appearance = dict(resolve_wardrobe().get("active_runtime_appearance") or {})
    return jsonify({
        "success": True,
        "exists": True,
        "url": make_url(model_path),
        "filename": model_path.name,
        "label": f"3D avatar ready: {model_path.stem}",
        "asset_key": str(wardrobe_appearance.get("asset_key", "") or "").strip(),
        "asset_label": str(wardrobe_appearance.get("asset_label", "") or "").strip(),
        "runtime_selected": bool(resolve() and resolve().resolve() == model_path.resolve()),
    })


@avatar_bp.route("/api/avatar/model/list", methods=["GET"])
def api_avatar_model_list():
    list_files = _h("_list_aurion_model_files")
    build_record = _h("_build_avatar_model_record")
    models = [build_record(p) for p in list_files()]
    return jsonify({"success": True, "models": models})


@avatar_bp.route("/api/avatar/model/upload", methods=["POST"])
def api_avatar_model_upload():
    import shutil, re, time as _time
    try:
        require_access = _h("_require_local_privileged_access")
        privileged = require_access()
        if privileged is not None:
            return privileged

        if "model" not in request.files:
            return jsonify({"success": False, "error": "No model file provided."}), 400
        file = request.files["model"]
        if not file or not str(file.filename or "").strip():
            return jsonify({"success": False, "error": "No model file selected."}), 400

        mod = _web_ui()
        AURION_MODEL_EXTENSIONS = getattr(mod, "_AURION_MODEL_EXTENSIONS", {".glb", ".gltf", ".vrm", ".fbx", ".obj"})
        AURION_MODEL_DIR = getattr(mod, "_AURION_MODEL_DIR", Path("."))
        AURION_MODEL_BASENAME = getattr(mod, "_AURION_MODEL_BASENAME", "aurion-avatar")

        source_name = Path(str(file.filename)).name
        suffix = Path(source_name).suffix.lower()
        if suffix not in AURION_MODEL_EXTENSIONS:
            return jsonify({"success": False, "error": "Unsupported avatar format."}), 400

        file_data = file.read()
        if not file_data:
            return jsonify({"success": False, "error": "Uploaded file was empty."}), 400

        validate_magic = _h("_validate_uploaded_magic_bytes")
        ok_magic, reason = validate_magic(source_name, file_data)
        if not ok_magic:
            return jsonify({"success": False, "error": reason}), 400

        AURION_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        make_default = str(request.form.get("set_default", "1")).strip().lower() not in {"0", "false", "no", "off"}
        source_stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(source_name).stem).strip("-.") or f"aurion-avatar-{int(_time.time())}"
        target_filename = f"{source_stem}{suffix}"
        target_path = AURION_MODEL_DIR / target_filename
        target_path.write_bytes(file_data)

        default_path = target_path
        if make_default:
            default_path = AURION_MODEL_DIR / f"{AURION_MODEL_BASENAME}{suffix}"
            if target_path.resolve() != default_path.resolve():
                shutil.copy2(str(target_path), str(default_path))

        record_event = _h("_record_runtime_event")
        record_event("avatar-upload", f"Avatar model updated: {target_path.name}", source="api")

        make_url = _h("_make_aurion_default_model_url")
        build_record = _h("_build_avatar_model_record")
        return jsonify({
            "success": True,
            "url": make_url(default_path),
            "filename": default_path.name,
            "stored_filename": target_path.name,
            "set_default": make_default,
            "model": build_record(target_path),
            "default_model": build_record(default_path),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Avatar portrait ───────────────────────────────────────────────────────────

@avatar_bp.route("/api/avatar/portrait", methods=["GET"])
def api_avatar_portrait():
    portrait_path = Path(__file__).parent.parent.parent / "static" / "models" / "aurion_portrait.png"
    if portrait_path.exists():
        return send_file(str(portrait_path), mimetype="image/png", conditional=True)
    return jsonify({"success": False, "error": "No portrait found.", "label": "2D portrait unavailable"}), 404


# ── Avatar reference images ───────────────────────────────────────────────────

@avatar_bp.route("/api/avatar/reference/latest/meta", methods=["GET"])
def api_avatar_reference_latest_meta():
    import time as _time
    collect = _h("_collect_avatar_reference_images")
    find_latest = _h("_find_latest_avatar_reference_image")
    format_label = _h("_format_reference_source_label")
    summarize = _h("_summarize_avatar_reference_sources")

    ref_dir, refs = collect()
    ref = find_latest()
    if not ref:
        return jsonify({
            "success": True, "exists": False, "url": "", "filename": "",
            "directory": str(ref_dir) if ref_dir else "", "count": 0,
            "source_label": format_label(ref_dir), "status_label": "No live reference frames",
        })
    try:
        version = int(ref.stat().st_mtime_ns)
    except Exception:
        version = int(_time.time() * 1000)
    return jsonify({
        "success": True, "exists": True, "count": len(refs),
        "directory": str(ref_dir) if ref_dir else "", "filename": ref.name,
        "url": f"/api/avatar/reference/latest?v={version}",
        "source_label": format_label(ref_dir),
        "status_label": f"{len(refs)} live reference frame{'s' if len(refs) != 1 else ''}",
        "source_summary": summarize(force_refresh=False),
    })


@avatar_bp.route("/api/avatar/reference/sources", methods=["GET"])
def api_avatar_reference_sources():
    try:
        force = str(request.args.get("refresh", "")).strip().lower() in {"1", "true", "yes", "on"}
        summarize = _h("_summarize_avatar_reference_sources")
        return jsonify({"success": True, "reference_sources": summarize(force_refresh=force)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@avatar_bp.route("/api/avatar/reference/latest", methods=["GET"])
def api_avatar_reference_latest():
    find_latest = _h("_find_latest_avatar_reference_image")
    ref = find_latest()
    if not ref:
        return jsonify({"success": False, "error": "No reference image found.", "label": "No live reference image"}), 404
    try:
        return send_file(str(ref), conditional=True)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@avatar_bp.route("/api/avatar/reference/palette", methods=["GET"])
def api_avatar_reference_palette():
    try:
        force = str(request.args.get("refresh", "")).strip().lower() in {"1", "true", "yes", "on"}
        extract_palette = _h("_extract_avatar_reference_palette")
        return jsonify({"success": True, "palette": extract_palette(force_refresh=force)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Selfies ───────────────────────────────────────────────────────────────────

@avatar_bp.route("/api/avatar/selfies", methods=["GET"])
def api_avatar_selfies_get():
    try:
        get_selfies = _h("_get_aurion_selfies")
        return jsonify({"success": True, "selfies": get_selfies()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@avatar_bp.route("/api/avatar/selfies", methods=["POST"])
def api_avatar_selfies_post():
    try:
        save_selfie = _h("_save_aurion_selfie")
        data = request.get_json(force=True) or {}
        result = save_selfie(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
