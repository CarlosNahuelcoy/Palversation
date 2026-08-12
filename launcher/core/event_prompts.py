"""
Descriptions for each spontaneous event type, used to build the message we
send to the LLM when it's NOT a chat message from the player.

This is our own design (part of the file protocol), it doesn't come from
any external documentation.
"""

import random

_EVENT_DESCRIPTIONS = {
    "deploy": "Your trainer just summoned you out of your sphere. Greet them.",
    "recall": "Your trainer just put you back in your sphere. Say goodbye.",
    "hunger": "You are hungry right now. Say so in your own way.",
    "cold": "You feel very cold right now. Comment on it.",
    "heat": "You feel very hot right now. Comment on it.",
    "ride_start": "Your trainer just got on you to travel together.",
    "ride_end": "Your trainer just got off you.",
    "combat": "You are in the middle of a fight right now, about to strike. Keep it short, like a quick battle cry, not a monologue.",
    "idle": "Nothing in particular is happening right now. Say something on your own, the way a companion would during a quiet moment. Keep it brief and low-key, not a big announcement.",
    "vision_check": "Your trainer just asked you to look at what's in front of you right now. Comment briefly and naturally on what you actually see in the attached image, in character. Don't describe it like a caption or a list -- react to it the way a companion glancing over would.",
}

# Personality starting points, picked at random per Pal so generated
# personalities don't all converge on the same archetype (which is what
# happened when we just said "be distinctive" with no concrete direction:
# the model kept falling back to the base prompt's own calm/grounded tone
# since nothing pushed it anywhere else).
_PERSONALITY_ARCHETYPES = [
    "energetic and eager",
    "gruff and blunt",
    "shy and anxious",
    "playful and mischievous",
    "arrogant and proud",
    "protective and serious",
    "curious and scatterbrained",
    "lazy and laid-back",
    "dramatic and theatrical",
    "affectionate and clingy",
    "aloof and independent",
    "sarcastic and dry-humored",
    "stubborn and competitive",
    "nervous but well-meaning",
]

# Detail that may come in 'content' for ride_start (see main.lua).
_RIDE_DETAIL = {
    "flying": " You are flying.",
    "swimming": " You are swimming.",
    "ground": "",
}

# Friendly English name for each item in the gift whitelist (see
# GIFT_WHITELIST in main.lua -- these IDs are the real, confirmed
# in-game item IDs, this dict is only for narration).
_ITEM_NAMES = {
    "Berries": "some berries",
    "Money": "a handful of gold coins",
    "Leather": "a piece of leather",
    "Wool": "some wool",
    "Bone": "a bone",
}


def _build_gift_message(content: str) -> str:
    """content comes from Lua already resolved as
    '<trigger>:<outcome>:<item_id>', where trigger is 'requested' (the
    player used the gift command) or 'ambient' (unprompted), and outcome
    is 'success' or 'failure'. The actual item delivery already happened
    (or failed) on the Lua side before this message was even sent, so we
    only narrate a real, already-known outcome -- never a promise."""
    parts = content.split(":")
    trigger = parts[0] if len(parts) > 0 else "requested"
    outcome = parts[1] if len(parts) > 1 else "failure"
    item_id = parts[2] if len(parts) > 2 else ""

    if outcome == "success":
        item_desc = _ITEM_NAMES.get(item_id, "something")
        if trigger == "requested":
            return (
                f"Your trainer just asked if you have something for them. "
                f"You do: you are giving them {item_desc} right now. "
                f"Mention it naturally, like you just remembered you had it."
            )
        return (
            f"Out of nowhere, you want to give your trainer something you found: "
            f"{item_desc}. Bring it up naturally, like a small unprompted gesture."
        )

    if trigger == "requested":
        return (
            "Your trainer just asked if you have something for them. You don't "
            "have anything to give right now (there's nowhere to put it). React "
            "briefly and naturally, no big apology."
        )
    return (
        "You wanted to give your trainer something you found, but there was "
        "nowhere to put it (their inventory is full). Mention it briefly, "
        "without naming any specific item."
    )


def build_user_message(event_type: str, content: str, time_gap_prefix: str = "") -> str:
    """Returns the text that goes as the 'user' message to the LLM,
    depending on the event type. For 'chat' (or any unknown type), returns
    the content as-is (it's the player's actual message). time_gap_prefix
    (e.g. "[about 3 hours later] "), if given, is prepended to whatever
    the result ends up being -- applies to every event type, not just
    chat, since a deploy after a long break deserves the same context."""
    if event_type == "gift_check":
        result = _build_gift_message(content)
    elif event_type == "chat" or event_type not in _EVENT_DESCRIPTIONS:
        result = content
    else:
        result = _EVENT_DESCRIPTIONS[event_type]
        if event_type == "ride_start":
            result += _RIDE_DETAIL.get(content, "")

    return f"{time_gap_prefix}{result}" if time_gap_prefix else result


