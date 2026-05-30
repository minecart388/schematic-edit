# core.py
import json
import os
import sys
import copy
from typing import List, Dict, Optional, Any
from PIL import Image, ImageTk
from .config import CFG, EMPTY

def path(rel: str, internal: bool = False) -> str:
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS if internal else os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

class TexMgr:
    def __init__(self) -> None:
        self.blocks: Dict[str, ImageTk.PhotoImage] = {}
        self.thumbs: Dict[str, ImageTk.PhotoImage] = {}
        self.codes: Dict[str, str] = {}
        self.icons: Dict[str, ImageTk.PhotoImage] = {}
        self.originals: Dict[str, Image.Image] = {}
        self.name_to_index: Dict[str, int] = {}
        self.index_to_name: Dict[int, str] = {}
        self._current_zoom: float = 1.0
        self._current_block_size: int = 0

    def load_blocks(self, folder: str, log_func=None) -> None:
        self.blocks.clear()
        self.thumbs.clear()
        self.codes.clear()
        self.originals.clear()
        self.name_to_index.clear()
        self.index_to_name.clear()
        if not os.path.isdir(folder):
            return
        files = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
        if not files:
            return
        files.sort()
        skipped = []
        for idx, name in enumerate(files):
            p = os.path.join(folder, name)
            try:
                img = Image.open(p)
                self.originals[name] = img.copy()
                self.name_to_index[name] = idx + 1
                self.index_to_name[idx + 1] = name
            except (IOError, OSError, Image.UnidentifiedImageError):
                skipped.append(name)
        if log_func and skipped:
            log_func(f"Пропущены некорректные файлы: {', '.join(skipped)}", "warning")
        self.update_block_size(self._current_zoom)

    def load_icons(self, folder: str) -> None:
        self.icons.clear()
        if not os.path.isdir(folder):
            return
        icon_names = ["void.png", "find.png", "fill.png", "undo.png", "redo.png",
                    "download.png", "upload.png", "clear.png", "circle.png", "rect.png", "line.png"]
        for name in icon_names:
            p = os.path.join(folder, name)
            if os.path.exists(p):
                try:
                    img = Image.open(p).resize((CFG.cell_size, CFG.cell_size), Image.Resampling.LANCZOS)
                    self.icons[name] = ImageTk.PhotoImage(img)
                except (IOError, OSError, Image.UnidentifiedImageError):
                    pass

    def update_block_size(self, zoom: float) -> None:
        new_size = max(1, int(CFG.cell_size * zoom))
        if new_size == self._current_block_size:
            return
        self._current_block_size = new_size
        self._current_zoom = zoom
        self.blocks.clear()
        for name, img in self.originals.items():
            resized = img.resize((new_size, new_size), Image.Resampling.NEAREST)
            self.blocks[name] = ImageTk.PhotoImage(resized)
            thumb_size = CFG.cell_size
            thumb = img.resize((thumb_size, thumb_size), Image.Resampling.NEAREST)
            self.thumbs[name] = ImageTk.PhotoImage(thumb)

    def get_block(self, name: str) -> Optional[ImageTk.PhotoImage]:
        return self.blocks.get(name)

    def get_thumb(self, name: str) -> Optional[ImageTk.PhotoImage]:
        return self.thumbs.get(name)

    def get_icon(self, name: str) -> Optional[ImageTk.PhotoImage]:
        return self.icons.get(name)

    def get_original(self, name: str) -> Optional[Image.Image]:
        return self.originals.get(name)

class UndoMgr:
    def __init__(self, limit: int = CFG.undo_limit) -> None:
        self.undo: List[Any] = []
        self.redo: List[Any] = []
        self.limit = limit

    def can_undo(self) -> bool:
        return len(self.undo) > 0

    def can_redo(self) -> bool:
        return len(self.redo) > 0

    def save(self, state: Any) -> None:
        self.undo.append(copy.deepcopy(state))
        if len(self.undo) > self.limit:
            self.undo.pop(0)
        self.redo.clear()

    def undo_op(self, cur: Any) -> Optional[Any]:
        if not self.undo:
            return None
        self.redo.append(copy.deepcopy(cur))
        return self.undo.pop()

    def redo_op(self, cur: Any) -> Optional[Any]:
        if not self.redo:
            return None
        self.undo.append(copy.deepcopy(cur))
        return self.redo.pop()

