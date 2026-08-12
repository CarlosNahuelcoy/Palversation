"""
Emoji filter. This is a second layer of defense besides the instruction in
system_prompt: the model may not always obey, this one guarantees it.

It doesn't cover 100% of the "weird" Unicode characters that exist out
there (impossible without an exhaustively maintained list), but it covers
the ranges where the vast majority of emojis actually used in practice
live.
"""

import re

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # pictographs, transport, supplemental symbols
    "\U00002600-\U000027BF"  # misc symbols and dingbats
    "\U0001F1E6-\U0001F1FF"  # flags (regional indicators)
    "\U00002B00-\U00002BFF"  # misc symbols and arrows
    "\U0000FE0F"             # variation selector (forces emoji style)
    "\U0001F000-\U0001F0FF"  # mahjong, dominoes, cards
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    without_emojis = _EMOJI_PATTERN.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", without_emojis).strip()
