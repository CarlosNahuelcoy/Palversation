# Palversation

A Palworld mod + launcher that lets your Pals actually talk back, using an
LLM. Pick a provider in the launcher: Player2 (one-click account connect,
no key to copy), OpenAI, Gemini, OpenRouter, NovelAI, or a Custom
OpenAI-compatible endpoint (e.g. a local Ollama server).

This repo has two parts:

- **[`launcher/`](launcher/)** -- the desktop app (Python + a GUI) that
  talks to the LLM provider and exchanges messages with the mod. It also
  finds Palworld and installs the mod for you. See
  [`launcher/README.md`](launcher/README.md) for running it from source or
  building the `.exe`.
- **[`mod/`](mod/)** -- the UE4SS Lua mod itself (`Scripts/main.lua`). It
  ships inside the launcher, so players don't need to install it by hand.

## Installing

1. **Get UE4SS** (the mod loader Palworld Lua mods run on), if you don't
   have it yet: subscribe to
   [UE4SS Experimental (Palworld) on the Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3625223587).
2. **Download the launcher** from this repo's [Releases](../../releases)
   page, extract the zip anywhere and open `Palversation.exe` (no Python
   needed). It finds Palworld through Steam and installs/updates the mod
   by itself. Its **Setup** tab shows a check for each part (Palworld,
   UE4SS, the mod, the AI provider), with a hint for anything missing.
3. **Connect a provider** in the **General** tab:
   - **Player2** -- no key to copy. Click **Connect Account**; it either
     grabs a key from the local Player2 app instantly, or opens your
     browser for a one-time approval.
   - **OpenAI / Gemini / OpenRouter / NovelAI** -- paste your own API key,
     and set the model if you want something other than the default.
   - **Custom (OpenAI-compatible)** -- for a local server or any other
     OpenAI-compatible endpoint. The server address alone is enough
     (e.g. `http://localhost:11434` for Ollama, `http://localhost:1234/v1`
     for LM Studio); the API key can stay empty if the server doesn't
     need one. Local models can be slow: raise **Response timeout** in
     the Events tab if replies time out.
4. Press **Play**. In-game, deploy a Pal and type `!pal <message>` in
   chat. Keep the launcher open while you play (minimized is fine); if
   it isn't running, your Pal says so in the chat.

You can also subscribe to
[Palversation on the Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3785893955)
instead of letting the launcher install the mod -- the launcher detects
that and leaves the Workshop copy alone. You still need the launcher
itself from Releases (Steam doesn't allow programs on the Workshop).

### Updating from v1.0.x

- You no longer pick any folders: the old Folders tab is gone, and the
  mod and launcher find each other through `%LOCALAPPDATA%\Palversation\`.
- Your settings and your Pals' memories now live in that same folder, so
  future updates never lose them. If you extracted the new version
  somewhere other than the old one, use **Setup > Import old data...** and
  pick your old launcher folder.
- The mod must be v0.14.0 or newer (the launcher installs it; Workshop
  subscribers get it from Steam). The PalSchema dependency was dropped.

## Running from source / building it yourself

See [`launcher/README.md`](launcher/README.md) -- it covers running with
Python directly, the file protocol between the mod and the launcher, and
`launcher/build_exe.bat` for building your own `.exe` (it bundles `mod/`
inside the build automatically).

## License

MIT -- see [`LICENSE`](LICENSE). One extra note in there about the bundled
Player2 Client ID specifically (not a license restriction, just a
courtesy ask if you redistribute a modified build).