class Layer:
    def __init__(self, w: int, h: int) -> None:
        self.w = w
        self.h = h
        self.grid: List[List[str]] = [[EMPTY] * w for _ in range(h)]

    def get_state(self) -> Dict[str, Any]:
        return {
            "grid": copy.deepcopy(self.grid)
        }

    def set_state(self, state: Dict[str, Any], tex_mgr: Optional['TexMgr'] = None) -> None:
        self.grid = state["grid"]
        self.h = len(self.grid)
        self.w = len(self.grid[0]) if self.h > 0 else 0

        if tex_mgr and tex_mgr.index_to_name:
            for y in range(self.h):
                for x in range(self.w):
                    val = self.grid[y][x]
                    if isinstance(val, int) and val != 0:
                        name = tex_mgr.index_to_name.get(val)
                        if name:
                            self.grid[y][x] = name
                        else:
                            self.grid[y][x] = EMPTY
                    elif val == 0:
                        self.grid[y][x] = EMPTY

    def clear(self) -> None:
        self.grid = [[EMPTY] * self.w for _ in range(self.h)]

    def resize(self, w: int, h: int, shift_x: int = 0, shift_y: int = 0) -> None:
        if self.h == h and self.w == w and shift_x == 0 and shift_y == 0:
            return
        new_grid = [[EMPTY] * w for _ in range(h)]
        for i in range(min(h, self.h)):
            for j in range(min(w, self.w)):
                ni = i + shift_y
                nj = j + shift_x
                if 0 <= ni < h and 0 <= nj < w:
                    new_grid[ni][nj] = self.grid[i][j]
        self.grid = new_grid
        self.w = w
        self.h = h

    def copy_rect(self, x1: int, y1: int, x2: int, y2: int) -> List[List[str]]:
        left = max(0, min(x1, x2))
        right = min(self.w - 1, max(x1, x2))
        top = max(0, min(y1, y2))
        bottom = min(self.h - 1, max(y1, y2))
        data = []
        for y in range(top, bottom + 1):
            row = []
            for x in range(left, right + 1):
                row.append(self.grid[y][x])
            data.append(row)
        return data

    def paste_rect(self, x1: int, y1: int, data: List[List[str]]) -> None:
        if not data:
            return
        h_data = len(data)
        w_data = len(data[0]) if h_data > 0 else 0
        for dy in range(h_data):
            for dx in range(w_data):
                nx = x1 + dx
                ny = y1 + dy
                if 0 <= nx < self.w and 0 <= ny < self.h:
                    self.grid[ny][nx] = data[dy][dx]

    def fill_rect(self, x1: int, y1: int, x2: int, y2: int, tex_name: str) -> None:
        left = max(0, min(x1, x2))
        right = min(self.w - 1, max(x1, x2))
        top = max(0, min(y1, y2))
        bottom = min(self.h - 1, max(y1, y2))
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                self.grid[y][x] = tex_name

    def move_rect(self, x1: int, y1: int, x2: int, y2: int, dx: int, dy: int) -> None:
        data = self.copy_rect(x1, y1, x2, y2)
        left = max(0, min(x1, x2))
        right = min(self.w - 1, max(x1, x2))
        top = max(0, min(y1, y2))
        bottom = min(self.h - 1, max(y1, y2))
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                self.grid[y][x] = EMPTY
        self.paste_rect(x1 + dx, y1 + dy, data)

    def replace_texture(self, old_tex: str, new_tex: str) -> None:
        if old_tex == EMPTY:
            return
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x] == old_tex:
                    self.grid[y][x] = new_tex

