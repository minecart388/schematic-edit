import tkinter as tk
from tkinter import filedialog, simpledialog
import os
import shutil
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw
from config import CFG, EMPTY
from core import TexMgr, Map, UndoMgr, FileMgr, Dialog, path, Msg
from ui_builder import UIBuilder

class Editor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Редактор карты")
        self.root.geometry(f"{CFG.width_px+20}x{CFG.height_px+135}")

        self.block_dir = path(os.path.join("assets", "textures", "block"))
        self.gui_dir = path(os.path.join("assets", "textures", "gui"), internal=True)
        self.preset_dir = path(os.path.join("assets", "presets"))

        self.tex = TexMgr()
        self.map = Map()
        self.undo = UndoMgr()
        self.file = FileMgr(self.map, self.tex, self.preset_dir)

        self.tex.load_blocks(self.block_dir)
        self.tex.load_icons(self.gui_dir)

        self.tool: Optional[int] = EMPTY
        self.fence: bool = False
        self.pipette_mode: bool = False
        self.flood_mode: bool = False
        self.fill_tool: int = EMPTY

        self._drag: bool = False
        self._last: Optional[Tuple[int, int]] = None

        self.current_layer: int = 0

        self.canvas: Optional[tk.Canvas] = None
        self.status: Optional[tk.Label] = None
        self.toolbar: Optional[tk.Frame] = None
        self.layer_frame: Optional[tk.Frame] = None
        self.layer_spinbox: Optional[tk.Spinbox] = None
        self.visible_var: Optional[tk.BooleanVar] = None

        self.brush_size: int = 1
        self.brush_size_label: Optional[tk.Label] = None
        self.show_grid: bool = True

        self._setup_ui()
        self.draw()

        self.root.bind("<Control-z>", lambda e: self.undo_op())
        self.root.bind("<Control-y>", lambda e: self.redo_op())
        self.root.bind("<Control-Z>", lambda e: self.redo_op())

    def _setup_ui(self) -> None:
        self.status = tk.Label(self.root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(self.root, width=CFG.width_px, height=CFG.height_px, bg=CFG.colors["WHITE"])
        self.canvas.pack(pady=5)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Alt-Button-1>", self._pick_texture)

        self._rebuild_toolbar()
        self._setup_layer_panel()
        self._setup_bottom_panel()

    def _setup_layer_panel(self) -> None:
        self.layer_frame = tk.Frame(self.root, bg=CFG.colors["L_GREY"], pady=5)
        self.layer_frame.pack(fill=tk.X)

        tk.Label(self.layer_frame, text="Слой:", bg=CFG.colors["L_GREY"]).pack(side=tk.LEFT, padx=5)

        self.layer_spinbox = tk.Spinbox(
            self.layer_frame, from_=1, to=CFG.max_layers, width=5,
            command=self._spinbox_changed
        )
        self.layer_spinbox.pack(side=tk.LEFT, padx=2)
        self.layer_spinbox.bind("<Return>", lambda e: self._spinbox_changed())

        btn_add = tk.Button(self.layer_frame, text="+", width=2, command=self.add_layer)
        btn_add.pack(side=tk.LEFT, padx=5)
        btn_remove = tk.Button(self.layer_frame, text="-", width=2, command=self.remove_layer)
        btn_remove.pack(side=tk.LEFT, padx=2)

        self.visible_var = tk.BooleanVar(value=True)
        chk_visible = tk.Checkbutton(
            self.layer_frame, text="Вид", variable=self.visible_var,
            command=self._toggle_visibility, bg=CFG.colors["L_GREY"]
        )
        chk_visible.pack(side=tk.LEFT, padx=10)

        btn_manager = tk.Button(self.layer_frame, text="Список слоёв", command=self._open_layer_manager)
        btn_manager.pack(side=tk.LEFT, padx=5)

        self._update_layer_ui()

    def _setup_bottom_panel(self) -> None:
        bottom = tk.Frame(self.root, bg=CFG.colors["L_GREY"], pady=5)
        bottom.pack(fill=tk.X)

        callbacks = {
            "save_png": self.save_png,
            "save_json": self.save_json,
            "load_json": self.load_json,
            "clear": self.clear,
            "undo": self.undo_op,
            "redo": self.redo_op,
            "import_textures": self.import_tex,
            "delete_textures": self.del_tex,
            "load_preset": self.load_preset,
            "save_preset": self.save_preset
        }
        
        ui = UIBuilder(self.tex, {})
        ui.build_action(bottom, callbacks)

        self._sep(bottom)

        tk.Label(bottom, text="Кисть:", bg=CFG.colors["L_GREY"]).pack(side=tk.LEFT, padx=5)
        self.brush_size_label = tk.Label(bottom, text=f"{self.brush_size}", width=3, bg="white", relief=tk.SUNKEN)
        self.brush_size_label.pack(side=tk.LEFT, padx=2)
        btn_minus = tk.Button(bottom, text="-", width=2, command=self._dec_brush)
        btn_minus.pack(side=tk.LEFT, padx=1)
        btn_plus = tk.Button(bottom, text="+", width=2, command=self._inc_brush)
        btn_plus.pack(side=tk.LEFT, padx=1)

        self.grid_var = tk.BooleanVar(value=True)
        chk_grid = tk.Checkbutton(bottom, text="Сетка", variable=self.grid_var, command=self.toggle_grid, bg=CFG.colors["L_GREY"])
        chk_grid.pack(side=tk.LEFT, padx=10)

    def _sep(self, parent: tk.Frame) -> None:
        tk.Frame(parent, width=1, bg=CFG.colors["GREY"], relief=tk.RAISED).pack(side=tk.LEFT, padx=5, fill=tk.Y)

    def _update_layer_ui(self) -> None:
        self.layer_spinbox.delete(0, tk.END)
        self.layer_spinbox.insert(0, str(self.current_layer + 1))
        self.visible_var.set(self.map.visible[self.current_layer])

    def _spinbox_changed(self) -> None:
        try:
            new = int(self.layer_spinbox.get()) - 1
            if 0 <= new < self.map.get_num_layers():
                self.set_active_layer(new)
            else:
                self._update_layer_ui()
        except ValueError:
            self._update_layer_ui()

    def _toggle_visibility(self) -> None:
        self.map.visible[self.current_layer] = self.visible_var.get()
        self.draw()

    def _open_layer_manager(self) -> None:
        LayerManagerDialog(self.root, self)

    def set_active_layer(self, idx: int) -> None:
        if 0 <= idx < self.map.get_num_layers():
            self.current_layer = idx
            self._update_layer_ui()
            self.update_status()

    def add_layer(self) -> None:
        if self.map.get_num_layers() < CFG.max_layers:
            self.map.add_layer()
            self.current_layer = self.map.get_num_layers() - 1
            self._update_layer_ui()
            self.draw()
            self.update_status()
        else:
            Msg.warn(f"Максимальное количество слоёв: {CFG.max_layers}")

    def remove_layer(self) -> None:
        if self.map.get_num_layers() <= 1:
            Msg.warn("Нельзя удалить единственный слой")
            return
        
        self.map.remove_layer(self.current_layer)
        if self.current_layer >= self.map.get_num_layers():
            self.current_layer = self.map.get_num_layers() - 1
        self._update_layer_ui()
        self.draw()

    def set_tool(self, code: Optional[int], fence: bool) -> None:
        if code != -1 and code != -2:
            self.pipette_mode = False
            self.flood_mode = False
            self.fence = fence
            if fence:
                self.tool = None
            else:
                self.tool = code
            self.update_status()
            return

        if code == -1:
            self.pipette_mode = True
            self.flood_mode = False
            self.fence = False
            self.tool = None
            self.update_status()
            return

        if code == -2:
            if self.tool is not None and self.tool != EMPTY and not self.fence:
                self.fill_tool = self.tool
                self.flood_mode = True
                self.pipette_mode = False
                self.fence = False
                self.update_status()
            else:
                Msg.warn("Сначала выберите текстуру для заливки")

    def _pick_texture(self, event: tk.Event) -> None:
        xc = event.x // CFG.cell_size
        yc = event.y // CFG.cell_size
        if not (0 <= xc < CFG.map_width and 0 <= yc < CFG.map_height):
            return
        for idx in range(len(self.map.layers) - 1, -1, -1):
            if not self.map.visible[idx]:
                continue
            tex_code = self.map.layers[idx].grid[yc][xc]
            if tex_code != EMPTY:
                self.set_tool(tex_code, False)
                return

    def _dec_brush(self) -> None:
        if self.brush_size > CFG.brush_min:
            self.brush_size -= 1
            self.brush_size_label.config(text=str(self.brush_size))
            self.update_status()

    def _inc_brush(self) -> None:
        if self.brush_size < CFG.brush_max:
            self.brush_size += 1
            self.brush_size_label.config(text=str(self.brush_size))
            self.update_status()

    def toggle_grid(self) -> None:
        self.show_grid = self.grid_var.get()
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        cell = CFG.cell_size
        w, h = CFG.map_width, CFG.map_height
        for layer_idx, layer in enumerate(self.map.layers):
            if not self.map.visible[layer_idx]:
                continue
            for y in range(h):
                for x in range(w):
                    t = layer.grid[y][x]
                    if t != EMPTY:
                        img = self.tex.get_block(t)
                        if img:
                            self.canvas.create_image(x*cell, y*cell, anchor=tk.NW, image=img)
            for y in range(h+1):
                for x in range(w):
                    if layer.fh[y][x]:
                        self.canvas.create_line(x*cell, y*cell, (x+1)*cell, y*cell, fill=CFG.colors["BLACK"], width=2)
            for y in range(h):
                for x in range(w+1):
                    if layer.fv[y][x]:
                        self.canvas.create_line(x*cell, y*cell, x*cell, (y+1)*cell, fill=CFG.colors["BLACK"], width=2)
        if self.show_grid:
            for x in range(w + 1):
                self.canvas.create_line(x*cell, 0, x*cell, CFG.height_px, fill="gray", width=1)
            for y in range(h + 1):
                self.canvas.create_line(0, y*cell, CFG.width_px, y*cell, fill="gray", width=1)

    def _press(self, e: tk.Event) -> None:
        self._save_state()
        self._drag = True
        xc = e.x // CFG.cell_size
        yc = e.y // CFG.cell_size
        if 0 <= yc < CFG.map_height and 0 <= xc < CFG.map_width:
            self._last = (xc, yc)
            self._apply(e.x, e.y)

    def _drag_move(self, e: tk.Event) -> None:
        if not self._drag or self.fence:
            return
        xc = e.x // CFG.cell_size
        yc = e.y // CFG.cell_size
        if not (0 <= yc < CFG.map_height and 0 <= xc < CFG.map_width):
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

    def _release(self, e: tk.Event) -> None:
        self._drag = False
        self._last = None

    def _line(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
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

    def _brush(self, x: int, y: int) -> bool:
        if self.fence or self.tool is None:
            return False
        layer = self.map.get_active_layer(self.current_layer)
        changed = False
        left = x - (self.brush_size - 1) // 2
        right = x + self.brush_size // 2
        top = y - (self.brush_size - 1) // 2
        bottom = y + self.brush_size // 2
        for ny in range(top, bottom + 1):
            for nx in range(left, right + 1):
                if 0 <= ny < CFG.map_height and 0 <= nx < CFG.map_width:
                    if layer.grid[ny][nx] != self.tool:
                        layer.grid[ny][nx] = self.tool
                        changed = True
        return changed

    def flood_fill(self, x: int, y: int, new_tex: int) -> None:
        layer = self.map.get_active_layer(self.current_layer)
        old_tex = layer.grid[y][x]
        if old_tex == new_tex or new_tex == EMPTY:
            return
        w, h = CFG.map_width, CFG.map_height
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if not (0 <= cx < w and 0 <= cy < h):
                continue
            if layer.grid[cy][cx] != old_tex:
                continue
            layer.grid[cy][cx] = new_tex
            stack.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])
        self.draw()

    def _apply(self, px: int, py: int) -> None:
        xc = px // CFG.cell_size
        yc = py // CFG.cell_size
        if not (0 <= yc < CFG.map_height and 0 <= xc < CFG.map_width):
            return
        layer = self.map.get_active_layer(self.current_layer)
        if self.fence:
            x0, y0 = xc*CFG.cell_size, yc*CFG.cell_size
            d = [abs(py - y0), abs(py - (y0+CFG.cell_size)), abs(px - x0), abs(px - (x0+CFG.cell_size))]
            m = min(d)
            if m > 6:
                return
            if m == d[0] and yc > 0:
                layer.fh[yc][xc] = not layer.fh[yc][xc]
            elif m == d[1] and yc < CFG.map_height:
                layer.fh[yc+1][xc] = not layer.fh[yc+1][xc]
            elif m == d[2] and xc > 0:
                layer.fv[yc][xc] = not layer.fv[yc][xc]
            elif m == d[3] and xc < CFG.map_width:
                layer.fv[yc][xc+1] = not layer.fv[yc][xc+1]
            self.draw()
        elif self.pipette_mode:
            for idx in range(len(self.map.layers) - 1, -1, -1):
                if not self.map.visible[idx]:
                    continue
                tex_code = self.map.layers[idx].grid[yc][xc]
                if tex_code != EMPTY:
                    self.set_tool(tex_code, False)
                    self.pipette_mode = False
                    self._brush(xc, yc)
                    self.draw()
                    self.update_status()
                    return
            self.pipette_mode = False
            self.update_status()
        elif self.flood_mode:
            if self.fill_tool != EMPTY:
                self._save_state()
                self.flood_fill(xc, yc, self.fill_tool)
                self.tool = self.fill_tool
                self.flood_mode = False
                self.update_status()
            else:
                self.flood_mode = False
                self.update_status()
        else:
            self._brush(xc, yc)
            self.draw()

    def _tool_text(self) -> str:
        if self.pipette_mode:
            return "Пипетка"
        if self.flood_mode:
            return "Заливка"
        if self.fence:
            return "Граница"
        elif self.tool == EMPTY:
            return "Пустой"
        else:
            name = [n for n, c in self.tex.codes.items() if c == self.tool]
            return name[0] if name else "Текстура"

    def update_status(self) -> None:
        self.status.config(text=f"{self._tool_text()} | Слой {self.current_layer+1} | Кисть {self.brush_size}")

    def _on_mouse_move(self, event: tk.Event) -> None:
        xc = event.x // CFG.cell_size
        yc = event.y // CFG.cell_size
        if 0 <= xc < CFG.map_width and 0 <= yc < CFG.map_height:
            self.status.config(text=f"({xc}, {yc}) | {self._tool_text()} | Слой {self.current_layer+1} | Кисть {self.brush_size}")
        else:
            self.update_status()

    def _save_state(self) -> None:
        self.undo.save(self.map.get())

    def undo_op(self) -> None:
        if s := self.undo.undo_op(self.map.get()):
            self.map.set(s)
            self._update_layer_ui()
            if self.current_layer >= self.map.get_num_layers():
                self.current_layer = self.map.get_num_layers() - 1
            self.set_active_layer(self.current_layer)
            self.draw()

    def redo_op(self) -> None:
        if s := self.undo.redo_op(self.map.get()):
            self.map.set(s)
            self._update_layer_ui()
            if self.current_layer >= self.map.get_num_layers():
                self.current_layer = self.map.get_num_layers() - 1
            self.set_active_layer(self.current_layer)
            self.draw()

    def save_png(self) -> None:
        if not self.tex.originals:
            Msg.error("Нет загруженных текстур для экспорта")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not file_path:
            return
        scale = 4
        w, h = CFG.map_width, CFG.map_height
        cell = CFG.cell_size
        img_width = w * cell * scale
        img_height = h * cell * scale
        img = Image.new("RGB", (img_width, img_height), CFG.colors["WHITE"])
        draw = ImageDraw.Draw(img)

        for layer_idx, layer in enumerate(self.map.layers):
            if not self.map.visible[layer_idx]:
                continue
            for y in range(h):
                for x in range(w):
                    tex_code = layer.grid[y][x]
                    if tex_code != EMPTY:
                        orig = self.tex.get_original(tex_code)
                        if orig:
                            scaled_tile = orig.resize((cell * scale, cell * scale), Image.Resampling.NEAREST)
                            img.paste(scaled_tile, (x * cell * scale, y * cell * scale))
            for y in range(h + 1):
                for x in range(w):
                    if layer.fh[y][x]:
                        x1 = x * cell * scale
                        y1 = y * cell * scale
                        x2 = (x + 1) * cell * scale
                        draw.line((x1, y1, x2, y1), fill=CFG.colors["BLACK"], width=2 * scale)
            for y in range(h):
                for x in range(w + 1):
                    if layer.fv[y][x]:
                        x1 = x * cell * scale
                        y1 = y * cell * scale
                        y2 = (y + 1) * cell * scale
                        draw.line((x1, y1, x1, y2), fill=CFG.colors["BLACK"], width=2 * scale)

        if self.show_grid:
            for x in range(w + 1):
                x1 = x * cell * scale
                draw.line((x1, 0, x1, img_height), fill="gray", width=2)
            for y in range(h + 1):
                y1 = y * cell * scale
                draw.line((0, y1, img_width, y1), fill="gray", width=2)

        img.save(file_path)
        Msg.info(f"Карта сохранена в {file_path} (масштаб ×{scale})")

    def save_json(self) -> None:
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if f and self.file.save_json(f):
            Msg.info("JSON сохранён")

    def load_json(self) -> None:
        f = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if f:
            try:
                self._save_state()
                if self.file.load_json(f):
                    self._update_layer_ui()
                    self.current_layer = 0
                    self.set_active_layer(0)
                    self.draw()
                    Msg.info("Карта загружена")
            except Exception as e:
                Msg.error(f"Ошибка загрузки: {e}")

    def clear(self) -> None:
        if Msg.ask("Очистить все слои?"):
            self._save_state()
            self.map.clear_all()
            self.draw()
        else:
            self._save_state()
            self.map.clear_layer(self.current_layer)
            self.draw()

    def import_tex(self) -> None:
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
        Msg.info(f"Загружено {len(files)} текстур")

    def del_tex(self) -> None:
        def done():
            self.tex.load_blocks(self.block_dir)
            self._rebuild_toolbar()
            self.draw()
            Msg.info("Текстуры обновлены")
        Dialog.del_textures(self.root, self.block_dir, done)

    def load_preset(self) -> None:
        lst = self.file.list_presets()
        if not lst:
            Msg.warn("Папка presets пуста")
            return
        
        def on_ok(name: str):
            self._save_state()
            if self.file.load_preset(name):
                self._update_layer_ui()
                self.current_layer = 0
                self.set_active_layer(0)
                self.draw()
                Msg.info(f"Пресет '{name}' загружен")
        
        def on_delete(name: str):
            if Msg.ask(f"Удалить пресет '{name}'?"):
                preset_path = os.path.join(self.preset_dir, name + ".json")
                try:
                    os.remove(preset_path)
                    Msg.info(f"Пресет '{name}' удалён")
                except Exception as e:
                    Msg.error(f"Ошибка удаления: {e}")
        
        Dialog.select(self.root, "Выберите пресет", lst, on_ok, on_delete)

    def save_preset(self) -> None:
        name = simpledialog.askstring("", "Введите название шаблона:", parent=self.root)
        if name:
            saved = self.file.save_preset(name)
            if saved:
                Msg.info(f"Пресет сохранён как '{saved}.json'")

    def _rebuild_toolbar(self) -> None:
        if self.toolbar:
            self.toolbar.destroy()
        self.toolbar = tk.Frame(self.root, bg=CFG.colors["L_GREY"], pady=5)
        self.toolbar.pack(fill=tk.X, after=self.canvas)
        ui = UIBuilder(self.tex, {"set_tool": self.set_tool})
        ui.build_toolbar(self.toolbar)


