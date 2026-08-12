# Palversation

A Palworld mod + launcher that lets your Pals actually talk back, using an
LLM (Player2 by default, or your own OpenAI/Gemini/OpenRouter/local Ollama
key).

This repo has two parts:

- **[`mod/`](mod/)** -- the UE4SS Lua mod itself (`Scripts/main.lua`).
  Install this into your Palworld UE4SS Mods folder like any other mod.
- **[`launcher/`](launcher/)** -- the desktop app (Python + a GUI) that
  actually talks to the LLM provider and exchanges messages with the mod.
  See [`launcher/README.md`](launcher/README.md) for how to run it from
  source or build it into a standalone `.exe`.

## Installing (if you're starting from zero)

### 1. Install UE4SS (the mod loader Palworld mods run on)

If you already have UE4SS working for other Palworld mods, skip to step 2.

1. Subscribe to
   [UE4SS Experimental (Palworld) on the Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3625223587)
   and let Steam download/install it -- this is the recommended way to
   get UE4SS for Palworld, and the Workshop page has its own
   troubleshooting/FAQ if something doesn't load.
2. Launch Palworld once. If UE4SS is working, you'll see a black console
   window pop up alongside the game.

### 2. Install the Palversation mod

Palversation is distributed on Nexus Mods, not via the Steam Workshop
(the Workshop entry above is only for UE4SS itself, the loader).

1. Download the mod from Nexus (or grab `mod/` from this repo).
2. Copy the `Palversation` folder (the one containing
   `Scripts\main.lua`) into your UE4SS `Mods` folder. Since UE4SS was
   installed via the Steam Workshop, that folder is at:
   `steamapps\common\Palworld\Mods\NativeMods\UE4SS\Mods\Palversation\`
   (per the Workshop page's own FAQ on installing Nexus mods).
3. In that same `Mods` folder, open `mods.txt` in a text editor and add
   a line for it:
   ```
   Palversation : 1
   ```

### 3. Install and set up the launcher

1. Install `launcher/` (or grab `Palversation.exe` from this repo's
   [Releases](../../releases) page and run it directly, no Python
   needed).
2. In the app's **Folders** tab, point "Mod Folder" at the
   `...\Palversation\` folder from step 2.2 above.
3. In the **General** tab, connect your Player2 account (or paste
   another provider's API key). Save.
4. In-game: deploy a Pal and type `!pal <message>` in chat -- if it
   responds, everything's installed and connected correctly.

## Running from source / building it yourself

See [`launcher/README.md`](launcher/README.md) -- it covers running with
Python directly, the file protocol between the mod and the launcher, and
`launcher/build_exe.bat` for building your own `.exe`.

## License

MIT -- see [`LICENSE`](LICENSE). One extra note in there about the bundled
Player2 Client ID specifically (not a license restriction, just a
courtesy ask if you redistribute a modified build).
