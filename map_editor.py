import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import sys
import shutil
import copy

try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Ошибка", "Не установлен модуль Pillow.")
    sys.exit(1)

CELL = 16
W = 100
H = 50
WIDTH = W * CELL
HEIGHT = H * CELL

WHITE = "#FFFFFF"
BLACK = "#000000"
L_GREY = "#D3D3D3"
GREY = "#9D9E80"
EMPTY = 0
MAX_LAYERS_LIMIT = 10

def path(rel, internal=False):
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS if internal else os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


class TexMgr:
    def __init__(self):
        self.blocks = {}
        self.thumbs = {}
        self.codes = {}
        self.icons = {}

    def load_blocks(self, folder):
        self.blocks.clear()
        self.thumbs.clear()
        self.codes.clear()
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
                self.blocks[code] = ImageTk.PhotoImage(img.resize((CELL, CELL), Image.Resampling.LANCZOS))
                self.thumbs[code] = ImageTk.PhotoImage(img.resize((CELL, CELL), Image.Resampling.LANCZOS))
                self.codes[name] = code
                code += 1
            except:
                pass

    def load_icons(self, folder):
        self.icons.clear()
        if not os.path.isdir(folder):
            return
        names = ["void.png", "fence.png", "undo.png", "redo.png", "download.png", "upload.png", "clear.png", "add.png", "remove.png"]
        for name in names:
            p = os.path.join(folder, name)
            if os.path.exists(p):
                try:
                    img = Image.open(p).resize((CELL, CELL), Image.Resampling.LANCZOS)
                    self.icons[name] = ImageTk.PhotoImage(img)
                except:
                    pass

    def get_block(self, code):
        return self.blocks.get(code)

    def get_thumb(self, code):
        return self.thumbs.get(code)

    def get_icon(self, name):
        return self.icons.get(name)


class UndoMgr:
    def __init__(self, limit=100):
        self.undo = []
        self.redo = []
        self.limit = limit

    def save(self, state):
        self.undo.append(copy.deepcopy(state))
        if len(self.undo) > self.limit:
            self.undo.pop(0)
        self.redo.clear()

    def undo_op(self, cur):
        if not self.undo:
            return None
        self.redo.append(copy.deepcopy(cur))
        return self.undo.pop()

    def redo_op(self, cur):
        if not self.redo:
            return None
        self.undo.append(copy.deepcopy(cur))
        return self.redo.pop()


class Layer:
    def __init__(self, w, h):
        self.grid = [[EMPTY] * w for _ in range(h)]
        self.fh = [[False] * w for _ in range(h + 1)]
        self.fv = [[False] * (w + 1) for _ in range(h)]

    def get_state(self):
        return {
            "grid": copy.deepcopy(self.grid),
            "fh": copy.deepcopy(self.fh),
            "fv": copy.deepcopy(self.fv)
        }

    def set_state(self, state):
        self.grid = state["grid"]
        self.fh = state["fh"]
        self.fv = state["fv"]

    def clear(self):
        self.grid = [[EMPTY] * len(self.grid[0]) for _ in range(len(self.grid))]
        self.fh = [[False] * len(self.grid[0]) for _ in range(len(self.grid) + 1)]
        self.fv = [[False] * (len(self.grid[0]) + 1) for _ in range(len(self.grid))]

    def resize(self, w, h):
        if len(self.grid) != h or len(self.grid[0]) != w:
            new_grid = [[EMPTY] * w for _ in range(h)]
            for i in range(min(h, len(self.grid))):
                for j in range(min(w, len(self.grid[0]))):
                    new_grid[i][j] = self.grid[i][j]
            self.grid = new_grid
            new_fh = [[False] * w for _ in range(h + 1)]
            for i in range(min(h+1, len(self.fh))):
                for j in range(min(w, len(self.fh[0]))):
                    new_fh[i][j] = self.fh[i][j]
            self.fh = new_fh
            new_fv = [[False] * (w + 1) for _ in range(h)]
            for i in range(min(h, len(self.fv))):
                for j in range(min(w+1, len(self.fv[0]))):
                    new_fv[i][j] = self.fv[i][j]
            self.fv = new_fv


