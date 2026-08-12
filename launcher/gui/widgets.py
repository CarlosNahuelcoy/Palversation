"""
Small custom widgets styled to match the game's own menus: a two-segment
OFF/ON toggle (like the "Multiplayer OFF/ON" control), and a "< value >"
cycle selector for picking from a fixed list of options (like "Difficulty
< Normal >" or "Screen Mode < Full Screen >").

Plain tk.Button (not ttk) is used here on purpose: ttk widgets on Windows
mostly ignore custom colors unless you fight the active theme, while a
plain tk.Button always respects bg/fg directly, which is what we need for
this precise a look.
"""

import tkinter as tk
from tkinter import ttk

from gui import theme


class ToggleSwitch(ttk.Frame):
    def __init__(self, parent, initial: bool = True, on_change=None, **kwargs):
        super().__init__(parent, style="Panel.TFrame", **kwargs)
        self.value = bool(initial)
        self.on_change = on_change

        self.off_button = tk.Button(
            self, text="OFF", relief="flat", bd=0, cursor="hand2",
            font=theme.FONT_BODY, padx=14, pady=6,
            command=lambda: self._set(False),
        )
        self.on_button = tk.Button(
            self, text="ON", relief="flat", bd=0, cursor="hand2",
            font=theme.FONT_BODY, padx=14, pady=6,
            command=lambda: self._set(True),
        )
        self.off_button.pack(side="left")
        self.on_button.pack(side="left")
        self._render()

    def _set(self, value: bool):
        self.value = value
        self._render()
        if self.on_change:
            self.on_change(self.value)

    def get(self) -> bool:
        return self.value

    def set(self, value: bool):
        self.value = bool(value)
        self._render()

    def _render(self):
        if self.value:
            self.on_button.configure(bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT)
            self.off_button.configure(bg=theme.PANEL_BG_ALT, fg=theme.TEXT_MUTED)
        else:
            self.off_button.configure(bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT)
            self.on_button.configure(bg=theme.PANEL_BG_ALT, fg=theme.TEXT_MUTED)


class CycleSelector(ttk.Frame):
    """options: list of (value, label) tuples."""

    def __init__(self, parent, options, initial_index: int = 0, on_change=None, width=18, **kwargs):
        super().__init__(parent, style="Panel.TFrame", **kwargs)
        self.options = list(options)
        self.index = initial_index if 0 <= initial_index < len(self.options) else 0
        self.on_change = on_change

        left_arrow = tk.Button(
            self, text="\u2039", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            command=self._prev, padx=8,
        )
        right_arrow = tk.Button(
            self, text="\u203a", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            command=self._next, padx=8,
        )
        self.value_label = tk.Label(
            self, text="", bg=theme.PANEL_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=width, anchor="center",
        )
        left_arrow.pack(side="left")
        self.value_label.pack(side="left", fill="x", expand=True)
        right_arrow.pack(side="left")
        self._render()

    def _prev(self):
        self.index = (self.index - 1) % len(self.options)
        self._render()
        self._fire()

    def _next(self):
        self.index = (self.index + 1) % len(self.options)
        self._render()
        self._fire()

    def _fire(self):
        if self.on_change:
            self.on_change(self.current_value())

    def _render(self):
        if self.options:
            _, label = self.options[self.index]
            self.value_label.configure(text=label)

    def current_value(self):
        if not self.options:
            return None
        value, _ = self.options[self.index]
        return value

    def set_value(self, value):
        for i, (v, _) in enumerate(self.options):
            if v == value:
                self.index = i
                self._render()
                return


class Dropdown(ttk.Frame):
    """Click-to-open dropdown list, for picking one of several options in
    one click instead of cycling through them one by one with CycleSelector.
    options: list of (value, label) tuples."""

    def __init__(self, parent, options, initial_index: int = 0, on_change=None, width=22, **kwargs):
        super().__init__(parent, style="Panel.TFrame", **kwargs)
        self.options = list(options)
        self.index = initial_index if 0 <= initial_index < len(self.options) else 0
        self.on_change = on_change
        self.width = width
        self._popup = None

        self.button = tk.Button(
            self, relief="flat", bd=0, cursor="hand2", anchor="w",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            padx=10, pady=6, width=width,
            command=self._toggle_popup,
        )
        self.button.pack(fill="x")
        self._render()

    def _render(self):
        if self.options:
            _, label = self.options[self.index]
            self.button.configure(text=f"{label}   \u25be")

    def _toggle_popup(self):
        if self._popup is not None:
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self):
        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.configure(bg=theme.BORDER)
        self._popup.attributes("-topmost", True)

        x = self.button.winfo_rootx()
        y = self.button.winfo_rooty() + self.button.winfo_height()
        self._popup.geometry(f"+{x}+{y}")

        inner = tk.Frame(self._popup, bg=theme.PANEL_BG_ALT)
        inner.pack(padx=1, pady=1)

        for i, (_value, label) in enumerate(self.options):
            selected = (i == self.index)
            row = tk.Button(
                inner, text=label, anchor="w", relief="flat", bd=0, cursor="hand2",
                bg=(theme.ACCENT if selected else theme.PANEL_BG_ALT),
                fg=(theme.TEXT_ON_ACCENT if selected else theme.TEXT),
                activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
                font=theme.FONT_BODY, padx=12, pady=6, width=self.width,
                command=lambda idx=i: self._select(idx),
            )
            row.pack(fill="x")

        self._popup.bind("<FocusOut>", lambda e: self._close_popup())
        self._popup.focus_set()

    def _close_popup(self):
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None

    def _select(self, index: int):
        self.index = index
        self._render()
        self._close_popup()
        if self.on_change:
            self.on_change(self.current_value())

    def current_value(self):
        if not self.options:
            return None
        value, _ = self.options[self.index]
        return value

    def set_value(self, value):
        for i, (v, _) in enumerate(self.options):
            if v == value:
                self.index = i
                self._render()
                return


class ScrollableFrame(ttk.Frame):
    """A frame whose content scrolls vertically when it's taller than the
    visible area (mouse wheel or the scrollbar). Put your widgets inside
    `.inner` instead of directly inside this frame."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="TFrame", **kwargs)
        self.canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="TFrame")

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._window, width=e.width))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="left", fill="y")

        self.canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
