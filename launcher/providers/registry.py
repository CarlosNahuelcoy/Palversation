"""
Registry of available LLM providers, so the GUI (and anything else) can
list them and build the right settings form without hardcoding a specific
provider's details.

To add a new provider that just needs a pasted API key (and follows the
OpenAI-compatible /chat/completions shape):
  1. Add one ProviderSpec entry below using OpenAICompatibleProvider,
     with key_is_pasted=True, auth_handler=None, and a default_model.
That's it -- the GUI reads this list and renders a plain API key field
plus a model field, it doesn't need any other change.

To add a provider with its own connect flow (like Player2's account
login), write a providers/<name>_auth.py with a
start_connect(on_key, on_status, on_error) function (see
providers/player2_auth.py), and set key_is_pasted=False and
auth_handler=that function.

To add a provider that DOESN'T follow the OpenAI-compatible shape, write
a class implementing LLMProvider (see providers/base.py) and point
factory at it instead.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from providers.base import LLMProvider
from providers.player2 import Player2Provider
from providers.player2_auth import start_connect as player2_start_connect
from providers.openai_compatible import OpenAICompatibleProvider
from providers.novelai import NovelAIProvider


@dataclass
class ProviderSpec:
    provider_id: str
    display_name: str
    default_base_url: str
    api_key_label: str
    api_key_placeholder: str
    key_is_pasted: bool
    factory: Callable[..., LLMProvider]
    auth_handler: Optional[Callable] = None
    default_model: str = ""
    model_placeholder: str = ""
    needs_model: bool = False
    requires_api_key: bool = True


def _make_player2(api_key: str, base_url: str, system_prompt: str, model_name: str = "") -> LLMProvider:
    return Player2Provider(api_key=api_key, base_url=base_url, system_prompt=system_prompt)


def _make_openai_compatible(api_key: str, base_url: str, system_prompt: str, model_name: str = "") -> LLMProvider:
    return OpenAICompatibleProvider(
        api_key=api_key, base_url=base_url, system_prompt=system_prompt, model_name=model_name
    )


def _make_novelai(
    api_key: str,
    base_url: str,
    system_prompt: str,
    model_name: str = "",
) -> LLMProvider:
    return NovelAIProvider(
        api_key=api_key,
        base_url=base_url,
        system_prompt=system_prompt,
        model_name=model_name or "glm-4-6",
    )


PROVIDERS: Dict[str, ProviderSpec] = {
    "player2": ProviderSpec(
        provider_id="player2",
        display_name="Player2",
        default_base_url="https://api.player2.game/v1/chat/completions",
        api_key_label="Player2 Account",
        api_key_placeholder="",
        key_is_pasted=False,
        factory=_make_player2,
        auth_handler=player2_start_connect,
    ),
    "openai": ProviderSpec(
        provider_id="openai",
        display_name="OpenAI",
        default_base_url="https://api.openai.com/v1/chat/completions",
        api_key_label="OpenAI API key",
        api_key_placeholder="sk-...",
        key_is_pasted=True,
        factory=_make_openai_compatible,
        default_model="gpt-4o-mini",
        model_placeholder="gpt-4o-mini",
        needs_model=True,
    ),
    "gemini": ProviderSpec(
        provider_id="gemini",
        display_name="Gemini",
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        api_key_label="Gemini API key",
        api_key_placeholder="AIza...",
        key_is_pasted=True,
        factory=_make_openai_compatible,
        default_model="gemini-3.6-flash",
        model_placeholder="gemini-3.6-flash",
        needs_model=True,
    ),
    "openrouter": ProviderSpec(
        provider_id="openrouter",
        display_name="OpenRouter",
        default_base_url="https://openrouter.ai/api/v1/chat/completions",
        api_key_label="OpenRouter API key",
        api_key_placeholder="sk-or-...",
        key_is_pasted=True,
        factory=_make_openai_compatible,
        default_model="openai/gpt-4o-mini",
        model_placeholder="openai/gpt-4o-mini",
        needs_model=True,
    ),
    "novelai": ProviderSpec(
        provider_id="novelai",
        display_name="NovelAI",
        default_base_url="https://image.novelai.net/oa/v1/chat/completions",
        api_key_label="NovelAI Persistent API Token",
        api_key_placeholder="Paste your NovelAI Persistent API Token",
        key_is_pasted=True,
        factory=_make_novelai,
        default_model="glm-4-6",
        model_placeholder="glm-4-6",
        needs_model=True,
        requires_api_key=True,
    ),
    "custom": ProviderSpec(
        provider_id="custom",
        display_name="Custom (OpenAI-compatible)",
        default_base_url="http://localhost:11434/v1/chat/completions",
        api_key_label="API key (leave blank if none needed, e.g. local Ollama)",
        api_key_placeholder="optional",
        key_is_pasted=True,
        factory=_make_openai_compatible,
        default_model="",
        model_placeholder="e.g. llama3, mistral, gpt-4o-mini",
        needs_model=True,
        requires_api_key=False,
    ),
}


def get_provider_spec(provider_id: str) -> ProviderSpec:
    if provider_id not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider_id}'. Known providers: {list(PROVIDERS.keys())}")
    return PROVIDERS[provider_id]


def list_providers() -> list:
    return list(PROVIDERS.values())
