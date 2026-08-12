"""
General tab: LLM provider (dropdown), base URL (always editable, e.g. for
a local Ollama server or a custom proxy), model (when the provider needs
one), API key (pasted field, optional for some providers, or a Connect
button for others), connection test, and the general system prompt. No
separate language selector -- language preference is just part of the
freeform prompt text, so it isn't limited to a predefined list.
"""

import tkinter as tk
from tkinter import ttk
import threading

from providers.registry import list_providers, get_provider_spec
from gui import theme
from gui.widgets import Dropdown


class GeneralTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app

        pad = {"padx": 0, "pady": 8}

        ttk.Label(self, text="LLM Provider", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", **pad
        )
        self.providers = list_providers()
        provider_options = [(p.provider_id, p.display_name) for p in self.providers]
        provider_ids = [p.provider_id for p in self.providers]
        current_provider = app.config_data.get("provider", "player2")
        provider_index = provider_ids.index(current_provider) if current_provider in provider_ids else 0
        self.provider_dropdown = Dropdown(
            self, provider_options, initial_index=provider_index,
            on_change=lambda _v: self._on_provider_change(),
        )
        self.provider_dropdown.grid(row=0, column=1, sticky="w", **pad)

        # Base URL: always shown and editable, for every provider -- lets
        # anyone point Player2/OpenAI/etc at a proxy, and is how a fully
        # custom OpenAI-compatible endpoint (a local Ollama server, some
        # other self-hosted thing) gets configured at all.
        ttk.Label(self, text="Base URL", style="Section.TLabel").grid(
            row=1, column=0, sticky="w", **pad
        )
        self.base_url_var = tk.StringVar()
        self.base_url_entry = tk.Entry(
            self, textvariable=self.base_url_var, width=46,
            bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
        )
        self.base_url_entry.grid(row=1, column=1, sticky="w", padx=0, pady=8, ipady=4)

        # Model field, only shown for providers that need one. Player2
        # chooses automatically, so it stays hidden for that one.
        self.model_label = ttk.Label(self, text="Model", style="Section.TLabel")
        self.model_var = tk.StringVar()
        self.model_entry = tk.Entry(
            self, textvariable=self.model_var, width=30,
            bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
        )

        # Row 3 hosts either an API key Entry or a Connect button+status,
        # swapped depending on the selected provider's key_is_pasted.
        self.auth_label = ttk.Label(self, text="", style="Section.TLabel")

        self.paste_frame = ttk.Frame(self)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = tk.Entry(
            self.paste_frame, textvariable=self.api_key_var, show="*", width=38,
            bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
        )
        self.api_key_entry.pack(ipady=4)

        self.connect_frame = ttk.Frame(self)
        self.connect_button = tk.Button(
            self.connect_frame, text="Connect Account", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=14, pady=6, command=self._start_connect,
        )
        self.connect_button.pack(side="left")
        self.connect_status_label = ttk.Label(self.connect_frame, text="")
        self.connect_status_label.pack(side="left", padx=(10, 0))

        test_row = ttk.Frame(self)
        test_row.grid(row=4, column=1, sticky="w", pady=(0, 8))
        self.test_button = tk.Button(
            test_row, text="Test Connection", relief="flat", bd=0, cursor="hand2",
            bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.FONT_BODY,
            activebackground=theme.PANEL_BG_ALT, activeforeground=theme.TEXT,
            padx=14, pady=6, command=self._test_connection,
        )
        self.test_button.pack(side="left")
        self.test_status_label = ttk.Label(test_row, text="")
        self.test_status_label.pack(side="left", padx=(10, 0))

        ttk.Label(self, text="General Prompt", style="Section.TLabel").grid(
            row=5, column=0, sticky="nw", **pad
        )
        self.prompt_text = tk.Text(
            self, height=9, width=52, wrap="word",
            bg=theme.PANEL_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
            padx=8, pady=8, font=(theme.FONT_FAMILY, 12),
        )
        self.prompt_text.insert("1.0", app.config_data.get("system_prompt", ""))
        self.prompt_text.grid(row=5, column=1, sticky="nsew", **pad)

        save_row = ttk.Frame(self)
        save_row.grid(row=6, column=1, sticky="e", pady=(10, 0))
        self.save_status_label = ttk.Label(save_row, text="")
        self.save_status_label.pack(side="left", padx=(0, 10))
        save_button = tk.Button(
            save_row, text="Save", relief="flat", bd=0, cursor="hand2",
            bg=theme.ACCENT, fg=theme.TEXT_ON_ACCENT, font=theme.FONT_BODY,
            activebackground=theme.ACCENT_HOVER, activeforeground=theme.TEXT_ON_ACCENT,
            padx=18, pady=8, command=self.save,
        )
        save_button.pack(side="left")

        self.columnconfigure(1, weight=1)
        self.rowconfigure(5, weight=1)

        self._render_provider_fields()

    def _current_provider_id(self) -> str:
        return self.provider_dropdown.current_value() or "player2"

    def _current_spec(self):
        return get_provider_spec(self._current_provider_id())

    def _render_provider_fields(self):
        spec = self._current_spec()

        # Base URL (row 1): always shown, pre-filled with whatever's
        # saved, falling back to the provider's own default.
        saved_base_url = self.app.config_data.get("provider_base_urls", {}).get(
            spec.provider_id, spec.default_base_url
        )
        self.base_url_var.set(saved_base_url)

        # Model field (row 2), only for providers that need one.
        self.model_label.grid_forget()
        self.model_entry.grid_forget()
        if spec.needs_model:
            self.model_label.grid(row=2, column=0, sticky="w", padx=0, pady=8)
            self.model_entry.grid(row=2, column=1, sticky="w", padx=0, pady=8, ipady=4)
            saved_model = self.app.config_data.get("provider_models", {}).get(
                spec.provider_id, spec.default_model
            )
            self.model_var.set(saved_model)

        # API key / connect row (row 3).
        self.auth_label.grid_forget()
        self.paste_frame.grid_forget()
        self.connect_frame.grid_forget()

        self.auth_label.configure(text=spec.api_key_label)
        self.auth_label.grid(row=3, column=0, sticky="w", padx=0, pady=8)

        if spec.key_is_pasted:
            self.paste_frame.grid(row=3, column=1, sticky="w", padx=0, pady=8)
            self._load_current_api_key()
        else:
            self.connect_frame.grid(row=3, column=1, sticky="w", padx=0, pady=8)
            self._update_connect_status_from_saved_key()

    def _update_connect_status_from_saved_key(self):
        provider_id = self._current_provider_id()
        key = self.app.config_data.get("api_keys", {}).get(provider_id, "")
        if key and key != "PUT_YOUR_API_KEY_HERE":
            self.connect_status_label.configure(text="Connected.", foreground="#4cc27a")
        else:
            self.connect_status_label.configure(text="Not connected.", foreground=theme.TEXT_MUTED)

    def _load_current_api_key(self):
        provider_id = self._current_provider_id()
        key = self.app.config_data.get("api_keys", {}).get(provider_id, "")
        if key == "PUT_YOUR_API_KEY_HERE":
            key = ""
        self.api_key_var.set(key)

    def _on_provider_change(self):
        self.test_status_label.configure(text="")
        self.save_status_label.configure(text="")
        self._render_provider_fields()

    def _start_connect(self):
        spec = self._current_spec()
        if not spec.auth_handler:
            return
        self.connect_button.configure(state="disabled")
        self.connect_status_label.configure(text="Starting...", foreground=theme.TEXT_MUTED)

        provider_id = spec.provider_id

        def on_status(msg):
            self.after(0, lambda: self.connect_status_label.configure(text=msg, foreground=theme.TEXT_MUTED))

        def on_key(key):
            def apply():
                self.app.config_data.setdefault("api_keys", {})[provider_id] = key
                self.connect_status_label.configure(text="Connected.", foreground="#4cc27a")
                self.connect_button.configure(state="normal")
                self.app.save_all()
            self.after(0, apply)

        def on_error(msg):
            self.after(0, lambda: (
                self.connect_status_label.configure(text=f"Failed: {msg}", foreground="#e05a5a"),
                self.connect_button.configure(state="normal"),
            ))

        spec.auth_handler(on_key=on_key, on_status=on_status, on_error=on_error)

    def _test_connection(self):
        provider_id = self._current_provider_id()
        spec = self._current_spec()
        api_key = (
            self.api_key_var.get().strip()
            if spec.key_is_pasted
            else self.app.config_data.get("api_keys", {}).get(provider_id, "")
        )
        if spec.requires_api_key and not api_key:
            self.test_status_label.configure(text="Connect or enter an API key first.", foreground="#e05a5a")
            return

        base_url = self.base_url_var.get().strip()
        if not base_url:
            self.test_status_label.configure(text="Enter a base URL first.", foreground="#e05a5a")
            return
        model_name = self.model_var.get().strip() if spec.needs_model else ""

        self.test_status_label.configure(text="Testing...", foreground=theme.TEXT_MUTED)
        self.test_button.configure(state="disabled")

        def run_test():
            try:
                provider = spec.factory(
                    api_key=api_key, base_url=base_url,
                    system_prompt="You are a test assistant.",
                    model_name=model_name,
                )
                provider.get_response("Say OK if you can read this.", event_type="chat")
                self.after(0, lambda: self._on_test_result(True, ""))
            except Exception as e:
                self.after(0, lambda: self._on_test_result(False, str(e)))

        threading.Thread(target=run_test, daemon=True).start()

    def _on_test_result(self, ok: bool, error: str):
        self.test_button.configure(state="normal")
        if ok:
            self.test_status_label.configure(text="Connection OK.", foreground="#4cc27a")
        else:
            self.test_status_label.configure(text=f"Failed: {error}", foreground="#e05a5a")

    def save(self):
        provider_id = self._current_provider_id()
        self.app.config_data["provider"] = provider_id

        spec = self._current_spec()
        if spec.key_is_pasted:
            self.app.config_data.setdefault("api_keys", {})[provider_id] = self.api_key_var.get().strip()
        if spec.needs_model:
            self.app.config_data.setdefault("provider_models", {})[provider_id] = self.model_var.get().strip()

        self.app.config_data.setdefault("provider_base_urls", {})[provider_id] = self.base_url_var.get().strip()

        self.app.config_data["system_prompt"] = self.prompt_text.get("1.0", "end").strip()
        self.app.save_all()
        self.save_status_label.configure(text="Saved.", foreground="#4cc27a")
