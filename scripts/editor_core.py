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
            self.editor.drawing.draw()
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
        self.editor.drawing.draw()

    def toggle_visibility(self) -> None:
        self.editor.save_state()
        self.editor.map.visible[self.current_layer] = not self.editor.map.visible[self.current_layer]
        self.editor.ui.update_visibility_check()
        self.editor.drawing.draw()
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

class Camera:
    def __init__(self, canvas_width: int, canvas_height: int, map_width: int, map_height: int, cell_size: int):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.map_width = map_width
        self.map_height = map_height
        self.cell_size = cell_size
        self.zoom: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self._drag_start = None

    def set_map_size(self, w: int, h: int):
        self.map_width = w
        self.map_height = h

    def set_canvas_size(self, w: int, h: int):
        self.canvas_width = w
        self.canvas_height = h

    def world_to_screen(self, x: int, y: int) -> Tuple[float, float]:
        sx = (x * self.cell_size + self.offset_x) * self.zoom
        sy = (y * self.cell_size + self.offset_y) * self.zoom
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        wx = (sx / self.zoom) - self.offset_x
        wy = (sy / self.zoom) - self.offset_y
        return wx / self.cell_size, wy / self.cell_size

    def clamp(self):
        total_w = self.map_width * self.cell_size
        total_h = self.map_height * self.cell_size
        view_w = self.canvas_width / self.zoom
        view_h = self.canvas_height / self.zoom
        min_x = -total_w + view_w
        min_y = -total_h + view_h
        if total_w > view_w:
            self.offset_x = max(min_x, min(0.0, self.offset_x))
        else:
            self.offset_x = (self.canvas_width / self.zoom - total_w) / 2
        if total_h > view_h:
            self.offset_y = max(min_y, min(0.0, self.offset_y))
        else:
            self.offset_y = (self.canvas_height / self.zoom - total_h) / 2

    def pan_start(self, x: int, y: int):
        self._drag_start = (x, y)

    def pan_move(self, x: int, y: int):
        if self._drag_start:
            dx = x - self._drag_start[0]
            dy = y - self._drag_start[1]
            self.offset_x += dx / self.zoom
            self.offset_y += dy / self.zoom
            self.clamp()
            self._drag_start = (x, y)

    def zoom_at(self, factor: float, cx: int, cy: int):
        old_zoom = self.zoom
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        if new_zoom == old_zoom:
            return
        wx, wy = self.screen_to_world(cx, cy)
        self.zoom = new_zoom
        nx, ny = self.world_to_screen(wx, wy)
        self.offset_x += (cx - nx) / self.zoom
        self.offset_y += (cy - ny) / self.zoom
        self.clamp()

