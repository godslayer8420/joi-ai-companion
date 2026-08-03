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
        self._conversation_cipher = None
        self._conversation_encryption_enabled = False
        self._conversation_encryption_error = ""
        self._configure_resilience_paths()
        self._configure_conversation_encryption()
        self._repair_corrupted_db_if_needed()
        self.db = None
        self.conversations = None
        self.user_profile = None
        self.topics = None
        self._open_db()
        self.session_id = datetime.utcnow().isoformat()
        self.session_turn = 0
        self._ensure_profile_schema()
        self._import_legacy_chat_memory()
        self._run_resilience_maintenance(force=True, reason="startup")

    def _resolve_db_path(self, db_path):
        configured = str(os.getenv("AURION_MEMORY_DB_PATH", "")).strip()
        default_d_drive = r"D:\AurionData\aurion_memory.json"
        candidate = configured or str(db_path or default_d_drive)
        if candidate.lower() == "aurion_memory.json":
            candidate = default_d_drive
        path = Path(candidate)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            return str(path)
        except Exception:
            # Fall back to local repo path if D: path cannot be created.
            return str(Path(db_path or "aurion_memory.json"))

    def _configure_resilience_paths(self):
        primary_path = Path(self.db_path)
        default_secondary = primary_path.with_name(f"{primary_path.stem}_secondary{primary_path.suffix}")
        secondary_raw = str(os.getenv("AURION_MEMORY_SECONDARY_DB_PATH", str(default_secondary))).strip()
        backup_default = primary_path.parent / "backups"
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

    def _configure_conversation_encryption(self):
        key_raw = str(os.getenv("AURION_MEMORY_ENCRYPTION_KEY", "")).strip()
        if not key_raw:
            self._conversation_encryption_enabled = False
            self._conversation_cipher = None
            self._conversation_encryption_error = ""
            return
        try:
            from cryptography.fernet import Fernet
        except Exception as e:
            self._conversation_encryption_enabled = False
            self._conversation_cipher = None
            self._conversation_encryption_error = f"cryptography_unavailable:{e}"
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
        except Exception as e:
            self._conversation_encryption_enabled = False
            self._conversation_cipher = None
            self._conversation_encryption_error = f"invalid_encryption_key:{e}"
            print(f"[MemorySystem] Conversation encryption key invalid: {e}")

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
        with self._db_lock:
            return [self._normalize_interaction(i) for i in self.conversations.all()]

    def _safe_copy_atomic(self, source_path, target_path):
        source = Path(source_path)
        target = Path(target_path)
        if not source.exists():
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f"{target.name}.tmp")
        shutil.copy2(str(source), str(tmp))
        os.replace(str(tmp), str(target))
        return True

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
            "conversation_encryption_enabled": bool(self._conversation_encryption_enabled),
            "conversation_encryption_error": self._conversation_encryption_error or None
        }

    def _open_db(self):
        self.db = TinyDB(self.db_path, encoding="utf-8")
        self.conversations = self.db.table('conversations')
        self.user_profile = self.db.table('user_profile')
        self.topics = self.db.table('topics')
        self.rag_documents = self.db.table('rag_documents')

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
            'life_context': {},
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
        with self._db_lock:
            profiles = self.user_profile.all()
            return profiles[0] if profiles else None

    def _save_profile(self, profile):
        with self._db_lock:
            self.user_profile.truncate()
            self.user_profile.insert(profile)
            self._mark_memory_written(reason="profile_save")

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