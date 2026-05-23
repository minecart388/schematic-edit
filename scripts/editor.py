# editor.py
import tkinter as tk
from tkinter import filedialog
import os
import shutil
from typing import Optional
from PIL import Image, ImageDraw
from .config import CFG, EMPTY, Settings
from .core import TexMgr, Map, UndoMgr, FileMgr, path
from .editor_core import ThemeManager, LayerManager, DrawingEngine
from .editor_ui import UIManager
from .console import ConsoleManager
from .hotbar import HotbarManager


class ToolManager:
    def __init__(self, editor):
        self.editor = editor
        self.tool: Optional[str] = EMPTY
        self.fence: bool = False
        self.pipette_mode: bool = False
        self.flood_mode: bool = False
        self.fill_tool: str = EMPTY
        self.brush_size: int = 1

    def set_tool(self, code, fence: bool, from_hotbar: bool = False) -> None:
        if not from_hotbar:
            self.editor.ui.clear_hotbar_selection()

        if code == -1:
            self.pipette_mode = True
            self.flood_mode = False
            self.fence = False
            self.tool = None
            self.editor.update_status()
            return
        if code == -2:
            if self.tool is not None and self.tool != EMPTY:
                self.fill_tool = self.tool
                self.flood_mode = True
                self.pipette_mode = False
                self.fence = False
                self.editor.update_status()
            else:
                self.editor.console._print("Сначала выберите текстуру для заливки", "error")
            return
        self.pipette_mode = False
        self.flood_mode = False
        self.fence = fence
        if fence:
            self.tool = None
        else:
            self.tool = code
        self.editor.update_status()

    def get_tool_name(self) -> str:
        if self.pipette_mode:
            return "Пипетка"
        if self.flood_mode:
            return "Заливка"
        if self.fence:
            return "Граница"
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
        self.map = Map()
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

        self.apply_theme()

        self.drawing.draw()
        self.update_status()

        self.root.bind("<Control-z>", lambda e: self.undo_op())
        self.root.bind("<Control-y>", lambda e: self.redo_op())
        self.root.bind("<Control-Z>", lambda e: self.undo_op())
        self.root.bind("<Control-Y>", lambda e: self.redo_op())

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
        self.drawing.draw()

    def toggle_theme(self) -> None:
        new_theme = "light" if CFG._current_theme == "dark" else "dark"
        CFG.set_theme(new_theme)
        self.settings.set_theme(new_theme)
        self.apply_theme()

    def _update_dynamic_widgets(self) -> None:
        colors = CFG.colors
        if self.ui.toolbar_frame:
            for child in self.ui.toolbar_frame.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                 activebackground=colors["BUTTON_ACTIVE"])
        if self.ui.bottom_frame:
            for child in self.ui.bottom_frame.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                 activebackground=colors["BUTTON_ACTIVE"])
                elif isinstance(child, tk.Label):
                    child.config(bg=colors["BG_PANEL"], fg=colors["TEXT"])
        if self.ui.layer_frame:
            for child in self.ui.layer_frame.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                 activebackground=colors["BUTTON_ACTIVE"])
                elif isinstance(child, tk.Label):
                    child.config(bg=colors["BG_PANEL"], fg=colors["TEXT"])

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
        self.drawing.draw()

    def draw(self) -> None:
        self.drawing.draw()

    def save_state(self) -> None:
        self.undo.save(self.map.get())

    def undo_op(self) -> None:
        if s := self.undo.undo_op(self.map.get()):
            self.map.set(s)
            self.ui.update_layer_ui()
            if self.layer_manager.current_layer >= self.map.get_num_layers():
                self.layer_manager.current_layer = self.map.get_num_layers() - 1
            self.layer_manager.set_active_layer(self.layer_manager.current_layer)
            self.draw()
            self.console._print("Отмена", "success")

    def redo_op(self) -> None:
        if s := self.undo.redo_op(self.map.get()):
            self.map.set(s)
            self.ui.update_layer_ui()
            if self.layer_manager.current_layer >= self.map.get_num_layers():
                self.layer_manager.current_layer = self.map.get_num_layers() - 1
            self.layer_manager.set_active_layer(self.layer_manager.current_layer)
            self.draw()
            self.console._print("Повтор", "success")

    def clear_layer(self, layer_idx: int, ask_confirm: bool = True) -> None:
        if ask_confirm:
            self.console.ask_yes_no(f"Очистить слой {layer_idx+1}?", lambda ok: self._do_clear_layer(layer_idx, ok))
        else:
            self._do_clear_layer(layer_idx, True)

    def _do_clear_layer(self, layer_idx: int, confirmed: bool) -> None:
        if confirmed:
            self.save_state()
            self.map.clear_layer(layer_idx)
            self.draw()
            self.console._print(f"✓ Слой {layer_idx+1} очищен", "success")

    def clear_all_layers(self, ask_confirm: bool = True) -> None:
        if ask_confirm:
            self.console.ask_yes_no("Очистить все слои?", self._do_clear_all_layers)
        else:
            self._do_clear_all_layers(True)

    def _do_clear_all_layers(self, confirmed: bool) -> None:
        if confirmed:
            self.save_state()
            self.map.clear_all()
            self.draw()
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

        scale = 4
        w, h = CFG.map_width, CFG.map_height
        cell = CFG.cell_size
        img_width = w * cell * scale
        img_height = h * cell * scale

        bg_color = CFG.colors["BG_CANVAS"]
        img = Image.new("RGBA", (img_width, img_height), bg_color)

        for layer_idx, layer in enumerate(self.map.layers):
            if not self.map.visible[layer_idx]:
                continue

            for y in range(h):
                for x in range(w):
                    tex_name = layer.grid[y][x]
                    if tex_name != EMPTY:
                        orig = self.tex.get_original(tex_name)
                        if orig:
                            scaled_tile = orig.resize((cell * scale, cell * scale), Image.Resampling.NEAREST)
                            if scaled_tile.mode == 'RGBA':
                                img.paste(scaled_tile, (x * cell * scale, y * cell * scale), scaled_tile)
                            else:
                                img.paste(scaled_tile, (x * cell * scale, y * cell * scale))

            draw = ImageDraw.Draw(img)
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
                    self.draw()
                    self.console._print("Карта загружена", "success")
            except Exception as e:
                self.console._print(f"Ошибка загрузки: {e}", "error")

    def import_tex(self) -> None:
        initial_dir = self.settings.get("last_import_path", "")
        files = filedialog.askopenfilenames(
            filetypes=[("PNG", "*.png")],
            initialdir=initial_dir
        )
        if not files:
            return

        self.settings.set("last_import_path", os.path.dirname(files[0]))

        os.makedirs(self.block_dir, exist_ok=True)
        for src in files:
            dst = os.path.join(self.block_dir, os.path.basename(src))
            shutil.copy(src, dst)
        self.tex.load_blocks(self.block_dir, log_func=self.console._print)
        self.ui.refresh_hotbar()
        self.draw()
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
            self.ui.refresh_hotbar()
            self.draw()
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
                self.ui.refresh_hotbar()
                self.draw()
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
        self.ui.update_status(f"{tool_text} | Слой {self.layer_manager.current_layer + 1} | Кисть {self.tool_manager.brush_size}")

    def on_mouse_move(self, event: tk.Event) -> None:
        xc = event.x // CFG.cell_size
        yc = event.y // CFG.cell_size
        if 0 <= xc < CFG.map_width and 0 <= yc < CFG.map_height:
            self.ui.update_status(f"({xc}, {yc}) | {self.tool_manager.get_tool_name()} | Слой {self.layer_manager.current_layer + 1} | Кисть {self.tool_manager.brush_size}")

    def on_closing(self) -> None:
        self.settings.set("brush_size", self.tool_manager.brush_size)
        self.settings.set("show_grid", self.show_grid)
        self.root.destroy()