class LayerManagerDialog:
    def __init__(self, parent: tk.Tk, editor: Editor):
        self.editor = editor
        self.window = tk.Toplevel(parent)
        self.window.title("Управление слоями")
        self.window.geometry("370x500")
        self.window.transient(parent)
        self.window.grab_set()

        self.listbox = tk.Listbox(self.window, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.listbox.bind("<Double-Button-1>", self.on_layer_double_click)

        self.visibility_var = tk.BooleanVar()
        self.visibility_check = tk.Checkbutton(
            self.window, text="Вид", variable=self.visibility_var,
            command=self.toggle_visibility
        )
        self.visibility_check.pack(pady=5)

        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Переключиться на выбранный", command=self.switch_to_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить выбранный слой", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i in range(self.editor.map.get_num_layers()):
            visibility = "✓" if self.editor.map.visible[i] else "✗"
            text = f"Слой {i+1} [{visibility}]"
            self.listbox.insert(tk.END, text)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(self.editor.current_layer)
        self.listbox.see(self.editor.current_layer)
        self.visibility_var.set(self.editor.map.visible[self.editor.current_layer])

    def on_layer_double_click(self, event):
        self.switch_to_selected()

    def switch_to_selected(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.editor.set_active_layer(idx)
            self.refresh_list()

    def toggle_visibility(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.editor.map.visible[idx] = self.visibility_var.get()
            self.editor.draw()
            self.refresh_list()
        else:
            self.visibility_var.set(self.editor.map.visible[self.editor.current_layer])

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if self.editor.map.get_num_layers() <= 1:
            Msg.warn("Нельзя удалить единственный слой")
            return
        if Msg.ask(f"Удалить слой {idx+1}?"):
            self.editor.remove_layer(idx)
            self.refresh_list()