"""
Interface that any LLM provider must implement (Player2, or another one
added later). This way the rest of the launcher doesn't need to know which
provider is being used, it just calls get_response().
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class LLMProvider(ABC):
    @abstractmethod
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
        """
        Receives the message/content, the active Pal's name and element,
        the event type ("chat" for player messages, or another value for
        spontaneous events like deploy/recall/hunger/etc), the prior
        conversation turns for this specific Pal (a list of
        {"role": "user"|"assistant", "content": "..."} dicts, oldest
        first, or None/empty if there's no history yet), an optional
        per-pal custom personality snippet (empty string if the user
        hasn't set one for this specific Pal), the Pal's raw passive
        skill IDs (comma-separated, used as a personality fallback ONLY
        when per_pal_prompt is empty -- currently always empty, see
        core/event_prompts.py), the Pal's real friendship "rank,point"
        (always applied when available, regardless of per_pal_prompt), a
        factual species lore snippet from the user's own pal_data.json
        (always applied when available -- this is factual grounding, not
        a personality choice, so it doesn't depend on per_pal_prompt
        either), an optional base64-encoded PNG screenshot (confirmed
        supported by Player2 and any other OpenAI-vision-compatible
        provider via an image_url content block -- providers that don't
        support vision should just ignore this or raise clearly, not
        silently drop it), and an optional long-term memory summary
        (always applied when available, same reasoning as the friendship
        hint -- remembered continuity, not a personality choice). Returns
        the response text, ready to send to the game chat. Must raise an
        exception if something goes wrong (the calling layer handles the
        error).
        """
        raise NotImplementedError
