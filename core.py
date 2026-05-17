import json
import os
import sys
import copy
from typing import List, Dict, Optional, Any
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox
from config import CFG, EMPTY

def path(rel: str, internal: bool = False) -> str:
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS if internal else os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)

class Msg:
    @staticmethod
    def info(msg: str) -> None:
        messagebox.showinfo("", msg)
    
    @staticmethod
    def error(msg: str) -> None:
        messagebox.showerror("Ошибка", msg)
    
    @staticmethod
    def warn(msg: str) -> None:
        messagebox.showwarning("", msg)
    
    @staticmethod
    def ask(msg: str) -> bool:
        return messagebox.askyesno("", msg)

class TexMgr:
    def __init__(self) -> None:
        self.blocks: Dict[int, ImageTk.PhotoImage] = {}
        self.thumbs: Dict[int, ImageTk.PhotoImage] = {}
        self.codes: Dict[str, int] = {}
        self.icons: Dict[str, ImageTk.PhotoImage] = {}
        self.originals: Dict[int, Image.Image] = {}

    def load_blocks(self, folder: str) -> None:
        self.blocks.clear()
        self.thumbs.clear()
        self.codes.clear()
        self.originals.clear()
        if not os.path.isdir(folder):
            return
        files = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
        if not files:
            return
        files.sort()
        code = 1
        for name in files:
            p = os.path.join(folder, name)
            try:
                img = Image.open(p)
                self.originals[code] = img.copy()
                self.blocks[code] = ImageTk.PhotoImage(img.resize((CFG.cell_size, CFG.cell_size), Image.Resampling.LANCZOS))
                self.thumbs[code] = ImageTk.PhotoImage(img.resize((CFG.cell_size, CFG.cell_size), Image.Resampling.LANCZOS))
                self.codes[name] = code
                code += 1
            except (IOError, OSError, Image.UnidentifiedImageError):
                pass

    def load_icons(self, folder: str) -> None:
        self.icons.clear()
        if not os.path.isdir(folder):
            return
        icon_names = ["void.png", "fence.png", "find.png", "fill.png", "undo.png", "redo.png",
                      "download.png", "upload.png", "clear.png", "add.png", "remove.png"]
        for name in icon_names:
            p = os.path.join(folder, name)
            if os.path.exists(p):
                try:
                    img = Image.open(p).resize((CFG.cell_size, CFG.cell_size), Image.Resampling.LANCZOS)
                    self.icons[name] = ImageTk.PhotoImage(img)
                except (IOError, OSError, Image.UnidentifiedImageError):
                    pass

    def get_block(self, code: int) -> Optional[ImageTk.PhotoImage]:
        return self.blocks.get(code)

    def get_thumb(self, code: int) -> Optional[ImageTk.PhotoImage]:
        return self.thumbs.get(code)

    def get_icon(self, name: str) -> Optional[ImageTk.PhotoImage]:
        return self.icons.get(name)

    def get_original(self, code: int) -> Optional[Image.Image]:
        return self.originals.get(code)

