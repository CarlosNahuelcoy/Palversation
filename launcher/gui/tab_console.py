"""
Console tab: live output from the background watcher thread. The "Show
live output" switch only controls whether new lines get rendered here --
the watcher itself keeps running either way, this is purely a display
option for players who don't want to look at it.
"""

import tkinter as tk
from tkinter import ttk

from gui import theme
from gui.widgets import ToggleSwitch

MAX_LINES = 500  # trim old lines so this can't grow forever in a long session


class ConsoleTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app
        self._line_count = 0

        top_row = ttk.Frame(self)
        top_row.pack(fill="x", pady=(0, 10))

        ttk.Label(top_row, text="Show live output").pack(side="left")
        self.visible_switch = ToggleSwitch(top_row, initial=True)
        self.visible_switch.pack(side="left", padx=(10, 0))

        tk.Button(
            top_row, text="Clear", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            padx=12, pady=4, command=self.clear,
        ).pack(side="right")

        text_frame = tk.Frame(self, bg=theme.PANEL_BG)
        text_frame.pack(fill="both", expand=True)
        self.text = tk.Text(
            text_frame, wrap="word", state="disabled",
            bg=theme.PANEL_BG, fg=theme.TEXT,
            relief="flat", highlightthickness=1, highlightbackground=theme.BORDER,
            padx=8, pady=8, font=("Consolas", 10),
        )
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

    def append_line(self, line: str):
        if not self.visible_switch.get():
            return
        self.text.configure(state="normal")
        self.text.insert("end", line + "\n")
        self._line_count += 1
        if self._line_count > MAX_LINES:
            self.text.delete("1.0", "2.0")
            self._line_count -= 1
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._line_count = 0
