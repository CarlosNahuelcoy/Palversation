"""
Loop that watches the file exchange folder, and when a request shows up,
calls the configured LLM provider (with this specific Pal's history and
custom personality, if any) and writes the response.

Runs either as the main thread of the CLI entry point (main.py) or as a
background thread started by the GUI. 'stop_event' lets either caller ask
it to stop cleanly instead of killing the whole process -- this is what
makes it possible for the GUI to Start/Stop/Restart it without exiting.
"""

import threading
from pathlib import Path
from typing import Optional

from providers.base import LLMProvider
from core.io_files import read_request, parse_request, delete_request, write_response
from core.history_store import load_history, save_history, get_turns, append_turn, turns_to_messages_with_time_gaps, time_gap_prefix_for_now
from core.pal_prompts import load_prompts, save_prompts, get_prompt, set_prompt
from core.pal_names import load_names, save_names, set_name
from core.pal_data import load_pal_data, resolve_pal_data_path, get_species_info, build_species_hint, export_species_names_lookup
from core.pal_memory import load_memories, save_memories, get_memory, set_memory, build_summarization_message
from core.event_prompts import build_personality_generation_message
from core.screenshot import capture_foreground_window_base64
from core.logger import log


def run_watch_loop(
    provider: LLMProvider,
    watch_folder: Path,
    request_filename: str,
    response_filename: str,
    poll_interval_seconds: float,
    history_path: Path,
    history_max_turns: int,
    prompts_path: Path,
    names_path: Path,
    pal_data_path: Path,
    memory_path: Path,
    stop_event: Optional[threading.Event] = None,
) -> None:
    if stop_event is None:
        stop_event = threading.Event()  # never set -> behaves like before

    watch_folder.mkdir(parents=True, exist_ok=True)
    request_path = watch_folder / request_filename
    response_path = watch_folder / response_filename

    history = load_history(history_path)
    # Per-pal custom prompts and display names are loaded once at startup,
    # same as history. If the GUI launcher changes them while this is
    # running, use Restart to pick up the change.
    prompts = load_prompts(prompts_path)
    names = load_names(names_path)
    memories = load_memories(memory_path)

    # Static species reference data (user-compiled, not read live from the
    # game). Prefers a real file next to the exe/launcher, falling back to
    # a copy bundled inside the exe itself (if built with one) so this
    # works out of the box for anyone who downloads the built .exe. If
    # present, we also export a simple text lookup into the IPC folder so
    # the Lua mod can show the real species name in the game chat too,
    # without needing to parse JSON on that side.
    resolved_pal_data_path = resolve_pal_data_path(pal_data_path)
    pal_data = load_pal_data(resolved_pal_data_path)
    if pal_data:
        export_species_names_lookup(pal_data, watch_folder / "pal_species_names.txt")
        log(f"[Palversation Launcher] Loaded species data for {len(pal_data)} Pals from {resolved_pal_data_path}")
    else:
        log(f"[Palversation Launcher] No species data found at {pal_data_path} (optional -- names/lore will just use what the game gives us).")

    # Discard any leftover request/response from a previous session that
    # crashed or was closed abruptly. request.txt/response.txt should only
    # ever exist for an instant while a live exchange is in flight, so
    # anything sitting there already at startup is stale, not a new event.
    if request_path.exists():
        log(f"[Palversation Launcher] Found a leftover {request_path.name} from a previous session, discarding it.")
        delete_request(request_path)
    if response_path.exists():
        log(f"[Palversation Launcher] Found a leftover {response_path.name} from a previous session, discarding it.")
        delete_request(response_path)

    log(f"[Palversation Launcher] Watching: {request_path}")
    log(f"[Palversation Launcher] History file: {history_path}")
    log(f"[Palversation Launcher] Per-pal prompts file: {prompts_path}")
    log(f"[Palversation Launcher] Long-term memory file: {memory_path}")
    log("[Palversation Launcher] Running.")

    while not stop_event.is_set():
        raw = read_request(request_path)
        if raw is not None:
            delete_request(request_path)

            pal_name, pal_element, pal_key, pal_passives, pal_friendship, event_type, content = parse_request(raw)
            log(f"[Palversation Launcher] Pal: {pal_name} ({pal_element}) [{pal_key}] - Passives: {pal_passives} - Friendship: {pal_friendship} - Event: {event_type} - Content: {content}")
            try:
                species_id = pal_key.split("#")[0] if pal_key else ""
                species_info = get_species_info(pal_data, species_id) if species_id else None

                # Lua falls back to the raw species ID when the player
                # hasn't set a nickname. If that's what we got, and we
                # have a nicer real name for this species, use that
                # instead -- but never override an actual player-chosen
                # nickname.
                display_name = pal_name
                if species_info and pal_name == species_id and species_info.get("name"):
                    display_name = species_info["name"]

                species_hint = build_species_hint(species_info) if species_info else ""
                memory_hint = get_memory(memories, pal_key) if pal_key else ""

                prior_turns_raw = get_turns(history, pal_key) if pal_key else []
                prior_turns = turns_to_messages_with_time_gaps(prior_turns_raw)
                time_gap_prefix = time_gap_prefix_for_now(prior_turns_raw)
                per_pal_prompt = get_prompt(prompts, pal_key) if pal_key else ""

                is_unresolved_pal = (pal_name == "Pal" and pal_element == "None")
                if pal_key and not per_pal_prompt and not prior_turns and not is_unresolved_pal:
                    log(f"[Palversation Launcher] First time meeting {display_name} ({pal_key}), generating a personality for them...")
                    try:
                        generation_prompt = build_personality_generation_message(display_name, pal_element)
                        generated = provider.get_response(
                            generation_prompt,
                            pal_name=display_name,
                            pal_element=pal_element,
                            event_type="chat",
                            history=[],
                            species_hint=species_hint,
                        )
                        set_prompt(prompts, pal_key, generated)
                        save_prompts(prompts_path, prompts)
                        per_pal_prompt = generated
                        log(f"[Palversation Launcher] Generated personality for {display_name}: {generated}")
                    except Exception as e:
                        log(f"[Palversation Launcher] Could not generate a personality, continuing without one: {e}")

                image_base64 = None
                if event_type == "vision_check":
                    try:
                        image_base64, window_title = capture_foreground_window_base64()
                        log(f"[Palversation Launcher] Captured screenshot of foreground window: '{window_title}'")
                    except Exception as e:
                        log(f"[Palversation Launcher] Could not capture a screenshot, reacting honestly instead: {e}")
                        event_type = "chat"
                        content = (
                            "Your trainer just asked you to look at something, but for some "
                            "reason you can't focus your eyes on anything right now. React "
                            "briefly, a little confused, without claiming to have seen anything."
                        )

                respuesta = provider.get_response(
                    content,
                    pal_name=display_name,
                    pal_element=pal_element,
                    event_type=event_type,
                    history=prior_turns,
                    per_pal_prompt=per_pal_prompt,
                    pal_passives=pal_passives,
                    pal_friendship=pal_friendship,
                    species_hint=species_hint,
                    image_base64=image_base64,
                    memory_hint=memory_hint,
                    time_gap_prefix=time_gap_prefix,
                )
                log(f"[Palversation Launcher] Response: {respuesta}")
                write_response(response_path, respuesta)

                if pal_key and not is_unresolved_pal:
                    dropped_turns = append_turn(history, pal_key, content or event_type, respuesta, history_max_turns)
                    save_history(history_path, history)
                    set_name(names, pal_key, display_name)
                    save_names(names_path, names)

                    if dropped_turns:
                        log(f"[Palversation Launcher] {len(dropped_turns)} old message(s) fell out of {display_name}'s recent memory, folding them into their long-term memory...")
                        try:
                            summarization_prompt = build_summarization_message(memory_hint, dropped_turns)
                            new_summary = provider.get_response(
                                summarization_prompt,
                                pal_name=display_name,
                                pal_element=pal_element,
                                event_type="chat",
                                history=[],
                            )
                            set_memory(memories, pal_key, new_summary)
                            save_memories(memory_path, memories)
                            log(f"[Palversation Launcher] Updated long-term memory for {display_name}: {new_summary}")
                        except Exception as e:
                            log(f"[Palversation Launcher] Could not update long-term memory, those older exchanges are lost: {e}")
                elif is_unresolved_pal:
                    log("[Palversation Launcher] Pal identity looks unresolved (fallback values), not saving to history.")
            except Exception as e:
                log(f"[Palversation Launcher] ERROR calling the provider: {e}")

        stop_event.wait(poll_interval_seconds)

    log("[Palversation Launcher] Stopped.")