class UndoMgr:
    def __init__(self, limit: int = CFG.undo_limit) -> None:
        self.undo: List[Any] = []
        self.redo: List[Any] = []
        self.limit = limit

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
        self.grid: List[List[int]] = [[EMPTY] * w for _ in range(h)]
        self.fh: List[List[bool]] = [[False] * w for _ in range(h + 1)]
        self.fv: List[List[bool]] = [[False] * (w + 1) for _ in range(h)]

    def get_state(self) -> Dict[str, Any]:
        return {
            "grid": copy.deepcopy(self.grid),
            "fh": copy.deepcopy(self.fh),
            "fv": copy.deepcopy(self.fv)
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        self.grid = state["grid"]
        self.fh = state["fh"]
        self.fv = state["fv"]
        self.h = len(self.grid)
        self.w = len(self.grid[0]) if self.h > 0 else 0

    def clear(self) -> None:
        self.grid = [[EMPTY] * self.w for _ in range(self.h)]
        self.fh = [[False] * self.w for _ in range(self.h + 1)]
        self.fv = [[False] * (self.w + 1) for _ in range(self.h)]

    def resize(self, w: int, h: int) -> None:
        if self.h == h and self.w == w:
            return
        
        new_grid = [[EMPTY] * w for _ in range(h)]
        for i in range(min(h, self.h)):
            for j in range(min(w, self.w)):
                new_grid[i][j] = self.grid[i][j]
        self.grid = new_grid

        new_fh = [[False] * w for _ in range(h + 1)]
        for i in range(min(h + 1, len(self.fh))):
            for j in range(min(w, len(self.fh[0]) if self.fh else 0)):
                new_fh[i][j] = self.fh[i][j]
        self.fh = new_fh

        new_fv = [[False] * (w + 1) for _ in range(h)]
        for i in range(min(h, len(self.fv))):
            for j in range(min(w + 1, len(self.fv[0]) if self.fv else 0)):
                new_fv[i][j] = self.fv[i][j]
        self.fv = new_fv
        
        self.w = w
        self.h = h

class Map:
    def __init__(self, w: int = CFG.map_width, h: int = CFG.map_height) -> None:
        self.w = w
        self.h = h
        self.layers: List[Layer] = [Layer(w, h)]
        self.visible: List[bool] = [True]

    def get(self) -> Dict[str, Any]:
        return {
            "w": self.w,
            "h": self.h,
            "layers": [layer.get_state() for layer in self.layers],
            "visible": self.visible[:]
        }

    def set(self, state: Dict[str, Any]) -> None:
        self.w = state.get("w", CFG.map_width)
        self.h = state.get("h", CFG.map_height)
        self.layers = []
        for layer_state in state["layers"]:
            layer = Layer(self.w, self.h)
            layer.set_state(layer_state)
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

    def resize(self) -> None:
        for layer in self.layers:
            layer.resize(self.w, self.h)

    def get_active_layer(self, idx: int) -> Layer:
        return self.layers[idx]

    def get_num_layers(self) -> int:
        return len(self.layers)

class FileMgr:
    def __init__(self, map_obj: Map, tex: TexMgr, preset_dir: str) -> None:
        self.map = map_obj
        self.tex = tex
        self.preset_dir = preset_dir

    def save_json(self, path: str) -> bool:
        data = self.map.get()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(',', ':'))
        return True

    def load_json(self, path: str) -> bool:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "grid" in data:
            self.map.w = CFG.map_width
            self.map.h = CFG.map_height
            single = Layer(self.map.w, self.map.h)
            single.set_state({"grid": data["grid"], "fh": data.get("fh", []), "fv": data.get("fv", [])})
            self.map.layers = [single]
            self.map.visible = [True]
        else:
            self.map.set(data)
        self.map.resize()
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

class Dialog:
    @staticmethod
    def select(parent: tk.Tk, title: str, items: List[str], on_ok: callable, on_delete: callable = None) -> None:
        win = tk.Toplevel(parent)
        win.title(title)
        win.geometry("300x400")
        win.transient(parent)
        win.grab_set()
        
        tk.Label(win, text="Доступные элементы:").pack(pady=5)
        
        lb = tk.Listbox(win, height=15)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for it in sorted(items):
            lb.insert(tk.END, it)
        
        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)
        
        def ok():
            sel = lb.curselection()
            if sel:
                on_ok(lb.get(sel[0]))
            win.destroy()
        
        def delete():
            sel = lb.curselection()
            if sel and on_delete:
                on_delete(lb.get(sel[0]))
                win.destroy()
        
        tk.Button(btn_frame, text="Выбрать", command=ok, width=10).pack(side=tk.LEFT, padx=5)
        
        if on_delete:
            tk.Button(btn_frame, text="Удалить", command=delete, width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Отмена", command=win.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        win.bind("<Double-Button-1>", lambda e: ok())
        win.bind("<Return>", lambda e: ok())
        win.bind("<Escape>", lambda e: win.destroy())

    @staticmethod
    def del_textures(parent: tk.Tk, folder: str, on_done: callable) -> None:
        if not os.path.isdir(folder):
            Msg.warn("Нет загруженных текстур")
            return
        files = [f for f in os.listdir(folder) if f.endswith('.png')]
        if not files:
            Msg.warn("Нет загруженных текстур")
            return
        win = tk.Toplevel(parent)
        win.title("Управление текстурами")
        win.geometry("300x400")
        win.transient(parent)
        win.grab_set()
        tk.Label(win, text="Выберите текстуры для удаления:").pack(pady=5)
        lb = tk.Listbox(win, selectmode=tk.MULTIPLE, height=15)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for f in sorted(files):
            lb.insert(tk.END, f)
        
        def delete_sel():
            sel = lb.curselection()
            if not sel:
                Msg.warn("Ничего не выбрано")
                return
            for idx in sel:
                p = os.path.join(folder, lb.get(idx))
                try:
                    os.remove(p)
                except OSError:
                    pass
            win.destroy()
            on_done()
        
        def delete_all():
            if Msg.ask("Удалить все текстуры?"):
                for f in files:
                    try:
                        os.remove(os.path.join(folder, f))
                    except OSError:
                        pass
                win.destroy()
                on_done()
        
        frm = tk.Frame(win)
        frm.pack(pady=10)
        tk.Button(frm, text="Удалить выбранные", command=delete_sel).pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Удалить всё", command=delete_all).pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Отмена", command=win.destroy).pack(side=tk.LEFT, padx=5)