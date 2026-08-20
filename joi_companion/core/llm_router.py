"""
Aurion LLM Router
Original architecture by Billy — integrated into joi_companion core.

Universal API wrapper routing payloads from UniversalContextManager
to local backends: Ollama, vLLM, KoboldCPP.

Usage:
    from joi_companion.core.llm_router import LLMRouter, SAMPLING_CONFIG
    router = LLMRouter(backend="ollama", model_name="aurion")
    response = router.generate(context_manager.get_payload())
"""

import json
import requests
from typing import Union, List, Dict, Generator, Optional


# Sacred geometry sampling defaults
# Numerology: 0.333, 0.666, 0.999 never exceed full unit boundaries
SAMPLING_CONFIG = {
    "temperature": 0.666,         # 6 = harmony
    "min_p": 0.033,
    "top_p": 0.999,               # 0.999 = never exactly 1.0
    "rep_pen": 1.12,              # KoboldCPP
    "repeat_penalty": 1.12,       # Ollama
    "presence_penalty": 0.033,
    "frequency_penalty": 0.066,
    "max_tokens": 1333,           # 1+3+3+3 = 10 → 1
}


class LLMRouter:
    def __init__(
        self,
        backend: str,
        base_url: Optional[str] = None,
        model_name: str = "aurion",
        temperature: float = SAMPLING_CONFIG["temperature"],
        max_tokens: int = SAMPLING_CONFIG["max_tokens"],
    ):
        """
        Universal API Wrapper routing payloads from UniversalContextManager
        to local backends.

        Args:
            backend:    Engine target ('ollama', 'vllm', or 'koboldcpp')
            base_url:   Base HTTP address (uses defaults if None)
            model_name: Target model identifier
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
        """
        self.backend = backend.lower()
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        defaults = {
            "ollama":     "http://localhost:11434",
            "vllm":       "http://localhost:8000",
            "koboldcpp":  "http://localhost:5001",
        }
        self.base_url = (
            base_url or defaults.get(self.backend, "http://localhost:8000")
        ).rstrip("/")

    def generate(
        self,
        payload: Union[List[Dict[str, str]], str],
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """
        Routes payload (messages list or formatted prompt string) to target backend.

        Args:
            payload: Output from UniversalContextManager.get_payload()
            stream:  If True, yields token chunks. If False, returns full string.
        """
        is_chat_list = isinstance(payload, list)

        if self.backend == "ollama":
            return self._call_ollama(payload, is_chat_list, stream)
        elif self.backend == "vllm":
            return self._call_vllm(payload, is_chat_list, stream)
        elif self.backend == "koboldcpp":
            return self._call_koboldcpp(payload, is_chat_list, stream)
        else:
            raise ValueError(f"[LLMRouter] Unsupported backend: '{self.backend}'")

    # -------------------------------------------------------------------------
    # Ollama
    # -------------------------------------------------------------------------

    def _call_ollama(
        self,
        payload: Union[List[Dict[str, str]], str],
        is_chat: bool,
        stream: bool
    ):
        endpoint = (
            f"{self.base_url}/api/chat"
            if is_chat
            else f"{self.base_url}/api/generate"
        )
        body = {
            "model": self.model_name,
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "repeat_penalty": SAMPLING_CONFIG["repeat_penalty"],
                "top_p": SAMPLING_CONFIG["top_p"],
            },
        }
        if is_chat:
            body["messages"] = payload
        else:
            body["prompt"] = payload

        response = requests.post(endpoint, json=body, stream=stream, timeout=120)
        response.raise_for_status()

        if stream:
            return self._stream_ollama(response, is_chat)
        else:
            data = response.json()
            return (
                data["message"]["content"] if is_chat else data["response"]
            )

    def _stream_ollama(
        self, response: requests.Response, is_chat: bool
    ) -> Generator[str, None, None]:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                data = json.loads(line)
                chunk = (
                    data.get("message", {}).get("content", "")
                    if is_chat
                    else data.get("response", "")
                )
                if chunk:
                    yield chunk

    # -------------------------------------------------------------------------
    # vLLM (OpenAI-compatible)
    # -------------------------------------------------------------------------

    def _call_vllm(
        self,
        payload: Union[List[Dict[str, str]], str],
        is_chat: bool,
        stream: bool
    ):
        endpoint = (
            f"{self.base_url}/v1/chat/completions"
            if is_chat
            else f"{self.base_url}/v1/completions"
        )
        body = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
        }
        if is_chat:
            body["messages"] = payload
        else:
            body["prompt"] = payload

        response = requests.post(endpoint, json=body, stream=stream, timeout=120)
        response.raise_for_status()

        if stream:
            return self._stream_openai_sse(response)
        else:
            data = response.json()
            return (
                data["choices"][0]["message"]["content"]
                if is_chat
                else data["choices"][0]["text"]
            )

    # -------------------------------------------------------------------------
    # KoboldCPP
    # -------------------------------------------------------------------------

    def _call_koboldcpp(
        self,
        payload: Union[List[Dict[str, str]], str],
        is_chat: bool,
        stream: bool
    ):
        if is_chat:
            endpoint = f"{self.base_url}/v1/chat/completions"
            body = {
                "model": self.model_name,
                "messages": payload,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "rep_pen": SAMPLING_CONFIG["rep_pen"],
                "stream": stream,
            }
            response = requests.post(endpoint, json=body, stream=stream, timeout=120)
            response.raise_for_status()
            return (
                self._stream_openai_sse(response)
                if stream
                else response.json()["choices"][0]["message"]["content"]
            )
        else:
            endpoint = (
                f"{self.base_url}/api/extra/generate/stream"
                if stream
                else f"{self.base_url}/api/v1/generate"
            )
            body = {
                "prompt": payload,
                "max_length": self.max_tokens,
                "temperature": self.temperature,
                "rep_pen": SAMPLING_CONFIG["rep_pen"],
            }
            response = requests.post(endpoint, json=body, stream=stream, timeout=120)
            response.raise_for_status()

            if stream:
                return self._stream_kobold_native_sse(response)
            else:
                return response.json()["results"][0]["text"]

    # -------------------------------------------------------------------------
    # Shared SSE helpers
    # -------------------------------------------------------------------------

    def _stream_openai_sse(
        self, response: requests.Response
    ) -> Generator[str, None, None]:
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        chunk = delta.get("content") or choices[0].get("text", "")
                        if chunk:
                            yield chunk
                except json.JSONDecodeError:
                    continue

    def _stream_kobold_native_sse(
        self, response: requests.Response
    ) -> Generator[str, None, None]:
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    data = json.loads(line[6:].strip())
                    chunk = data.get("token", "")
                    if chunk:
                        yield chunk
                except json.JSONDecodeError:
                    continue
