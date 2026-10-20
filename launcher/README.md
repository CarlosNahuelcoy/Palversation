# Palversation Launcher

External launcher that bridges the Palworld mod (Palversation) and an LLM
provider -- Player2, OpenAI, Gemini, OpenRouter, or a Custom
OpenAI-compatible endpoint (e.g. local Ollama). Runs as a single program:
settings + the live connection, in one window.

## Installing (players)

1. Install **UE4SS Experimental (Palworld)** if you don't have it yet
   (the launcher's Setup tab links to it and tells you if it's missing).
2. Extract the Palversation zip anywhere and open `Palversation.exe`.
   It finds Palworld through Steam and installs/updates the in-game mod
   by itself -- there's no separate mod download and no folder to pick.
3. Press **Connect Account** (Player2) in the General tab, then **Play**.

Keep the launcher open (minimized is fine) while you play. If it isn't
running, your Pal says so in the game chat instead of staying silent.

## Building the standalone .exe

Run `build_exe.bat` from an activated venv with `requirements.txt`
already installed (it installs PyInstaller itself, then builds). In
PowerShell (the default terminal on modern Windows) you need the `.\`
prefix for a script in the current folder:
```
.\build_exe.bat
```
In `cmd.exe` either `build_exe.bat` or `.\build_exe.bat` works. Find
`Palversation.exe` inside the `dist` folder afterward -- it's a single
file, no Python install needed on the end user's machine.

The in-game Lua mod (`mod/Palversation/` at the repo root) is bundled inside the build
and installed into the game by the launcher, so a release is just the
launcher zip. Bump `VERSION` in `mod/Palversation/Scripts/main.lua` when
the mod changes; the launcher replaces any installed copy that differs.

`config.json`, `pal_history.json`, `pal_prompts.json`, and the rest are
all created automatically in `%LOCALAPPDATA%\Palversation\` the first
time it runs (see `core/paths.py`), so updating, moving or deleting the
launcher folder never loses a Pal's memories. Files left next to an old
exe are copied over automatically, or with "Import old data..." in the
Setup tab if the new version was extracted elsewhere. If you want to ship the
curated `pal_data.json` (real species names + lore) alongside it, just
copy that file into the `dist` folder before zipping it up for
distribution.

### Before publishing publicly (e.g. on Nexus)

- [x] Register your own app on the **Player2 Developer Dashboard** and
      put the real Client ID in `providers/player2_auth.py`'s
      `PLAYER2_CLIENT_ID` -- done, "Connect Account" works out of the box.
- [x] No API keys ship with the build: `config.json` is created per
      player in `%LOCALAPPDATA%\Palversation\` and is git-ignored.
- [ ] Bump `CURRENT_VERSION` in `core/update_check.py` (and the mod's
      `VERSION` + `info.json` if the mod changed), then rebuild.

## One program, not two

`python gui/app.py` (or `run_gui.bat`) is the only thing you normally need
to run. It holds the settings tabs AND runs the actual watcher (the
connection to the LLM provider) in a background thread, with a live
**Console** tab to see what it's doing. The status dot + Start/Stop button
in the top right control it; saving any tab restarts it automatically so
changes take effect right away.

`main.py` / `run.bat` still exist as a CLI-only way to run just the
watcher, useful for debugging without the graphical console, but you
don't need it for normal play.

## Player2's "Connect Account" button

Player2's real connect flow (tried here: local app detection, then a
browser-based Device Code approval) needs a Game Client ID registered on
the **Player2 Developer Dashboard**. `providers/player2_auth.py`'s
`PLAYER2_CLIENT_ID` already has one -- if you fork this for your own
distribution, register your own app there instead of reusing this ID:
every connection made through it gets attributed to whichever app it
belongs to.

## Structure

```
palversation-launcher/
  main.py                 CLI-only entry point (debugging, no GUI).
  requirements.txt          Dependencies (just 'requests' for now).
  run.bat                    Windows shortcut: activates venv + runs main.py (CLI only).
  run_gui.bat                 Windows shortcut: activates venv + runs the GUI (normal use).
  gui/
    app.py                     GUI entry point. Main window, header status, tabs, and owns
                                the background watcher thread's lifecycle.
    watcher_controller.py        Start/stop/restart the watcher thread from the GUI.
    theme.py                      Color palette and ttk.Style setup (game-menu look).
    widgets.py                     Custom ToggleSwitch and CycleSelector widgets.
    tab_general.py                   Provider (Connect button or pasted key, depending on
                                      the provider), connection test, general prompt.
    tab_pals.py                       Per-Pal list (friendly names), personality editor,
                                       history viewer.
    tab_events.py                      Per-event on/off toggles and timing settings.
    tab_setup.py                        What was found/installed (Palworld, UE4SS,
                                         mod, provider) with a fix for each problem.
    tab_console.py                       Live output from the background watcher thread.
  providers/
    base.py                 Interface any provider must implement.
    player2.py                Player2 chat provider (tested and working).
    player2_auth.py             Player2's real connect flow (local app + Device Code OAuth).
    openai_compatible.py          Generic provider for OpenAI/Gemini/OpenRouter (same
                                   request/response shape, confirmed for all three).
    registry.py                     Lists available providers for the GUI (add a provider here).
  core/
    watcher.py                The loop that watches the exchange folder (interruptible,
                               runs as a thread from the GUI or as main.py's main thread).
    launcher_runtime.py         Shared provider/path-building logic (used by main.py and the GUI).
    logger.py                    Print-and-forward logging (feeds the GUI's Console tab).
    io_files.py                    Reading/writing the request/response files.
    event_prompts.py                Descriptions for each spontaneous event type.
    text_clean.py                    Emoji filter, second layer of defense.
    history_store.py                   Persistent per-Pal conversation history (JSON).
    pal_prompts.py                       Persistent per-Pal custom personality (JSON).
    pal_names.py                          Persistent per-Pal friendly display name (JSON).
    launcher_config.py                      Reads/writes config.json AND the mod's config.txt.
    game_locator.py                          Finds Palworld (Steam registry + libraries) and UE4SS.
    mod_installer.py                          Installs/updates the bundled mod, enables it for UE4SS.
    install_check.py                           Runs the whole automatic setup + diagnostics.
  ../mod/Palversation/       The in-game Lua mod (main.lua, info.json, enabled.txt), at the
                              repo root; bundled into the build and installed by the launcher.
  %LOCALAPPDATA%\Palversation\   Fixed data folder shared with the Lua mod: config.txt,
                              request.txt / response.txt, pal_species_names.txt.
                              Both sides find it on their own -- nothing to configure.
                              Also holds the player's own files below:
  config.json                Provider, API keys, prompt, etc. Created on first run.
  pal_history.json           Generated automatically. One conversation
                              history per Pal, keyed by its stable
                              CharacterID#InstanceId key.
  pal_prompts.json           Generated automatically by the GUI. One
                              custom personality snippet per Pal, same key.
  pal_names.json               Generated automatically by the background
                                watcher. Last known display name per Pal,
                                same key -- just so the GUI can show a
                                friendly name instead of the raw key.
```

## How to run it

We always use a virtual environment (venv), so that when it's time to
package with PyInstaller, the final exe only includes the project's
real dependencies instead of everything installed globally (that's
exactly what inflates the executable's size).

The GUI uses `tkinter`, part of Python's standard library (no `pip
install` needed) -- it ships with the official python.org Windows
installer by default. If `python gui/app.py` complains it can't find
`tkinter`, reinstall Python from python.org and make sure "tcl/tk and
IDLE" stays checked during setup.

1. Create and activate the venv:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the GUI:
   ```
   python gui\app.py
   ```
   (or double-click `run_gui.bat`)
4. The launcher finds Palworld and installs the mod into it on startup
   (see the **Setup** tab). In the **General** tab, connect or paste your
   provider's API key. Settings save immediately; the mod re-reads them
   every few seconds, so there's no need to restart the game.

## File protocol (IPC with the Lua mod)

This is our own design, it doesn't come from any external documentation.
5 plain text lines, no JSON:

```
<Pal name>
<Pal element>
<Pal key: stable per-individual, CharacterID#InstanceId>
<event type: chat, deploy, recall, hunger, cold, heat, ride_start, ride_end, combat, idle, gift_check>
<content: player's message if event type is "chat", empty or extra detail otherwise>
```

- The Lua mod writes `request.txt` into `%LOCALAPPDATA%\Palversation\` in that format.
- The launcher detects it, deletes it, calls the LLM provider (including
  this specific Pal's prior conversation turns and custom personality,
  loaded by its stable key), and writes `response.txt` next to it:
  ```
  <response text>
  ```
- The Lua mod reads that file, shows it in the chat, and deletes it.
- The launcher then appends this exchange to `pal_history.json` under
  that Pal's key, trimmed to the last `history_max_turns` exchanges
  (configurable in the Events tab), so each individual Pal keeps its own
  coherent conversation across sessions.

## Testing without the mod (by hand)

With the launcher running, you can simulate the Lua mod by writing the
request file yourself (PowerShell):

```
"Chillet`nDragon`nChillet#1`n`n`nchat`nhello" | Out-File -Encoding utf8 $env:LOCALAPPDATA\Palversation\request.txt
```

A `response.txt` should appear in that same folder a few seconds later.

## Adding another provider

1. Write a class in `providers/<name>.py` implementing `LLMProvider`
   (see `providers/base.py`).
2. Add one `ProviderSpec` entry in `providers/registry.py`. If it just
   needs a pasted API key (OpenAI, Gemini, OpenRouter, etc), set
   `key_is_pasted=True` and `auth_handler=None` -- the GUI renders a
   plain key field automatically. If it needs its own connect flow like
   Player2's, write a `providers/<name>_auth.py` with a
   `start_connect(on_key, on_status, on_error)` function and point
   `auth_handler` at it.

That's the whole integration surface -- the GUI doesn't need any other
change to pick up a new provider.
