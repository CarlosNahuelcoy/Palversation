"""
Player2 provider. Confirmed working against:
  https://api.player2.game/v1/chat/completions
Verified response shape: choices[0].message.content
(OpenAI-style, as tested with test_player2.py).
"""

import requests
from typing import List, Dict, Optional

from .base import LLMProvider
from core.text_clean import strip_emojis
from core.event_prompts import build_user_message, build_passive_hint, build_friendship_hint
from core.pal_memory import build_memory_hint


class Player2Provider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, system_prompt: str, timeout_seconds: float = 30.0):
        self.api_key = api_key
        self.base_url = base_url
        self.system_prompt = system_prompt
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

        # Confirmed format: content becomes an array of {type, ...} blocks
        # when an image is attached, instead of a plain string.
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
            "messages": messages,
            "stream": False,
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        # Shape confirmed in the real test: choices[0].message.content.
        # Defensive parsing below: an empty/unusual user message can make
        # the model return a shape without 'content' (e.g. a refusal or a
        # tool call), and a bare KeyError there is not helpful to debug.
        try:
            choice = data["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected response shape from Player2 (missing {e}): {data}") from e

        text = msg.get("content")
        if not text:
            raise RuntimeError(f"Player2 response has no usable 'content' (message was: {msg})")

        return strip_emojis(text)
