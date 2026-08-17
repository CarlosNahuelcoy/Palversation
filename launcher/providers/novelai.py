"""
NovelAI text-generation provider.

NovelAI exposes an OpenAI-like chat-completions endpoint, but its response
format has some NovelAI-specific behavior, particularly around streaming
and GLM reasoning/content fields.

Confirmed endpoint:

    https://image.novelai.net/oa/v1/chat/completions

A second endpoint, https://text.novelai.net/oa/v1/chat/completions, was
also reported to work by a user during testing, but hasn't been confirmed
here directly. The Base URL field in the launcher is editable, so either
one can be used without touching this file.

Authentication uses a NovelAI Persistent API Token as a Bearer token.

This provider is intentionally text-only. NovelAI's public generation API
does not expose the multimodal/VLM functionality needed by Palversation's
screenshot feature, so image_base64 is rejected rather than being sent in
an incompatible request.
"""

import json
from typing import List, Dict, Optional

import requests

from .base import LLMProvider
from core.text_clean import strip_emojis
from core.event_prompts import build_user_message, build_system_prompt


class NovelAIProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        system_prompt: str,
        model_name: str = "glm-4-6",
        timeout_seconds: float = 90.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.system_prompt = system_prompt
        self.model_name = model_name or "glm-4-6"
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _extract_choice_text(choice: Dict) -> str:
        """Extract generated text from a NovelAI/OpenAI-style choice.

        NovelAI documents its generation response as choices[0].text. We
        also accept several OpenAI-style variants for compatibility,
        since NovelAI's endpoint doesn't always return that documented
        shape in practice (see get_response's own comment on 'stream')."""
        if not isinstance(choice, dict):
            return ""

        # NovelAI documented response format.
        text = choice.get("text")
        if isinstance(text, str) and text:
            return text

        # Some NovelAI/OpenAI-compatible responses may put generated
        # content inside message.
        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content:
                return content

            # Some reasoning models expose their answer separately.
            reasoning_content = message.get("reasoning_content")
            if isinstance(reasoning_content, str) and reasoning_content:
                return reasoning_content

            # Defensive handling for array-style content.
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict):
                        part_text = item.get("text")
                        if isinstance(part_text, str):
                            parts.append(part_text)
                result = "".join(parts)
                if result:
                    return result

        # Streaming/OpenAI-style response.
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str) and content:
                return content

            reasoning_content = delta.get("reasoning_content")
            if isinstance(reasoning_content, str) and reasoning_content:
                return reasoning_content

        return ""

    def _parse_non_streaming_response(self, data: Dict) -> str:
        """Parse a normal (non-SSE) NovelAI response. NovelAI's current
        API returns generated text in choices[0].text; we also accept
        OpenAI-style message.content as a fallback."""
        try:
            choices = data["choices"]
            if not isinstance(choices, list) or not choices:
                raise RuntimeError(f"NovelAI response contains no choices: {data}")
            text = self._extract_choice_text(choices[0])
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected NovelAI response shape: {data}") from e

        if not text:
            raise RuntimeError(
                "NovelAI response has no usable text.\n"
                f"Full response: {json.dumps(data, indent=2, ensure_ascii=False)}"
            )
        return text

    def _parse_streaming_response(self, response) -> str:
        """Parse NovelAI's SSE streaming response. NovelAI sends lines
        such as 'data: {"choices":[{"delta":{"content":"hello"}}]}' and
        finishes with 'data: [DONE]'."""
        pieces = []
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")
            line = line.strip()
            if not line.startswith("data:"):
                continue

            payload = line[5:].strip()
            if payload == "[DONE]":
                break

            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue

            choices = chunk.get("choices", [])
            if not choices:
                continue

            text = self._extract_choice_text(choices[0])
            if text:
                pieces.append(text)

        result = "".join(pieces)
        if not result:
            raise RuntimeError("NovelAI streaming response contained no usable text.")
        return result

    def get_response(
        self,
        message: str,
        pal_name: str = "",
        pal_element: str = "",
        event_type: str = "chat",
        history: List[Dict[str, str]] = None,
        per_pal_prompt: str = "",
        pal_passives: str = "",
        pal_friendship: str = "",
        species_hint: str = "",
        image_base64: Optional[str] = None,
        memory_hint: str = "",
        time_gap_prefix: str = "",
    ) -> str:
        # NovelAI does not expose the multimodal API required by
        # Palversation's screenshot feature. Fail explicitly rather than
        # sending a malformed OpenAI-style image message.
        if image_base64:
            raise RuntimeError("NovelAI provider does not support screenshot/image input.")

        system_prompt = build_system_prompt(
            self.system_prompt,
            pal_name=pal_name,
            pal_element=pal_element,
            species_hint=species_hint,
            per_pal_prompt=per_pal_prompt,
            pal_passives=pal_passives,
            pal_friendship=pal_friendship,
            memory_hint=memory_hint,
        )

        user_message = build_user_message(event_type, message, time_gap_prefix)

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # 'stream' is set to True on purpose: testing showed NovelAI's
        # endpoint returns a chunk-shaped body (object: 'chat.completion.
        # chunk', text under choice['text']) even when a client explicitly
        # asks for stream=False, so we may as well request real streaming
        # and handle both response shapes (see the Content-Type branch
        # below), instead of fighting a flag the server appears to ignore.
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "max_tokens": 200,
            "temperature": 0.7,
        }

        try:
            response = requests.post(
                self.base_url, headers=headers, json=payload, timeout=self.timeout_seconds
            )
        except requests.RequestException as e:
            raise RuntimeError(f"NovelAI request failed: {e}") from e

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Include NovelAI's actual response body when available. This
            # makes authentication/model/API errors much easier to diagnose.
            try:
                detail = response.text
            except Exception:
                detail = "<unable to read response body>"
            raise RuntimeError(f"NovelAI returned HTTP {response.status_code}: {detail}") from e

        # NovelAI's OpenAI-compatible endpoint returns usable text through
        # its streaming/SSE interface, so streaming is enabled above.
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/event-stream" in content_type:
            text = self._parse_streaming_response(response)
        else:
            try:
                data = response.json()
            except ValueError as e:
                raise RuntimeError(f"NovelAI returned invalid JSON: {response.text}") from e
            text = self._parse_non_streaming_response(data)

        return strip_emojis(text)
