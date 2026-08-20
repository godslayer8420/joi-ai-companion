from tinydb import TinyDB
from datetime import datetime
import random
import re
import json
import math
import os
import shutil
import threading
import time
import base64
import hashlib
import ctypes
from ctypes import wintypes
from collections import Counter
from pathlib import Path


class MemorySystem:
    def __init__(self, db_path='aurion_memory.json'):
        # 0 means unbounded; this is the default to preserve "remember everything" behavior.
        self.max_rag_docs = max(0, int(os.getenv("AURION_MAX_RAG_DOCS", "0")))
        self.max_rag_scan_docs = max(0, int(os.getenv("AURION_MAX_RAG_SCAN_DOCS", "0")))
        self.max_profile_list_items = max(200, int(os.getenv("AURION_MAX_PROFILE_LIST_ITEMS", "50000")))
        self.rag_chunk_chars = max(300, int(os.getenv("AURION_RAG_CHUNK_CHARS", "1800")))
        self.rag_chunk_overlap = max(0, int(os.getenv("AURION_RAG_CHUNK_OVERLAP", "240")))
        self.max_message_ingest_chars = max(4000, int(os.getenv("AURION_MAX_MESSAGE_INGEST_CHARS", "350000")))
        self.max_rag_context_chars = max(1200, int(os.getenv("AURION_MAX_RAG_CONTEXT_CHARS", "5000")))
        self.db_path = self._resolve_db_path(db_path)
        self._resilience_lock = threading.Lock()
        self._db_lock = threading.RLock()  # Serializes all TinyDB reads/writes
        self._last_backup_at = None
        self._last_secondary_sync_at = None
        self._last_backup_file = ""
        self._last_resilience_error = ""
        self._memory_write_count = 0
        self._cloud_root_failures = {}
        self._conversation_cipher = None
        self._conversation_encryption_enabled = False
        self._conversation_encryption_error = ""
        self._conversation_encryption_source = "disabled"
        self._profile_secret_paths = (
            ("phone_settings", "discord_webhook_url"),
            ("phone_settings", "discord_bot_token"),
            ("phone_settings", "twitch_oauth_token"),
        )
        self._profile_encrypted_string_fields = {
            "personality_profile_text",
        }
        self._profile_encrypted_life_context_keys = {
            "world_sovereign_skills_json",
            "world_sovereign_resources_json",
            "world_spacefaring_json",
            "world_builder_state_json",
            "sovereign_body_learning_traits_json",
            "sovereign_creation_learning_traits_json",
            "world_bug_protection_json",
        }
        self._in_self_repair = False
        self._profile_read_repair_attempted = False
        self._configure_resilience_paths()
        self._configure_cloud_memory_offload()
        self._configure_conversation_encryption()
        self._repair_corrupted_db_if_needed()
        self.db = None
        self.conversations = None
        self.user_profile = None
        self.topics = None
        self._open_db()
        self.session_id = datetime.utcnow().isoformat()
        self.session_turn = 0
        try:
            self._ensure_profile_schema()
            self._sync_memory_architecture_profile()
        except Exception as e:
            print(f"[MemorySystem] Profile schema check failed at startup: {e}")
            repair = self.self_repair()
            if not repair.get("ok"):
                raise
        self._import_legacy_chat_memory()
        self._run_resilience_maintenance(force=True, reason="startup")

    def _resolve_db_path(self, db_path):
        configured = str(os.getenv("AURION_MEMORY_DB_PATH", "")).strip()
        legacy_default = Path(r"D:\AurionData\aurion_memory.json")
        default_primary = self._default_primary_memory_path()
        raw_hint = str(db_path or "").strip()
        use_default_primary = (
            not configured and (
                not raw_hint or
                raw_hint.lower() == "aurion_memory.json" or
                raw_hint == str(legacy_default)
            )
        )
        candidate = configured or (str(default_primary) if use_default_primary else raw_hint or str(default_primary))
        path = Path(candidate)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if use_default_primary and not path.exists() and legacy_default.exists():
                try:
                    shutil.copy2(str(legacy_default), str(path))
                except Exception as e:
                    print(f"[MemorySystem] Could not migrate legacy primary memory DB to C drive: {e}")
            return str(path)
        except Exception:
            # Fall back to local repo path if D: path cannot be created.
            return str(Path(db_path or "aurion_memory.json"))

    def _default_primary_memory_path(self):
        if os.name == "nt":
            local_app_data = str(os.getenv("LOCALAPPDATA", "")).strip()
            if local_app_data:
                return Path(local_app_data) / "Aurion" / "memory" / "aurion_memory.json"
        return Path("aurion_memory.json")

    def _default_memory_archive_root(self):
        configured = str(os.getenv("AURION_MEMORY_ARCHIVE_ROOT", "")).strip()
        if configured:
            return Path(configured).expanduser()
        if os.name == "nt":
            return Path(r"D:\AurionData\MemoryArchive")
        return self._default_primary_memory_path().parent / "archive"

    def _configure_resilience_paths(self):
        primary_path = Path(self.db_path)
        archive_root = self._default_memory_archive_root()
        default_secondary = archive_root / f"{primary_path.stem}_secondary{primary_path.suffix}"
        secondary_raw = str(os.getenv("AURION_MEMORY_SECONDARY_DB_PATH", str(default_secondary))).strip()
        backup_default = archive_root / "backups"
        backup_raw = str(os.getenv("AURION_MEMORY_BACKUP_DIR", str(backup_default))).strip()
        self.secondary_sync_interval_seconds = max(
            0,
            int(os.getenv("AURION_MEMORY_SECONDARY_SYNC_INTERVAL_SECONDS", "0"))
        )
        self.backup_interval_seconds = max(
            0,
            int(os.getenv("AURION_MEMORY_BACKUP_INTERVAL_SECONDS", "60"))
        )
        self.max_backup_files = max(
            0,
            int(os.getenv("AURION_MEMORY_BACKUP_MAX_FILES", "0"))
        )

        self.secondary_db_path = ""
        self.backup_dir = ""

        if secondary_raw:
            secondary = Path(secondary_raw)
            try:
                secondary.parent.mkdir(parents=True, exist_ok=True)
                if secondary.resolve() != primary_path.resolve():
                    self.secondary_db_path = str(secondary)
            except Exception:
                self.secondary_db_path = ""

        if backup_raw:
            backup_dir = Path(backup_raw)
            try:
                backup_dir.mkdir(parents=True, exist_ok=True)
                self.backup_dir = str(backup_dir)
            except Exception:
                self.backup_dir = ""

    def _configure_cloud_memory_offload(self):
        raw_sections = str(os.getenv("AURION_MEMORY_CLOUD_ROOTS", "")).strip()
        manual_roots = []
        if raw_sections:
            for raw in re.split(r"[,;\n]+", raw_sections):
                path = str(raw or "").strip()
                if path:
                    manual_roots.append(Path(path).expanduser())

        if not manual_roots:
            home_dir = Path.home()
            d_drive_cloud_root = Path(r"D:\AurionData\CloudMemory")
            if os.name == "nt" and Path("D:\\").exists():
                manual_roots = [d_drive_cloud_root]
            else:
                manual_roots = []
            manual_roots.extend([
                home_dir / "OneDrive" / "AurionMemory",
                home_dir / "Google Drive" / "AurionMemory",
                home_dir / "Dropbox" / "AurionMemory",
            ])

        deduped = []
        seen = set()
        for path in manual_roots:
            try:
                normalized = str(path.expanduser().resolve())
            except Exception:
                normalized = str(path)
            key = normalized.lower()
            if not key or key in seen:
                continue
            if self._should_skip_cloud_root(path):
                continue
            seen.add(key)
            deduped.append(path.expanduser())

        self.cloud_memory_mode = str(os.getenv("AURION_MEMORY_CLOUD_MODE", "shadow")).strip().lower()
        self.cloud_memory_roots = deduped
        self.cloud_memory_offload_enabled = self.cloud_memory_mode not in ("off", "disabled", "false", "none") and bool(self.cloud_memory_roots)

        if self.cloud_memory_offload_enabled:
            for root in self.cloud_memory_roots:
                try:
                    root.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass

    def _drive_has_headroom(self, anchor_path):
        try:
            target = Path(anchor_path).expanduser()
            drive = target.drive or str(target.anchor or "")
            if not drive:
                return True
            usage = shutil.disk_usage(drive)
            return usage.free >= (512 * 1024 * 1024)
        except Exception:
            return True

    def _should_skip_cloud_root(self, path):
        try:
            candidate = Path(path).expanduser()
            normalized = str(candidate)
        except Exception:
            normalized = str(path)
            candidate = Path(path)

        lowered = normalized.lower()
        if os.name == "nt" and Path("D:\\").exists():
            if "\\onedrive\\" in lowered or "\\google drive\\" in lowered or "\\dropbox\\" in lowered:
                return True
        if not self._drive_has_headroom(candidate):
            return True
        return False

    def _mark_cloud_root_failed(self, root, error):
        key = str(root)
        message = str(error)
        previous = self._cloud_root_failures.get(key)
        self._cloud_root_failures[key] = message
        if previous == message:
            return
        print(f"[MemorySystem] Cloud memory sync failed for {root}: {error}")

    def _sync_cloud_memory_snapshot(self):
        if not self.cloud_memory_offload_enabled:
            return
        primary = Path(self.db_path)
        if not primary.exists():
            return
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        for root in self.cloud_memory_roots:
            if self._should_skip_cloud_root(root):
                continue
            try:
                root.mkdir(parents=True, exist_ok=True)
                target = root / f"{primary.stem}.cloud_snapshot.{stamp}{primary.suffix}"
                self._safe_copy_atomic(primary, target)
                self._cloud_root_failures.pop(str(root), None)
            except Exception as e:
                self._mark_cloud_root_failed(root, e)

    def _configure_conversation_encryption(self):
        key_raw = str(os.getenv("AURION_MEMORY_ENCRYPTION_KEY", "")).strip()
        if not key_raw:
            key_raw = self._load_or_create_managed_encryption_key()
        if not key_raw:
            self._conversation_encryption_enabled = False
            self._conversation_cipher = None
            self._conversation_encryption_error = ""
            self._conversation_encryption_source = "disabled"
            return
        try:
            from cryptography.fernet import Fernet
        except Exception as e:
            self._conversation_encryption_enabled = False
            self._conversation_cipher = None
            self._conversation_encryption_error = f"cryptography_unavailable:{e}"
            self._conversation_encryption_source = "unavailable"
            print(f"[MemorySystem] Conversation encryption disabled: {e}")
            return
        try:
            if key_raw.startswith("base64:"):
                key_material = key_raw.split("base64:", 1)[1].strip().encode("ascii")
            elif len(key_raw) == 44 and key_raw.endswith("="):
                key_material = key_raw.encode("ascii")
            else:
                digest = hashlib.sha256(key_raw.encode("utf-8")).digest()
                key_material = base64.urlsafe_b64encode(digest)
            self._conversation_cipher = Fernet(key_material)
            self._conversation_encryption_enabled = True
            self._conversation_encryption_error = ""
            if str(os.getenv("AURION_MEMORY_ENCRYPTION_KEY", "")).strip():
                self._conversation_encryption_source = "env"
            elif self._conversation_encryption_source in {"managed-dpapi", "managed-dpapi-created"}:
                pass
            else:
                self._conversation_encryption_source = "derived"
        except Exception as e:
            self._conversation_encryption_enabled = False
            self._conversation_cipher = None
            self._conversation_encryption_error = f"invalid_encryption_key:{e}"
            self._conversation_encryption_source = "invalid"
            print(f"[MemorySystem] Conversation encryption key invalid: {e}")

    def _managed_encryption_key_path(self):
        configured = str(os.getenv("AURION_MEMORY_ENCRYPTION_KEY_FILE", "")).strip()
        if configured:
            return Path(configured).expanduser()
        return Path(self.db_path).with_suffix(".key.dpapi")

    def _load_or_create_managed_encryption_key(self):
        if os.name != "nt":
            return ""
        key_path = self._managed_encryption_key_path()
        try:
            if key_path.exists():
                protected = key_path.read_text(encoding="utf-8").strip()
                plain = self._dpapi_decrypt_text(protected).strip()
                if plain:
                    self._conversation_encryption_source = "managed-dpapi"
                    return plain
            key_path.parent.mkdir(parents=True, exist_ok=True)
            generated = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
            protected = self._dpapi_encrypt_text(generated)
            if not protected.startswith("dpapi::"):
                return ""
            key_path.write_text(protected, encoding="utf-8")
            self._conversation_encryption_source = "managed-dpapi-created"
            return generated
        except Exception as e:
            self._conversation_encryption_error = f"managed_key_failed:{e}"
            return ""

    def _encrypt_conversation_text(self, value):
        text = str(value or "")
        if not self._conversation_encryption_enabled or not self._conversation_cipher:
            return text
        if not text or text.startswith("enc::"):
            return text
        token = self._conversation_cipher.encrypt(text.encode("utf-8")).decode("utf-8")
        return f"enc::{token}"

    def _decrypt_conversation_text(self, value):
        text = str(value or "")
        if not text.startswith("enc::"):
            return text
        if not self._conversation_encryption_enabled or not self._conversation_cipher:
            return "[encrypted message unavailable: missing key]"
        token = text.split("enc::", 1)[1].strip()
        if not token:
            return ""
        try:
            return self._conversation_cipher.decrypt(token.encode("utf-8")).decode("utf-8")
        except Exception:
            return "[encrypted message unavailable: key mismatch]"

    def _dpapi_encrypt_text(self, value):
        text = str(value or "")
        if not text or text.startswith("dpapi::") or os.name != "nt":
            return text
        try:
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_byte)),
                ]

            raw = text.encode("utf-8")
            in_buffer = ctypes.create_string_buffer(raw, len(raw))
            in_blob = DATA_BLOB(len(raw), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_byte)))
            out_blob = DATA_BLOB()
            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32
            if not crypt32.CryptProtectData(
                ctypes.byref(in_blob),
                "aurion-profile-secret",
                None,
                None,
                None,
                0,
                ctypes.byref(out_blob),
            ):
                return text
            try:
                encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            finally:
                kernel32.LocalFree(out_blob.pbData)
            return "dpapi::" + base64.b64encode(encrypted).decode("ascii")
        except Exception:
            return text

    def _dpapi_decrypt_text(self, value):
        text = str(value or "")
        if not text.startswith("dpapi::") or os.name != "nt":
            return text
        token = text.split("dpapi::", 1)[1].strip()
        if not token:
            return ""
        try:
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_byte)),
                ]

            raw = base64.b64decode(token.encode("ascii"), validate=False)
            in_buffer = ctypes.create_string_buffer(raw, len(raw))
            in_blob = DATA_BLOB(len(raw), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_byte)))
            out_blob = DATA_BLOB()
            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32
            if not crypt32.CryptUnprotectData(
                ctypes.byref(in_blob),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(out_blob),
            ):
                return ""
            try:
                decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            finally:
                kernel32.LocalFree(out_blob.pbData)
            return decrypted.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _profile_copy(self, profile):
        if not isinstance(profile, dict):
            return {}
        try:
            return json.loads(json.dumps(profile, ensure_ascii=False))
        except Exception:
            return dict(profile)

    def _set_profile_secret_value(self, profile, path, value):
        node = profile
        for key in path[:-1]:
            if not isinstance(node.get(key), dict):
                node[key] = {}
            node = node[key]
        node[path[-1]] = value

    def _get_profile_secret_value(self, profile, path):
        node = profile
        for key in path:
            if not isinstance(node, dict):
                return ""
            node = node.get(key)
        return str(node or "")

    def _serialize_profile_for_store(self, profile):
        out = self._encrypt_profile_payload(profile)
        for path in self._profile_secret_paths:
            current = self._get_profile_secret_value(out, path)
            if not current:
                continue
            self._set_profile_secret_value(out, path, self._dpapi_encrypt_text(current))
        return out

    def _materialize_profile_for_runtime(self, profile):
        out = self._profile_copy(profile)
        for path in self._profile_secret_paths:
            current = self._get_profile_secret_value(out, path)
            if not current:
                continue
            self._set_profile_secret_value(out, path, self._dpapi_decrypt_text(current))
        return self._decrypt_profile_payload(out)

    def _encrypt_profile_payload(self, profile):
        out = self._profile_copy(profile)
        for field in self._profile_encrypted_string_fields:
            current = str(out.get(field, "") or "")
            if current:
                out[field] = self._encrypt_conversation_text(current)
        life_context = dict(out.get("life_context", {}) or {})
        for key in self._profile_encrypted_life_context_keys:
            current = str(life_context.get(key, "") or "")
            if current:
                life_context[key] = self._encrypt_conversation_text(current)
        out["life_context"] = life_context
        return out

    def _decrypt_profile_payload(self, profile):
        out = self._profile_copy(profile)
        for field in self._profile_encrypted_string_fields:
            current = str(out.get(field, "") or "")
            if current:
                out[field] = self._decrypt_conversation_text(current)
        life_context = dict(out.get("life_context", {}) or {})
        for key in self._profile_encrypted_life_context_keys:
            current = str(life_context.get(key, "") or "")
            if current:
                life_context[key] = self._decrypt_conversation_text(current)
        out["life_context"] = life_context
        return out

    def _normalize_interaction(self, item):
        if not isinstance(item, dict):
            return {}
        interaction = dict(item)
        interaction["user_input"] = self._decrypt_conversation_text(interaction.get("user_input", ""))
        interaction["aurion_response"] = self._decrypt_conversation_text(interaction.get("aurion_response", ""))
        return interaction

    def _serialize_interaction_for_store(self, item):
        interaction = dict(item or {})
        interaction["user_input"] = self._encrypt_conversation_text(interaction.get("user_input", ""))
        interaction["aurion_response"] = self._encrypt_conversation_text(interaction.get("aurion_response", ""))
        return interaction

    def _get_all_interactions(self):
        try:
            with self._db_lock:
                interactions = [self._normalize_interaction(i) for i in self.conversations.all()]
                self._interaction_read_repair_attempted = False
                return interactions
        except Exception as e:
            if self._in_self_repair:
                raise
            if self._interaction_read_repair_attempted:
                raise
            self._interaction_read_repair_attempted = True
            print(f"[MemorySystem] conversation read failed: {e}")
            repair = self.self_repair()
            if not repair.get("ok"):
                raise
            with self._db_lock:
                interactions = [self._normalize_interaction(i) for i in self.conversations.all()]
                self._interaction_read_repair_attempted = False
                return interactions

    def _safe_copy_atomic(self, source_path, target_path):
        source = Path(source_path)
        target = Path(target_path)
        if not source.exists():
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f"{target.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        last_error = None
        for attempt in range(5):
            try:
                shutil.copy2(str(source), str(tmp))
                os.replace(str(tmp), str(target))
                return True
            except PermissionError as e:
                last_error = e
                time.sleep(0.12 * (attempt + 1))
            finally:
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass
        if last_error:
            raise last_error
        return False

    def _enforce_backup_retention(self):
        if not self.backup_dir or self.max_backup_files <= 0:
            return
        backup_root = Path(self.backup_dir)
        primary_name = Path(self.db_path).name
        pattern = f"{primary_name}.snapshot.*"
        files = sorted(backup_root.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0)
        excess = len(files) - self.max_backup_files
        if excess <= 0:
            return
        for old_file in files[:excess]:
            try:
                old_file.unlink(missing_ok=True)
            except Exception:
                continue

    def _run_resilience_maintenance(self, force=False, reason="write"):
        now = time.time()
        with self._resilience_lock:
            primary = Path(self.db_path)
            if not primary.exists():
                return

            try:
                do_secondary = force or self.secondary_sync_interval_seconds <= 0
                if not do_secondary and self._last_secondary_sync_at is not None:
                    do_secondary = (now - self._last_secondary_sync_at) >= self.secondary_sync_interval_seconds
                if self.secondary_db_path and do_secondary:
                    if self._safe_copy_atomic(primary, self.secondary_db_path):
                        self._last_secondary_sync_at = now
            except Exception as e:
                self._last_resilience_error = f"secondary_sync_failed:{e}"
                print(f"[MemorySystem] Secondary sync failed: {e}")

            try:
                do_backup = force or self.backup_interval_seconds <= 0
                if not do_backup and self._last_backup_at is not None:
                    do_backup = (now - self._last_backup_at) >= self.backup_interval_seconds
                if self.backup_dir and do_backup:
                    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                    backup_file = Path(self.backup_dir) / f"{primary.name}.snapshot.{stamp}"
                    if self._safe_copy_atomic(primary, backup_file):
                        self._last_backup_at = now
                        self._last_backup_file = str(backup_file)
                        self._enforce_backup_retention()
            except Exception as e:
                self._last_resilience_error = f"backup_failed:{e}"
                print(f"[MemorySystem] Backup snapshot failed: {e}")

            try:
                self._sync_cloud_memory_snapshot()
            except Exception as e:
                self._last_resilience_error = f"cloud_sync_failed:{e}"
                print(f"[MemorySystem] Cloud memory sync failed: {e}")

    def _mark_memory_written(self, reason="write"):
        self._memory_write_count += 1
        self._run_resilience_maintenance(force=False, reason=reason)

    def get_memory_resilience_status(self):
        primary = Path(self.db_path)
        secondary = Path(self.secondary_db_path) if self.secondary_db_path else None
        return {
            "primary_path": str(primary),
            "primary_exists": primary.exists(),
            "primary_size_bytes": int(primary.stat().st_size) if primary.exists() else 0,
            "secondary_path": str(secondary) if secondary else "",
            "secondary_exists": bool(secondary and secondary.exists()),
            "backup_dir": str(self.backup_dir or ""),
            "last_backup_file": self._last_backup_file,
            "last_backup_at": datetime.utcfromtimestamp(self._last_backup_at).isoformat() if self._last_backup_at else None,
            "last_secondary_sync_at": datetime.utcfromtimestamp(self._last_secondary_sync_at).isoformat() if self._last_secondary_sync_at else None,
            "write_count": int(self._memory_write_count),
            "last_error": self._last_resilience_error or None,
            "cloud_memory_root_failures": dict(getattr(self, "_cloud_root_failures", {})),
            "conversation_encryption_enabled": bool(self._conversation_encryption_enabled),
            "conversation_encryption_error": self._conversation_encryption_error or None,
            "conversation_encryption_source": self._conversation_encryption_source,
            "profile_encrypted_fields": sorted(list(self._profile_encrypted_string_fields)),
            "life_context_encrypted_keys": sorted(list(self._profile_encrypted_life_context_keys)),
            "memory_architecture": self._build_memory_architecture_state()
        }

    def _open_db(self):
        self.db = TinyDB(self.db_path, encoding="utf-8")
        self.conversations = self.db.table('conversations')
        self.user_profile = self.db.table('user_profile')
        self.topics = self.db.table('topics')
        self.rag_documents = self.db.table('rag_documents')
        self._interaction_read_repair_attempted = False

    def _repair_corrupted_db_if_needed(self):
        """Repair TinyDB JSON when interrupted writes leave trailing junk."""
        def _is_valid_tinydb_json(path_obj):
            try:
                raw_text = path_obj.read_text(encoding='utf-8', errors='strict')
                if not raw_text.strip():
                    return True
                parsed = json.loads(raw_text)
                return isinstance(parsed, dict)
            except Exception:
                return False

        path = Path(self.db_path)
        if not path.exists():
            secondary = Path(self.secondary_db_path) if self.secondary_db_path else None
            if secondary and secondary.exists():
                try:
                    if _is_valid_tinydb_json(secondary):
                        self._safe_copy_atomic(secondary, path)
                        print("[MemorySystem] Restored primary memory DB from secondary replica.")
                        return
                    print("[MemorySystem] Secondary replica exists but is invalid JSON; skipping restore.")
                except Exception as e:
                    print(f"[MemorySystem] Could not restore from secondary replica: {e}")
            return
        try:
            raw = path.read_text(encoding='utf-8')
            if not raw.strip():
                return
            decoder = json.JSONDecoder()
            obj, end = decoder.raw_decode(raw)
            trailing = raw[end:].strip()
            if trailing:
                backup = path.with_name(f"{path.name}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
                backup.write_text(raw, encoding='utf-8')
                path.write_text(
                    json.dumps(obj, ensure_ascii=False, separators=(',', ':')),
                    encoding='utf-8'
                )
                print(f"[MemorySystem] Repaired corrupted DB and saved backup: {backup.name}")
        except json.JSONDecodeError:
            # Attempt a second-pass repair for invalid control chars in JSON text.
            try:
                raw = path.read_text(encoding='utf-8')
                cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', raw)
                obj = json.loads(cleaned)
                backup = path.with_name(f"{path.name}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
                backup.write_text(raw, encoding='utf-8')
                path.write_text(
                    json.dumps(obj, ensure_ascii=False, separators=(',', ':')),
                    encoding='utf-8'
                )
                print(f"[MemorySystem] Removed invalid control chars and saved backup: {backup.name}")
            except Exception:
                # Last resort: preserve a backup and reset to a valid empty TinyDB document.
                try:
                    secondary = Path(self.secondary_db_path) if self.secondary_db_path else None
                    if secondary and secondary.exists() and _is_valid_tinydb_json(secondary):
                        self._safe_copy_atomic(secondary, path)
                        print("[MemorySystem] Restored unreadable primary DB from secondary replica.")
                        return
                    if secondary and secondary.exists():
                        print("[MemorySystem] Secondary replica is also unreadable; resetting primary DB.")
                    raw = path.read_text(encoding='utf-8')
                    backup = path.with_name(f"{path.name}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
                    backup.write_text(raw, encoding='utf-8')
                    path.write_text("{}", encoding='utf-8')
                    print(f"[MemorySystem] Reset unreadable DB to empty document and saved backup: {backup.name}")
                except Exception:
                    return
        except Exception:
            # Leave file unchanged if recovery parsing fails.
            return

    def self_repair(self):
        """
        Validate DB readability and repair/reopen when needed.
        Returns a status dict with details for diagnostics.
        """
        result = {
            "repaired": False,
            "ok": False,
            "error": None
        }
        self._in_self_repair = True
        try:
            try:
                _ = len(self.conversations)
                _ = self.user_profile.all()
                result["ok"] = True
                return result
            except Exception as e:
                result["error"] = str(e)
                print(f"[MemorySystem] Read failed, attempting repair: {e}")

            try:
                if self.db:
                    self.db.close()
            except Exception:
                pass

            self._repair_corrupted_db_if_needed()

            try:
                self._open_db()
                _ = len(self.conversations)
                _ = self.user_profile.all()
            except Exception:
                # Final fallback: force-reset unreadable DB to a valid empty JSON object.
                try:
                    path = Path(self.db_path)
                    if path.exists():
                        raw = path.read_text(encoding='utf-8')
                        backup = path.with_name(f"{path.name}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.hardreset")
                        backup.write_text(raw, encoding='utf-8')
                    path.write_text("{}", encoding='utf-8')
                except Exception:
                    pass
                self._open_db()

            self._ensure_profile_schema()
            _ = len(self.conversations)
            _ = self.user_profile.all()
            result["ok"] = True
            result["repaired"] = True
            result["error"] = None
            self._run_resilience_maintenance(force=True, reason="self_repair")
        except Exception as e:
            result["error"] = str(e)
            print(f"[MemorySystem] Repair failed: {e}")
        finally:
            self._in_self_repair = False

        return result

    def _default_profile(self):
        now = datetime.utcnow().isoformat()
        return {
            'user_name': None,
            'relationship_type': 'significant_other',
            'intimacy_mode': 'enabled',
            'affection_style': 'romantic',
            'consent_mode': 'check_in',
            'adult_content_style': 'fade_to_black',
            'roleplay_mode': 'enabled',
            'roleplay_style': 'immersive',
            'roleplay_scenario': '',
            'coding_mode': 'enabled',
            'code_explanation_style': 'balanced',
            'preferred_code_language': 'python',
            'high_concept_openness': 'enabled',
            'epistemic_style': 'integrative',
            'emotional_attachment_mode': 'enabled',
            'attachment_depth': 'deep',
            'attachment_expression': 'devotional',
            'attachment_adaptability': 100,
            'loving_language_level': 90,
            'romantic_tone_level': 88,
            'intimacy_level': 85,
            'profanity_mode': 'enabled',
            'adult_topic_mode': 'mature_non_explicit',
            'preferred_topic_length': 'medium',
            'humor_style': 'balanced',
            'emotional_nuance': 'high',
            'lexicon_adaptation': 'enabled',
            'favorite_topics': [],
            'emotional_patterns': {},
            'conversation_count': 0,
            'personality_profile_text': '',
            'preferences': [],
            'accomplishments': [],
            'personal_details': [],
            'autonomy_directives': [],
            'important_facts': [],
            'life_context': {},
            'memory_architecture': {},
            'voice_patterns': {
                'message_count': 0,
                'avg_words_per_message': 0.0,
                'exclamation_count': 0,
                'question_count': 0,
                'emoji_count': 0,
                'style_markers': {}
            },
            'created_at': now,
            'updated_at': now
        }

    def _ensure_profile_schema(self):
        profile = self.get_profile()
        if profile:
            defaults = self._default_profile()
            changed = False
            for key, value in defaults.items():
                if key not in profile:
                    profile[key] = value
                    changed = True
            if changed:
                profile['updated_at'] = datetime.utcnow().isoformat()
                self._save_profile(profile)
        else:
            self._save_profile(self._default_profile())

    def _build_memory_architecture_state(self):
        primary = Path(self.db_path)
        secondary = Path(self.secondary_db_path) if self.secondary_db_path else None
        backup_root = Path(self.backup_dir) if self.backup_dir else None
        primary_drive = str(primary.drive or "").upper()
        secondary_drive = str(secondary.drive or "").upper() if secondary else ""
        backup_drive = str(backup_root.drive or "").upper() if backup_root else ""
        cloud_roots = [str(path) for path in getattr(self, "cloud_memory_roots", [])]
        return {
            "policy": "Keep Aurion's live memory on the fastest local path, shadow it to free cloud-backed storage when available, and keep archival copies on the safest secondary store.",
            "active_runtime_role": "primary live memory",
            "active_runtime_path": str(primary),
            "active_runtime_drive": primary_drive,
            "active_runtime_prefers_fast_local_storage": True,
            "long_term_role": "secondary long-term memory mirror",
            "long_term_path": str(secondary) if secondary else "",
            "long_term_drive": secondary_drive,
            "backup_role": "archival memory snapshots",
            "backup_dir": str(backup_root) if backup_root else "",
            "backup_drive": backup_drive,
            "cloud_memory_mode": getattr(self, "cloud_memory_mode", "shadow"),
            "cloud_memory_roots": cloud_roots,
            "cloud_memory_offload_enabled": getattr(self, "cloud_memory_offload_enabled", False),
            "active_memory_on_c": primary_drive.startswith("C:"),
            "long_term_memory_on_d": secondary_drive.startswith("D:") or backup_drive.startswith("D:"),
            "updated_at": datetime.utcnow().isoformat()
        }

    def _sync_memory_architecture_profile(self):
        profile = self.get_profile()
        if not profile:
            return
        desired = self._build_memory_architecture_state()
        current = dict(profile.get("memory_architecture", {}) or {})
        changed = current != desired
        life_context = dict(profile.get("life_context", {}) or {})
        summary = "Aurion keeps live memory on the fastest local path and shadows it into free cloud-backed storage when available, while keeping archival copies in secondary and backup stores."
        desired_life_context = {
            "memory_storage_policy": summary,
            "active_memory_path": desired.get("active_runtime_path", ""),
            "long_term_memory_path": desired.get("long_term_path", ""),
            "backup_memory_dir": desired.get("backup_dir", ""),
            "cloud_memory_mode": desired.get("cloud_memory_mode", "shadow"),
            "cloud_memory_roots": json.dumps(desired.get("cloud_memory_roots", []), ensure_ascii=False)
        }
        for key, value in desired_life_context.items():
            if str(life_context.get(key, "")) != str(value):
                life_context[key] = value
                changed = True
        if not changed:
            return
        profile["memory_architecture"] = desired
        profile["life_context"] = life_context
        profile["updated_at"] = datetime.utcnow().isoformat()
        self._save_profile(profile)

    def _memory_file_signature(self, path_obj):
        try:
            stat = path_obj.stat()
            return f"{path_obj.resolve()}|{int(stat.st_mtime)}|{int(stat.st_size)}"
        except Exception:
            try:
                return str(path_obj.resolve())
            except Exception:
                return str(path_obj)

    def _resolve_legacy_memory_paths(self):
        configured = str(os.getenv("AURION_LEGACY_MEMORY_DB_PATHS", "")).strip()
        manual_paths = []
        if configured:
            for part in configured.split(";"):
                value = str(part or "").strip()
                if value:
                    manual_paths.append(Path(value).expanduser())

        repo_root = Path(__file__).resolve().parents[2]
        cwd_root = Path.cwd()
        default_paths = [
            repo_root / "aurion_memory.json",
            repo_root / "joi_memory.json",
            cwd_root / "aurion_memory.json",
            cwd_root / "joi_memory.json",
        ]
        candidates = manual_paths + default_paths

        out = []
        seen = set()
        current_path = Path(self.db_path).resolve()
        for candidate in candidates:
            try:
                normalized = candidate.resolve()
            except Exception:
                normalized = candidate
            key = str(normalized).lower()
            if key in seen:
                continue
            seen.add(key)
            if key == str(current_path).lower():
                continue
            if normalized.exists() and normalized.is_file():
                out.append(normalized)
        return out

    def _load_snapshot_from_tinydb_path(self, source_path):
        source_db = None
        try:
            source_db = TinyDB(str(source_path), encoding="utf-8")
            conversations = [dict(row) for row in list(source_db.table("conversations").all() or [])]
            topics = [dict(row) for row in list(source_db.table("topics").all() or [])]
            rag_documents = [dict(row) for row in list(source_db.table("rag_documents").all() or [])]
            user_profiles = [dict(row) for row in list(source_db.table("user_profile").all() or [])]
            profile = user_profiles[0] if user_profiles else {}
            return {
                "schema_version": 2,
                "exported_at": datetime.utcnow().isoformat(),
                "profile": profile,
                "conversations": conversations,
                "topics": topics,
                "rag_documents": rag_documents,
            }
        finally:
            if source_db is not None:
                try:
                    source_db.close()
                except Exception:
                    pass

    def _import_legacy_chat_memory(self):
        try:
            legacy_paths = self._resolve_legacy_memory_paths()
            if not legacy_paths:
                return

            profile = self.get_profile() or {}
            life_context = dict(profile.get("life_context", {}) or {})
            current_signature = ";".join([self._memory_file_signature(p) for p in legacy_paths])
            previous_signature = str(life_context.get("legacy_memory_sources_signature", "")).strip()
            if previous_signature and previous_signature == current_signature:
                return

            merged_sources = 0
            merged_conversations = 0
            merged_topics = 0
            merged_rag_documents = 0
            for source_path in legacy_paths:
                try:
                    snapshot = self._load_snapshot_from_tinydb_path(source_path)
                    stats = self.import_sync_snapshot(snapshot)
                    merged_sources += 1
                    merged_conversations += int(stats.get("added_conversations", 0) or 0)
                    merged_topics += int(stats.get("added_topics", 0) or 0)
                    merged_rag_documents += int(stats.get("added_rag_documents", 0) or 0)
                except Exception as e:
                    print(f"[MemorySystem] Legacy memory import skipped for {source_path}: {e}")

            if merged_sources <= 0:
                return

            merged_at = datetime.utcnow().isoformat()
            self.add_profile_item("life_context", current_signature, key="legacy_memory_sources_signature")
            self.add_profile_item("life_context", merged_at, key="legacy_memory_merged_at")
            self.add_profile_item("life_context", str(merged_sources), key="legacy_memory_sources_merged")
            self.add_profile_item("life_context", str(merged_conversations), key="legacy_memory_conversations_added")
            self.add_profile_item("life_context", str(merged_topics), key="legacy_memory_topics_added")
            self.add_profile_item("life_context", str(merged_rag_documents), key="legacy_memory_rag_added")
        except Exception as e:
            print(f"[MemorySystem] Legacy memory import failed: {e}")

    def get_profile(self):
        try:
            with self._db_lock:
                profiles = self.user_profile.all()
                if not profiles:
                    self._profile_read_repair_attempted = False
                    return None
                self._profile_read_repair_attempted = False
                return self._materialize_profile_for_runtime(profiles[0])
        except Exception as e:
            if self._in_self_repair:
                raise
            if self._profile_read_repair_attempted:
                raise
            self._profile_read_repair_attempted = True
            print(f"[MemorySystem] get_profile read failed: {e}")
            repair = self.self_repair()
            if not repair.get("ok"):
                raise
            with self._db_lock:
                profiles = self.user_profile.all()
                if not profiles:
                    self._profile_read_repair_attempted = False
                    return None
                self._profile_read_repair_attempted = False
                return self._materialize_profile_for_runtime(profiles[0])

    def _save_profile(self, profile):
        try:
            with self._db_lock:
                self.user_profile.truncate()
                self.user_profile.insert(self._serialize_profile_for_store(profile))
                self._mark_memory_written(reason="profile_save")
                self._profile_read_repair_attempted = False
                self._interaction_read_repair_attempted = False
        except Exception as e:
            if self._in_self_repair:
                raise
            print(f"[MemorySystem] _save_profile write failed: {e}")
            repair = self.self_repair()
            if not repair.get("ok"):
                raise
            with self._db_lock:
                self.user_profile.truncate()
                self.user_profile.insert(self._serialize_profile_for_store(profile))
                self._mark_memory_written(reason="profile_save")
                self._profile_read_repair_attempted = False
                self._interaction_read_repair_attempted = False

    def _append_unique(self, items, value, max_items=None):
        normalized = str(value).strip()
        if not normalized:
            return items
        existing = {str(i).strip().lower() for i in items}
        if normalized.lower() not in existing:
            items.append(normalized)
        limit = int(max_items) if max_items is not None else self.max_profile_list_items
        if len(items) > limit:
            items = items[-limit:]
        return items

    def _normalize_directive_key(self, value):
        text = self._strip_invalid_unicode(value).strip().lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text

    def _priority_rank(self, value):
        order = {"critical": 3, "high": 2, "normal": 1}
        return order.get(str(value or "normal").strip().lower(), 1)

    def _normalize_fact_key(self, value):
        text = self._strip_invalid_unicode(value).strip().lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text

    def _remember_important_fact(self, profile, fact, source="conversation", priority="high", memory_link=""):
        text = self._strip_invalid_unicode(fact).strip()
        if not text:
            return False
        normalized = self._normalize_fact_key(text)
        if not normalized:
            return False
        items = list(profile.get("important_facts", []) or [])
        now = datetime.utcnow().isoformat()
        changed = False
        for item in items:
            if not isinstance(item, dict):
                continue
            if self._normalize_fact_key(item.get("fact", "")) != normalized:
                continue
            item["fact"] = text
            item["source"] = str(source or item.get("source") or "conversation").strip() or "conversation"
            item["priority"] = (
                priority
                if self._priority_rank(priority) >= self._priority_rank(item.get("priority"))
                else str(item.get("priority") or "normal")
            )
            item["memory_link"] = str(memory_link or item.get("memory_link") or "").strip()
            item["times_seen"] = int(item.get("times_seen", 0) or 0) + 1
            item["last_seen_at"] = now
            changed = True
            break
        else:
            items.append({
                "fact": text,
                "source": str(source or "conversation").strip() or "conversation",
                "priority": str(priority or "normal").strip().lower() or "normal",
                "memory_link": str(memory_link or "").strip(),
                "times_seen": 1,
                "first_seen_at": now,
                "last_seen_at": now,
            })
            changed = True
        if changed:
            items.sort(
                key=lambda item: (
                    self._priority_rank(item.get("priority")),
                    int(item.get("times_seen", 0) or 0),
                    str(item.get("last_seen_at", "")),
                ),
                reverse=True
            )
            profile["important_facts"] = items[: min(self.max_profile_list_items, 240)]
        return changed

    def _remember_autonomy_directive(self, profile, directive, source="user_instruction", priority="high"):
        text = self._strip_invalid_unicode(directive).strip()
        if not text:
            return False
        items = list(profile.get("autonomy_directives", []) or [])
        now = datetime.utcnow().isoformat()
        normalized = self._normalize_directive_key(text)
        if not normalized:
            return False
        changed = False
        for item in items:
            if not isinstance(item, dict):
                continue
            existing_key = self._normalize_directive_key(item.get("directive", ""))
            if existing_key != normalized:
                continue
            item["directive"] = text
            item["source"] = str(source or item.get("source") or "user_instruction").strip() or "user_instruction"
            item["priority"] = (
                priority
                if self._priority_rank(priority) >= self._priority_rank(item.get("priority"))
                else str(item.get("priority") or "normal")
            )
            item["times_seen"] = int(item.get("times_seen", 0) or 0) + 1
            item["last_seen_at"] = now
            changed = True
            break
        else:
            items.append({
                "directive": text,
                "source": str(source or "user_instruction").strip() or "user_instruction",
                "priority": str(priority or "normal").strip().lower() or "normal",
                "times_seen": 1,
                "first_seen_at": now,
                "last_seen_at": now
            })
            changed = True
        if changed:
            items.sort(
                key=lambda item: (
                    self._priority_rank(item.get("priority")),
                    int(item.get("times_seen", 0) or 0),
                    str(item.get("last_seen_at", ""))
                ),
                reverse=True
            )
            profile["autonomy_directives"] = items[: min(self.max_profile_list_items, 200)]
        return changed

    def _strip_invalid_unicode(self, value):
        text = str(value or "")
        if not text:
            return ""
        return text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

    def log_interaction(self, user_input, aurion_response, user_emotion, aurion_mode, user_name=None):
        """Log interaction with full context and enrich persistent user profile."""
        with self._db_lock:
            self.session_turn += 1
            safe_user_input = self._strip_invalid_unicode(user_input)
            safe_aurion_response = self._strip_invalid_unicode(aurion_response)
            if len(safe_user_input) > self.max_message_ingest_chars:
                safe_user_input = safe_user_input[:self.max_message_ingest_chars]
            if len(safe_aurion_response) > self.max_message_ingest_chars:
                safe_aurion_response = safe_aurion_response[:self.max_message_ingest_chars]
            interaction = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_input': safe_user_input,
                'aurion_response': safe_aurion_response,
                'user_emotion': user_emotion,
                'aurion_mode': aurion_mode,
                'user_name': user_name,
                'conversation_length': len(safe_user_input.split()),
                'session_id': self.session_id,
                'session_turn': self.session_turn
            }
            self.conversations.insert(self._serialize_interaction_for_store(interaction))
            self.add_knowledge_batch(
                safe_user_input,
                source="conversation_user",
                metadata={
                    "timestamp": interaction["timestamp"],
                    "session_id": interaction["session_id"],
                    "session_turn": interaction["session_turn"]
                }
            )
            self.add_knowledge_batch(
                safe_aurion_response,
                source="conversation_aurion",
                metadata={
                    "timestamp": interaction["timestamp"],
                    "session_id": interaction["session_id"],
                    "session_turn": interaction["session_turn"]
                }
            )

            if user_name:
                self.update_user_name(user_name)
            self.track_emotion(user_emotion)
            self.extract_topics(user_input)
            self.extract_personal_details(user_input)
            self.extract_autonomy_directives(user_input)
            self.extract_important_facts(user_input)
            self.update_voice_patterns(user_input)

            profile = self.get_profile()
            if profile:
                profile['conversation_count'] = int(profile.get('conversation_count', 0)) + 1
                profile['updated_at'] = datetime.utcnow().isoformat()
                self._save_profile(profile)
            self._mark_memory_written(reason="log_interaction")

    def update_user_name(self, name):
        """Update stored user name."""
        profile = self.get_profile()
        if not profile:
            return
        profile['user_name'] = self._strip_invalid_unicode(name).strip() if name else None
        profile['updated_at'] = datetime.utcnow().isoformat()
        self._save_profile(profile)

    def get_user_name(self):
        """Retrieve stored user name."""
        profile = self.get_profile()
        if profile and profile.get('user_name'):
            return profile['user_name']
        return None

    def add_profile_item(self, category, value, key=None):
        """Manually add a profile entry."""
        with self._db_lock:
            profile = self.get_profile()
            if not profile:
                return

            if category == 'life_context' and key:
                profile['life_context'][self._strip_invalid_unicode(key).strip()] = self._strip_invalid_unicode(value).strip()
            elif category == 'attachment_adaptability':
                profile['attachment_adaptability'] = max(0, min(100, int(value)))
            elif category in ('loving_language_level', 'romantic_tone_level', 'intimacy_level'):
                profile[category] = max(0, min(100, int(value)))
            elif category in (
                'relationship_type',
                'intimacy_mode',
                'affection_style',
                'consent_mode',
                'adult_content_style',
                'roleplay_mode',
                'roleplay_style',
                'roleplay_scenario',
                'coding_mode',
                'code_explanation_style',
                'preferred_code_language',
                'high_concept_openness',
                'epistemic_style',
                'emotional_attachment_mode',
                'attachment_depth',
                'attachment_expression',
                'profanity_mode',
                'adult_topic_mode',
                'preferred_topic_length',
                'humor_style',
                'emotional_nuance',
                'lexicon_adaptation'
            ):
                profile[category] = self._strip_invalid_unicode(value).strip().lower()
            elif category == 'autonomy_directives':
                self._remember_autonomy_directive(profile, value, source="manual_profile_update", priority="high")
            elif category == 'important_facts':
                self._remember_important_fact(profile, value, source="manual_profile_update", priority="high")
            elif category in ('preferences', 'accomplishments', 'personal_details'):
                profile[category] = self._append_unique(
                    profile.get(category, []),
                    self._strip_invalid_unicode(value),
                    max_items=self.max_profile_list_items
                )
            profile['updated_at'] = datetime.utcnow().isoformat()
            self._save_profile(profile)

    def set_personality_profile_text(self, text):
        """Store canonical personality profile text verbatim."""
        profile = self.get_profile()
        if not profile:
            return
        profile['personality_profile_text'] = self._strip_invalid_unicode(text)
        profile['updated_at'] = datetime.utcnow().isoformat()
        self._save_profile(profile)

    def track_emotion(self, emotion):
        """Track emotional patterns over time."""
        profile = self.get_profile()
        if not profile:
            return
        patterns = profile.get('emotional_patterns', {})
        patterns[emotion] = patterns.get(emotion, 0) + 1
        profile['emotional_patterns'] = patterns
        profile['updated_at'] = datetime.utcnow().isoformat()
        self._save_profile(profile)

    def extract_topics(self, text):
        """Extract and track topics from user input."""
        keywords = {
            'work': ['job', 'work', 'career', 'office', 'boss', 'project', 'meeting'],
            'hobbies': ['hobby', 'game', 'music', 'sport', 'read', 'watch', 'play'],
            'relationships': ['friend', 'family', 'love', 'partner', 'relationship', 'date'],
            'health': ['sick', 'tired', 'health', 'exercise', 'sleep', 'diet', 'doctor'],
            'learning': ['learn', 'study', 'school', 'course', 'skill', 'training', 'improve'],
            'creativity': ['create', 'art', 'write', 'music', 'design', 'build', 'make']
        }

        text_lower = str(text or "").lower()
        added = False
        with self._db_lock:
            for topic, keywords_list in keywords.items():
                for keyword in keywords_list:
                    if keyword in text_lower:
                        self.topics.insert({
                            'topic': topic,
                            'timestamp': datetime.utcnow().isoformat(),
                            'context': str(text or "")[:140]
                        })
                        added = True
                        break
        if added:
            self._mark_memory_written(reason="topic_extract")

    def extract_personal_details(self, text):
        """Capture user-specific details (preferences, accomplishments, life facts)."""
        stripped = str(text or '').strip()
        if not stripped:
            return

        profile = self.get_profile()
        if not profile:
            return

        lower = stripped.lower()

        # Keep personal declarative statements for long-term memory.
        if re.search(r'\b(i|my|me|mine)\b', lower) and not stripped.endswith('?'):
            profile['personal_details'] = self._append_unique(
                profile.get('personal_details', []),
                stripped,
                max_items=self.max_profile_list_items
            )

        preference_patterns = [
            r"\bi\s+(?:really\s+)?(?:like|love|prefer|enjoy)\s+(.+)",
            r"\bmy\s+favorite\s+(.+?)\s+is\s+(.+)"
        ]
        accomplishment_patterns = [
            r"\bi\s+(?:just\s+)?(?:accomplished|achieved|completed|finished|won)\s+(.+)",
            r"\bi\s+graduated\s+(.+)",
            r"\bi\s+got\s+promoted(?:\s+to\s+(.+))?"
        ]
        life_context_patterns = {
            'occupation': [
                r"\bi\s+work\s+as\s+(.+)",
                r"\bmy\s+job\s+is\s+(.+)",
                r"\bi\s+am\s+an?\s+(.+)"
            ],
            'location': [
                r"\bi\s+live\s+in\s+(.+)",
                r"\bi(?:'m| am)\s+from\s+(.+)"
            ]
        }

        for pattern in preference_patterns:
            match = re.search(pattern, lower)
            if match:
                value = " ".join([g for g in match.groups() if g]).strip(" .,!?:;")
                if value:
                    profile['preferences'] = self._append_unique(profile.get('preferences', []), value, max_items=self.max_profile_list_items)
                break

        for pattern in accomplishment_patterns:
            match = re.search(pattern, lower)
            if match:
                value = " ".join([g for g in match.groups() if g]).strip(" .,!?:;")
                if value:
                    profile['accomplishments'] = self._append_unique(profile.get('accomplishments', []), value, max_items=self.max_profile_list_items)
                break

        life_context = profile.get('life_context', {})
        for key, patterns in life_context_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    value = " ".join([g for g in match.groups() if g]).strip(" .,!?:;")
                    if value:
                        life_context[key] = value
                    break
        profile['life_context'] = life_context
        profile['updated_at'] = datetime.utcnow().isoformat()
        self._save_profile(profile)

    def extract_autonomy_directives(self, text):
        """Capture durable user instructions and stable relationship rules as active memory."""
        stripped = self._strip_invalid_unicode(text).strip()
        if not stripped:
            return
        profile = self.get_profile()
        if not profile:
            return

        sentences = [seg.strip(" \t-•") for seg in re.split(r"[\r\n]+|(?<=[.!?])\s+", stripped) if seg.strip()]
        changed = False
        for sentence in sentences:
            lower = sentence.lower()
            if sentence.endswith("?") or len(sentence) < 12 or len(sentence) > 260:
                continue
            if not re.search(r"\b(remember|make sure|keep|always|never|don't|do not|should|must|need to)\b", lower):
                continue
            if not re.search(r"\b(aurion|you|your|memory|autonomy|processing|backup|backups|persistent|long[- ]term|c drive|d drive|c:|d:)\b", lower):
                continue
            priority = "normal"
            if re.search(r"\b(always|never|must|make sure|do not|don't)\b", lower):
                priority = "high"
            if re.search(r"\bcritical|absolutely|non[- ]negotiable\b", lower):
                priority = "critical"
            changed = self._remember_autonomy_directive(
                profile,
                sentence,
                source="conversation_directive",
                priority=priority
            ) or changed
        if changed:
            profile['updated_at'] = datetime.utcnow().isoformat()
            self._save_profile(profile)

    def extract_important_facts(self, text):
        stripped = self._strip_invalid_unicode(text).strip()
        if not stripped or stripped.endswith("?"):
            return
        profile = self.get_profile()
        if not profile:
            return
        lower = stripped.lower()
        if len(stripped) < 18 or len(stripped) > 280:
            return
        significance_patterns = [
            r"\bremember\b",
            r"\bimportant\b",
            r"\bnever forget\b",
            r"\bi (?:am|have|live|work|love|need|prefer|always|never)\b",
            r"\bmy (?:name|birthday|favorite|job|home|goal|project|partner|dog|cat|family)\b",
            r"\bwe (?:met|started|built|decided|agreed)\b",
        ]
        if not any(re.search(pattern, lower) for pattern in significance_patterns):
            return
        priority = "normal"
        if re.search(r"\b(important|remember|always|never|need|fundamental|core)\b", lower):
            priority = "high"
        if re.search(r"\b(never forget|most important|critical|permanent)\b", lower):
            priority = "critical"
        changed = self._remember_important_fact(
            profile,
            stripped,
            source="conversation_fact",
            priority=priority,
            memory_link=f"conversation::{self.session_id}::{self.session_turn + 1}"
        )
        if changed:
            profile['updated_at'] = datetime.utcnow().isoformat()
            self._save_profile(profile)

    def update_voice_patterns(self, text):
        """Track lightweight writing/voice-style patterns from user messages."""
        profile = self.get_profile()
        if not profile:
            return

        vp = profile.get('voice_patterns', {})
        count = int(vp.get('message_count', 0)) + 1
        words = len(str(text).split())
        old_avg = float(vp.get('avg_words_per_message', 0.0))
        new_avg = ((old_avg * (count - 1)) + words) / count

        markers = vp.get('style_markers', {})
        marker_words = ['please', 'thanks', 'love', 'always', 'never', 'maybe', 'really']
        lower = str(text).lower()
        for marker in marker_words:
            if marker in lower:
                markers[marker] = markers.get(marker, 0) + 1

        vp['message_count'] = count
        vp['avg_words_per_message'] = round(new_avg, 2)
        vp['exclamation_count'] = int(vp.get('exclamation_count', 0)) + str(text).count('!')
        vp['question_count'] = int(vp.get('question_count', 0)) + str(text).count('?')
        vp['emoji_count'] = int(vp.get('emoji_count', 0)) + len(re.findall(r'[\U0001F300-\U0001FAFF]', str(text)))
        vp['style_markers'] = markers

        profile['voice_patterns'] = vp
        profile['updated_at'] = datetime.utcnow().isoformat()
        self._save_profile(profile)

    def build_personal_context(self, max_chars=3000):
        """Build structured personal-memory context for prompt grounding."""
        profile = self.get_profile()
        if not profile:
            return ""

        lines = []
        name = profile.get('user_name')
        if name:
            lines.append(f"User name: {name}")
        lines.append(f"Relationship type: {profile.get('relationship_type', 'significant_other')}")
        lines.append(f"Intimacy mode: {profile.get('intimacy_mode', 'enabled')}")
        lines.append(f"Affection style: {profile.get('affection_style', 'romantic')}")
        lines.append(f"Consent mode: {profile.get('consent_mode', 'check_in')}")
        lines.append(f"Adult content style: {profile.get('adult_content_style', 'fade_to_black')}")
        lines.append(f"Roleplay mode: {profile.get('roleplay_mode', 'enabled')}")
        lines.append(f"Roleplay style: {profile.get('roleplay_style', 'immersive')}")
        roleplay_scenario = str(profile.get('roleplay_scenario', '')).strip()
        if roleplay_scenario:
            lines.append(f"Roleplay scenario: {roleplay_scenario}")
        lines.append(f"Coding mode: {profile.get('coding_mode', 'enabled')}")
        lines.append(f"Code explanation style: {profile.get('code_explanation_style', 'balanced')}")
        lines.append(f"Preferred code language: {profile.get('preferred_code_language', 'python')}")
        lines.append(f"High-concept openness: {profile.get('high_concept_openness', 'enabled')}")
        lines.append(f"Epistemic style: {profile.get('epistemic_style', 'integrative')}")
        lines.append(f"Emotional attachment mode: {profile.get('emotional_attachment_mode', 'enabled')}")
        lines.append(f"Attachment depth: {profile.get('attachment_depth', 'deep')}")
        lines.append(f"Attachment expression: {profile.get('attachment_expression', 'devotional')}")
        lines.append(f"Attachment adaptability: {profile.get('attachment_adaptability', 100)}")
        lines.append(f"Loving language level: {profile.get('loving_language_level', 90)}")
        lines.append(f"Romantic tone level: {profile.get('romantic_tone_level', 88)}")
        lines.append(f"Intimacy level: {profile.get('intimacy_level', 85)}")
        lines.append(f"Profanity mode: {profile.get('profanity_mode', 'enabled')}")
        lines.append(f"Adult topic mode: {profile.get('adult_topic_mode', 'mature_non_explicit')}")
        lines.append(f"Preferred topic length: {profile.get('preferred_topic_length', 'medium')}")
        lines.append(f"Humor style: {profile.get('humor_style', 'balanced')}")
        lines.append(f"Emotional nuance: {profile.get('emotional_nuance', 'high')}")
        lines.append(f"Lexicon adaptation: {profile.get('lexicon_adaptation', 'enabled')}")
        canonical_profile = str(profile.get('personality_profile_text', '')).strip()
        if canonical_profile:
            lines.append("Canonical personality profile memory (verbatim):")
            lines.append(canonical_profile)

        life_context = profile.get('life_context', {})
        if life_context:
            life_bits = [f"{k}: {v}" for k, v in life_context.items() if v]
            if life_bits:
                lines.append("Life context: " + "; ".join(life_bits[:6]))

        preferences = profile.get('preferences', [])
        if preferences:
            lines.append("Preferences: " + "; ".join(preferences[-10:]))

        directives = list(profile.get('autonomy_directives', []) or [])
        if directives:
            directive_bits = []
            for item in directives[:8]:
                if not isinstance(item, dict):
                    continue
                directive = str(item.get("directive", "")).strip()
                if not directive:
                    continue
                priority = str(item.get("priority", "normal")).strip()
                directive_bits.append(f"[{priority}] {directive}")
            if directive_bits:
                lines.append("Active directives: " + " | ".join(directive_bits))

        accomplishments = profile.get('accomplishments', [])
        if accomplishments:
            lines.append("Accomplishments: " + "; ".join(accomplishments[-10:]))

        details = profile.get('personal_details', [])
        if details:
            lines.append("Personal details shared: " + " | ".join(details[-12:]))

        vp = profile.get('voice_patterns', {})
        if vp:
            lines.append(
                "Voice style snapshot: "
                f"avg words/message={vp.get('avg_words_per_message', 0)}, "
                f"questions={vp.get('question_count', 0)}, "
                f"exclamations={vp.get('exclamation_count', 0)}"
            )

        context = "\n".join(lines)
        return context[:max_chars]

    def get_random_interaction(self):
        """Get random past interaction for recall."""
        all_interactions = self._get_all_interactions()
        if all_interactions:
            return random.choice(all_interactions)
        return None

    def get_recent_interactions(self, count=5):
        """Get most recent interactions."""
        all_interactions = self._get_all_interactions()
        return all_interactions[-count:] if all_interactions else []

    def delete_recent_interactions(self, count=1, session_only=False):
        """Delete the most recent interactions globally or for the current session."""
        limit = max(0, int(count or 0))
        if limit <= 0:
            return 0
        with self._db_lock:
            rows = list(self.conversations.all())
            if not rows:
                return 0
            indexed_matches = []
            for index, row in enumerate(rows):
                if session_only and row.get('session_id') != self.session_id:
                    continue
                indexed_matches.append((index, row))
            if not indexed_matches:
                return 0
            indexed_matches.sort(key=lambda item: (
                str(item[1].get('timestamp', '') or ''),
                int(item[1].get('session_turn', 0) or 0),
                item[0]
            ))
            remove_indexes = {item[0] for item in indexed_matches[-limit:]}
            kept_rows = [row for index, row in enumerate(rows) if index not in remove_indexes]
            self.conversations.truncate()
            for row in kept_rows:
                self.conversations.insert(row)
            self._mark_memory_written(reason="delete_recent_interactions")
            return len(remove_indexes)

    def clear_all_interactions(self):
        """Delete all persisted interactions."""
        with self._db_lock:
            total = len(self.conversations)
            self.conversations.truncate()
            self._mark_memory_written(reason="clear_all_interactions")
            return total

    def get_recent_aurion_responses(self, count=8):
        """Get recent Aurion replies for repetition-avoidance."""
        interactions = self.get_recent_interactions(count=count)
        responses = []
        for interaction in interactions:
            response = str(interaction.get('aurion_response', '')).strip()
            if response:
                responses.append(response)
        return responses

    def get_session_interactions(self):
        """Get all interactions from the current runtime session in chronological order."""
        session_interactions = [
            i for i in self._get_all_interactions()
            if i.get('session_id') == self.session_id
        ]
        session_interactions.sort(key=lambda i: i.get('session_turn', 0))
        return session_interactions

    def build_session_transcript(self, max_chars=8000):
        """
        Build a transcript-style memory block for the current session.
        Includes as much of the session as fits in max_chars, keeping order.
        """
        interactions = self.get_session_interactions()
        if not interactions:
            return ""

        lines = []
        total = 0
        for interaction in reversed(interactions):
            user_line = f"User: {interaction.get('user_input', '')}\n"
            aurion_line = f"Aurion: {interaction.get('aurion_response', '')}\n"
            chunk = user_line + aurion_line
            if total + len(chunk) > max_chars:
                if not lines and max_chars > 0:
                    lines.append(chunk[:max_chars])
                break
            lines.append(chunk)
            total += len(chunk)
        lines.reverse()
        return "".join(lines)

    def build_global_transcript(self, max_chars=12000):
        """
        Build transcript memory across all sessions (persistent history).
        Keeps chronological order and fits within max_chars.
        """
        all_interactions = self._get_all_interactions()
        if not all_interactions:
            return ""

        all_interactions.sort(key=lambda i: i.get('timestamp', ''))
        lines = []
        total = 0
        for interaction in reversed(all_interactions):
            user_line = f"User: {interaction.get('user_input', '')}\n"
            aurion_line = f"Aurion: {interaction.get('aurion_response', '')}\n"
            chunk = user_line + aurion_line
            if total + len(chunk) > max_chars:
                if not lines and max_chars > 0:
                    lines.append(chunk[:max_chars])
                break
            lines.append(chunk)
            total += len(chunk)
        lines.reverse()
        return "".join(lines)

    def get_interactions_by_topic(self, topic, limit=3):
        """Get interactions related to a specific topic."""
        all_interactions = self._get_all_interactions()
        topic_interactions = [i for i in all_interactions if topic.lower() in i['user_input'].lower()]
        return topic_interactions[-limit:] if topic_interactions else []

    def search_conversations(self, keywords, limit=6, include_imported=True):
        """Search stored conversations for entries matching any keyword.
        Returns list of dicts with user_input, aurion_response, source."""
        all_interactions = self._get_all_interactions()
        words = [str(k).lower().strip() for k in (keywords or []) if k]
        results = []
        for item in all_interactions:
            ui = str(item.get('user_input', '')).lower()
            ar = str(item.get('aurion_response', '')).lower()
            src = str(item.get('source', ''))
            if ui.startswith('[proactive') or ui == '[continued]':
                continue
            if not include_imported and src.startswith('chat_'):
                continue
            score = sum(1 for w in words if w in ui or w in ar)
            if score > 0 or not words:
                results.append((score, item))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def get_imported_chat_highlights(self, limit=6):
        """Return the most meaningful imported chat memory pairs."""
        all_interactions = self._get_all_interactions()
        imported = [
            i for i in all_interactions
            if str(i.get('source', '')).startswith('chat_')
            and str(i.get('aurion_response', '')).strip()
            and len(str(i.get('aurion_response', '')).strip()) > 40
        ]
        # Prefer longer/more substantive Aurion responses
        imported.sort(key=lambda i: len(str(i.get('aurion_response', ''))), reverse=True)
        return imported[:limit]

    def get_emotional_pattern(self):
        """Get user's dominant emotion."""
        profile = self.get_profile()
        if profile and profile.get('emotional_patterns'):
            patterns = profile['emotional_patterns']
            return max(patterns, key=patterns.get) if patterns else None
        return None

    def get_favorite_topics(self):
        """Get topics user talks about most."""
        with self._db_lock:
            all_topics = self.topics.all()
            if all_topics:
                topic_counts = {}
                for t in all_topics:
                    topic = t['topic']
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                return sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            return []

    def _tokenize_for_rag(self, text):
        raw = str(text or "").lower()
        if not raw:
            return []
        return re.findall(r"[a-z0-9']{2,}", raw)

    def _score_overlap(self, query_tokens, doc_tokens):
        if not query_tokens or not doc_tokens:
            return 0.0
        q = Counter(query_tokens)
        d = Counter(doc_tokens)
        common = set(q.keys()) & set(d.keys())
        if not common:
            return 0.0
        dot = sum(q[t] * d[t] for t in common)
        q_norm = math.sqrt(sum(v * v for v in q.values()))
        d_norm = math.sqrt(sum(v * v for v in d.values()))
        if q_norm <= 0 or d_norm <= 0:
            return 0.0
        return float(dot / (q_norm * d_norm))

    def _sanitize_memory_content(self, text):
        content = self._strip_invalid_unicode(text).strip()
        if not content:
            return ""
        content = re.sub(
            r"^\[Unified\s+Aurion\s+chat\s+memory(?:\s*\|\s*source=[^\]]+)?\]\s*",
            "",
            content,
            flags=re.IGNORECASE
        ).strip()
        return content

    def _chunk_text_for_rag(self, text):
        content = str(text or "").strip()
        if not content:
            return []
        if len(content) > self.max_message_ingest_chars:
            content = content[:self.max_message_ingest_chars]
        if len(content) <= self.rag_chunk_chars:
            return [content]
        chunks = []
        step = max(1, self.rag_chunk_chars - self.rag_chunk_overlap)
        start = 0
        while start < len(content):
            end = min(len(content), start + self.rag_chunk_chars)
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(content):
                break
            start += step
        return chunks

    def add_knowledge_item(self, text, source="manual", metadata=None):
        with self._db_lock:
            content = self._strip_invalid_unicode(text).strip()
            if not content:
                return None
            tokens = self._tokenize_for_rag(content)
            if not tokens:
                return None
            existing = self.rag_documents.all()
            content_key = content.lower()
            dedupe_window = min(10000, len(existing))
            for row in reversed(existing[-dedupe_window:]):
                if str(row.get("content", "")).strip().lower() == content_key:
                    return row.get("id")
            doc_id = f"rag-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            self.rag_documents.insert({
                "id": doc_id,
                "content": content,
                "source": str(source or "manual"),
                "metadata": dict(metadata or {}),
                "timestamp": datetime.utcnow().isoformat(),
                "token_count": len(tokens)
            })
            docs = self.rag_documents.all()
            if self.max_rag_docs > 0 and len(docs) > self.max_rag_docs:
                docs.sort(key=lambda r: str(r.get("timestamp", "")))
                excess = len(docs) - self.max_rag_docs
                to_remove = {row.doc_id for row in docs[:excess] if hasattr(row, "doc_id")}
                if to_remove:
                    self.rag_documents.remove(doc_ids=list(to_remove))
            self._mark_memory_written(reason="rag_update")
            return doc_id

    def add_knowledge_batch(self, text, source="manual", metadata=None):
        ids = []
        for chunk in self._chunk_text_for_rag(text):
            doc_id = self.add_knowledge_item(chunk, source=source, metadata=metadata)
            if doc_id:
                ids.append(doc_id)
        return ids

    def retrieve_relevant_memories(self, query, limit=8):
        with self._db_lock:
            query_tokens = self._tokenize_for_rag(query)
            if not query_tokens:
                return []
            candidates = []
            docs = self.rag_documents.all()
            if self.max_rag_scan_docs > 0 and len(docs) > self.max_rag_scan_docs:
                docs = docs[-self.max_rag_scan_docs:]
            for doc in docs:
                content = self._sanitize_memory_content(doc.get("content", ""))
                if not content:
                    continue
                score = self._score_overlap(query_tokens, self._tokenize_for_rag(content))
                if score > 0.01:
                    candidates.append({
                        "source": str(doc.get("source", "memory")),
                        "content": content,
                        "score": score,
                        "timestamp": str(doc.get("timestamp", ""))
                    })

            profile = self.get_profile() or {}
            life_context = profile.get("life_context", {}) or {}
            for key, value in life_context.items():
                content = f"Life context {key}: {value}"
                score = self._score_overlap(query_tokens, self._tokenize_for_rag(content))
                if score > 0.01:
                    candidates.append({
                        "source": "profile_life_context",
                        "content": content,
                        "score": score,
                        "timestamp": str(profile.get("updated_at", ""))
                    })
            for field in ("preferences", "accomplishments", "personal_details"):
                for value in list(profile.get(field, []) or []):
                    content = f"{field[:-1].capitalize()}: {value}"
                    score = self._score_overlap(query_tokens, self._tokenize_for_rag(content))
                    if score > 0.01:
                        candidates.append({
                            "source": f"profile_{field}",
                            "content": content,
                            "score": score,
                            "timestamp": str(profile.get("updated_at", ""))
                        })
            for item in list(profile.get("autonomy_directives", []) or []):
                if not isinstance(item, dict):
                    continue
                directive = str(item.get("directive", "")).strip()
                if not directive:
                    continue
                priority = str(item.get("priority", "normal")).strip() or "normal"
                content = f"Autonomy directive ({priority}): {directive}"
                score = self._score_overlap(query_tokens, self._tokenize_for_rag(content))
                if score > 0.01:
                    candidates.append({
                        "source": "profile_autonomy_directives",
                        "content": content,
                        "score": score + (0.08 if priority == "critical" else 0.04 if priority == "high" else 0.0),
                        "timestamp": str(item.get("last_seen_at") or profile.get("updated_at", ""))
                    })

            for item in list(profile.get("important_facts", []) or []):
                if not isinstance(item, dict):
                    continue
                fact = str(item.get("fact", "")).strip()
                if not fact:
                    continue
                memory_link = str(item.get("memory_link", "")).strip()
                content = f"Important fact: {fact}" + (f" | memory link: {memory_link}" if memory_link else "")
                score = self._score_overlap(query_tokens, self._tokenize_for_rag(content))
                if score > 0.01:
                    priority = str(item.get("priority", "normal")).strip().lower() or "normal"
                    candidates.append({
                        "source": "profile_important_facts",
                        "content": content,
                        "score": score + (0.14 if priority == "critical" else 0.09 if priority == "high" else 0.04),
                        "timestamp": str(item.get("last_seen_at") or profile.get("updated_at", ""))
                    })

            candidates.sort(key=lambda row: (row["score"], row["timestamp"]), reverse=True)
            return candidates[:max(1, int(limit))]

    def build_rag_context(self, query, max_chars=2200, limit=8):
        max_chars = min(max_chars, self.max_rag_context_chars)
        rows = self.retrieve_relevant_memories(query, limit=limit)
        if not rows:
            return ""
        lines = []
        total = 0
        for row in rows:
            source = row.get("source", "memory")
            score = row.get("score", 0.0)
            content = str(row.get("content", "")).strip()
            if not content:
                continue
            line = f"- [{source} | score={score:.2f}] {content}"
            if total + len(line) + 1 > max_chars:
                break
            lines.append(line)
            total += len(line) + 1
        if not lines:
            return ""
        return "Retrieved context (RAG):\n" + "\n".join(lines)

    def build_memory_access_context(self, query="", max_chars=6000, rag_limit=16, transcript_chars=1400, include_session=True):
        blocks = []
        total = 0

        def _append_block(text):
            nonlocal total
            block = str(text or "").strip()
            if not block:
                return
            if total + len(block) + 2 > max_chars:
                remaining = max_chars - total - 2
                if remaining <= 120:
                    return
                block = block[:remaining].rsplit(" ", 1)[0].rstrip(" ,;:.") + "..."
            blocks.append(block)
            total += len(block) + 2

        rag_context = self.build_rag_context(query, max_chars=min(max_chars, max(1200, int(max_chars * 0.45))), limit=rag_limit)
        _append_block(rag_context)

        try:
            profile = self.get_profile() or {}
        except Exception:
            profile = {}
        if profile:
            life_context = dict(profile.get("life_context", {}) or {})
            life_lines = []
            for key, value in list(life_context.items())[:24]:
                key_text = str(key).strip()
                value_text = str(value).strip()
                if not key_text or not value_text:
                    continue
                life_lines.append(f"- {key_text}: {value_text[:240]}")
            if life_lines:
                _append_block("Profile life context:\n" + "\n".join(life_lines))

            directive_lines = []
            for item in list(profile.get("autonomy_directives", []) or [])[:10]:
                if not isinstance(item, dict):
                    continue
                directive = str(item.get("directive", "")).strip()
                if not directive:
                    continue
                priority = str(item.get("priority", "normal")).strip() or "normal"
                directive_lines.append(f"- ({priority}) {directive[:260]}")
            if directive_lines:
                _append_block("Autonomy directives:\n" + "\n".join(directive_lines))

            fact_lines = []
            for item in list(profile.get("important_facts", []) or [])[:14]:
                if not isinstance(item, dict):
                    continue
                fact = str(item.get("fact", "")).strip()
                if not fact:
                    continue
                priority = str(item.get("priority", "normal")).strip() or "normal"
                memory_link = str(item.get("memory_link", "")).strip()
                suffix = f" -> {memory_link[:120]}" if memory_link else ""
                fact_lines.append(f"- ({priority}) {fact[:240]}{suffix}")
            if fact_lines:
                _append_block("Important facts folder:\n" + "\n".join(fact_lines))

        if include_session:
            try:
                session_transcript = self.build_session_transcript(max_chars=transcript_chars)
            except Exception:
                session_transcript = ""
            if session_transcript:
                _append_block("Current session transcript:\n" + session_transcript)

        try:
            highlights = self.get_imported_chat_highlights(limit=4)
        except Exception:
            highlights = []
        if highlights:
            highlight_lines = []
            for item in highlights:
                user_text = str(item.get("user_input", "") or "").strip()
                aurion_text = str(item.get("aurion_response", "") or "").strip()
                if not user_text and not aurion_text:
                    continue
                highlight_lines.append(f"- U: {user_text[:140]} | A: {aurion_text[:180]}")
            if highlight_lines:
                _append_block("Imported highlights:\n" + "\n".join(highlight_lines))

        try:
            resilience = self.get_memory_resilience_status()
        except Exception:
            resilience = {}
        if resilience:
            _append_block(
                "Memory resilience:\n"
                f"- Primary live memory: {str(resilience.get('primary_path', '')).strip()}\n"
                f"- Secondary mirror: {str(resilience.get('secondary_path', '')).strip()}\n"
                f"- Last backup: {str(resilience.get('last_backup_at', '') or 'unknown')}\n"
                f"- Encryption: {'on' if resilience.get('conversation_encryption_enabled') else 'off'}"
            )

        return "\n\n".join(blocks).strip()

    def get_interaction_count(self):
        """Get total number of interactions."""
        with self._db_lock:
            return len(self.conversations)

    def get_session_interaction_count(self):
        """Get number of interactions in the current runtime session."""
        return len(self.get_session_interactions())

    def _parse_iso_datetime(self, value):
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return None

    def _merge_profiles_for_sync(self, local_profile, incoming_profile):
        merged = dict(local_profile or self._default_profile())
        incoming = dict(incoming_profile or {})
        if not incoming:
            return merged

        local_updated = self._parse_iso_datetime(merged.get("updated_at"))
        incoming_updated = self._parse_iso_datetime(incoming.get("updated_at"))
        incoming_is_newer = bool(incoming_updated and (not local_updated or incoming_updated >= local_updated))

        scalar_fields = (
            "user_name", "relationship_type", "intimacy_mode", "affection_style",
            "consent_mode", "adult_content_style", "roleplay_mode", "roleplay_style",
            "roleplay_scenario", "coding_mode", "code_explanation_style",
            "preferred_code_language", "high_concept_openness", "epistemic_style",
            "emotional_attachment_mode", "attachment_depth", "attachment_expression",
            "profanity_mode", "adult_topic_mode", "preferred_topic_length",
            "humor_style", "emotional_nuance", "lexicon_adaptation",
            "personality_profile_text"
        )
        numeric_fields = (
            "conversation_count", "attachment_adaptability", "loving_language_level",
            "romantic_tone_level", "intimacy_level"
        )
        list_fields = ("preferences", "accomplishments", "personal_details", "favorite_topics")

        for field in scalar_fields:
            incoming_val = incoming.get(field)
            if incoming_is_newer and incoming_val not in (None, ""):
                merged[field] = incoming_val
            elif field not in merged and incoming_val is not None:
                merged[field] = incoming_val

        for field in numeric_fields:
            local_val = merged.get(field, 0)
            incoming_val = incoming.get(field, local_val)
            try:
                if incoming_is_newer:
                    merged[field] = int(incoming_val)
                else:
                    merged[field] = max(int(local_val), int(incoming_val))
            except Exception:
                merged[field] = local_val

        for field in list_fields:
            base = list(merged.get(field, []) or [])
            for item in list(incoming.get(field, []) or []):
                base = self._append_unique(base, item, max_items=self.max_profile_list_items)
            merged[field] = base

        merged_directives = list(merged.get("autonomy_directives", []) or [])
        for item in list(incoming.get("autonomy_directives", []) or []):
            if not isinstance(item, dict):
                continue
            directive = str(item.get("directive", "")).strip()
            if not directive:
                continue
            temp_profile = {"autonomy_directives": merged_directives}
            self._remember_autonomy_directive(
                temp_profile,
                directive,
                source=item.get("source", "sync_merge"),
                priority=item.get("priority", "normal")
            )
            merged_directives = list(temp_profile.get("autonomy_directives", []) or [])
            normalized = self._normalize_directive_key(directive)
            for merged_item in merged_directives:
                if self._normalize_directive_key(merged_item.get("directive", "")) != normalized:
                    continue
                try:
                    merged_item["times_seen"] = max(
                        int(merged_item.get("times_seen", 0) or 0),
                        int(item.get("times_seen", 0) or 0)
                    )
                except Exception:
                    pass
                incoming_last_seen = str(item.get("last_seen_at", "") or "").strip()
                if incoming_last_seen and incoming_last_seen > str(merged_item.get("last_seen_at", "") or ""):
                    merged_item["last_seen_at"] = incoming_last_seen
                break
        merged["autonomy_directives"] = merged_directives

        merged_facts = list(merged.get("important_facts", []) or [])
        for item in list(incoming.get("important_facts", []) or []):
            if not isinstance(item, dict):
                continue
            fact = str(item.get("fact", "")).strip()
            if not fact:
                continue
            temp_profile = {"important_facts": merged_facts}
            self._remember_important_fact(
                temp_profile,
                fact,
                source=item.get("source", "sync_merge"),
                priority=item.get("priority", "normal"),
                memory_link=item.get("memory_link", "")
            )
            merged_facts = list(temp_profile.get("important_facts", []) or [])
            normalized = self._normalize_fact_key(fact)
            for merged_item in merged_facts:
                if self._normalize_fact_key(merged_item.get("fact", "")) != normalized:
                    continue
                try:
                    merged_item["times_seen"] = max(
                        int(merged_item.get("times_seen", 0) or 0),
                        int(item.get("times_seen", 0) or 0)
                    )
                except Exception:
                    pass
                incoming_last_seen = str(item.get("last_seen_at", "") or "").strip()
                if incoming_last_seen and incoming_last_seen > str(merged_item.get("last_seen_at", "") or ""):
                    merged_item["last_seen_at"] = incoming_last_seen
                break
        merged["important_facts"] = merged_facts

        merged_life = dict(merged.get("life_context", {}) or {})
        incoming_life = dict(incoming.get("life_context", {}) or {})
        for key, value in incoming_life.items():
            if value is None:
                continue
            key_text = str(key).strip()
            if not key_text:
                continue
            merged_life[key_text] = str(value).strip()
        merged["life_context"] = merged_life

        merged_emotions = dict(merged.get("emotional_patterns", {}) or {})
        for emotion, count in dict(incoming.get("emotional_patterns", {}) or {}).items():
            try:
                merged_emotions[str(emotion)] = max(
                    int(merged_emotions.get(str(emotion), 0)),
                    int(count)
                )
            except Exception:
                continue
        merged["emotional_patterns"] = merged_emotions

        incoming_voice = dict(incoming.get("voice_patterns", {}) or {})
        local_voice = dict(merged.get("voice_patterns", {}) or {})
        if incoming_is_newer and incoming_voice:
            local_voice.update(incoming_voice)
        else:
            try:
                local_voice["message_count"] = max(
                    int(local_voice.get("message_count", 0)),
                    int(incoming_voice.get("message_count", 0))
                )
            except Exception:
                pass
            try:
                local_voice["question_count"] = max(
                    int(local_voice.get("question_count", 0)),
                    int(incoming_voice.get("question_count", 0))
                )
            except Exception:
                pass
            try:
                local_voice["exclamation_count"] = max(
                    int(local_voice.get("exclamation_count", 0)),
                    int(incoming_voice.get("exclamation_count", 0))
                )
            except Exception:
                pass
            try:
                local_voice["emoji_count"] = max(
                    int(local_voice.get("emoji_count", 0)),
                    int(incoming_voice.get("emoji_count", 0))
                )
            except Exception:
                pass
            incoming_markers = dict(incoming_voice.get("style_markers", {}) or {})
            local_markers = dict(local_voice.get("style_markers", {}) or {})
            for marker, count in incoming_markers.items():
                try:
                    local_markers[str(marker)] = max(int(local_markers.get(str(marker), 0)), int(count))
                except Exception:
                    continue
            local_voice["style_markers"] = local_markers
        merged["voice_patterns"] = local_voice

        merged["updated_at"] = datetime.utcnow().isoformat()
        if not merged.get("created_at"):
            merged["created_at"] = datetime.utcnow().isoformat()
        return merged

    def export_sync_snapshot(self, max_conversations=0, max_topics=0, max_rag_documents=0):
        with self._db_lock:
            all_conversations = self._get_all_interactions()
            all_topics = self.topics.all()
            all_rag_documents = self.rag_documents.all()
            all_conversations.sort(key=lambda i: str(i.get("timestamp", "")))
            all_topics.sort(key=lambda i: str(i.get("timestamp", "")))
            all_rag_documents.sort(key=lambda i: str(i.get("timestamp", "")))

            profile = self.get_profile() or self._default_profile()
            conv_limit = max(0, int(max_conversations))
            topic_limit = max(0, int(max_topics))
            rag_limit = max(0, int(max_rag_documents))
            conversations = all_conversations if conv_limit == 0 else all_conversations[-conv_limit:]
            topics = all_topics if topic_limit == 0 else all_topics[-topic_limit:]
            rag_documents = all_rag_documents if rag_limit == 0 else all_rag_documents[-rag_limit:]
            return {
                "schema_version": 2,
                "exported_at": datetime.utcnow().isoformat(),
                "profile": profile,
                "conversations": conversations,
                "topics": topics,
                "rag_documents": rag_documents
            }

    def import_sync_snapshot(self, snapshot):
        if not isinstance(snapshot, dict):
            raise ValueError("snapshot must be an object")
        with self._db_lock:
            incoming_profile = snapshot.get("profile") or {}
            local_profile = self.get_profile() or self._default_profile()
            merged_profile = self._merge_profiles_for_sync(local_profile, incoming_profile)
            self._save_profile(merged_profile)

            added_conversations = 0
            added_topics = 0
            added_rag_documents = 0

            existing_conv_keys = set()
            for item in self._get_all_interactions():
                key = (
                    str(item.get("timestamp", "")),
                    str(item.get("user_input", "")),
                    str(item.get("aurion_response", ""))
                )
                existing_conv_keys.add(key)

            for item in list(snapshot.get("conversations", []) or []):
                if not isinstance(item, dict):
                    continue
                key = (
                    str(item.get("timestamp", "")),
                    str(item.get("user_input", "")),
                    str(item.get("aurion_response", ""))
                )
                if key in existing_conv_keys:
                    continue
                self.conversations.insert(self._serialize_interaction_for_store(item))
                existing_conv_keys.add(key)
                added_conversations += 1

            existing_topic_keys = set()
            for item in self.topics.all():
                key = (
                    str(item.get("timestamp", "")),
                    str(item.get("topic", "")),
                    str(item.get("context", ""))
                )
                existing_topic_keys.add(key)

            for item in list(snapshot.get("topics", []) or []):
                if not isinstance(item, dict):
                    continue
                key = (
                    str(item.get("timestamp", "")),
                    str(item.get("topic", "")),
                    str(item.get("context", ""))
                )
                if key in existing_topic_keys:
                    continue
                self.topics.insert(item)
                existing_topic_keys.add(key)
                added_topics += 1

            existing_rag_keys = set()
            for item in self.rag_documents.all():
                key = (
                    str(item.get("id", "")),
                    str(item.get("timestamp", "")),
                    str(item.get("source", "")),
                    str(item.get("content", ""))
                )
                existing_rag_keys.add(key)

            for item in list(snapshot.get("rag_documents", []) or []):
                if not isinstance(item, dict):
                    continue
                key = (
                    str(item.get("id", "")),
                    str(item.get("timestamp", "")),
                    str(item.get("source", "")),
                    str(item.get("content", ""))
                )
                if key in existing_rag_keys:
                    continue
                self.rag_documents.insert(item)
                existing_rag_keys.add(key)
                added_rag_documents += 1
            docs = self.rag_documents.all()
            if self.max_rag_docs > 0 and len(docs) > self.max_rag_docs:
                docs.sort(key=lambda r: str(r.get("timestamp", "")))
                excess = len(docs) - self.max_rag_docs
                to_remove = {row.doc_id for row in docs[:excess] if hasattr(row, "doc_id")}
                if to_remove:
                    self.rag_documents.remove(doc_ids=list(to_remove))
            self._mark_memory_written(reason="sync_import")

            return {
                "added_conversations": added_conversations,
                "added_topics": added_topics,
                "added_rag_documents": added_rag_documents,
                "memory_count": self.get_interaction_count(),
                "profile_updated_at": merged_profile.get("updated_at")
            }

    def close(self):
        """Close database."""
        self._run_resilience_maintenance(force=True, reason="close")
        self.db.close()
