# console_cmd.py
import tkinter as tk
from typing import List, Optional, Tuple
from .config import CFG, EMPTY

class ConsoleCommands:
    def __init__(self, console):
        self.console = console
        self.editor = console.editor
        
        self.commands = {
            'help': self._cmd_help,
            'circle': self._cmd_circle,
            'rect': self._cmd_rect,
            'line': self._cmd_line,
            'clear': self._cmd_clear,
            'layers': self._cmd_layers,
            'layer': self._cmd_layer,
            'tool': self._cmd_tool,
            'clear_console': self._cmd_clear_console,
            'presets': self._cmd_presets,
            'save_preset': self._cmd_save_preset,
            'delete_preset': self._cmd_delete_preset,
            'load_preset': self._cmd_load_preset,
            'replace': self._cmd_replace,
            'brush': self._cmd_brush
        }
    
    def execute(self, command: str, parts: List[str]) -> bool:
        cmd = parts[0]
        if cmd in self.commands:
            self.commands[cmd](parts)
            return True
        return False
    
    def _cmd_help(self, parts=None) -> None:
        help_text = """
Доступные команды:
------------------------------------------
  circle x y radius fill [texture.png] - круг
  rect x1 y1 x2 y2 fill [texture.png] - прямоугольник
  line x1 y1 x2 y2 <thickness> [texture.png] - линия
  layers - показать информацию о слоях
  layer <номер> - переключиться на слой
  layer <номер> show - показать/скрыть слой
  layer <номер> del - удалить слой
  tool - показать текущий инструмент
  clear <all/layer> - очистить всё или текущий слой
  presets - показать список пресетов
  save_preset - сохранить текущую карту как пресет
  load_preset - загрузить пресет
  delete_preset <name> - удалить пресет
  replace <old> <new> - замена текстуры во всех слоях
  brush <размер> - установить размер кисти
  clear_console - очистить консоль
  help - показать справку

Параметры:
  fill: true/false - заливка фигуры
  texture.png - имя файла текстуры
------------------------------------------
        """
        self.console._print(help_text, "info")
    
    def _get_current_texture_or_default(self, provided_name: Optional[str]) -> Optional[str]:
        if provided_name and provided_name in self.editor.tex.blocks:
            return provided_name
        if isinstance(self.editor.tool_manager.tool, str) and self.editor.tool_manager.tool in self.editor.tex.blocks:
            return self.editor.tool_manager.tool
        self.console._print("Ошибка: не выбрана текстура или текстура не найдена", "error")
        return None
    
    def _cmd_circle(self, parts: list) -> None:
        if len(parts) < 5 or len(parts) > 6:
            self.console._print("Ошибка использования: circle x y radius fill [texture.png]", "error")
            self.console._print("Пример: circle 50 25 10 true stone.png", "info")
            return
        try:
            x = int(parts[1])
            y = int(parts[2])
            radius = int(parts[3])
            fill = parts[4].lower() in ['true', '1', 'yes', 't']
            tex_name = parts[5] if len(parts) == 6 else None
            tool = self._get_current_texture_or_default(tex_name)
            if tool is None:
                return
            if radius < 1:
                self.console._print("Ошибка: радиус должен быть больше 0", "error")
                return
            self.editor.save_state()
            self._draw_circle(x, y, radius, fill, tool)
            self.editor.drawing.full_redraw()
            self.console._print(f"✓ Круг нарисован: центр({x},{y}) радиус={radius} заливка={'да' if fill else 'нет'} текстура={tool}", "success")
        except ValueError:
            self.console._print("Ошибка: неверный формат чисел", "error")
    
    def _draw_circle(self, cx: int, cy: int, radius: int, fill: bool, tex_name: str) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        w, h = self.editor.map.w, self.editor.map.h
        if fill:
            for y in range(-radius, radius + 1):
                for x in range(-radius, radius + 1):
                    if x*x + y*y <= radius*radius:
                        nx = cx + x
                        ny = cy + y
                        if 0 <= nx < w and 0 <= ny < h:
                            layer.grid[ny][nx] = tex_name
        else:
            x = 0
            y = radius
            d = 1 - radius
            points = []
            while x <= y:
                points.extend([
                    (cx + x, cy + y), (cx - x, cy + y),
                    (cx + x, cy - y), (cx - x, cy - y),
                    (cx + y, cy + x), (cx - y, cy + x),
                    (cx + y, cy - x), (cx - y, cy - x)
                ])
                if d < 0:
                    d += 2 * x + 3
                else:
                    d += 2 * (x - y) + 5
                    y -= 1
                x += 1
            for px, py in points:
                if 0 <= px < w and 0 <= py < h:
                    layer.grid[py][px] = tex_name
    
    def _cmd_rect(self, parts: list) -> None:
        if len(parts) < 6 or len(parts) > 7:
            self.console._print("Ошибка использования: rect x1 y1 x2 y2 fill [texture.png]", "error")
            self.console._print("Пример: rect 10 10 90 40 true stone.png", "info")
            return
        try:
            x1 = int(parts[1])
            y1 = int(parts[2])
            x2 = int(parts[3])
            y2 = int(parts[4])
            fill = parts[5].lower() in ['true', '1', 'yes', 't']
            tex_name = parts[6] if len(parts) == 7 else None
            tool = self._get_current_texture_or_default(tex_name)
            if tool is None:
                return
            self.editor.save_state()
            self._draw_rectangle(x1, y1, x2, y2, fill, tool)
            self.editor.drawing.full_redraw()
            self.console._print(f"✓ Прямоугольник нарисован: ({x1},{y1})-({x2},{y2}) заливка={'да' if fill else 'нет'} текстура={tool}", "success")
        except ValueError:
            self.console._print("Ошибка: неверный формат чисел", "error")
    
    def _draw_rectangle(self, x1: int, y1: int, x2: int, y2: int, fill: bool, tex_name: str) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        left = max(0, min(x1, x2))
        right = min(self.editor.map.w - 1, max(x1, x2))
        top = max(0, min(y1, y2))
        bottom = min(self.editor.map.h - 1, max(y1, y2))
        if fill:
            for y in range(top, bottom + 1):
                for x in range(left, right + 1):
                    layer.grid[y][x] = tex_name
        else:
            for x in range(left, right + 1):
                if 0 <= top < self.editor.map.h:
                    layer.grid[top][x] = tex_name
                if 0 <= bottom < self.editor.map.h:
                    layer.grid[bottom][x] = tex_name
            for y in range(top + 1, bottom):
                if 0 <= left < self.editor.map.w:
                    layer.grid[y][left] = tex_name
                if 0 <= right < self.editor.map.w:
                    layer.grid[y][right] = tex_name
    
    def _cmd_line(self, parts: list) -> None:
        if len(parts) < 6 or len(parts) > 7:
            self.console._print("Ошибка использования: line x1 y1 x2 y2 толщина [texture.png]", "error")
            self.console._print("Пример: line 10 10 90 40 3 stone.png", "info")
            return
        try:
            x1 = int(parts[1])
            y1 = int(parts[2])
            x2 = int(parts[3])
            y2 = int(parts[4])
            thickness = int(parts[5])
            tex_name = parts[6] if len(parts) == 7 else None
            tool = self._get_current_texture_or_default(tex_name)
            if tool is None:
                return
            if thickness < CFG.brush_min or thickness > CFG.brush_max:
                self.console._print(f"Ошибка: толщина должна быть от {CFG.brush_min} до {CFG.brush_max}", "error")
                return
            self.editor.save_state()
            self._draw_line(x1, y1, x2, y2, thickness, tool)
            self.editor.drawing.full_redraw()
            self.console._print(f"✓ Линия нарисована: ({x1},{y1})→({x2},{y2}) толщина={thickness} текстура={tool}", "success")
        except ValueError:
            self.console._print("Ошибка: неверный формат чисел", "error")
    
    def _draw_line(self, x1: int, y1: int, x2: int, y2: int, thickness: int, tex_name: str) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        points = self._get_line_points(x1, y1, x2, y2)
        w, h = self.editor.map.w, self.editor.map.h
        for px, py in points:
            for dy in range(-(thickness // 2), (thickness + 1) // 2):
                for dx in range(-(thickness // 2), (thickness + 1) // 2):
                    nx = px + dx
                    ny = py + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        layer.grid[ny][nx] = tex_name
    
    def _get_line_points(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        x, y = x1, y1
        while True:
            points.append((x, y))
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return points
    
    def _cmd_layers(self, parts=None) -> None:
        num_layers = self.editor.map.get_num_layers()
        self.console._print(f"Слои:", "info")
        self.console._print(f"  Всего слоёв: {num_layers}", "info")
        self.console._print(f"  Активный слой: {self.editor.layer_manager.current_layer + 1}", "info")
        for i in range(num_layers):
            visibility = "✓" if self.editor.map.visible[i] else "✗"
            status = "вид" if self.editor.map.visible[i] else "скрыт"
            self.console._print(f"  Слой {i+1}: [{visibility}] {status}", "normal")
    
    def _cmd_layer(self, parts: list) -> None:
        if len(parts) < 2:
            self.console._print("Ошибка использования: layer <номер> [show|del]", "error")
            self.console._print("Примеры: layer 2, layer 2 show, layer 2 del", "info")
            return
        try:
            idx = int(parts[1]) - 1
            if idx < 0 or idx >= self.editor.map.get_num_layers():
                self.console._print(f"Ошибка: слой {idx + 1} не существует", "error")
                self.console._print(f"Всего слоёв: {self.editor.map.get_num_layers()}", "info")
                return
            if len(parts) == 2:
                self.editor.layer_manager.set_active_layer(idx)
                self.console._print(f"✓ Переключились на слой {idx + 1}", "success")
            elif len(parts) == 3:
                subcmd = parts[2].lower()
                if subcmd == "show":
                    self.editor.map.visible[idx] = not self.editor.map.visible[idx]
                    self.editor.ui.update_visibility_check()
                    self.editor.drawing.full_redraw()
                    status = "показан" if self.editor.map.visible[idx] else "скрыт"
                    self.console._print(f"Слой {idx+1} {status}", "success")
                elif subcmd == "del":
                    if self.editor.map.get_num_layers() <= 1:
                        self.console._print("Ошибка: нельзя удалить единственный слой", "error")
                        return
                    self.editor.save_state()
                    self.editor.map.remove_layer(idx)
                    if self.editor.layer_manager.current_layer >= self.editor.map.get_num_layers():
                        self.editor.layer_manager.current_layer = self.editor.map.get_num_layers() - 1
                    self.editor.layer_manager.set_active_layer(self.editor.layer_manager.current_layer)
                    self.editor.ui.update_layer_ui()
                    self.editor.drawing.full_redraw()
                    self.console._print(f"✓ Слой {idx + 1} удалён", "success")
                else:
                    self.console._print(f"Ошибка: неизвестная подкоманда '{subcmd}'", "error")
            else:
                self.console._print("Ошибка: слишком много аргументов", "error")
        except ValueError:
            self.console._print("Ошибка: неверный номер слоя", "error")
    
    def _cmd_tool(self, parts=None) -> None:
        tool_name = self.editor.tool_manager.get_tool_name()
        self.console._print(f"Текущий инструмент: {tool_name}", "info")
        if self.editor.tool_manager.tool == EMPTY or self.editor.tool_manager.tool is None:
            self.console._print("Для рисования выберите текстуру на панели инструментов", "warning")
    
    def _cmd_clear(self, parts: list) -> None:
        if len(parts) > 1 and parts[1] == "layer":
            self.editor.clear_layer(self.editor.layer_manager.current_layer)
        else:
            self.editor.clear_all_layers()
    
    def _cmd_clear_console(self, parts=None) -> None:
        self.console.text.config(state=tk.NORMAL)
        self.console.text.delete(1.0, tk.END)
        self.console.text.config(state=tk.DISABLED)
        self.console._print("Консоль очищена", "success")
    
    def _cmd_presets(self, parts=None) -> None:
        presets = self.editor.file.list_presets()
        if not presets:
            self.console._print("Нет доступных пресетов", "info")
            return
        self.console._print("Доступные пресеты:", "info")
        for p in sorted(presets):
            self.console._print(f"  {p}.json", "info")
    
    def _cmd_save_preset(self, parts=None) -> None:
        self.console.ask_input("Введите название пресета:", self.editor.save_preset_with_name)
    
    def _cmd_delete_preset(self, parts: list) -> None:
        if len(parts) != 2:
            self.console._print("Ошибка использования: delete_preset <имя>", "error")
            self.console._print("Пример: delete_preset kakoi_to", "info")
            return
        preset_name = parts[1]
        if self.editor.file.delete_preset(preset_name):
            self.console._print(f"✓ Пресет '{preset_name}.json' удалён", "success")
        else:
            self.console._print(f"Ошибка удаления пресета '{preset_name}.json'", "error")
    
    def _cmd_load_preset(self, parts=None) -> None:
        presets = self.editor.file.list_presets()
        if not presets:
            self.console._print("Нет доступных пресетов", "error")
            return
        self.console.show_preset_selection(presets)

    def _cmd_replace(self, parts: list) -> None:
        if len(parts) != 3:
            self.console._print("Ошибка использования: replace старая_текстура.png новая_текстура.png", "error")
            return
        old = parts[1]
        new = parts[2]
        self.editor.replace_texture_all_layers(old, new)

    def _cmd_brush(self, parts: list) -> None:
        if len(parts) != 2:
            self.console._print("Ошибка использования: brush <размер>", "error")
            return
        try:
            size = int(parts[1])
            self.editor.set_brush_size(size)
        except ValueError:
            self.console._print("Ошибка: размер должен быть числом", "error")