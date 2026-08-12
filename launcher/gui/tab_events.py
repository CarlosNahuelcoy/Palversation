"""
Events tab: chat/gift commands, on/off switches, and timing/probability
settings for each spontaneous comment type. Writes to the mod's
config.txt (via app.mod_config and app.save_all()), not config.json --
these settings are read by Lua. Scrollable, with the Save button pinned
in a footer so it's always visible regardless of window size.
"""

import tkinter as tk
from tkinter import ttk

from gui import theme
from gui.widgets import ToggleSwitch, ScrollableFrame


class EventsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app
        mc = app.mod_config

        self.toggle_vars = {}
        self.entry_vars = {}
        self.command_vars = {}

        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x", pady=(10, 0))
        self.status_label = ttk.Label(footer, text="", foreground="#e05a5a")
        self.status_label.pack(side="left")
        save_button = tk.Button(
            footer, text="Save", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=18, pady=8, command=self.save,
        )
        save_button.pack(side="right")

        scroll = ScrollableFrame(self)
        scroll.pack(side="top", fill="both", expand=True)
        content = scroll.inner

        row = 0
        ttk.Label(content, text="Commands", style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        row += 1

        command_fields = [
            ("chat_prefix", "Chat command"),
            ("gift_command", "Gift command"),
            ("vision_command", "Vision command"),
        ]
        for key, label in command_fields:
            ttk.Label(content, text=label).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=mc.get(key, ""))
            entry = tk.Entry(
                content, textvariable=var, width=14,
                bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
                relief="flat", highlightthickness=1,
                highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
            )
            entry.grid(row=row, column=1, sticky="w", pady=3, ipady=3)
            self.command_vars[key] = var
            row += 1

        row += 1
        ttk.Label(content, text="Comment Types", style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(14, 8)
        )
        row += 1

        toggles = [
            ("enable_deploy_recall_comments", "Deploy / recall greetings"),
            ("enable_hunger_comments", "Hunger comments"),
            ("enable_temperature_comments", "Temperature comments"),
            ("enable_ride_comments", "Riding comments"),
            ("enable_combat_comments", "Combat comments"),
            ("enable_idle_comments", "Idle chatter"),
            ("enable_gift_system", "Gift system (command + ambient)"),
        ]
        for key, label in toggles:
            ttk.Label(content, text=label).grid(row=row, column=0, sticky="w", pady=4)
            toggle = ToggleSwitch(content, initial=(mc.get(key, "true").lower() == "true"))
            toggle.grid(row=row, column=1, sticky="w", pady=4)
            self.toggle_vars[key] = toggle
            row += 1

        row += 1
        ttk.Label(content, text="Timing", style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(14, 8)
        )
        row += 1

        numeric_fields = [
            ("hunger_threshold", "Hunger threshold (0-1)"),
            ("idle_min_seconds", "Idle chatter: min seconds"),
            ("idle_max_seconds", "Idle chatter: max seconds"),
            ("ambient_gift_min_seconds", "Ambient gift: min seconds"),
            ("ambient_gift_max_seconds", "Ambient gift: max seconds"),
            ("ambient_gift_chance", "Ambient gift: chance (0-1)"),
            ("response_timeout_seconds", "Response timeout (seconds)"),
        ]
        for key, label in numeric_fields:
            ttk.Label(content, text=label).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=mc.get(key, ""))
            entry = tk.Entry(
                content, textvariable=var, width=10,
                bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
                relief="flat", highlightthickness=1,
                highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
            )
            entry.grid(row=row, column=1, sticky="w", pady=3, ipady=3)
            self.entry_vars[key] = var
            row += 1

        # A little breathing room at the bottom of the scroll area.
        ttk.Frame(content, height=10).grid(row=row, column=0)

    def save(self):
        for key, var in self.entry_vars.items():
            value = var.get().strip()
            try:
                float(value)
            except ValueError:
                self.status_label.configure(text=f"'{key}' must be a number, not saved.", foreground="#e05a5a")
                return
        for key, var in self.command_vars.items():
            if not var.get().strip():
                self.status_label.configure(text=f"'{key}' can't be empty, not saved.", foreground="#e05a5a")
                return

        for key, toggle in self.toggle_vars.items():
            self.app.mod_config[key] = "true" if toggle.get() else "false"
        for key, var in self.entry_vars.items():
            self.app.mod_config[key] = var.get().strip()
        for key, var in self.command_vars.items():
            self.app.mod_config[key] = var.get().strip()

        self.app.save_all()
        self.status_label.configure(text="Saved.", foreground="#4cc27a")