class Map:
    def __init__(self, w=W, h=H):
        self.w = w
        self.h = h
        self.layers = [Layer(w, h) for _ in range(4)]
        self.visible = [True] * 4

    def get(self):
        return {
            "layers": [layer.get_state() for layer in self.layers],
            "visible": self.visible[:]
        }

    def set(self, state):
        self.layers = []
        for layer_state in state["layers"]:
            layer = Layer(self.w, self.h)
            layer.set_state(layer_state)
            self.layers.append(layer)
        if "visible" in state:
            self.visible = state["visible"][:len(self.layers)]
        else:
            self.visible = [True] * len(self.layers)
        if len(self.layers) > MAX_LAYERS_LIMIT:
            self.layers = self.layers[:MAX_LAYERS_LIMIT]
            self.visible = self.visible[:MAX_LAYERS_LIMIT]

    def add_layer(self):
        if len(self.layers) < MAX_LAYERS_LIMIT:
            self.layers.append(Layer(self.w, self.h))
            self.visible.append(True)

    def remove_layer(self, idx):
        if len(self.layers) > 1 and 0 <= idx < len(self.layers):
            del self.layers[idx]
            del self.visible[idx]
            return True
        return False

    def clear_layer(self, idx):
        if 0 <= idx < len(self.layers):
            self.layers[idx].clear()

    def clear_all(self):
        for layer in self.layers:
            layer.clear()

    def resize(self):
        for layer in self.layers:
            layer.resize(self.w, self.h)

    def get_active_layer(self, idx):
        return self.layers[idx]

    def get_num_layers(self):
        return len(self.layers)


class FileMgr:
    def __init__(self, map, tex, canvas, preset_dir):
        self.map = map
        self.tex = tex
        self.canvas = canvas
        self.preset_dir = preset_dir

    def save_json(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.map.get(), f, indent=2)
        return True

    def load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if "grid" in d:
            single = Layer(self.map.w, self.map.h)
            single.set_state({"grid": d["grid"], "fh": d.get("fh", []), "fv": d.get("fv", [])})
            self.map.layers = [single]
            self.map.visible = [True]
        else:
            self.map.set(d)
        self.map.resize()
        return True

    def save_png(self, path):
        try:
            from PIL import ImageGrab
            x = self.canvas.winfo_rootx() + self.canvas.winfo_x()
            y = self.canvas.winfo_rooty() + self.canvas.winfo_y()
            img = ImageGrab.grab((x, y, x + WIDTH, y + HEIGHT))
            img.save(path)
            return True
        except:
            return False

    def save_preset(self, name):
        os.makedirs(self.preset_dir, exist_ok=True)
        safe = "".join(c for c in name if c.isalnum() or c in " _-")
        if not safe:
            return None
        self.save_json(os.path.join(self.preset_dir, safe + ".json"))
        return safe

    def load_preset(self, name):
        p = os.path.join(self.preset_dir, name + ".json")
        if os.path.exists(p):
            return self.load_json(p)
        return False

    def list_presets(self):
        if not os.path.isdir(self.preset_dir):
            return []
        return [os.path.splitext(f)[0] for f in os.listdir(self.preset_dir) if f.endswith('.json')]


