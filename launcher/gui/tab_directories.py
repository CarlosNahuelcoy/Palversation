"""
Directories tab: pick the mod folder (where config.txt will be written)
and the shared IPC folder (used by both config.json's watch_folder and
config.txt's ipc_dir). Styled with the game-menu theme.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog

from core.launcher_runtime import default_watch_folder
from gui import theme


class DirectoriesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app

        pad = {"pady": 8}

        ttk.Label(self, text="Mod Folder", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", **pad
        )
        ttk.Label(
            self,
            text=(
                "The Palversation folder itself, inside your UE4SS Mods "
                "folder (...\\UE4SS\\Mods\\Palversation) -- not the Scripts "
                "subfolder inside it. If you point here at Scripts by "
                "mistake, it's corrected automatically."
            ),
            style="Muted.TLabel", justify="left", wraplength=520,
        ).grid(row=1, column=0, sticky="w")
        self.mod_folder_var = tk.StringVar(value=app.config_data.get("mod_folder", ""))
        self._make_path_row(row=0, rowspan=2, var=self.mod_folder_var, browse_cmd=self._browse_mod_folder)

        ttk.Label(self, text="Shared IPC Folder", style="Section.TLabel").grid(
            row=2, column=0, sticky="w", pady=(20, 0)
        )
        ttk.Label(self, text="(optional -- defaults to a folder next to the launcher)", style="Muted.TLabel").grid(
            row=3, column=0, sticky="w"
        )
        # Pre-filled with the same default the watcher itself falls back
        # to when this is left blank, so it's visible what will actually
        # be used instead of looking like a required, empty field.
        saved_ipc = app.config_data.get("watch_folder", "").strip()
        self.ipc_folder_var = tk.StringVar(value=saved_ipc or str(default_watch_folder()))
        self._make_path_row(row=2, rowspan=2, var=self.ipc_folder_var, browse_cmd=self._browse_ipc_folder, pady=(20, 8))

        ttk.Label(
            self,
            text=(
                "Both files (config.json here, config.txt in the mod folder)\n"
                "will be written with this same IPC folder path, so the mod\n"
                "and the launcher agree on where to exchange files. It's\n"
                "created automatically if it doesn't exist yet."
            ),
            style="Muted.TLabel", justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 16))

        self.status_label = ttk.Label(self, text="", foreground="#4cc27a")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky="w")

        save_button = tk.Button(
            self, text="Save", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=18, pady=8, command=self.save,
        )
        save_button.grid(row=6, column=1, sticky="e", pady=(14, 0))

        self.columnconfigure(1, weight=1)

    def _make_path_row(self, row, rowspan, var, browse_cmd, pady=(0, 8)):
        entry = tk.Entry(
            self, textvariable=var, width=46,
            bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
        )
        entry.grid(row=row, column=1, sticky="ew", pady=pady, ipady=4)
        browse_button = tk.Button(
            self, text="Browse...", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            padx=12, pady=4, command=browse_cmd,
        )
        browse_button.grid(row=row, column=2, padx=(8, 0), pady=pady)

    def _browse_mod_folder(self):
        folder = filedialog.askdirectory(title="Select the Palversation mod folder")
        if folder:
            self.mod_folder_var.set(folder)

    def _browse_ipc_folder(self):
        folder = filedialog.askdirectory(title="Select (or create) the shared IPC folder")
        if folder:
            self.ipc_folder_var.set(folder)

    def refresh_from_config(self):
        """
        Called by the app (see app._try_start_watcher) when mod_folder
        gets auto-corrected in the background -- e.g. the player had
        pointed at the Scripts subfolder, and it silently got fixed to
        its parent. Without this, the Entry would keep showing the old
        (wrong) path until the player happened to leave and come back to
        this tab, which looks like the fix didn't actually happen.
        """
        self.mod_folder_var.set(self.app.config_data.get("mod_folder", ""))

    def save(self):
        mod_folder = self.mod_folder_var.get().strip()
        ipc_folder = self.ipc_folder_var.get().strip()

        if mod_folder and not os.path.isabs(mod_folder):
            self.status_label.configure(
                text="Mod folder must be an absolute path (use Browse...), not saved.",
                foreground="#e05a5a",
            )
            return
        if ipc_folder and not os.path.isabs(ipc_folder):
            self.status_label.configure(
                text="IPC folder must be an absolute path (use Browse...), not saved.",
                foreground="#e05a5a",
            )
            return

        self.app.config_data["mod_folder"] = mod_folder
        self.app.config_data["watch_folder"] = ipc_folder

        self.app.mod_config["ipc_dir"] = ipc_folder
        if ipc_folder and not ipc_folder.endswith(("\\", "/")):
            self.app.mod_config["ipc_dir"] += "\\"

        self.app.save_all()
        if not mod_folder:
            self.status_label.configure(
                text="Saved, but the mod folder is still empty -- the connection won't start until it's set.",
                foreground="#e05a5a",
            )
        else:
            self.status_label.configure(
                text=f"Saved. config.txt will be written to: {mod_folder}\\config.txt",
                foreground="#4cc27a",
            )