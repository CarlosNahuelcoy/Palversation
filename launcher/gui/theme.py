"""
Color palette and ttk.Style setup, styled after Palworld's own in-game
menus (dark navy background, flat rectangular buttons, blue accent for
selected/ON states).
"""

from tkinter import ttk

BG = "#101d29"           # main window background
PANEL_BG = "#1a2b3a"      # row / panel background
PANEL_BG_ALT = "#16242f"  # slightly darker alt panel
ACCENT = "#2f8fdb"        # selected / ON / primary action
ACCENT_HOVER = "#4aa3e8"
BORDER = "#2c4356"

TEXT = "#ffffff"
TEXT_MUTED = "#93a9bd"
TEXT_ON_ACCENT = "#ffffff"

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_SECTION = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_NAV = (FONT_FAMILY, 11)


def configure_style(root) -> ttk.Style:
    style = ttk.Style(root)
    # "clam" is the only built-in theme that reliably honors custom colors
    # on every platform; the native Windows themes ignore most of this.
    style.theme_use("clam")

    root.configure(bg=BG)

    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL_BG)

    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_BODY)
    style.configure("Muted.TLabel", background=BG, foreground=TEXT_MUTED, font=FONT_BODY)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
    style.configure("Section.TLabel", background=BG, foreground=TEXT, font=FONT_SECTION)
    style.configure("Panel.TLabel", background=PANEL_BG, foreground=TEXT, font=FONT_BODY)

    # Flat accent button (primary actions: Save, Test connection, Browse).
    style.configure(
        "Accent.TButton",
        background=ACCENT, foreground=TEXT_ON_ACCENT,
        font=FONT_BODY, borderwidth=0, focusthickness=0, padding=(14, 8),
    )
    style.map(
        "Accent.TButton",
        background=[("active", ACCENT_HOVER), ("disabled", BORDER)],
    )

    # Secondary flat button (less prominent actions).
    style.configure(
        "Secondary.TButton",
        background=PANEL_BG, foreground=TEXT,
        font=FONT_BODY, borderwidth=1, relief="flat", padding=(12, 6),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", PANEL_BG_ALT)],
        bordercolor=[("!disabled", BORDER)],
    )

    # Sidebar navigation buttons (Graphics / Sounds / ... look-alike).
    style.configure(
        "Nav.TButton",
        background=PANEL_BG, foreground=TEXT,
        font=FONT_NAV, borderwidth=0, anchor="w", padding=(16, 12),
    )
    style.map("Nav.TButton", background=[("active", PANEL_BG_ALT)])

    style.configure(
        "NavSelected.TButton",
        background=ACCENT, foreground=TEXT_ON_ACCENT,
        font=FONT_NAV, borderwidth=0, anchor="w", padding=(16, 12),
    )
    style.map("NavSelected.TButton", background=[("active", ACCENT_HOVER)])

    style.configure(
        "TEntry",
        fieldbackground=PANEL_BG, foreground=TEXT, insertcolor=TEXT,
        borderwidth=1, bordercolor=BORDER, padding=6,
    )
    style.configure(
        "TCombobox",
        fieldbackground=PANEL_BG, foreground=TEXT, background=PANEL_BG,
        arrowcolor=TEXT, borderwidth=1, padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", PANEL_BG)],
        foreground=[("readonly", TEXT)],
    )

    style.configure("TCheckbutton", background=BG, foreground=TEXT, font=FONT_BODY)
    style.map("TCheckbutton", background=[("active", BG)])

    style.configure("TScrollbar", background=PANEL_BG, troughcolor=BG, bordercolor=BG)

    return style