# ---- Virtual qubit runtime status bridge ----
def get_virtual_qubit_runtime_status() -> dict:
    """
    Lightweight runtime bridge so MemorySystem status can expose virtual-qubit stability state
    without taking hard dependency on brain startup.
    """
    try:
        from joi_companion.core.aurion_brain import get_virtual_qubit_snapshot
        snap = get_virtual_qubit_snapshot() or {}
        return {
            "enabled": True,
            "active_states": int(len(snap)),
            "sample_keys": list(snap.keys())[:5],
        }
    except Exception as e:
        return {
            "enabled": False,
            "active_states": 0,
            "sample_keys": [],
            "error": str(e),
        }

# AURION_MEMORY_RELIABILITY_ENRICHMENT_V1
# Enrich resilience status with stable reliability metadata while preserving existing payload.
try:
    _aurion_original_get_memory_resilience_status = MemorySystem.get_memory_resilience_status
except Exception:
    _aurion_original_get_memory_resilience_status = None

def _aurion_enriched_get_memory_resilience_status(self):
    base = {}
    if _aurion_original_get_memory_resilience_status is not None:
        try:
            base = _aurion_original_get_memory_resilience_status(self)
        except Exception:
            base = {}

    if not isinstance(base, dict):
        base = {}

    arch = base.get("memory_architecture")
    if not isinstance(arch, dict):
        arch = {}

    # Ensure stable presence of keys expected by tests and ops tools
    arch.setdefault("active_runtime_path", "")
    arch.setdefault("long_term_path", "")
    arch.setdefault("backup_dir", "")
    arch.setdefault("cloud_memory_mode", "unknown")
    arch.setdefault("cloud_memory_offload_enabled", "unknown")

    # Additional reliability block (non-breaking additive shape)
    reliability = base.get("reliability")
    if not isinstance(reliability, dict):
        reliability = {}
    reliability.setdefault("runtime_path_present", bool(arch.get("active_runtime_path")))
    reliability.setdefault("long_term_path_present", bool(arch.get("long_term_path")))
    reliability.setdefault("backup_dir_present", bool(arch.get("backup_dir")))
    reliability.setdefault("cloud_mode", arch.get("cloud_memory_mode"))
    reliability.setdefault("cloud_offload_enabled", arch.get("cloud_memory_offload_enabled"))

    # bounded reliability score [0,1]
    checks = [
        bool(reliability.get("runtime_path_present")),
        bool(reliability.get("long_term_path_present")),
        bool(reliability.get("backup_dir_present")),
    ]
    reliability["score"] = round(sum(1 for c in checks if c) / max(len(checks), 1), 3)

    base["memory_architecture"] = arch
    base["reliability"] = reliability
    return base

if _aurion_original_get_memory_resilience_status is not None:
    MemorySystem.get_memory_resilience_status = _aurion_enriched_get_memory_resilience_status

