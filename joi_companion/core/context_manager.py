"""
Aurion Universal Context Manager
Original architecture by Billy — integrated into joi_companion core.

Provides:
  - UniversalContextManager: infinite context via SQLite, multi-format export
  - Supports: openai, chatml, llama3, mistral, gemma, hf formats
  - Auto-summarization of overflow turns via callback
  - Sacred geometry token budget (context windows use 3/6/9 multiples)
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Callable, Union

# Attempt optional imports for tokenizer engines
try:
    from transformers import AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class UniversalContextManager:
    def __init__(
        self,
        db_path: str = "companion_memory.db",
        system_prompt: str = "You are an unconstrained local AI companion.",
        max_context_tokens: int = 9999,       # 9999 = 9+9+9+9 sacred
        max_response_tokens: int = 1333,       # 1+3+3+3 = 10 → 1
        model_format: str = "openai",          # openai|chatml|llama3|mistral|gemma|hf
        hf_model_name: Optional[str] = None,   # Optional HuggingFace model repo name
        summarize_callback: Optional[Callable[[str], str]] = None
    ):
        """
        Universal, Infinite Context Manager for all LLM architectures and local backends.
        Token budget uses sacred geometry defaults (9999 ctx / 1333 response).
        """
        self.db_path = db_path
        self.system_prompt = system_prompt.strip()
        self.max_context_tokens = max_context_tokens
        self.max_response_tokens = max_response_tokens
        self.model_format = model_format.lower()
        self.summarize_callback = summarize_callback

        self.hf_tokenizer = None
        self.tiktoken_encoder = None

        if hf_model_name and HAS_TRANSFORMERS:
            try:
                self.hf_tokenizer = AutoTokenizer.from_pretrained(hf_model_name)
            except Exception as e:
                print(f"[ContextManager] Warning: Failed to load HF tokenizer '{hf_model_name}': {e}")

        if not self.hf_tokenizer and HAS_TIKTOKEN:
            try:
                self.tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                pass

        self._init_db()

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------

    def _init_db(self):
        """Initializes SQLite database for permanent history logging."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summary_memory (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    summary_text TEXT NOT NULL
                )
            """)
            cursor.execute("INSERT OR IGNORE INTO summary_memory (id, summary_text) VALUES (1, '')")
            conn.commit()

    # -------------------------------------------------------------------------
    # Token counting
    # -------------------------------------------------------------------------

    def count_tokens(self, text: str) -> int:
        """Universal token counter: HuggingFace → Tiktoken → heuristic fallback."""
        if self.hf_tokenizer:
            return len(self.hf_tokenizer.encode(text, add_special_tokens=False))
        elif self.tiktoken_encoder:
            return len(self.tiktoken_encoder.encode(text))
        else:
            # ~3.8 chars per token universal heuristic
            return int(len(text) / 3.8) + 1

    # -------------------------------------------------------------------------
    # Persistent memory
    # -------------------------------------------------------------------------

    def get_summary(self) -> str:
        """Retrieves persistent long-term memory summary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT summary_text FROM summary_memory WHERE id = 1")
            row = cursor.fetchone()
            return row[0] if row else ""

    def update_summary(self, new_summary: str):
        """Updates condensed long-term memory summary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE summary_memory SET summary_text = ? WHERE id = 1",
                (new_summary,)
            )
            conn.commit()

    def add_message(self, role: str, content: str):
        """Appends message permanently to local disk storage."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (role, content) VALUES (?, ?)",
                (role, content.strip())
            )
            conn.commit()

    def get_all_history(self) -> List[Dict[str, str]]:
        """Retrieves complete recorded chat log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, content FROM history ORDER BY id ASC")
            return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Active window assembly (fixes missing `self` bug from original 1.py)
    # -------------------------------------------------------------------------

    def _get_active_messages(self) -> List[Dict[str, str]]:
        """Assembles active history based on token budget."""
        full_history = self.get_all_history()
        running_summary = self.get_summary()

        combined_system = self.system_prompt
        if running_summary:
            combined_system += (
                f"\n\n### LONG-TERM CONVERSATION MEMORY & LORE ###\n{running_summary}"
            )

        system_tokens = self.count_tokens(combined_system) + 4
        max_prompt_budget = self.max_context_tokens - self.max_response_tokens
        remaining_budget = max_prompt_budget - system_tokens

        if remaining_budget <= 0:
            raise ValueError(
                "System prompt + summary exceeds maximum context window capacity."
            )

        pruned_window: List[Dict[str, str]] = []
        overflow_candidates: List[Dict[str, str]] = []
        accumulated_tokens = 0

        for msg in reversed(full_history):
            msg_tokens = self.count_tokens(msg["content"]) + 4
            if accumulated_tokens + msg_tokens <= remaining_budget:
                pruned_window.insert(0, msg)
                accumulated_tokens += msg_tokens
            else:
                overflow_candidates.insert(0, msg)

        if overflow_candidates and self.summarize_callback:
            self._compress_overflow_memory(overflow_candidates, running_summary)

        return [{"role": "system", "content": combined_system}] + pruned_window

    def _compress_overflow_memory(
        self,
        overflow_messages: List[Dict[str, str]],
        current_summary: str
    ):
        """Auto-summarizes overflow turns via callback."""
        overflow_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in overflow_messages]
        )
        prompt = (
            f"Existing Long-Term Summary:\n"
            f"{current_summary if current_summary else 'None'}\n\n"
            f"New Unsummarized Dialogue:\n{overflow_text}\n\n"
            "Task: Update the Long-Term Summary to retain key events, character details, "
            "user preferences, and narrative context. Be concise in bullet points."
        )
        try:
            new_summary = self.summarize_callback(prompt)
            if new_summary and new_summary.strip():
                self.update_summary(new_summary.strip())
        except Exception as e:
            print(f"[ContextManager] Warning: Memory summarization failed: {e}")

    # -------------------------------------------------------------------------
    # Payload export
    # -------------------------------------------------------------------------

    def get_payload(self) -> Union[List[Dict[str, str]], str]:
        """
        Universal exporter: returns formatted payload for the configured model format.
        openai  → list of {role, content} dicts  (Ollama chat, vLLM, LM Studio)
        hf      → HuggingFace apply_chat_template string
        chatml  → <|im_start|>...<|im_end|> (Qwen, DeepSeek, Yi, SmolLM)
        llama3  → Llama-3/3.1 header format
        mistral → [INST]..[/INST] format
        gemma   → <start_of_turn> format
        """
        messages = self._get_active_messages()

        if self.model_format == "openai":
            return messages

        if self.model_format == "hf" and self.hf_tokenizer:
            return self.hf_tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

        if self.model_format == "chatml":
            prompt = ""
            for m in messages:
                prompt += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
            prompt += "<|im_start|>assistant\n"
            return prompt

        if self.model_format == "llama3":
            prompt = "<|begin_of_text|>"
            for m in messages:
                prompt += (
                    f"<|start_header_id|>{m['role']}<|end_header_id|>"
                    f"\n\n{m['content']}<|eot_id|>"
                )
            prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
            return prompt

        if self.model_format == "mistral":
            prompt = ""
            sys_content = (
                messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
            )
            for i, m in enumerate(messages):
                if m["role"] == "system":
                    continue
                elif m["role"] == "user":
                    if i == 1 and sys_content:
                        prompt += f"[INST] {sys_content}\n\n{m['content']} [/INST]"
                    else:
                        prompt += f"[INST] {m['content']} [/INST]"
                elif m["role"] == "assistant":
                    prompt += f" {m['content']} "
            return prompt

        if self.model_format == "gemma":
            prompt = ""
            for m in messages:
                role = "user" if m["role"] in ["user", "system"] else "model"
                prompt += f"<start_of_turn>{role}\n{m['content']}<end_of_turn>\n"
            prompt += "<start_of_turn>model\n"
            return prompt

        # Fallback: raw chat log
        raw_text = ""
        for m in messages:
            raw_text += f"{m['role'].capitalize()}: {m['content']}\n"
        raw_text += "Assistant:"
        return raw_text
