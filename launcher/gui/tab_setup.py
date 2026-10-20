"""
Setup tab: shows what the launcher found and installed on its own
(Palworld, UE4SS, the Palversation mod, the AI provider), with a fix
button for each thing it can't do by itself. Replaces the old Folders tab
-- no paths need to be typed or paired anymore.
"""

import os
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from core.game_locator import normalize_palworld_dir
from core.install_check import CheckStatus, UE4SS_DOWNLOAD_URL
from core.paths import get_data_dir, import_user_data, USER_DATA_FILES
from gui import theme

_STATUS_STYLE = {
    CheckStatus.OK: ("✔", "#4cc27a"),
    CheckStatus.MISSING: ("✖", "#e05a5a"),
    CheckStatus.UNKNOWN: ("•", theme.TEXT_MUTED),
}


class SetupTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app

        ttk.Label(self, text="Setup", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            self,
            text=(
                "Palversation finds Palworld and installs the in-game mod by itself. "
                "If something below is red, follow its hint, then press Re-check."
            ),
            style="Muted.TLabel", justify="left", wraplength=560,
        ).pack(anchor="w", pady=(2, 12))

        self.rows_frame = ttk.Frame(self)
        self.rows_frame.pack(fill="x")

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(16, 0))
        self._button(buttons, "Re-check", self._recheck, primary=True).pack(side="left")
        self._button(buttons, "Choose Palworld folder...", self._choose_palworld).pack(side="left", padx=(8, 0))
        self.ue4ss_button = self._button(buttons, "Get UE4SS", lambda: webbrowser.open(UE4SS_DOWNLOAD_URL))
        self._button(buttons, "Open data folder", self._open_data_folder).pack(side="right")
        self._button(buttons, "Import old data...", self._import_old_data).pack(side="right", padx=(0, 8))

        self.ue4ss_hint = ttk.Label(
            self,
            text=(
                "UE4SS: download the zip from the page that opens, and extract it into\n"
                "Palworld\\Pal\\Binaries\\Win64 (or install \"UE4SS Experimental (Palworld)\"\n"
                "from the in-game mod manager / Workshop)."
            ),
            style="Muted.TLabel", justify="left",
        )

        self.status_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.status_label.pack(anchor="w", pady=(12, 0))

    def _button(self, parent, text, command, primary=False):
        return tk.Button(
            parent, text=text, relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT if primary else theme.PANEL_BG,
            fg=theme.TEXT_ON_ACCENT if primary else theme.TEXT,
            activebackground=theme.ACCENT_HOVER if primary else theme.PANEL_BG_ALT,
            activeforeground=theme.TEXT_ON_ACCENT if primary else theme.TEXT,
            font=theme.FONT_BODY, padx=12, pady=6, command=command,
        )

    def show_report(self, report):
        for child in self.rows_frame.winfo_children():
            child.destroy()
        for row, (label, result) in enumerate(report.checks):
            icon, color = _STATUS_STYLE[result.status]
            tk.Label(
                self.rows_frame, text=icon, bg=theme.BG, fg=color, font=(theme.FONT_FAMILY, 12),
            ).grid(row=row * 2, column=0, rowspan=2, sticky="nw", padx=(0, 10), pady=(6, 0))
            ttk.Label(self.rows_frame, text=label, style="Section.TLabel").grid(
                row=row * 2, column=1, sticky="w", pady=(6, 0),
            )
            ttk.Label(
                self.rows_frame, text=result.message, style="Muted.TLabel", justify="left", wraplength=540,
            ).grid(row=row * 2 + 1, column=1, sticky="w")

        ue4ss_missing = report.palworld_dir is not None and report.ue4ss is None
        if ue4ss_missing:
            self.ue4ss_button.pack(side="left", padx=(8, 0))
            self.ue4ss_hint.pack(anchor="w", pady=(10, 0), before=self.status_label)
        else:
            self.ue4ss_button.pack_forget()
            self.ue4ss_hint.pack_forget()

    def _recheck(self):
        self.app.run_setup(show_errors=False)
        self.status_label.configure(text="Checked just now.")

    def _choose_palworld(self):
        folder = filedialog.askdirectory(title="Select your Palworld folder (the one with Palworld.exe)")
        if not folder:
            return
        root = normalize_palworld_dir(Path(folder))
        if root is None:
            self.status_label.configure(text=f"That folder isn't a Palworld install: {folder}")
            return
        self.app.config_data["palworld_dir"] = str(root)
        self.app.save_all()
        self._recheck()

    def _import_old_data(self):
        """For players who extracted v1.1+ into a different folder than
        their old launcher: brings their Pals' memories and settings over."""
        folder = filedialog.askdirectory(title="Select your OLD Palversation launcher folder (the one with Palversation.exe)")
        if not folder:
            return
        found = [name for name in USER_DATA_FILES if (Path(folder) / name).is_file()]
        if not found:
            messagebox.showinfo("Palversation", "No saved Palversation data was found in that folder.")
            return
        if not messagebox.askyesno(
            "Palversation - Import old data",
            "Found: " + ", ".join(found) + "\n\nThis replaces the current settings and Pal "
            "memories with the ones from that folder. The launcher restarts afterwards. Continue?",
        ):
            return
        import_user_data(Path(folder), overwrite=True)
        self.app.restart_app()

    def _open_data_folder(self):
        os.startfile(str(get_data_dir()))