def build_passive_hint(passives_csv: str) -> str:
    """Builds a system-prompt addition from the Pal's raw passive skill
    IDs (comma-separated, from GetPassiveSkillList() -- internal game
    codenames, not localized display names). Only used as a FALLBACK
    personality source when the player hasn't set a custom per-pal
    prompt; a real per-pal prompt always takes priority over this.

    We don't maintain our own ID -> trait mapping table (that would need
    covering ~200 passives to be worth much); instead we hand the raw IDs
    to the model and let it use its own judgement to pick out the ones
    that clearly read as a personality trait, ignoring the ones that are
    obviously combat/stat mechanics instead."""
    if not passives_csv:
        return ""
    return (
        f" Your character also has these internal ability IDs (raw game "
        f"codenames, not curated for readability): {passives_csv}. Only "
        f"pick up on the ones that clearly read as a personality trait in "
        f"plain English (like Lazy, Serious, Aggressive, Friendly), and "
        f"let that lightly color your attitude. Ignore any that look like "
        f"combat, stat, or mechanical effects instead of a personality "
        f"trait."
    )


def build_friendship_hint(friendship_csv: str) -> str:
    """Builds a system-prompt addition from the Pal's real in-game trust
    value ("rank,point", from GetFriendshipRank()/GetFriendshipPoint()).
    Unlike the passive hint, this is always added when available,
    regardless of whether a custom per-pal prompt is set -- the bond
    level is a separate axis from personality.

    Palworld's own Trust system (confirmed via the community wiki, not
    guessed) runs from rank 0 (brand new) to a hard cap of rank 10, so we
    anchor concrete behavior to real tiers instead of a vague "let the
    number shape your tone" instruction, which didn't reliably do
    anything on its own."""
    if not friendship_csv:
        return ""
    parts = friendship_csv.split(",")
    rank_str = parts[0].strip() if len(parts) > 0 else ""
    point = parts[1].strip() if len(parts) > 1 else "?"
    if not rank_str:
        return ""
    try:
        rank = int(float(rank_str))
    except ValueError:
        return ""

    if rank <= 0:
        tier = "You barely know this trainer yet. Stay a little guarded and formal, still sizing them up."
    elif rank <= 2:
        tier = "You're just starting to warm up to this trainer. Be polite but keep a little distance, testing the waters."
    elif rank <= 4:
        tier = "You've spent real time together and trust them reasonably well now. Let genuine warmth show through, without being clingy about it."
    elif rank <= 6:
        tier = "You have a strong, established bond. Speak with real affection and familiarity, like an old friend would."
    elif rank <= 8:
        tier = "You're deeply attached to this trainer. Be openly warm, a little playful or teasing, protective of them."
    else:
        tier = "This is as close a bond as you two can have. Speak with complete ease and devotion, like family -- affectionate and unguarded."

    return (
        f" Your trust rank with this trainer is {rank} out of 10 (raw score "
        f"{point}). {tier} Don't state the numbers out loud, just embody "
        f"the closeness."
    )


def build_personality_generation_message(pal_name: str, pal_element: str) -> str:
    """Builds the one-time instruction used to generate a Pal's permanent
    personality on first contact. Picks a random archetype as a starting
    point so different Pals don't all converge on the same description --
    without a concrete direction, the model kept defaulting to describing
    itself with the base prompt's own calm/grounded tone, since nothing
    pushed it anywhere else."""
    archetype = random.choice(_PERSONALITY_ARCHETYPES)
    element_bit = ""
    if pal_element and pal_element.lower() != "none":
        element_bit = f" You are a {pal_element}-type Pal, feel free to let that flavor it too."

    return (
        "This is the very first time you're meeting your trainer. Describe "
        "your own personality in 1-2 short sentences, written as a note "
        "about who you are (not addressed to anyone).\n\n"
        f"Lean toward being {archetype} -- make that your own distinctive "
        f"spin on it, not a generic version.{element_bit}\n\n"
        "Important: your default conversational tone is already calm and "
        "low-key, so don't just describe yourself as 'calm', 'grounded', "
        "or 'patient' -- that's the baseline, not a personality. Give "
        "yourself something that actually stands out and could surprise "
        "your trainer. This description will be remembered permanently, "
        "so make it something you could act consistently for a long time."
    )
