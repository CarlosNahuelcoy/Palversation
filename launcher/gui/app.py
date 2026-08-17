"""
Main window for the Palversation GUI launcher. This is now the ONE thing
a player runs: it holds the settings tabs AND runs the actual watcher
(the connection to Player2) in a background thread, with a Console tab to
see what it's doing. No separate main.py process needed anymore -- that
file still exists for CLI debugging, but everything a player needs is
here, which is also what makes packaging this into a single .exe later
straightforward.
"""

import sys
import math
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Running this file directly (`python gui/app.py`) only puts gui/ itself on
# sys.path, not its parent -- so `core` and `providers` wouldn't be found.
# Adding the parent here makes it work no matter how this script is
# launched (direct, `python -m gui.app`, a shortcut, etc).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.launcher_config import (
    load_launcher_config,
    save_launcher_config,
    load_mod_config,
    save_mod_config,
)
from core.pal_prompts import load_prompts, save_prompts
from core.history_store import load_history
from core.pal_names import load_names
from core.pal_memory import load_memories, save_memories
from core.paths import get_launcher_dir, get_bundled_dir
from core.update_check import CURRENT_VERSION, is_newer_version, fetch_latest_release
from gui import theme
from gui.watcher_controller import WatcherController

LAUNCHER_DIR = get_launcher_dir()

# Header logo cap, so an oversized image someone drops in assets/ doesn't
# blow up the header -- scaled down (keeping aspect ratio) to fit within
# this box, never enlarged if it's already smaller.
MAX_LOGO_WIDTH = 220
MAX_LOGO_HEIGHT = 64


class PalversationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Palversation")
        self.geometry("920x640")
        self.minsize(780, 540)

        self.style = theme.configure_style(self)
        self._maybe_set_window_icon()

        self.config_data = load_launcher_config()
        self.mod_config = load_mod_config(self.mod_config_path())
        self.prompts = load_prompts(self.prompts_path())
        self.history = load_history(self.history_path())
        self.names = load_names(self.names_path())
        self.memories = load_memories(self.memory_path())

        self.watcher = WatcherController(get_config=lambda: self.config_data)

        self._tabs = {}
        self._nav_buttons = {}
        self._active_tab_id = None

        self._build_header()
        self._build_body()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Try to start right away; if settings aren't ready yet, this just
        # leaves the status as "Stopped" instead of popping an error --
        # the player hasn't necessarily finished configuring things yet.
        self._try_start_watcher(silent=True)
        self._poll_log_queue()
        self._poll_watcher_status()
        self._start_update_check()

    # ------------------------------------------------------------------
    # Path helpers -- shared by every tab, all derived from config_data.
    # ------------------------------------------------------------------

    def mod_config_path(self) -> Path:
        mod_folder = self.config_data.get("mod_folder", "")
        if mod_folder:
            return Path(mod_folder) / "config.txt"
        return LAUNCHER_DIR / "config.txt"  # placeholder until a folder is set

    def prompts_path(self) -> Path:
        return LAUNCHER_DIR / self.config_data.get("prompts_file", "pal_prompts.json")

    def history_path(self) -> Path:
        return LAUNCHER_DIR / self.config_data.get("history_file", "pal_history.json")

    def names_path(self) -> Path:
        return LAUNCHER_DIR / self.config_data.get("names_file", "pal_names.json")

    def memory_path(self) -> Path:
        return LAUNCHER_DIR / self.config_data.get("memory_file", "pal_memory.json")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=24, pady=(20, 10))

        # Not packed here -- only shown if a real logo image loads
        # successfully (see _maybe_load_logo). An empty placeholder box
        # otherwise just looked like a broken/missing icon next to the
        # title.
        self.logo_label = tk.Label(
            header, text="", bg=theme.BG,
            relief="flat", highlightthickness=0,
        )

        self.title_label = ttk.Label(header, text="PALVERSATION", style="Title.TLabel")
        self.title_label.pack(side="left", anchor="w")

        # Small, muted version tag next to the title -- not meant to draw
        # attention, just a quick reference for the player (and for us,
        # when someone reports a bug) to see at a glance which build
        # they're running, without digging through files or Task Manager.
        self.version_label = tk.Label(
            header, text=f"v{CURRENT_VERSION}", bg=theme.BG, fg=theme.TEXT_MUTED,
            font=(theme.FONT_FAMILY, 9),
        )
        self.version_label.pack(side="left", anchor="s", padx=(6, 0), pady=(0, 3))

        self._maybe_load_logo()

        status_area = ttk.Frame(header)
        status_area.pack(side="right", anchor="e")

        self.status_dot = tk.Label(status_area, text="\u25cf", font=(theme.FONT_FAMILY, 12), bg=theme.BG)
        self.status_dot.pack(side="left")
        self.status_label = ttk.Label(status_area, text="Stopped")
        self.status_label.pack(side="left", padx=(6, 14))

        self.start_stop_button = tk.Button(
            status_area, text="Start", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=14, pady=6, command=self._toggle_watcher,
        )
        self.start_stop_button.pack(side="left")

        # Hidden until an update check finds something newer than
        # CURRENT_VERSION (see _show_update_notice). Sits to the left of
        # the status area, since pack(side="right") stacks new widgets
        # inward from the edge already claimed by status_area.
        self.update_label = tk.Label(
            header, text="", bg=theme.BG, fg=theme.ACCENT,
            font=theme.FONT_BODY, cursor="hand2",
        )

        separator = tk.Frame(self, bg=theme.BORDER, height=1)
        separator.pack(fill="x", padx=24, pady=(10, 10))

    def _find_asset_dirs(self):
        """Yields the assets/ folder to check, in priority order: a real
        one next to the exe/launcher first (lets anyone override branding
        without rebuilding), then the copy bundled inside the exe itself
        (via build_exe.bat's --add-data), if this is a build that has
        one. Checking both is what lets a single .exe work completely on
        its own -- no separate assets folder needs to ship alongside it."""
        yield LAUNCHER_DIR / "assets"
        bundled_dir = get_bundled_dir()
        if bundled_dir:
            yield bundled_dir / "assets"

    def _maybe_set_window_icon(self):
        # Window/taskbar icon while the app is running (separate from the
        # header logo below, and from the .exe's own file icon, which is
        # set at build time via build_exe.bat's --icon flag instead).
        ico_path = None
        png_path = None
        for assets_dir in self._find_asset_dirs():
            if not assets_dir.exists():
                continue
            candidate = assets_dir / "icon.ico"
            if not candidate.exists():
                # Accept any .ico in this folder, not just one named
                # exactly "icon.ico" -- e.g. a hash-named file exported
                # from an icon generator site.
                candidate = next(assets_dir.glob("*.ico"), None)
            if candidate and candidate.exists():
                ico_path = candidate
                break
            candidate_png = assets_dir / "icon.png"
            if candidate_png.exists() and png_path is None:
                png_path = candidate_png

        try:
            if ico_path:
                self.iconbitmap(str(ico_path))
                return
        except Exception:
            pass  # .ico icons only work on Windows; fall through to PNG
        try:
            if png_path:
                img = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, img)
                self._window_icon_ref = img  # keep a reference, tkinter needs it
        except Exception:
            pass  # no icon set is fine, just keeps the default

    def _maybe_load_logo(self):
        # Developer-provided branding, not a user setting -- no app asks
        # the end user to pick its own logo. Looks for logo.png
        # specifically (a wider banner-style image next to the title,
        # distinct from the square icon.ico/icon.png used for the window
        # and taskbar).
        logo_path = None
        for assets_dir in self._find_asset_dirs():
            candidate = assets_dir / "logo.png"
            if candidate.exists():
                logo_path = candidate
                break

        if not logo_path:
            self.logo_label.pack_forget()
            self.logo_label.configure(image="", text="")
            self.logo_label.image = None
            return
        try:
            img = tk.PhotoImage(file=str(logo_path))
            # tk.PhotoImage only shrinks by whole-number factors
            # (subsample), so this won't land on an exact pixel size, but
            # it reliably keeps the image within the box and preserves
            # its aspect ratio (same factor on both axes).
            factor = max(
                1,
                math.ceil(img.width() / MAX_LOGO_WIDTH),
                math.ceil(img.height() / MAX_LOGO_HEIGHT),
            )
            if factor > 1:
                img = img.subsample(factor, factor)
            self.logo_label.configure(image=img, text="")
            self.logo_label.image = img  # keep a reference, tkinter needs it
            self.logo_label.pack(side="left", padx=(0, 16), before=self.title_label)
        except Exception:
            # Bad/missing path: no logo shown, not a broken empty box.
            self.logo_label.pack_forget()

    def _build_body(self):
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        sidebar = tk.Frame(body, bg=theme.PANEL_BG, width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.content_area = ttk.Frame(body)
        self.content_area.pack(side="left", fill="both", expand=True, padx=(16, 0))

        from gui.tab_general import GeneralTab
        from gui.tab_pals import PalsTab
        from gui.tab_events import EventsTab
        from gui.tab_directories import DirectoriesTab
        from gui.tab_console import ConsoleTab

        tab_specs = [
            ("general", "General", GeneralTab),
            ("pals", "Pals", PalsTab),
            ("events", "Events", EventsTab),
            ("folders", "Folders", DirectoriesTab),
            ("console", "Console", ConsoleTab),
        ]

        for tab_id, label, tab_class in tab_specs:
            frame = tab_class(self.content_area, self)
            self._tabs[tab_id] = frame

            nav_button = tk.Button(
                sidebar, text=label, anchor="w", relief="flat", bd=0, cursor="hand2",
                font=theme.FONT_NAV, padx=16, pady=12,
                command=lambda t=tab_id: self.show_tab(t),
            )
            nav_button.pack(fill="x")
            self._nav_buttons[tab_id] = nav_button

        self.show_tab("general")

    def show_tab(self, tab_id: str):
        for tid, frame in self._tabs.items():
            frame.pack_forget()
        for tid, button in self._nav_buttons.items():
            selected = (tid == tab_id)
            button.configure(
                bg=theme.ACCENT if selected else theme.PANEL_BG,
                fg=theme.TEXT_ON_ACCENT if selected else theme.TEXT,
                activebackground=theme.ACCENT_HOVER if selected else theme.PANEL_BG_ALT,
                activeforeground=theme.TEXT_ON_ACCENT if selected else theme.TEXT,
            )
        self._tabs[tab_id].pack(fill="both", expand=True)
        self._active_tab_id = tab_id

    # ------------------------------------------------------------------
    # Watcher lifecycle
    # ------------------------------------------------------------------

    def _try_start_watcher(self, silent: bool = False):
        mod_folder = self.config_data.get("mod_folder", "").strip()
        if not mod_folder or not Path(mod_folder).is_dir():
            message = (
                "The mod folder isn't set yet (or the folder doesn't exist).\n\n"
                "Go to the Folders tab and point it at your Palversation mod "
                "installation -- the folder that contains Scripts\\main.lua. "
                "This is required so the in-game mod knows where to find its "
                "own settings; without it, the connection can't start."
            )
            if not silent:
                messagebox.showwarning("Palversation - Mod folder missing", message)
            return message

        error = self.watcher.start()
        if error and not silent:
            messagebox.showwarning("Palversation", f"Could not start: {error}")
        return error

    def _toggle_watcher(self):
        if self.watcher.is_running():
            self.watcher.stop()
        else:
            self._try_start_watcher(silent=False)

    def _poll_watcher_status(self):
        running = self.watcher.is_running()
        self.status_dot.configure(fg=("#4cc27a" if running else "#e05a5a"))
        self.status_label.configure(text=("Running" if running else "Stopped"))
        self.start_stop_button.configure(text=("Stop" if running else "Start"))
        self.after(500, self._poll_watcher_status)

    def _poll_log_queue(self):
        console_tab = self._tabs.get("console")
        try:
            while True:
                line = self.watcher.log_queue.get_nowait()
                if console_tab is not None:
                    console_tab.append_line(line)
        except Exception:
            pass  # queue.Empty, nothing new right now
        self.after(200, self._poll_log_queue)

    def _on_close(self):
        self.watcher.stop()
        self.destroy()

    # ------------------------------------------------------------------
    # Update check -- see core/update_check.py for the actual GitHub
    # call. This never downloads or replaces anything by itself: it just
    # notices a newer release exists and shows a clickable link to it.
    # The network call is blocking, so it runs in a background thread;
    # the result comes back through a queue and only touches the GUI
    # from the main thread via self.after, same pattern as the watcher's
    # own log_queue above.
    # ------------------------------------------------------------------

    def _start_update_check(self):
        self._update_check_queue = queue.Queue()
        threading.Thread(target=self._update_check_worker, daemon=True).start()
        self.after(500, self._poll_update_check)

    def _update_check_worker(self):
        result = fetch_latest_release()  # None on any failure -- see its own docstring
        self._update_check_queue.put(result)

    def _poll_update_check(self):
        try:
            result = self._update_check_queue.get_nowait()
        except queue.Empty:
            self.after(500, self._poll_update_check)
            return
        # One-shot check: whether or not we found something, we're done
        # polling here -- no need to reschedule again after this.
        if result and is_newer_version(result["version"], CURRENT_VERSION):
            self._show_update_notice(result["version"], result["url"])

    def _show_update_notice(self, latest_version: str, release_url: str):
        self.update_label.configure(text=f"Update available: {latest_version}")
        self.update_label.bind("<Button-1>", lambda event: webbrowser.open(release_url))
        self.update_label.pack(side="right", padx=(0, 14))

    # ------------------------------------------------------------------
    # Saving -- every tab calls this after updating self.config_data /
    # self.mod_config / self.prompts in place. Restarting here means
    # settings changes take effect right away, no manual restart needed.
    # ------------------------------------------------------------------

    def save_all(self):
        try:
            save_launcher_config(self.config_data)
            save_mod_config(self.mod_config_path(), self.mod_config)
            save_prompts(self.prompts_path(), self.prompts)
            save_memories(self.memory_path(), self.memories)
        except Exception as e:
            messagebox.showerror("Palversation", f"Could not save settings: {e}")
            return
        if "pals" in self._tabs:
            self._tabs["pals"]._refresh_pal_list()
        self._maybe_load_logo()

        was_running = self.watcher.is_running()
        if was_running:
            self.watcher.restart()
        else:
            self._try_start_watcher(silent=True)


def main():
    app = PalversationApp()
    app.mainloop()


if __name__ == "__main__":
    main()