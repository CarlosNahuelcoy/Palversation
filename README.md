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

1. Download the latest UE4SS release from
   [UE4SS-RE/RE-UE4SS on GitHub](https://github.com/UE4SS-RE/RE-UE4SS/releases)
   (grab the `.zip`, not the source code).
2. Find your Palworld install folder, then go into
   `Pal\Binaries\Win64\` inside it (for a normal Steam install this is
   usually something like
   `SteamLibrary\steamapps\common\Palworld\Pal\Binaries\Win64\`).
3. Extract the UE4SS zip **directly into that `Win64` folder** -- not
   into a subfolder. When you're done, `Win64` should directly contain
   things like `dwmapi.dll`, `UE4SS-settings.ini`, and a `Mods` folder.
4. Launch Palworld once. If UE4SS is working, you'll see a black console
   window pop up alongside the game (if you don't, check
   `UE4SS-settings.ini` for `GuiConsoleVisible = 1`).

### 2. Install the Palversation mod

1. Grab `mod/` from this repo (or the zip from a Nexus download).
2. Copy the `Palversation` folder (the one containing
   `Scripts\main.lua`) into your UE4SS `Mods` folder. For a normal Steam
   install this usually looks like
   `...\Palworld\Mods\NativeMods\UE4SS\Mods\Palversation\` (your exact
   path may differ depending on where Steam is installed).
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