class Dialog:
    @staticmethod
    def select(parent, title, items, on_ok):
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
        def ok():
            sel = lb.curselection()
            if sel:
                on_ok(lb.get(sel[0]))
            win.destroy()
        tk.Button(win, text="Выбрать", command=ok).pack(pady=5)
        tk.Button(win, text="Отмена", command=win.destroy).pack(pady=5)

    @staticmethod
    def del_textures(parent, folder, on_done):
        if not os.path.isdir(folder):
            messagebox.showinfo("", "Нет загруженных текстур")
            return
        files = [f for f in os.listdir(folder) if f.endswith('.png')]
        if not files:
            messagebox.showinfo("", "Нет загруженных текстур")
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
                messagebox.showwarning("", "Ничего не выбрано")
                return
            for idx in sel:
                p = os.path.join(folder, lb.get(idx))
                try:
                    os.remove(p)
                except:
                    pass
            win.destroy()
            on_done()
        def delete_all():
            if messagebox.askyesno("", "Удалить все текстуры?"):
                for f in files:
                    try:
                        os.remove(os.path.join(folder, f))
                    except:
                        pass
                win.destroy()
                on_done()
        frm = tk.Frame(win)
        frm.pack(pady=10)
        tk.Button(frm, text="Удалить выбранные", command=delete_sel).pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Удалить всё", command=delete_all).pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Отмена", command=win.destroy).pack(side=tk.LEFT, padx=5)


class UIBuilder:
    def __init__(self, parent, tex, callbacks):
        self.parent = parent
        self.tex = tex
        self.cb = callbacks

    def _btn(self, parent, icon, text, cmd, compound=tk.LEFT):
        img = self.tex.get_icon(icon)
        if img:
            return tk.Button(parent, image=img, text=text, compound=compound, relief=tk.SOLID, bd=1, command=cmd)
        else:
            return tk.Button(parent, text=text, bg=WHITE, relief=tk.SOLID, bd=1, command=cmd)

    def build_toolbar(self, parent):
        b = self._btn(parent, "void.png", None, lambda: self.cb["set_tool"](EMPTY, False))
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "fence.png", None, lambda: self.cb["set_tool"](None, True))
        b.pack(side=tk.LEFT, padx=2)
        for code, img in self.tex.thumbs.items():
            btn = tk.Button(parent, image=img, relief=tk.SOLID, bd=1,
                            command=lambda c=code: self.cb["set_tool"](c, False))
            btn.pack(side=tk.LEFT, padx=2)

    def build_action(self, parent):
        down = self.tex.get_icon("download.png")
        up = self.tex.get_icon("upload.png")

        if down:
            btn = tk.Button(parent, image=down, text=".png", compound=tk.LEFT, relief=tk.SOLID, bd=1, command=self.cb["save_png"])
        else:
            btn = tk.Button(parent, text="Сохранить PNG", bg=WHITE, width=12, command=self.cb["save_png"])
        btn.pack(side=tk.LEFT, padx=2)

        if down:
            btn = tk.Button(parent, image=down, text=".json", compound=tk.LEFT, relief=tk.SOLID, bd=1, command=self.cb["save_json"])
        else:
            btn = tk.Button(parent, text="Сохранить JSON", bg=WHITE, width=13, command=self.cb["save_json"])
        btn.pack(side=tk.LEFT, padx=2)

        if up:
            btn = tk.Button(parent, image=up, text=".json", compound=tk.LEFT, relief=tk.SOLID, bd=1, command=self.cb["load_json"])
        else:
            btn = tk.Button(parent, text="Загрузить JSON", bg=WHITE, width=13, command=self.cb["load_json"])
        btn.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        b = self._btn(parent, "clear.png", None, self.cb["clear"])
        b.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        b = self._btn(parent, "undo.png", None, self.cb["undo"])
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "redo.png", None, self.cb["redo"])
        b.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        b = self._btn(parent, "add.png", "files", self.cb["import_textures"])
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "remove.png", "files", self.cb["delete_textures"])
        b.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        tk.Button(parent, text="Загрузить пресет", bg=WHITE, width=14, command=self.cb["load_preset"]).pack(side=tk.LEFT, padx=2)
        tk.Button(parent, text="Сохранить пресет", bg=WHITE, width=16, command=self.cb["save_preset"]).pack(side=tk.LEFT, padx=2)

    def _sep(self, parent):
        tk.Frame(parent, width=1, bg=GREY, relief=tk.RAISED).pack(side=tk.LEFT, padx=5, fill=tk.Y)


