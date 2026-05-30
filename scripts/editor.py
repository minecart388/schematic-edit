# editor.py
import tkinter as tk
from tkinter import filedialog
import os
import shutil
from typing import Optional
from PIL import Image, ImageDraw
from .config import CFG, EMPTY, Settings, ProgressDialog
from .core import TexMgr, Map, UndoMgr, FileMgr, path
from .editor_core import ThemeManager, LayerManager, DrawingEngine, Camera, Selection
from .editor_ui import UIManager
from .console import ConsoleManager
from .hotbar import HotbarManager

class ToolManager:
    def __init__(self, editor):
        self.editor = editor
        self.tool: Optional[str] = EMPTY
        self.pipette_mode: bool = False
        self.flood_mode: bool = False
        self.fill_tool: str = EMPTY
        self.brush_size: int = 1
        self.selection_mode: bool = False

    def set_tool(self, code, from_hotbar: bool = False) -> None:
        self.editor.drawing.cancel_primitive()
        if not from_hotbar:
            self.editor.ui.clear_hotbar_selection()
        if code == -1:
            self.pipette_mode = True
            self.flood_mode = False
            self.selection_mode = False
            self.tool = None
            self.editor.update_status()
            return
        if code == -2:
            if self.tool is not None and self.tool != EMPTY:
                self.fill_tool = self.tool
                self.flood_mode = True
                self.pipette_mode = False
                self.selection_mode = False
                self.editor.update_status()
            else:
                self.editor.console._print("Сначала выберите текстуру для заливки", "error")
            return
        if code == -3:
            self.selection_mode = True
            self.pipette_mode = False
            self.flood_mode = False
            self.tool = None
            self.editor.update_status()
            return
        self.pipette_mode = False
        self.flood_mode = False
        self.selection_mode = False
        self.tool = code
        self.editor.update_status()

    def get_tool_name(self) -> str:
        if self.selection_mode:
            return "Выделение"
        if self.pipette_mode:
            return "Пипетка"
        if self.flood_mode:
            return "Заливка"
        if self.tool == EMPTY:
            return "Ластик"
        return self.tool if self.tool else "Текстура"

