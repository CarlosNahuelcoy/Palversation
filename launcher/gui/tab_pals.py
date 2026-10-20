"""
Pals tab: list of known Pals (from history + custom prompts files, shown
with a friendly display name instead of the raw stable key), a per-Pal
personality editor, a long-term memory editor, and an editable view of
that Pal's conversation history (edit specific lines and Save, or wipe it
entirely with Clear). Styled with the game-menu theme. Scrollable, since
three editable sections plus their buttons don't reliably fit in a
smaller window.
"""

import time
import tkinter as tk
from tkinter import ttk, messagebox

from core.pal_prompts import load_prompts, save_prompts, get_prompt, set_prompt
from core.pal_memory import load_memories, get_memory, set_memory, save_memories
from core.history_store import load_history, get_turns, save_history
from core.pal_names import load_names
from gui import theme
from gui.widgets import ScrollableFrame

LARGE_FONT = (theme.FONT_FAMILY, 12)
# How often the tab checks for new conversation written by the background
# connection.
AUTO_REFRESH_MS = 1500


class PalsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app
        self.current_pal_key = None
        self._current_turns_snapshot = []

        left = tk.Frame(self, bg=theme.PANEL_BG, width=220)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ttk.Label(left, text="Known Pals", style="Panel.TLabel").pack(
            anchor="w", padx=12, pady=(12, 6)
        )
        self.pal_listbox = tk.Listbox(
            left, exportselection=False, relief="flat", bd=0,
            bg=theme.PANEL_BG_ALT, fg=theme.TEXT,
            selectbackground=theme.ACCENT, selectforeground=theme.TEXT_ON_ACCENT,
            highlightthickness=0, activestyle="none",
            font=LARGE_FONT,
        )
        self.pal_listbox.pack(fill="both", expand=True, padx=12)
        self.pal_listbox.bind("<<ListboxSelect>>", self._on_select)

        tk.Button(
            left, text="Refresh List", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG_ALT, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.BORDER, activeforeground=theme.TEXT,
            command=self._refresh_pal_list,
        ).pack(fill="x", padx=12, pady=12)

        scroll = ScrollableFrame(self)
        scroll.pack(side="left", fill="both", expand=True, padx=(16, 0))
        right = scroll.inner

        ttk.Label(right, text="Custom Personality", style="Section.TLabel").pack(anchor="w")
        self.prompt_text = tk.Text(
            right, height=6, wrap="word",
            bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
            padx=8, pady=8, font=LARGE_FONT,
        )
        self.prompt_text.pack(fill="x", pady=(6, 6))

        button_row = ttk.Frame(right)
        button_row.pack(fill="x", pady=(0, 6))
        tk.Button(
            button_row, text="Save Personality", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=14, pady=6, command=self._save_prompt,
        ).pack(side="left")
        self.prompt_status_label = ttk.Label(button_row, text="")
        self.prompt_status_label.pack(side="left", padx=(10, 0))

        ttk.Label(right, text="Long-Term Memory", style="Section.TLabel").pack(
            anchor="w", pady=(16, 0)
        )
        ttk.Label(
            right,
            text="A running summary the Pal keeps of your shared history, updated automatically as older conversation falls out of its recent memory.",
            style="Muted.TLabel", wraplength=520, justify="left",
        ).pack(anchor="w", pady=(2, 6))
        self.memory_text = tk.Text(
            right, height=4, wrap="word",
            bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
            padx=8, pady=8, font=LARGE_FONT,
        )
        self.memory_text.pack(fill="x", pady=(0, 6))

        memory_button_row = ttk.Frame(right)
        memory_button_row.pack(fill="x", pady=(0, 6))
        tk.Button(
            memory_button_row, text="Save Memory", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=14, pady=6, command=self._save_memory,
        ).pack(side="left")
        tk.Button(
            memory_button_row, text="Clear Memory", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            padx=14, pady=6, command=self._clear_memory,
        ).pack(side="left", padx=(10, 0))
        self.memory_status_label = ttk.Label(memory_button_row, text="")
        self.memory_status_label.pack(side="left", padx=(10, 0))

        ttk.Label(right, text="Conversation History", style="Section.TLabel").pack(
            anchor="w", pady=(16, 0)
        )
        ttk.Label(
            right,
            text="Edit or delete specific lines and Save, or wipe the whole thing with Clear. Format: 'You: ...' / 'Pal: ...', one exchange per paragraph.",
            style="Muted.TLabel", wraplength=520, justify="left",
        ).pack(anchor="w", pady=(2, 6))
        history_frame = tk.Frame(right, bg=theme.PANEL_BG)
        history_frame.pack(fill="x", pady=(0, 6))
        self.history_text = tk.Text(
            history_frame, wrap="word", height=10,
            bg=theme.PANEL_BG, fg=theme.TEXT,
            relief="flat", highlightthickness=1, highlightbackground=theme.BORDER,
            padx=8, pady=8, font=LARGE_FONT,
        )
        history_scroll = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_text.yview)
        self.history_text.configure(yscrollcommand=history_scroll.set)
        self.history_text.pack(side="left", fill="both", expand=True)
        history_scroll.pack(side="left", fill="y")

        history_button_row = ttk.Frame(right)
        history_button_row.pack(fill="x", pady=(0, 16))
        tk.Button(
            history_button_row, text="Save History", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=14, pady=6, command=self._save_history,
        ).pack(side="left")
        tk.Button(
            history_button_row, text="Clear History", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            padx=14, pady=6, command=self._clear_history,
        ).pack(side="left", padx=(10, 0))
        self.history_status_label = ttk.Label(history_button_row, text="")
        self.history_status_label.pack(side="left", padx=(10, 0))

        self.pal_keys = []
        self._watched_mtimes = None
        self._refresh_pal_list()
        self.after(AUTO_REFRESH_MS, self._auto_refresh)

    # ------------------------------------------------------------------
    # Always work on what's on disk: the background connection keeps
    # writing history, names and memories while this tab is open, so any
    # copy held here goes stale within one message.
    # ------------------------------------------------------------------

    def _data_paths(self):
        return (self.app.history_path(), self.app.prompts_path(), self.app.names_path(), self.app.memory_path())

    def _reload_from_disk(self):
        self.app.history = load_history(self.app.history_path())
        self.app.prompts = load_prompts(self.app.prompts_path())
        self.app.names = load_names(self.app.names_path())
        self.app.memories = load_memories(self.app.memory_path())
        self._watched_mtimes = self._read_mtimes()

    def _read_mtimes(self):
        mtimes = []
        for path in self._data_paths():
            try:
                mtimes.append(path.stat().st_mtime)
            except OSError:
                mtimes.append(None)
        return tuple(mtimes)

    def _auto_refresh(self):
        """Shows new conversation as it happens: when a data file changed
        on disk, refresh the list and the selected Pal -- unless you're in
        the middle of editing one of its boxes."""
        try:
            if self._read_mtimes() != self._watched_mtimes and not self._has_unsaved_edits():
                self._refresh_pal_list()
        finally:
            self.after(AUTO_REFRESH_MS, self._auto_refresh)

    def _has_unsaved_edits(self):
        return any(box.edit_modified() for box in (self.prompt_text, self.memory_text, self.history_text))

    def _set_box(self, box, text):
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.edit_modified(False)

    def _refresh_pal_list(self):
        self._reload_from_disk()

        keys = set(self.app.history.keys()) | set(self.app.prompts.keys()) | set(self.app.names.keys()) | set(self.app.memories.keys())
        self.pal_keys = sorted(keys)
        self.pal_listbox.delete(0, "end")
        for key in self.pal_keys:
            display_name = self.app.names.get(key, key)
            self.pal_listbox.insert("end", display_name)

        # Keep the same Pal selected (rebuilding the list clears the
        # selection, which used to leave stale text on screen).
        if self.current_pal_key in self.pal_keys:
            index = self.pal_keys.index(self.current_pal_key)
            self.pal_listbox.selection_set(index)
            self.pal_listbox.see(index)
            self._show_pal(self.current_pal_key)

    def _on_select(self, event=None):
        selection = self.pal_listbox.curselection()
        if not selection:
            return
        self._show_pal(self.pal_keys[selection[0]])
        self.prompt_status_label.configure(text="")
        self.memory_status_label.configure(text="")
        self.history_status_label.configure(text="")

    def _show_pal(self, pal_key):
        self.current_pal_key = pal_key
        self._set_box(self.prompt_text, get_prompt(self.app.prompts, pal_key))
        self._set_box(self.memory_text, get_memory(self.app.memories, pal_key))

        turns = get_turns(self.app.history, pal_key)
        self._current_turns_snapshot = turns  # used by _save_history to preserve timestamps by position
        lines = []
        for turn in turns:
            speaker = "You" if turn.get("role") == "user" else "Pal"
            lines.append(f"{speaker}: {turn.get('content', '')}\n\n")
        self._set_box(self.history_text, "".join(lines))
        self.history_text.see("end")

    def _save_prompt(self):
        if not self.current_pal_key:
            messagebox.showwarning("Palversation", "Select a Pal first.")
            return
        self.app.prompts = load_prompts(self.app.prompts_path())
        set_prompt(self.app.prompts, self.current_pal_key, self.prompt_text.get("1.0", "end"))
        save_prompts(self.app.prompts_path(), self.app.prompts)
        self.prompt_text.edit_modified(False)
        self.prompt_status_label.configure(text="Saved.", foreground="#4cc27a")

    def _save_memory(self):
        if not self.current_pal_key:
            messagebox.showwarning("Palversation", "Select a Pal first.")
            return
        self.app.memories = load_memories(self.app.memory_path())
        set_memory(self.app.memories, self.current_pal_key, self.memory_text.get("1.0", "end"))
        save_memories(self.app.memory_path(), self.app.memories)
        self.memory_text.edit_modified(False)
        self.memory_status_label.configure(text="Saved.", foreground="#4cc27a")

    def _clear_memory(self):
        if not self.current_pal_key:
            messagebox.showwarning("Palversation", "Select a Pal first.")
            return
        display_name = self.app.names.get(self.current_pal_key, self.current_pal_key)
        if not messagebox.askyesno("Palversation", f"Clear the long-term memory for {display_name}?"):
            return
        self.app.memories = load_memories(self.app.memory_path())
        self.app.memories.pop(self.current_pal_key, None)
        save_memories(self.app.memory_path(), self.app.memories)
        self._set_box(self.memory_text, "")
        self.memory_status_label.configure(text="Cleared.", foreground="#4cc27a")

    def _save_history(self):
        if not self.current_pal_key:
            messagebox.showwarning("Palversation", "Select a Pal first.")
            return

        raw_text = self.history_text.get("1.0", "end").strip()
        blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]
        now = time.time()
        new_turns = []
        skipped = 0
        for i, block in enumerate(blocks):
            if block.startswith("You:"):
                role, content = "user", block[len("You:"):].strip()
            elif block.startswith("Pal:"):
                role, content = "assistant", block[len("Pal:"):].strip()
            else:
                skipped += 1
                continue
            # Keep the original timestamp for a line that was already
            # there (matched by position), so time-gap notes elsewhere
            # don't all collapse to "just now" just because you edited
            # the wording of an old line. New/reordered lines get "now".
            ts = self._current_turns_snapshot[i]["ts"] if (
                i < len(self._current_turns_snapshot) and "ts" in self._current_turns_snapshot[i]
            ) else now
            new_turns.append({"role": role, "content": content, "ts": ts})

        self.app.history = load_history(self.app.history_path())
        if new_turns:
            self.app.history[self.current_pal_key] = new_turns
        else:
            self.app.history.pop(self.current_pal_key, None)
        save_history(self.app.history_path(), self.app.history)
        self._current_turns_snapshot = new_turns
        self.history_text.edit_modified(False)

        if skipped:
            self.history_status_label.configure(
                text=f"Saved ({skipped} line(s) skipped -- must start with 'You:' or 'Pal:').",
                foreground="#e05a5a",
            )
        else:
            self.history_status_label.configure(text="Saved.", foreground="#4cc27a")

    def _clear_history(self):
        if not self.current_pal_key:
            messagebox.showwarning("Palversation", "Select a Pal first.")
            return
        display_name = self.app.names.get(self.current_pal_key, self.current_pal_key)
        if not messagebox.askyesno("Palversation", f"Clear conversation history for {display_name}?"):
            return
        self.app.history = load_history(self.app.history_path())
        self.app.history.pop(self.current_pal_key, None)
        save_history(self.app.history_path(), self.app.history)
        self._current_turns_snapshot = []
        self._set_box(self.history_text, "")
        self.history_status_label.configure(text="Cleared.", foreground="#4cc27a")
