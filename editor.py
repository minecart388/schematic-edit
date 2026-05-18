# editor.py
import tkinter as tk
from tkinter import filedialog
import os
import shutil
from typing import Optional
from PIL import Image, ImageDraw
from config import CFG, EMPTY, Settings
from core import TexMgr, Map, UndoMgr, FileMgr, path
from editor_core import ThemeManager, LayerManager, DrawingEngine
from editor_ui import UIManager
from console import ConsoleManager

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
        
        self.tex.load_blocks(self.block_dir)
        self.tex.load_icons(self.gui_dir)
        
        self.tool: Optional[int] = EMPTY
        self.fence: bool = False
        self.pipette_mode: bool = False
        self.flood_mode: bool = False
        self.fill_tool: int = EMPTY
        
        self.brush_size = self.settings.get("brush_size", 1)
        self.show_grid = self.settings.get("show_grid", True)
        
        saved_theme = self.settings.get("theme", "light")
        if saved_theme != CFG.theme:
            CFG.switch_theme()
        
        self.layer_manager = LayerManager(self)
        self.drawing = DrawingEngine(self)
        
        main_container = tk.Frame(self.root, bg=CFG.colors["BG_PANEL"])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        left_panel = tk.Frame(main_container, bg=CFG.colors["BG_PANEL"])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_panel = tk.Frame(main_container, bg=CFG.colors["BG_PANEL"])
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.console = ConsoleManager(self)
        self.console.create(right_panel)
        
        self.ui = UIManager(self)
        self.ui.setup(left_panel)
        
        self.theme.apply_theme()
        
        self.drawing.draw()
        self.update_status()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def toggle_theme(self) -> None:
        CFG.switch_theme()
        self.settings.set("theme", CFG.theme)
        
        main_container = self.root.winfo_children()[0]
        main_container.configure(bg=CFG.colors["BG_PANEL"])
        
        for child in main_container.winfo_children():
            child.configure(bg=CFG.colors["BG_PANEL"])
        
        self.theme.apply_theme()
        self.console.update_theme()
        self.ui.rebuild_all()
        self.drawing.draw()
        self.update_status()
    
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
            if self.tool is not None:
                self.fill_tool = self.tool
                self.flood_mode = True
                self.pipette_mode = False
                self.fence = False
                self.update_status()
            else:
                self.console._print("Сначала выберите текстуру для заливки", "error")
    
    def dec_brush(self) -> None:
        if self.brush_size > CFG.brush_min:
            self.brush_size -= 1
            self.ui.brush_size_label.config(text=str(self.brush_size))
            self.settings.set("brush_size", self.brush_size)
            self.update_status()
    
    def inc_brush(self) -> None:
        if self.brush_size < CFG.brush_max:
            self.brush_size += 1
            self.ui.brush_size_label.config(text=str(self.brush_size))
            self.settings.set("brush_size", self.brush_size)
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
        
        img = Image.new("RGB", (img_width, img_height), CFG.colors["BG_CANVAS"])
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
                draw.line((x1, 0, x1, img_height), fill=CFG.colors["GRID"], width=2)
            for y in range(h + 1):
                y1 = y * cell * scale
                draw.line((0, y1, img_width, y1), fill=CFG.colors["GRID"], width=2)
        
        img.save(file_path)
        
        if not self.tex.originals:
            self.console._print(f"Карта сохранена в {file_path} (масштаб ×{scale})", "success")
            self.console._print("Текстуры не загружены, сохранены только границы и сетка", "warning")
        else:
            self.console._print(f"Карта сохранена в {file_path} (масштаб ×{scale})", "success")
    
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
        self.tex.load_blocks(self.block_dir)
        self.ui.rebuild_toolbar()
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
        
        self.console._print("ДОСТУПНЫЕ ТЕКСТУРЫ:", "info")
        for i, f in enumerate(sorted(files)):
            self.console._print(f"  {i+1}. {f}", "info")
        
        self.console.ask_input("Введите номера текстур для удаления (через пробел) или 'all' для удаления всех:", self._delete_textures_callback)
    
    def _delete_textures_callback(self, answer: str) -> None:
        files = [f for f in os.listdir(self.block_dir) if f.endswith('.png')]
        
        if answer.lower() == 'all':
            for f in files:
                try:
                    os.remove(os.path.join(self.block_dir, f))
                except OSError:
                    pass
            self.tex.load_blocks(self.block_dir)
            self.ui.rebuild_toolbar()
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
                self.tex.load_blocks(self.block_dir)
                self.ui.rebuild_toolbar()
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
        self.console.ask_input("Введите название пресета:", self._save_preset_callback)
    
    def _save_preset_callback(self, name: str) -> None:
        if not name.strip():
            self.console._print("Ошибка: название не может быть пустым", "error")
            return
        saved = self.file.save_preset(name.strip())
        if saved:
            self.console._print(f"Пресет сохранён как '{saved}.json'", "success")
        else:
            self.console._print("Ошибка сохранения пресета", "error")
    
    def update_status(self) -> None:
        tool_text = self._get_tool_text()
        self.ui.update_status(f"{tool_text} | Слой {self.layer_manager.current_layer + 1} | Кисть {self.brush_size}")
    
    def _get_tool_text(self) -> str:
        if self.pipette_mode:
            return "Пипетка"
        if self.flood_mode:
            return "Заливка"
        if self.fence:
            return "Граница"
        if self.tool == EMPTY:
            return "Ластик"
        name = [n for n, c in self.tex.codes.items() if c == self.tool]
        return name[0] if name else "Текстура"
    
    def on_mouse_move(self, event: tk.Event) -> None:
        xc = event.x // CFG.cell_size
        yc = event.y // CFG.cell_size
        if 0 <= xc < CFG.map_width and 0 <= yc < CFG.map_height:
            self.ui.update_status(f"({xc}, {yc}) | {self._get_tool_text()} | Слой {self.layer_manager.current_layer + 1} | Кисть {self.brush_size}")
        else:
            self.update_status()
    
    def on_closing(self) -> None:
        self.settings.set("brush_size", self.brush_size)
        self.settings.set("show_grid", self.show_grid)
        self.root.destroy()