class Editor:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор карты")
        self.root.geometry(f"{WIDTH+20}x{HEIGHT+135}")

        self.block_dir = path(os.path.join("assets", "textures", "block"))
        self.gui_dir = path(os.path.join("assets", "textures", "gui"), internal=True)
        self.preset_dir = path(os.path.join("assets", "presets"))

        self.tex = TexMgr()
        self.map = Map()
        self.undo = UndoMgr()
        self.file = FileMgr(self.map, self.tex, None, self.preset_dir)

        self.tex.load_blocks(self.block_dir)
        self.tex.load_icons(self.gui_dir)

        self.tool = EMPTY
        self.fence = False
        self._drag = False
        self._last = None
        self.current_layer = 0
        self.layer_buttons = []
        self.layer_check_vars = []
        self.canvas = None
        self.status = None
        self.panel = None
        self.layer_frame = None
        self._setup_ui()
        self.draw()
        self.file.canvas = self.canvas

        self.root.bind("<Control-z>", lambda e: self.undo_op())
        self.root.bind("<Control-y>", lambda e: self.redo_op())
        self.root.bind("<Control-Z>", lambda e: self.redo_op())

    def _setup_ui(self):
        self.status = tk.Label(self.root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg=WHITE)
        self.canvas.pack(pady=5)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._release)

        self.layer_frame = tk.Frame(self.root, bg=L_GREY, pady=5)
        self.layer_frame.pack(fill=tk.X)
        tk.Label(self.layer_frame, text="Слои:", bg=L_GREY).pack(side=tk.LEFT, padx=5)
        self._rebuild_layer_panel()

        self._rebuild_toolbar()

        act = tk.Frame(self.root, bg=L_GREY, pady=5)
        act.pack(fill=tk.X)
        cb = {
            "save_png": self.save_png,
            "save_json": self.save_json,
            "load_json": self.load_json,
            "clear": self.clear,
            "undo": self.undo_op,
            "redo": self.redo_op,
            "import_textures": self.import_tex,
            "delete_textures": self.del_tex,
            "load_preset": self.load_preset,
            "save_preset": self.save_preset,
        }
        self.ui = UIBuilder(self.root, self.tex, cb)
        self.ui.build_action(act)

    def _rebuild_layer_panel(self):
        children = list(self.layer_frame.winfo_children())
        for child in children:
            if child != children[0]:
                child.destroy()
        self.layer_buttons = []
        self.layer_check_vars = []
        num = self.map.get_num_layers()
        for i in range(num):
            btn = tk.Button(self.layer_frame, text=f"Слой {i+1}", width=8,
                            command=lambda idx=i: self.set_active_layer(idx))
            btn.pack(side=tk.LEFT, padx=2)
            self.layer_buttons.append(btn)
            var = tk.BooleanVar(value=self.map.visible[i])
            chk = tk.Checkbutton(self.layer_frame, text="", bg=L_GREY,
                                 variable=var, command=lambda idx=i: self.toggle_visibility(idx))
            chk.pack(side=tk.LEFT, padx=1)
            self.layer_check_vars.append(var)
        btn_add = tk.Button(self.layer_frame, text="+", width=3, command=self.add_layer)
        btn_add.pack(side=tk.LEFT, padx=5)
        btn_remove = tk.Button(self.layer_frame, text="-", width=3, command=self.remove_layer)
        btn_remove.pack(side=tk.LEFT, padx=2)
        self.set_active_layer(self.current_layer)

    def add_layer(self):
        if self.map.get_num_layers() < MAX_LAYERS_LIMIT:
            self.map.add_layer()
            self._rebuild_layer_panel()
            self.set_active_layer(self.map.get_num_layers() - 1)
            self.draw()

    def remove_layer(self):
        if self.map.get_num_layers() > 1:
            old_idx = self.current_layer
            if self.map.remove_layer(self.current_layer):
                new_idx = old_idx - 1 if old_idx > 0 else 0
                self._rebuild_layer_panel()
                self.set_active_layer(new_idx)
                self.draw()

    def set_active_layer(self, idx):
        if 0 <= idx < self.map.get_num_layers():
            self.current_layer = idx
            for i, btn in enumerate(self.layer_buttons):
                if i == idx:
                    btn.config(relief=tk.SUNKEN, bg="lightblue")
                else:
                    btn.config(relief=tk.RAISED, bg="SystemButtonFace")
            self.update_status()

    def toggle_visibility(self, idx):
        if 0 <= idx < len(self.layer_check_vars):
            self.map.visible[idx] = self.layer_check_vars[idx].get()
            self.draw()

    def update_status(self):
        if self.fence:
            tool_text = "Граница"
        elif self.tool == EMPTY:
            tool_text = "Пустой"
        else:
            name = [n for n, c in self.tex.codes.items() if c == self.tool]
            tool_text = name[0] if name else "Текстура"
        self.status.config(text=f"Инструмент: {tool_text} | Слой: {self.current_layer+1} из {self.map.get_num_layers()}")

    def _rebuild_toolbar(self):
        if self.panel:
            self.panel.destroy()
        self.panel = tk.Frame(self.root, bg=L_GREY, pady=5)
        self.panel.pack(fill=tk.X, after=self.canvas)
        self.ui = UIBuilder(self.root, self.tex, {"set_tool": self.set_tool})
        self.ui.build_toolbar(self.panel)

    def set_tool(self, code, fence):
        self.fence = fence
        if fence:
            self.tool = None
        else:
            self.tool = code
        self.update_status()

    def draw(self):
        self.canvas.delete("all")
        for layer_idx, layer in enumerate(self.map.layers):
            if not self.map.visible[layer_idx]:
                continue
            for y in range(H):
                for x in range(W):
                    t = layer.grid[y][x]
                    if t != EMPTY and (img := self.tex.get_block(t)):
                        x1, y1 = x*CELL, y*CELL
                        self.canvas.create_image(x1, y1, anchor=tk.NW, image=img)
            for y in range(H+1):
                for x in range(W):
                    if layer.fh[y][x]:
                        self.canvas.create_line(x*CELL, y*CELL, (x+1)*CELL, y*CELL, fill=BLACK, width=2)
            for y in range(H):
                for x in range(W+1):
                    if layer.fv[y][x]:
                        self.canvas.create_line(x*CELL, y*CELL, x*CELL, (y+1)*CELL, fill=BLACK, width=2)
        for y in range(H):
            for x in range(W):
                x1, y1 = x*CELL, y*CELL
                x2, y2 = x1+CELL, y1+CELL
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1)

    def _press(self, e):
        self._save_state()
        self._drag = True
        xc, yc = e.x // CELL, e.y // CELL
        if 0 <= yc < H and 0 <= xc < W:
            self._last = (xc, yc)
            self._apply(e.x, e.y)

    def _drag_move(self, e):
        if not self._drag or self.fence:
            return
        xc, yc = e.x // CELL, e.y // CELL
        if not (0 <= yc < H and 0 <= xc < W):
            return
        if self._last:
            x0, y0 = self._last
            cells = self._line(x0, y0, xc, yc)
            changed = False
            for cx, cy in cells:
                if self._brush(cx, cy):
                    changed = True
            if changed:
                self.draw()
        else:
            self._apply(e.x, e.y)
        self._last = (xc, yc)

    def _release(self, e):
        self._drag = False
        self._last = None

    def _line(self, x0, y0, x1, y1):
        cells = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            cells.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return cells

    def _brush(self, x, y):
        if not (0 <= y < H and 0 <= x < W) or self.fence or self.tool is None:
            return False
        layer = self.map.get_active_layer(self.current_layer)
        if layer.grid[y][x] != self.tool:
            layer.grid[y][x] = self.tool
            return True
        return False

    def _apply(self, px, py):
        xc, yc = px // CELL, py // CELL
        if not (0 <= yc < H and 0 <= xc < W):
            return
        layer = self.map.get_active_layer(self.current_layer)
        if self.fence:
            x0, y0 = xc*CELL, yc*CELL
            d = [abs(py - y0), abs(py - (y0+CELL)), abs(px - x0), abs(px - (x0+CELL))]
            m = min(d)
            if m > 6:
                return
            if m == d[0] and yc > 0:
                layer.fh[yc][xc] = not layer.fh[yc][xc]
            elif m == d[1] and yc < H:
                layer.fh[yc+1][xc] = not layer.fh[yc+1][xc]
            elif m == d[2] and xc > 0:
                layer.fv[yc][xc] = not layer.fv[yc][xc]
            elif m == d[3] and xc < W:
                layer.fv[yc][xc+1] = not layer.fv[yc][xc+1]
            self.draw()
        else:
            if self.tool is not None:
                layer.grid[yc][xc] = self.tool
                self.draw()

    def _save_state(self):
        self.undo.save(self.map.get())

    def undo_op(self):
        if s := self.undo.undo_op(self.map.get()):
            self.map.set(s)
            self._rebuild_layer_panel()
            if self.current_layer >= self.map.get_num_layers():
                self.current_layer = self.map.get_num_layers() - 1
            self.set_active_layer(self.current_layer)
            self.draw()

    def redo_op(self):
        if s := self.undo.redo_op(self.map.get()):
            self.map.set(s)
            self._rebuild_layer_panel()
            if self.current_layer >= self.map.get_num_layers():
                self.current_layer = self.map.get_num_layers() - 1
            self.set_active_layer(self.current_layer)
            self.draw()

    def save_png(self):
        f = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG","*.png")])
        if f and self.file.save_png(f):
            messagebox.showinfo("", "PNG сохранён")

    def save_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if f and self.file.save_json(f):
            messagebox.showinfo("", "JSON сохранён")

    def load_json(self):
        f = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if f:
            try:
                self._save_state()
                if self.file.load_json(f):
                    self._rebuild_layer_panel()
                    self.current_layer = 0
                    self.set_active_layer(0)
                    self.draw()
                    messagebox.showinfo("", "Карта загружена")
            except Exception as e:
                messagebox.showerror("", f"Ошибка загрузки: {e}")

    def clear(self):
        if messagebox.askyesno("", "Очистить все слои?"):
            self._save_state()
            self.map.clear_all()
            self.draw()
        else:
            self._save_state()
            self.map.clear_layer(self.current_layer)
            self.draw()

    def import_tex(self):
        files = filedialog.askopenfilenames(filetypes=[("PNG","*.png")])
        if not files:
            return
        os.makedirs(self.block_dir, exist_ok=True)
        for src in files:
            dst = os.path.join(self.block_dir, os.path.basename(src))
            shutil.copy(src, dst)
        self.tex.load_blocks(self.block_dir)
        self._rebuild_toolbar()
        self.draw()
        messagebox.showinfo("", f"Загружено {len(files)} текстур")

    def del_tex(self):
        def done():
            self.tex.load_blocks(self.block_dir)
            self._rebuild_toolbar()
            self.draw()
            messagebox.showinfo("", "Текстуры обновлены")
        Dialog.del_textures(self.root, self.block_dir, done)

    def load_preset(self):
        lst = self.file.list_presets()
        if not lst:
            messagebox.showinfo("", "Папка presets пуста")
            return
        def on_ok(name):
            self._save_state()
            if self.file.load_preset(name):
                self._rebuild_layer_panel()
                self.current_layer = 0
                self.set_active_layer(0)
                self.draw()
                messagebox.showinfo("", f"Пресет '{name}' загружен")
        Dialog.select(self.root, "Выберите пресет", lst, on_ok)

    def save_preset(self):
        name = simpledialog.askstring("", "Введите название шаблона:", parent=self.root)
        if name:
            saved = self.file.save_preset(name)
            if saved:
                messagebox.showinfo("", f"Пресет сохранён как '{saved}.json'")


if __name__ == "__main__":
    root = tk.Tk()
    app = Editor(root)
    root.mainloop()