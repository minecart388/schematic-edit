# config.py
from dataclasses import dataclass
from typing import Dict, List, Any
import json
import os
import tkinter as tk
from tkinter import ttk

@dataclass
class Config:
    cell_size: int = 16
    map_width: int = 100
    map_height: int = 50
    max_layers: int = 383
    undo_limit: int = 30
    brush_min: int = 1
    brush_max: int = 10

    dark_colors: Dict[str, str] = None
    light_colors: Dict[str, str] = None
    _current_theme: str = "dark"

    def __post_init__(self):
        self.dark_colors = {
            "WHITE": "#2D2D2D",
            "BLACK": "#FFFFFF",
            "L_GREY": "#3C3C3C",
            "GREY": "#666666",
            "BG_CANVAS": "#1E1E1E",
            "BG_PANEL": "#2D2D2D",
            "TEXT": "#FFFFFF",
            "GRID": "#4A4A4A",
            "BUTTON": "#3C3C3C",
            "BUTTON_ACTIVE": "#4A4A4A",
            "SLOT_BORDER": "#555555",
        }
        self.light_colors = {
            "WHITE": "#FFFFFF",
            "BLACK": "#000000",
            "L_GREY": "#E8E8E8",
            "GREY": "#9D9E80",
            "BG_CANVAS": "#F5F5F5",
            "BG_PANEL": "#E0E0E0",
            "TEXT": "#000000",
            "GRID": "#CCCCCC",
            "BUTTON": "#FFFFFF",
            "BUTTON_ACTIVE": "#E0E0E0",
            "SLOT_BORDER": "#AFAFAF",
        }

    @property
    def colors(self) -> Dict[str, str]:
        return self.dark_colors if self._current_theme == "dark" else self.light_colors

    def set_theme(self, theme: str) -> None:
        if theme in ("dark", "light"):
            self._current_theme = theme

    @property
    def width_px(self) -> int:
        return self.map_width * self.cell_size

    @property
    def height_px(self) -> int:
        return self.map_height * self.cell_size

class ProgressDialog:
    def __init__(self, parent, title: str = "Прогресс", max_value: int = 100):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x120")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        colors = CFG.colors
        self.dialog.configure(bg=colors["BG_PANEL"])
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        self._cancelled = False
        self._callback = None
        
        main_frame = tk.Frame(self.dialog, bg=colors["BG_PANEL"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.label = tk.Label(main_frame, text="", bg=colors["BG_PANEL"], fg=colors["TEXT"])
        self.label.pack(pady=5)
        
        self.progress = ttk.Progressbar(main_frame, length=350, mode='determinate', maximum=max_value)
        self.progress.pack(pady=10)
        
        self.cancel_btn = tk.Button(main_frame, text="Отмена", command=self._cancel,
                                   bg=colors["BUTTON"], fg=colors["TEXT"])
        self.cancel_btn.pack(pady=5)
        
        self.center_window()
        
    def center_window(self):
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _on_close(self):
        self._cancelled = True
        if self._callback:
            self._callback(False)
        self.dialog.destroy()
    
    def _cancel(self):
        self._cancelled = True
        if self._callback:
            self._callback(False)
        self.dialog.destroy()
    
    def update(self, value: int, message: str = ""):
        self.progress['value'] = value
        if message:
            self.label.config(text=message)
        self.dialog.update()
    
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def set_callback(self, callback):
        self._callback = callback
    
    def close(self):
        self.dialog.destroy()

class Settings:
    SETTINGS_FILE = os.path.join("assets", "editor_settings.json")

    def __init__(self):
        self.settings: Dict[str, Any] = {
            "window_geometry": "",
            "last_export_path": "",
            "last_import_path": "",
            "last_json_path": "",
            "recent_files": [],
            "max_recent_files": 10,
            "show_grid": True,
            "brush_size": 1,
            "theme": "dark",
            "zoom": 1.0,
            "offset_x": 0,
            "offset_y": 0
        }
        os.makedirs("assets", exist_ok=True)
        self.load()

    def load(self) -> None:
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except (json.JSONDecodeError, IOError):
                pass

    def save(self) -> None:
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def get(self, key: str, default=None):
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save()

    def add_recent_file(self, filepath: str) -> None:
        recent = self.settings["recent_files"]
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        max_files = self.settings["max_recent_files"]
        self.settings["recent_files"] = recent[:max_files]
        self.save()

    def get_recent_files(self) -> List[str]:
        return self.settings.get("recent_files", [])

    def get_theme(self) -> str:
        return self.settings.get("theme", "dark")

    def set_theme(self, theme: str) -> None:
        self.set("theme", theme)


CFG = Config()
EMPTY = ""