class DrawingEngine:
    def __init__(self, editor):
        self.editor = editor
        self._drag: bool = False
        self._last: Optional[Tuple[int, int]] = None
        self._pending_redraw = False
        self._redraw_timer = None
        self._cached_items: Dict[Tuple[int, int, int], int] = {}
        self._cached_grid_items: List[int] = []

    def draw(self, full_redraw: bool = True) -> None:
        canvas = self.editor.ui.canvas
        if not canvas:
            return

        if full_redraw:
            self._full_redraw()
        else:
            self._schedule_redraw()

    def _schedule_redraw(self):
        if self._redraw_timer is not None:
            self.editor.root.after_cancel(self._redraw_timer)
        self._redraw_timer = self.editor.root.after(50, self._full_redraw)

    def _full_redraw(self):
        canvas = self.editor.ui.canvas
        if not canvas:
            return
        canvas.delete("all")
        self._cached_items.clear()
        self._cached_grid_items.clear()

        cell = CFG.cell_size
        w, h = CFG.map_width, CFG.map_height
        colors = CFG.colors
        cam = self.editor.camera

        for layer_idx, layer in enumerate(self.editor.map.layers):
            if not self.editor.map.visible[layer_idx]:
                continue
            for y in range(h):
                for x in range(w):
                    tex_name = layer.grid[y][x]
                    if tex_name != EMPTY:
                        img = self.editor.tex.get_block(tex_name)
                        if img:
                            sx, sy = cam.world_to_screen(x, y)
                            item_id = canvas.create_image(sx, sy, anchor=tk.NW, image=img)
                            self._cached_items[(x, y, layer_idx)] = item_id

        if self.editor.show_grid:
            for x in range(w + 1):
                x1, y1 = cam.world_to_screen(x, 0)
                x2, y2 = cam.world_to_screen(x, h)
                line_id = canvas.create_line(x1, y1, x2, y2, fill=colors["GRID"], width=1)
                self._cached_grid_items.append(line_id)
            for y in range(h + 1):
                x1, y1 = cam.world_to_screen(0, y)
                x2, y2 = cam.world_to_screen(w, y)
                line_id = canvas.create_line(x1, y1, x2, y2, fill=colors["GRID"], width=1)
                self._cached_grid_items.append(line_id)

    def update_cell(self, x: int, y: int, layer_idx: int, tex_name: str):
        canvas = self.editor.ui.canvas
        if not canvas:
            return
        key = (x, y, layer_idx)
        if key in self._cached_items:
            canvas.delete(self._cached_items[key])
            del self._cached_items[key]
        if tex_name != EMPTY:
            img = self.editor.tex.get_block(tex_name)
            if img:
                sx, sy = self.editor.camera.world_to_screen(x, y)
                item_id = canvas.create_image(sx, sy, anchor=tk.NW, image=img)
                self._cached_items[key] = item_id

    def update_grid(self):
        canvas = self.editor.ui.canvas
        if not canvas:
            return
        for item_id in self._cached_grid_items:
            canvas.delete(item_id)
        self._cached_grid_items.clear()
        if not self.editor.show_grid:
            return
        w, h = CFG.map_width, CFG.map_height
        colors = CFG.colors
        cam = self.editor.camera
        for x in range(w + 1):
            x1, y1 = cam.world_to_screen(x, 0)
            x2, y2 = cam.world_to_screen(x, h)
            line_id = canvas.create_line(x1, y1, x2, y2, fill=colors["GRID"], width=1)
            self._cached_grid_items.append(line_id)
        for y in range(h + 1):
            x1, y1 = cam.world_to_screen(0, y)
            x2, y2 = cam.world_to_screen(w, y)
            line_id = canvas.create_line(x1, y1, x2, y2, fill=colors["GRID"], width=1)
            self._cached_grid_items.append(line_id)

    def on_press(self, e: tk.Event) -> None:
        self.editor.save_state()
        self._drag = True
        wx, wy = self.editor.camera.screen_to_world(e.x, e.y)
        xc = int(wx)
        yc = int(wy)
        if 0 <= yc < CFG.map_height and 0 <= xc < CFG.map_width:
            self._last = (xc, yc)
            self._apply(e.x, e.y)

    def on_drag(self, e: tk.Event) -> None:
        if not self._drag:
            return
        if self.editor.tool_manager.pipette_mode or self.editor.tool_manager.flood_mode:
            return
        wx, wy = self.editor.camera.screen_to_world(e.x, e.y)
        xc = int(wx)
        yc = int(wy)
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
                self.draw(full_redraw=False)
        else:
            self._apply(e.x, e.y)
        self._last = (xc, yc)

    def on_release(self, e: tk.Event) -> None:
        self._drag = False
        self._last = None
        if self._redraw_timer:
            self.editor.root.after_cancel(self._redraw_timer)
            self._full_redraw()

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
                        self.update_cell(nx, ny, self.editor.layer_manager.current_layer, new_value)
                        changed = True
        return changed

    def _apply(self, px: int, py: int) -> None:
        wx, wy = self.editor.camera.screen_to_world(px, py)
        xc = int(wx)
        yc = int(wy)
        if not (0 <= yc < CFG.map_height and 0 <= xc < CFG.map_width):
            return

        if self.editor.tool_manager.pipette_mode:
            self._apply_pipette(xc, yc)
        elif self.editor.tool_manager.flood_mode:
            self._apply_flood_fill(xc, yc)
        else:
            self._brush(xc, yc)

    def _apply_pipette(self, xc: int, yc: int) -> None:
        for idx in range(len(self.editor.map.layers) - 1, -1, -1):
            if not self.editor.map.visible[idx]:
                continue
            tex_name = self.editor.map.layers[idx].grid[yc][xc]
            if tex_name != EMPTY:
                self.editor.tool_manager.set_tool(tex_name, False)
                self.editor.tool_manager.pipette_mode = False
                self.editor.update_status()
                return
        self.editor.tool_manager.pipette_mode = False
        self.editor.update_status()
        self.editor.console._print("Пипетка: не удалось найти текстуру", "warning")

    def _apply_flood_fill(self, xc: int, yc: int) -> None:
        if self.editor.tool_manager.fill_tool != EMPTY:
            self._flood_fill_scanline(xc, yc, self.editor.tool_manager.fill_tool)
            self.editor.tool_manager.tool = self.editor.tool_manager.fill_tool
            self.editor.tool_manager.flood_mode = False
            self.editor.update_status()
        else:
            self.editor.tool_manager.flood_mode = False
            self.editor.update_status()
            self.editor.console._print("Заливка: сначала выберите текстуру", "error")

    def _flood_fill_scanline(self, x: int, y: int, new_tex: str) -> None:
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
            left = cx
            right = cx
            while left-1 >= 0 and layer.grid[cy][left-1] == old_tex:
                left -= 1
            while right+1 < w and layer.grid[cy][right+1] == old_tex:
                right += 1
            for nx in range(left, right+1):
                layer.grid[cy][nx] = new_tex
                self.update_cell(nx, cy, self.editor.layer_manager.current_layer, new_tex)
                if cy-1 >= 0 and layer.grid[cy-1][nx] == old_tex:
                    stack.append((nx, cy-1))
                if cy+1 < h and layer.grid[cy+1][nx] == old_tex:
                    stack.append((nx, cy+1))

    def pick_texture(self, event: tk.Event) -> None:
        wx, wy = self.editor.camera.screen_to_world(event.x, event.y)
        xc = int(wx)
        yc = int(wy)
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