class Map:
    def __init__(self, w: int = 100, h: int = 50) -> None:
        self.w = w
        self.h = h
        self.layers: List[Layer] = [Layer(w, h)]
        self.visible: List[bool] = [True]
        self.tex_mgr: Optional['TexMgr'] = None

    def set_tex_mgr(self, tex_mgr: 'TexMgr') -> None:
        self.tex_mgr = tex_mgr

    def get(self) -> Dict[str, Any]:
        return {
            "w": self.w,
            "h": self.h,
            "layers": [layer.get_state() for layer in self.layers],
            "visible": self.visible[:]
        }

    def set(self, state: Dict[str, Any]) -> None:
        self.w = state.get("w", 100)
        self.h = state.get("h", 50)
        self.layers = []
        for layer_state in state["layers"]:
            layer = Layer(self.w, self.h)
            layer.set_state(layer_state, self.tex_mgr)
            self.layers.append(layer)
        if "visible" in state:
            self.visible = state["visible"][:len(self.layers)]
        else:
            self.visible = [True] * len(self.layers)
        if len(self.layers) > CFG.max_layers:
            self.layers = self.layers[:CFG.max_layers]
            self.visible = self.visible[:CFG.max_layers]

    def add_layer(self) -> None:
        if len(self.layers) < CFG.max_layers:
            self.layers.append(Layer(self.w, self.h))
            self.visible.append(True)

    def remove_layer(self, idx: int) -> bool:
        if len(self.layers) > 1 and 0 <= idx < len(self.layers):
            del self.layers[idx]
            del self.visible[idx]
            return True
        return False

    def clear_layer(self, idx: int) -> None:
        if 0 <= idx < len(self.layers):
            self.layers[idx].clear()

    def clear_all(self) -> None:
        for layer in self.layers:
            layer.clear()

    def resize(self, new_w: int, new_h: int, shift_x: int = 0, shift_y: int = 0) -> None:
        self.w = new_w
        self.h = new_h
        for layer in self.layers:
            layer.resize(new_w, new_h, shift_x, shift_y)

    def get_active_layer(self, idx: int) -> Layer:
        return self.layers[idx]

    def get_num_layers(self) -> int:
        return len(self.layers)

    def replace_texture_all_layers(self, old_tex: str, new_tex: str) -> None:
        if old_tex == EMPTY:
            return
        for layer in self.layers:
            layer.replace_texture(old_tex, new_tex)

class FileMgr:
    def __init__(self, map_obj: Map, tex: TexMgr, preset_dir: str) -> None:
        self.map = map_obj
        self.tex = tex
        self.preset_dir = preset_dir
        self.map.set_tex_mgr(tex)

    def save_json(self, path: str) -> bool:
        data = self.map.get()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(',', ':'))
        return True

    def load_json(self, path: str) -> bool:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "grid" in data:
            old_grid = data["grid"]
            old_h = len(old_grid)
            old_w = len(old_grid[0]) if old_h > 0 else 0
            self.map.w = old_w
            self.map.h = old_h
            single = Layer(old_w, old_h)
            single.set_state({"grid": old_grid}, self.tex)
            self.map.layers = [single]
            self.map.visible = [True]
        else:
            self.map.set(data)
        self.map.resize(self.map.w, self.map.h)
        return True

    def save_preset(self, name: str) -> Optional[str]:
        os.makedirs(self.preset_dir, exist_ok=True)
        safe = "".join(c for c in name if c.isalnum() or c in " _-")
        if not safe:
            return None
        self.save_json(os.path.join(self.preset_dir, safe + ".json"))
        return safe

    def load_preset(self, name: str) -> bool:
        p = os.path.join(self.preset_dir, name + ".json")
        if os.path.exists(p):
            return self.load_json(p)
        return False

    def list_presets(self) -> List[str]:
        if not os.path.isdir(self.preset_dir):
            return []
        return [os.path.splitext(f)[0] for f in os.listdir(self.preset_dir) if f.endswith('.json')]

    def delete_preset(self, name: str) -> bool:
        preset_path = os.path.join(self.preset_dir, name + ".json")
        if os.path.exists(preset_path):
            os.remove(preset_path)
            return True
        return False