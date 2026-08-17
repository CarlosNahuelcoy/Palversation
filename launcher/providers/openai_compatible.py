"""
Generic OpenAI-compatible chat provider, reused for any provider whose
API matches OpenAI's /chat/completions shape closely enough. Confirmed
for three providers via their own docs:
  - OpenAI:      https://api.openai.com/v1/chat/completions
  - Gemini:      https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
  - OpenRouter:  https://openrouter.ai/api/v1/chat/completions

Unlike Player2Provider, this always sends a 'model' field -- all three
above require it (Player2 chooses a model automatically instead, which
is why it stays a separate, simpler class).
"""

import requests
from typing import List, Dict, Optional

from .base import LLMProvider
from core.text_clean import strip_emojis
from core.event_prompts import build_user_message, build_passive_hint, build_friendship_hint
from core.pal_memory import build_memory_hint


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        system_prompt: str,
        model_name: str = "",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

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
        system_prompt = self.system_prompt
        if pal_name:
            system_prompt += f" Your name is {pal_name}."
        if pal_element and pal_element.lower() != "none":
            system_prompt += f" You are a {pal_element}-type Pal."
        if species_hint:
            system_prompt += species_hint
        if per_pal_prompt:
            system_prompt += f" {per_pal_prompt}"
        elif pal_passives:
            system_prompt += build_passive_hint(pal_passives)
        if pal_friendship:
            system_prompt += build_friendship_hint(pal_friendship)
        if memory_hint:
            system_prompt += build_memory_hint(memory_hint)

        user_message = build_user_message(event_type, message, time_gap_prefix)

        if image_base64:
            user_content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
            ]
        else:
            user_content = user_message

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_content})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }

        response = requests.post(
            self.base_url, headers=headers, json=payload, timeout=self.timeout_seconds
        )
        response.raise_for_status()
        data = response.json()

        # Same defensive parsing as Player2Provider: don't let an
        # unexpected response shape crash with a bare KeyError.
        try:
            choice = data["choices"][0]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected response shape (missing {e}): {data}") from e

        msg = choice.get("message")
        if isinstance(msg, dict) and msg.get("content"):
            text = msg.get("content")
        else:
            # Some OpenAI-compatible providers (confirmed with NovelAI's
            # /oa/v1/chat/completions endpoint) return a completions-style
            # shape even for a non-streaming chat request: no 'message'
            # object at all, just the text directly under choice['text'].
            # Falling back to that instead of failing keeps this working
            # for those providers without breaking the standard shape.
            text = choice.get("text")

        if not text:
            raise RuntimeError(f"Response has no usable text content (choice was: {choice})")

        return strip_emojis(text)