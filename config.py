# config.py
from dataclasses import dataclass
from typing import Dict, List, Any
import json
import os

@dataclass
class Config:
    cell_size: int = 16
    map_width: int = 100
    map_height: int = 50
    max_layers: int = 383
    undo_limit: int = 100
    brush_min: int = 1
    brush_max: int = 10

    theme: str = 'light'

    light_colors: Dict[str, str] = None
    dark_colors: Dict[str, str] = None
    
    def __post_init__(self):
        if self.light_colors is None:
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
            }

        if self.dark_colors is None:
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
            }
    
    @property
    def colors(self) -> Dict[str, str]:
        if self.theme == 'dark':
            return self.dark_colors
        return self.light_colors
    
    @colors.setter
    def colors(self, value):
        pass
    
    def switch_theme(self) -> None:
        self.theme = 'dark' if self.theme == 'light' else 'light'
    
    @property
    def width_px(self) -> int:
        return self.map_width * self.cell_size

    @property
    def height_px(self) -> int:
        return self.map_height * self.cell_size


class Settings:
    SETTINGS_FILE = "editor_settings.json"
    
    def __init__(self):
        self.settings: Dict[str, Any] = {
            "window_geometry": "",
            "last_export_path": "",
            "last_import_path": "",
            "last_json_path": "",
            "recent_files": [],
            "max_recent_files": 10,
            "theme": "light",
            "show_grid": True,
            "brush_size": 1,
            "auto_save": False,
            "auto_save_interval": 300
        }
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


CFG = Config()
EMPTY = 0