class Editor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Редактор карты")
        self.root.state('zoomed')
        self.theme = ThemeManager(root)
        self.block_dir = path(os.path.join("assets", "textures", "block"))
        self.gui_dir = path(os.path.join("assets", "textures", "gui"), internal=True)
        self.preset_dir = path(os.path.join("assets", "presets"))
        self.tex = TexMgr()
        self.map = Map(100, 50)
        self.undo = UndoMgr()
        self.file = FileMgr(self.map, self.tex, self.preset_dir)
        self.settings = Settings()
        self.tool_manager = ToolManager(self)
        self.hotbar_mgr = HotbarManager()
        self.tool_manager.brush_size = self.settings.get("brush_size", 1)
        self.show_grid = self.settings.get("show_grid", True)
        theme_name = self.settings.get_theme()
        CFG.set_theme(theme_name)
        self.layer_manager = LayerManager(self)
        self.drawing = DrawingEngine(self)
        self.selection = Selection()
        self.clipboard = None
        self.main_container = tk.Frame(self.root, bg=CFG.colors["BG_PANEL"])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.left_panel = tk.Frame(self.main_container, bg=CFG.colors["BG_PANEL"])
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_panel = tk.Frame(self.main_container, bg=CFG.colors["BG_PANEL"])
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.console = ConsoleManager(self)
        self.console.create(self.right_panel)
        self.tex.load_blocks(self.block_dir, log_func=self.console._print)
        self.tex.load_icons(self.gui_dir)
        self.ui = UIManager(self)
        self.ui.setup(self.left_panel)
        self.camera = Camera(0, 0, self.map.w, self.map.h, CFG.cell_size)
        self.camera.zoom = self.settings.get("zoom", 1.0)
        self.camera.offset_x = self.settings.get("offset_x", 0.0)
        self.camera.offset_y = self.settings.get("offset_y", 0.0)
        self.tex.update_block_size(self.camera.zoom)
        self.apply_theme()
        self.drawing.redraw_visible_tiles()
        self.update_status()
        self.root.bind("<Control-z>", lambda e: self.undo_op())
        self.root.bind("<Control-y>", lambda e: self.redo_op())
        self.root.bind("<Control-Z>", lambda e: self.undo_op())
        self.root.bind("<Control-Y>", lambda e: self.redo_op())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Button-3>", self.on_canvas_right_press)
        self.root.bind("<B3-Motion>", self.on_canvas_right_drag)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def apply_theme(self) -> None:
        self.theme.apply_theme()
        self.console.update_theme()
        if self.ui.hotbar_widget:
            self.ui.hotbar_widget.update_theme()
        self.ui.update_theme()
        if self.ui.canvas:
            self.ui.canvas.config(bg=CFG.colors["BG_CANVAS"])
        self.main_container.configure(bg=CFG.colors["BG_PANEL"])
        self.left_panel.configure(bg=CFG.colors["BG_PANEL"])
        self.right_panel.configure(bg=CFG.colors["BG_PANEL"])
        self.drawing.redraw_visible_tiles()

    def toggle_theme(self) -> None:
        new_theme = "light" if CFG._current_theme == "dark" else "dark"
        CFG.set_theme(new_theme)
        self.settings.set_theme(new_theme)
        self.apply_theme()

    def dec_brush(self) -> None:
        if self.tool_manager.brush_size > CFG.brush_min:
            self.tool_manager.brush_size -= 1
            self.ui.brush_size_label.config(text=str(self.tool_manager.brush_size))
            self.settings.set("brush_size", self.tool_manager.brush_size)
            self.update_status()

    def inc_brush(self) -> None:
        if self.tool_manager.brush_size < CFG.brush_max:
            self.tool_manager.brush_size += 1
            self.ui.brush_size_label.config(text=str(self.tool_manager.brush_size))
            self.settings.set("brush_size", self.tool_manager.brush_size)
            self.update_status()

    def toggle_grid(self) -> None:
        self.show_grid = self.ui.grid_var.get()
        self.settings.set("show_grid", self.show_grid)
        self.drawing.update_grid()
        self.drawing.redraw_visible_tiles()

    def save_state(self) -> None:
        self.undo.save(self.map.get())

    def undo_op(self) -> None:
        if s := self.undo.undo_op(self.map.get()):
            self.map.set(s)
            self.ui.update_layer_ui()
            if self.layer_manager.current_layer >= self.map.get_num_layers():
                self.layer_manager.current_layer = self.map.get_num_layers() - 1
            self.layer_manager.set_active_layer(self.layer_manager.current_layer)
            self.drawing.redraw_visible_tiles()
            self.console._print("Отмена", "success")

    def redo_op(self) -> None:
        if s := self.undo.redo_op(self.map.get()):
            self.map.set(s)
            self.ui.update_layer_ui()
            if self.layer_manager.current_layer >= self.map.get_num_layers():
                self.layer_manager.current_layer = self.map.get_num_layers() - 1
            self.layer_manager.set_active_layer(self.layer_manager.current_layer)
            self.drawing.redraw_visible_tiles()
            self.console._print("Повтор", "success")

    def clear_layer(self, layer_idx: int) -> None:
        if 0 <= layer_idx < self.map.get_num_layers():
            self.save_state()
            self.map.clear_layer(layer_idx)
            self.drawing.redraw_visible_tiles()
            self.console._print(f"✓ Слой {layer_idx+1} очищен", "success")

    def clear_all_layers(self) -> None:
        self.save_state()
        self.map.clear_all()
        self.drawing.redraw_visible_tiles()
        self.console._print("✓ Все слои очищены", "success")

    def save_png(self) -> None:
        initial_dir = self.settings.get("last_export_path", "")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialdir=initial_dir
        )
        if not file_path:
            return
        self.settings.set("last_export_path", os.path.dirname(file_path))
        self.settings.add_recent_file(file_path)
        total_cells = self.map.h * self.map.w * len(self.map.layers)
        progress = ProgressDialog(self.root, "Сохранение PNG", total_cells)
        scale = 4
        w, h = self.map.w, self.map.h
        cell = CFG.cell_size
        img_width = w * cell * scale
        img_height = h * cell * scale
        bg_color = CFG.colors["BG_CANVAS"]
        img = Image.new("RGBA", (img_width, img_height), bg_color)
        processed = 0
        for layer_idx, layer in enumerate(self.map.layers):
            if not self.map.visible[layer_idx]:
                processed += w * h
                continue
            for y in range(h):
                for x in range(w):
                    if progress.is_cancelled():
                        progress.close()
                        return
                    tex_name = layer.grid[y][x]
                    if tex_name != EMPTY:
                        orig = self.tex.get_original(tex_name)
                        if orig:
                            scaled_tile = orig.resize((cell * scale, cell * scale), Image.Resampling.NEAREST)
                            if scaled_tile.mode == 'RGBA':
                                img.paste(scaled_tile, (x * cell * scale, y * cell * scale), scaled_tile)
                            else:
                                img.paste(scaled_tile, (x * cell * scale, y * cell * scale))
                    processed += 1
                    if processed % 500 == 0:
                        progress.update(processed, f"Слой {layer_idx+1}: {processed}/{total_cells}")
        if self.show_grid:
            draw = ImageDraw.Draw(img)
            for x in range(w + 1):
                x1 = x * cell * scale
                draw.line((x1, 0, x1, img_height), fill=CFG.colors["GRID"], width=2)
            for y in range(h + 1):
                y1 = y * cell * scale
                draw.line((0, y1, img_width, y1), fill=CFG.colors["GRID"], width=2)
        if img.mode == 'RGBA':
            rgb_img = Image.new("RGB", img.size, bg_color)
            rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
            img = rgb_img
        img.save(file_path)
        progress.close()
        self.console._print(f"Карта сохранена в {file_path}", "success")

    def save_json(self) -> None:
        initial_dir = self.settings.get("last_json_path", "")
        f = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=initial_dir
        )
        if f:
            self.settings.set("last_json_path", os.path.dirname(f))
            self.settings.add_recent_file(f)
            if self.file.save_json(f):
                self.console._print("JSON сохранён", "success")

    def load_json(self) -> None:
        initial_dir = self.settings.get("last_json_path", "")
        f = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")],
            initialdir=initial_dir
        )
        if f:
            try:
                self.save_state()
                if self.file.load_json(f):
                    self.settings.set("last_json_path", os.path.dirname(f))
                    self.settings.add_recent_file(f)
                    self.ui.update_layer_ui()
                    self.layer_manager.current_layer = 0
                    self.layer_manager.set_active_layer(0)
                    self.camera.set_map_size(self.map.w, self.map.h)
                    self.camera.clamp()
                    self.tex.update_block_size(self.camera.zoom)
                    self.drawing.redraw_visible_tiles()
                    self.console._print("Карта загружена", "success")
            except Exception as e:
                self.console._print(f"Ошибка загрузки: {e}", "error")

    def resize_map(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Изменить размер карты")
        dialog.geometry("270x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=CFG.colors["BG_PANEL"])
        colors = CFG.colors
        frame = tk.Frame(dialog, bg=colors["BG_PANEL"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(frame, text="Ширина:", bg=colors["BG_PANEL"], fg=colors["TEXT"]).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        width_entry = tk.Entry(frame, width=10, bg=colors["BUTTON"], fg=colors["TEXT"])
        width_entry.insert(0, str(self.map.w))
        width_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(frame, text="Высота:", bg=colors["BG_PANEL"], fg=colors["TEXT"]).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        height_entry = tk.Entry(frame, width=10, bg=colors["BUTTON"], fg=colors["TEXT"])
        height_entry.insert(0, str(self.map.h))
        height_entry.grid(row=1, column=1, padx=5, pady=5)
        shift_frame = tk.Frame(frame, bg=colors["BG_PANEL"])
        shift_frame.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Label(shift_frame, text="Сдвиг X:", bg=colors["BG_PANEL"], fg=colors["TEXT"]).pack(side=tk.LEFT, padx=5)
        shift_x_entry = tk.Entry(shift_frame, width=5, bg=colors["BUTTON"], fg=colors["TEXT"])
        shift_x_entry.insert(0, "0")
        shift_x_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(shift_frame, text="Сдвиг Y:", bg=colors["BG_PANEL"], fg=colors["TEXT"]).pack(side=tk.LEFT, padx=5)
        shift_y_entry = tk.Entry(shift_frame, width=5, bg=colors["BUTTON"], fg=colors["TEXT"])
        shift_y_entry.insert(0, "0")
        shift_y_entry.pack(side=tk.LEFT, padx=5)
        crop_var = tk.BooleanVar(value=False)
        crop_check = tk.Checkbutton(frame, text="Обрезать содержимое (иначе сдвинуть)", variable=crop_var,
                                    bg=colors["BG_PANEL"], fg=colors["TEXT"], selectcolor=colors["BG_PANEL"])
        crop_check.grid(row=3, column=0, columnspan=2, pady=5)

        def apply():
            try:
                new_w = int(width_entry.get())
                new_h = int(height_entry.get())
                if new_w < 1 or new_h < 1:
                    raise ValueError
                shift_x = int(shift_x_entry.get())
                shift_y = int(shift_y_entry.get())
                if crop_var.get():
                    shift_x = shift_y = 0
                self.save_state()
                self.map.resize(new_w, new_h, shift_x, shift_y)
                self.camera.set_map_size(new_w, new_h)
                self.camera.clamp()
                self.tex.update_block_size(self.camera.zoom)
                self.drawing.redraw_visible_tiles()
                self.console._print(f"Размер карты изменён на {new_w}x{new_h}", "success")
                dialog.destroy()
            except ValueError:
                self.console._print("Введите корректные числа", "error")

        tk.Button(frame, text="Применить", command=apply, bg=colors["BUTTON"], fg=colors["TEXT"]).grid(row=4, column=0, columnspan=2, pady=10)

    def center_map(self) -> None:
        canvas_width = self.ui.canvas.winfo_width()
        canvas_height = self.ui.canvas.winfo_height()
        if canvas_width <= 0 or canvas_height <= 0:
            canvas_width = self.camera.canvas_width
            canvas_height = self.camera.canvas_height
        map_width_px = self.map.w * CFG.cell_size
        map_height_px = self.map.h * CFG.cell_size
        if map_width_px <= 0 or map_height_px <= 0:
            return
        zoom_x = canvas_width / map_width_px
        zoom_y = canvas_height / map_height_px
        new_zoom = min(zoom_x, zoom_y)
        new_zoom = max(self.camera.min_zoom, min(self.camera.max_zoom, new_zoom))
        if new_zoom != self.camera.zoom:
            self.camera.zoom = new_zoom
            self.tex.update_block_size(self.camera.zoom)
        self.camera.offset_x = (canvas_width / new_zoom - map_width_px) / 2
        self.camera.offset_y = (canvas_height / new_zoom - map_height_px) / 2
        self.camera.clamp()
        self.settings.set("zoom", self.camera.zoom)
        self.settings.set("offset_x", self.camera.offset_x)
        self.settings.set("offset_y", self.camera.offset_y)
        self.drawing.redraw_visible_tiles()
        self.update_status()

    def import_tex(self) -> None:
        initial_dir = self.settings.get("last_import_path", "")
        files = filedialog.askopenfilenames(
            filetypes=[("PNG", "*.png")],
            initialdir=initial_dir
        )
        if not files:
            return
        self.settings.set("last_import_path", os.path.dirname(files[0]))
        progress = ProgressDialog(self.root, "Импорт текстур", len(files))
        os.makedirs(self.block_dir, exist_ok=True)
        for i, src in enumerate(files):
            if progress.is_cancelled():
                break
            dst = os.path.join(self.block_dir, os.path.basename(src))
            shutil.copy(src, dst)
            progress.update(i + 1, f"Копирование {os.path.basename(src)}")
        progress.close()
        self.tex.load_blocks(self.block_dir, log_func=self.console._print)
        self.tex.update_block_size(self.camera.zoom)
        self.ui.refresh_hotbar()
        self.drawing.redraw_visible_tiles()
        self.console._print(f"Загружено {len(files)} текстур", "success")

    def del_tex(self) -> None:
        if not os.path.isdir(self.block_dir):
            self.console._print("Нет загруженных текстур", "error")
            return
        files = [f for f in os.listdir(self.block_dir) if f.endswith('.png')]
        if not files:
            self.console._print("Нет загруженных текстур", "error")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Удаление текстур")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=CFG.colors["BG_PANEL"])
        text_frame = tk.Frame(dialog, bg=CFG.colors["BG_PANEL"])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, height=15,
                              bg=CFG.colors["BG_CANVAS"], fg=CFG.colors["TEXT"])
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        text_widget.insert(tk.END, "ДОСТУПНЫЕ ТЕКСТУРЫ:\n\n")
        for i, f in enumerate(sorted(files)):
            text_widget.insert(tk.END, f"  {i+1}. {f}\n")
        text_widget.insert(tk.END, "\nВведите номера текстур для удаления (через пробел)\nили 'all' для удаления всех:")
        text_widget.configure(state=tk.DISABLED)
        entry_frame = tk.Frame(dialog, bg=CFG.colors["BG_PANEL"])
        entry_frame.pack(fill=tk.X, padx=10, pady=5)
        entry = tk.Entry(entry_frame, bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"])
        entry.pack(fill=tk.X)
        entry.focus()

        def on_submit():
            self._delete_textures_callback(entry.get())
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=CFG.colors["BG_PANEL"])
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Удалить", command=on_submit,
                 bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"]).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=on_cancel,
                 bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"]).pack(side=tk.LEFT, padx=5)
        entry.bind("<Return>", lambda e: on_submit())

    def _delete_textures_callback(self, answer: str) -> None:
        files = [f for f in os.listdir(self.block_dir) if f.endswith('.png')]
        if answer.lower() == 'all':
            for f in files:
                try:
                    os.remove(os.path.join(self.block_dir, f))
                except OSError:
                    pass
            self.tex.load_blocks(self.block_dir, log_func=self.console._print)
            self.tex.update_block_size(self.camera.zoom)
            self.ui.refresh_hotbar()
            self.drawing.redraw_visible_tiles()
            self.console._print("Все текстуры удалены", "success")
            return
        try:
            indices = [int(x.strip()) - 1 for x in answer.split()]
            deleted = []
            for idx in indices:
                if 0 <= idx < len(files):
                    os.remove(os.path.join(self.block_dir, files[idx]))
                    deleted.append(files[idx])
            if deleted:
                self.tex.load_blocks(self.block_dir, log_func=self.console._print)
                self.tex.update_block_size(self.camera.zoom)
                self.ui.refresh_hotbar()
                self.drawing.redraw_visible_tiles()
                self.console._print(f"Удалено текстур: {len(deleted)}", "success")
            else:
                self.console._print("Ничего не удалено", "warning")
        except ValueError:
            self.console._print("Ошибка: неверный формат", "error")

    def load_preset(self) -> None:
        presets = self.file.list_presets()
        if not presets:
            self.console._print("Нет доступных пресетов", "error")
            return
        self.console.show_preset_selection(presets)

    def save_preset(self) -> None:
        self.console.ask_input("Введите название пресета:", self.save_preset_with_name)

    def save_preset_with_name(self, name: str) -> None:
        if not name.strip():
            self.console._print("Ошибка: название не может быть пустым", "error")
            return
        saved = self.file.save_preset(name.strip())
        if saved:
            self.console._print(f"Пресет сохранён как '{saved}.json'", "success")
        else:
            self.console._print("Ошибка сохранения пресета", "error")

    def update_status(self) -> None:
        tool_text = self.tool_manager.get_tool_name()
        self.ui.update_status(f"{tool_text} | Слой {self.layer_manager.current_layer + 1} | Кисть {self.tool_manager.brush_size} | Zoom {self.camera.zoom:.1f}x")

    def on_mouse_move(self, event: tk.Event) -> None:
        wx, wy = self.camera.screen_to_world(event.x, event.y)
        xc = int(wx)
        yc = int(wy)
        if 0 <= xc < self.map.w and 0 <= yc < self.map.h:
            self.ui.update_status(f"({xc}, {yc}) | {self.tool_manager.get_tool_name()} | Слой {self.layer_manager.current_layer + 1} | Кисть {self.tool_manager.brush_size} | Zoom {self.camera.zoom:.1f}x")

    def on_canvas_right_press(self, event: tk.Event) -> None:
        self.camera.pan_start(event.x, event.y)

    def on_canvas_right_drag(self, event: tk.Event) -> None:
        self.camera.pan_move(event.x, event.y)
        self.drawing.redraw_visible_tiles()

    def on_mousewheel(self, event: tk.Event) -> None:
        if hasattr(event, 'delta') and event.delta:
            factor = 1.1 if event.delta > 0 else 0.9
        elif hasattr(event, 'num') and event.num == 4:
            factor = 1.1
        elif hasattr(event, 'num') and event.num == 5:
            factor = 0.9
        else:
            return
        old_zoom = self.camera.zoom
        self.camera.zoom_at(factor, event.x, event.y)
        if self.camera.zoom != old_zoom:
            self.tex.update_block_size(self.camera.zoom)
        self.settings.set("zoom", self.camera.zoom)
        self.settings.set("offset_x", self.camera.offset_x)
        self.settings.set("offset_y", self.camera.offset_y)
        self.drawing.redraw_visible_tiles()
        self.update_status()

    def zoom_in(self):
        if self.console.console_has_focus():
            return
        old_zoom = self.camera.zoom
        self.camera.zoom_at(1.1, self.camera.canvas_width//2, self.camera.canvas_height//2)
        if self.camera.zoom != old_zoom:
            self.tex.update_block_size(self.camera.zoom)
        self.settings.set("zoom", self.camera.zoom)
        self.settings.set("offset_x", self.camera.offset_x)
        self.settings.set("offset_y", self.camera.offset_y)
        self.drawing.redraw_visible_tiles()
        self.update_status()

    def zoom_out(self):
        if self.console.console_has_focus():
            return
        old_zoom = self.camera.zoom
        self.camera.zoom_at(0.9, self.camera.canvas_width//2, self.camera.canvas_height//2)
        if self.camera.zoom != old_zoom:
            self.tex.update_block_size(self.camera.zoom)
        self.settings.set("zoom", self.camera.zoom)
        self.settings.set("offset_x", self.camera.offset_x)
        self.settings.set("offset_y", self.camera.offset_y)
        self.drawing.redraw_visible_tiles()
        self.update_status()

    def on_closing(self) -> None:
        self.settings.set("brush_size", self.tool_manager.brush_size)
        self.settings.set("show_grid", self.show_grid)
        self.settings.set("zoom", self.camera.zoom)
        self.settings.set("offset_x", self.camera.offset_x)
        self.settings.set("offset_y", self.camera.offset_y)
        self.root.destroy()

    def copy_selection(self) -> None:
        if not self.selection.active:
            self.console._print("Нет выделенной области", "error")
            return
        x1, y1, x2, y2 = self.selection.get_rect()
        layer = self.map.get_active_layer(self.selection.layer_idx)
        data = layer.copy_rect(x1, y1, x2, y2)
        self.clipboard = data
        self.console._print("Выделение скопировано", "success")

    def cut_selection(self) -> None:
        if not self.selection.active:
            self.console._print("Нет выделенной области", "error")
            return
        self.save_state()
        x1, y1, x2, y2 = self.selection.get_rect()
        layer = self.map.get_active_layer(self.selection.layer_idx)
        data = layer.copy_rect(x1, y1, x2, y2)
        self.clipboard = data
        layer.fill_rect(x1, y1, x2, y2, EMPTY)
        self.drawing.redraw_visible_tiles()
        self.console._print("Выделение вырезано", "success")

    def paste_selection(self) -> None:
        if self.clipboard is None:
            self.console._print("Буфер обмена пуст", "error")
            return
        x1, y1, x2, y2 = self.selection.get_rect() if self.selection.active else (0, 0, 0, 0)
        if not self.selection.active:
            x1, y1 = 0, 0
        self.save_state()
        layer = self.map.get_active_layer(self.layer_manager.current_layer)
        layer.paste_rect(x1, y1, self.clipboard)
        self.drawing.redraw_visible_tiles()
        self.console._print("Вставка выполнена", "success")

    def move_selection(self, dx: int, dy: int) -> None:
        if not self.selection.active:
            return
        self.save_state()
        x1, y1, x2, y2 = self.selection.get_rect()
        layer = self.map.get_active_layer(self.selection.layer_idx)
        layer.move_rect(x1, y1, x2, y2, dx, dy)
        self.selection.set_rect(x1 + dx, y1 + dy, x2 + dx, y2 + dy, self.selection.layer_idx)
        self.drawing.redraw_visible_tiles()
        self.console._print(f"Перемещение на ({dx},{dy})", "success")

    def replace_texture_all_layers(self, old: str, new: str) -> None:
        if old == EMPTY:
            self.console._print("Замена пустых ячеек запрещена", "error")
            return
        if old not in self.tex.originals:
            self.console._print(f"Текстура {old} не найдена", "error")
            return
        if new != EMPTY and new not in self.tex.originals:
            self.console._print(f"Текстура {new} не найдена", "error")
            return
        self.save_state()
        self.map.replace_texture_all_layers(old, new)
        self.drawing.redraw_visible_tiles()
        self.console._print(f"Замена {old} -> {new} выполнена", "success")

    def set_brush_size(self, size: int) -> None:
        if size < CFG.brush_min or size > CFG.brush_max:
            self.console._print(f"Размер кисти должен быть от {CFG.brush_min} до {CFG.brush_max}", "error")
            return
        self.tool_manager.brush_size = size
        self.ui.brush_size_label.config(text=str(size))
        self.settings.set("brush_size", size)
        self.update_status()
        self.console._print(f"Размер кисти установлен на {size}", "success")

    def enable_selection_tool(self) -> None:
        self.tool_manager.set_tool(-3, False)