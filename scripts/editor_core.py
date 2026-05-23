# editor_core.py
import tkinter as tk
from typing import List, Optional, Tuple, Dict, Any
from .config import CFG, EMPTY

class ThemeManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._widgets: Dict[str, Any] = {}

    def register_widget(self, name: str, widget: Any) -> None:
        self._widgets[name] = widget

    def apply_theme(self) -> None:
        colors = CFG.colors

        self.root.configure(bg=colors["BG_PANEL"])

        if self._widgets.get("canvas"):
            self._widgets["canvas"].configure(bg=colors["BG_CANVAS"])

        if self._widgets.get("status"):
            self._widgets["status"].configure(bg=colors["L_GREY"], fg=colors["TEXT"])

        if self._widgets.get("layer_frame"):
            self._apply_theme_to_frame(self._widgets["layer_frame"], colors)

        if self._widgets.get("bottom_frame"):
            self._apply_theme_to_frame(self._widgets["bottom_frame"], colors)

        if self._widgets.get("layer_spinbox"):
            self._apply_theme_to_spinbox(self._widgets["layer_spinbox"], colors)

        if self._widgets.get("brush_size_label"):
            self._widgets["brush_size_label"].configure(bg=colors["BUTTON"], fg=colors["TEXT"])

        if self._widgets.get("visible_check"):
            self._widgets["visible_check"].configure(bg=colors["BG_PANEL"], fg=colors["TEXT"], 
                                                     selectcolor=colors["BG_PANEL"])

        if self._widgets.get("grid_check"):
            self._widgets["grid_check"].configure(bg=colors["BG_PANEL"], fg=colors["TEXT"], 
                                                  selectcolor=colors["BG_PANEL"])

    def _apply_theme_to_frame(self, frame: tk.Frame, colors: Dict) -> None:
        frame.configure(bg=colors["BG_PANEL"])
        for child in frame.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=colors["BG_PANEL"], fg=colors["TEXT"])
            elif isinstance(child, tk.Button):
                child.configure(bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
            elif isinstance(child, tk.Checkbutton):
                child.configure(bg=colors["BG_PANEL"], fg=colors["TEXT"],
                               selectcolor=colors["BG_PANEL"])
            elif isinstance(child, tk.Spinbox):
                self._apply_theme_to_spinbox(child, colors)

    def _apply_theme_to_spinbox(self, spinbox: tk.Spinbox, colors: Dict) -> None:
        spinbox.configure(bg=colors["BUTTON"], fg=colors["TEXT"],
                         buttonbackground=colors["BUTTON"],
                         selectbackground=colors["GREY"],
                         selectforeground=colors["TEXT"])

class LayerManager:
    def __init__(self, editor):
        self.editor = editor
        self.current_layer: int = 0

    def set_active_layer(self, idx: int) -> None:
        if 0 <= idx < self.editor.map.get_num_layers():
            self.current_layer = idx
            self.editor.ui.update_layer_ui()
            self.editor.update_status()

    def add_layer(self) -> None:
        if self.editor.map.get_num_layers() < CFG.max_layers:
            self.editor.save_state()
            self.editor.map.add_layer()
            self.current_layer = self.editor.map.get_num_layers() - 1
            self.editor.ui.update_layer_ui()
            self.editor.draw()
            self.editor.update_status()
        else:
            self.editor.console._print(f"Ошибка: максимальное количество слоёв {CFG.max_layers}", "error")

    def remove_layer(self) -> None:
        if self.editor.map.get_num_layers() <= 1:
            self.editor.console._print("Ошибка: нельзя удалить единственный слой", "error")
            return

        self.editor.save_state()
        self.editor.map.remove_layer(self.current_layer)
        if self.current_layer >= self.editor.map.get_num_layers():
            self.current_layer = self.editor.map.get_num_layers() - 1
        self.editor.ui.update_layer_ui()
        self.editor.draw()

    def toggle_visibility(self) -> None:
        self.editor.save_state()
        self.editor.map.visible[self.current_layer] = not self.editor.map.visible[self.current_layer]
        self.editor.ui.update_visibility_check()
        self.editor.draw()
        self.editor.update_status()

    def clear_current(self) -> None:
        self.editor.clear_layer(self.current_layer, ask_confirm=True)

    def prev_layer(self) -> None:
        if self.current_layer > 0:
            self.set_active_layer(self.current_layer - 1)

    def next_layer(self) -> None:
        if self.current_layer < self.editor.map.get_num_layers() - 1:
            self.set_active_layer(self.current_layer + 1)

    def get_active_layer_obj(self):
        return self.editor.map.get_active_layer(self.current_layer)

class DrawingEngine:
    def __init__(self, editor):
        self.editor = editor
        self._drag: bool = False
        self._last: Optional[Tuple[int, int]] = None

    def draw(self) -> None:
        canvas = self.editor.ui.canvas
        if not canvas:
            return

        canvas.delete("all")
        cell = CFG.cell_size
        w, h = CFG.map_width, CFG.map_height
        colors = CFG.colors

        for layer_idx, layer in enumerate(self.editor.map.layers):
            if not self.editor.map.visible[layer_idx]:
                continue
            for y in range(h):
                for x in range(w):
                    tex_name = layer.grid[y][x]
                    if tex_name != EMPTY:
                        img = self.editor.tex.get_block(tex_name)
                        if img:
                            canvas.create_image(x*cell, y*cell, anchor=tk.NW, image=img)
            for y in range(h+1):
                for x in range(w):
                    if layer.fh[y][x]:
                        canvas.create_line(x*cell, y*cell, (x+1)*cell, y*cell, fill=colors["BLACK"], width=2)
            for y in range(h):
                for x in range(w+1):
                    if layer.fv[y][x]:
                        canvas.create_line(x*cell, y*cell, x*cell, (y+1)*cell, fill=colors["BLACK"], width=2)

        if self.editor.show_grid:
            grid_color = colors["GRID"]
            for x in range(w + 1):
                canvas.create_line(x*cell, 0, x*cell, CFG.height_px, fill=grid_color, width=1)
            for y in range(h + 1):
                canvas.create_line(0, y*cell, CFG.width_px, y*cell, fill=grid_color, width=1)

    def on_press(self, e: tk.Event) -> None:
        self.editor.save_state()
        self._drag = True
        xc = e.x // CFG.cell_size
        yc = e.y // CFG.cell_size
        if 0 <= yc < CFG.map_height and 0 <= xc < CFG.map_width:
            self._last = (xc, yc)
            self._apply(e.x, e.y)

    def on_drag(self, e: tk.Event) -> None:
        if not self._drag:
            return
        if self.editor.tool_manager.pipette_mode or self.editor.tool_manager.flood_mode:
            return
        if self.editor.tool_manager.fence:
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

    def on_release(self, e: tk.Event) -> None:
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
        if self.editor.tool_manager.fence:
            return False

        layer = self.editor.layer_manager.get_active_layer_obj()
        changed = False
        left = x - (self.editor.tool_manager.brush_size - 1) // 2
        right = x + self.editor.tool_manager.brush_size // 2
        top = y - (self.editor.tool_manager.brush_size - 1) // 2
        bottom = y + self.editor.tool_manager.brush_size // 2

        for ny in range(top, bottom + 1):
            for nx in range(left, right + 1):
                if 0 <= ny < CFG.map_height and 0 <= nx < CFG.map_width:
                    new_value = self.editor.tool_manager.tool if self.editor.tool_manager.tool is not None else EMPTY
                    if layer.grid[ny][nx] != new_value:
                        layer.grid[ny][nx] = new_value
                        changed = True
        return changed

    def _apply(self, px: int, py: int) -> None:
        xc = px // CFG.cell_size
        yc = py // CFG.cell_size
        if not (0 <= yc < CFG.map_height and 0 <= xc < CFG.map_width):
            return

        layer = self.editor.layer_manager.get_active_layer_obj()

        if self.editor.tool_manager.fence:
            self._apply_fence(px, py, xc, yc, layer)
        elif self.editor.tool_manager.pipette_mode:
            self._apply_pipette(xc, yc)
        elif self.editor.tool_manager.flood_mode:
            self._apply_flood_fill(xc, yc)
        else:
            self._brush(xc, yc)
            self.draw()

    def _apply_fence(self, px: int, py: int, xc: int, yc: int, layer) -> None:
        x0, y0 = xc * CFG.cell_size, yc * CFG.cell_size
        d = [abs(py - y0), abs(py - (y0 + CFG.cell_size)), 
             abs(px - x0), abs(px - (x0 + CFG.cell_size))]
        m = min(d)
        threshold = CFG.cell_size // 3
        if m > threshold:
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

    def _apply_pipette(self, xc: int, yc: int) -> None:
        for idx in range(len(self.editor.map.layers) - 1, -1, -1):
            if not self.editor.map.visible[idx]:
                continue
            tex_name = self.editor.map.layers[idx].grid[yc][xc]
            if tex_name != EMPTY:
                self.editor.tool_manager.set_tool(tex_name, False)
                self.editor.tool_manager.pipette_mode = False
                self.draw()
                self.editor.update_status()
                return
        self.editor.tool_manager.pipette_mode = False
        self.editor.update_status()
        self.editor.console._print("Пипетка: не удалось найти текстуру", "warning")

    def _apply_flood_fill(self, xc: int, yc: int) -> None:
        if self.editor.tool_manager.fill_tool != EMPTY:
            self._flood_fill(xc, yc, self.editor.tool_manager.fill_tool)
            self.editor.tool_manager.tool = self.editor.tool_manager.fill_tool
            self.editor.tool_manager.flood_mode = False
            self.editor.update_status()
        else:
            self.editor.tool_manager.flood_mode = False
            self.editor.update_status()
            self.editor.console._print("Заливка: сначала выберите текстуру", "error")

    def _flood_fill(self, x: int, y: int, new_tex: str) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        old_tex = layer.grid[y][x]
        if old_tex == new_tex:
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

    def pick_texture(self, event: tk.Event) -> None:
        xc = event.x // CFG.cell_size
        yc = event.y // CFG.cell_size
        if not (0 <= xc < CFG.map_width and 0 <= yc < CFG.map_height):
            return
        for idx in range(len(self.editor.map.layers) - 1, -1, -1):
            if not self.editor.map.visible[idx]:
                continue
            tex_name = self.editor.map.layers[idx].grid[yc][xc]
            if tex_name != EMPTY:
                self.editor.tool_manager.set_tool(tex_name, False)
                self.editor.console._print(f"Выбрана текстура: {tex_name}", "success")
                return