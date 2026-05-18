# console.py
import tkinter as tk
from typing import Optional, List, Tuple
from config import CFG, EMPTY
import os

class ConsoleManager:
    def __init__(self, editor):
        self.editor = editor
        self.frame: Optional[tk.Frame] = None
        self.text: Optional[tk.Text] = None
        self.entry: Optional[tk.Entry] = None
        self.history: List[str] = []
        self.history_index = 0
        self.entry_frame: Optional[tk.Frame] = None
        self.current_prompt = ">> "
        self.waiting_for_input = False
        self.input_callback = None
        self.waiting_for_preset = False
        self.preset_list = []
        self.prompt_label: Optional[tk.Label] = None
    
    def create(self, parent) -> None:
        colors = CFG.colors
        
        self.frame = tk.Frame(parent, bg=colors["BG_PANEL"], bd=1, relief=tk.SUNKEN, width=350)
        self.frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        self.frame.pack_propagate(False)
        
        self.text = tk.Text(self.frame, bg=colors["BG_CANVAS"], 
                            fg=colors["TEXT"], relief=tk.FLAT, bd=0,
                            font=("Consolas", 9), wrap=tk.WORD, height=50)
        self.text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))
        
        self.text.tag_config("prompt", foreground="#00AA00", font=("Consolas", 9, "bold"))
        self.text.tag_config("command", foreground="#FFFF00")
        self.text.tag_config("error", foreground="red")
        self.text.tag_config("success", foreground="green")
        self.text.tag_config("info", foreground="#66CCFF")
        self.text.tag_config("warning", foreground="#FFA500")
        
        self.text.config(state=tk.DISABLED)
        
        self.entry_frame = tk.Frame(self.frame, bg=colors["BG_PANEL"])
        self.entry_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        
        self.prompt_label = tk.Label(self.entry_frame, text=self.current_prompt, 
                                     bg=colors["BG_PANEL"], fg="#00AA00",
                                     font=("Consolas", 9, "bold"))
        self.prompt_label.pack(side=tk.LEFT)
        
        self.entry = tk.Entry(self.entry_frame, bg=colors["BUTTON"], fg=colors["TEXT"],
                              relief=tk.SUNKEN, bd=1, font=("Consolas", 9))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.entry.bind("<Return>", self._execute_command)
        self.entry.bind("<Up>", self._prev_command)
        self.entry.bind("<Down>", self._next_command)
        self.entry.focus_set()
        
        self._print("Консоль управления", "success")
        self._print("Команды: help, circle, square, rect, line, clear, layers, layer, tool", "warning")
    
    def update_theme(self) -> None:
        colors = CFG.colors
        if self.frame:
            self.frame.configure(bg=colors["BG_PANEL"])
        if self.text:
            self.text.configure(bg=colors["BG_CANVAS"], fg=colors["TEXT"])
        if self.entry_frame:
            self.entry_frame.configure(bg=colors["BG_PANEL"])
        if self.prompt_label:
            self.prompt_label.configure(bg=colors["BG_PANEL"])
        if self.entry:
            self.entry.configure(bg=colors["BUTTON"], fg=colors["TEXT"])
    
    def _print(self, message: str, msg_type: str = "normal") -> None:
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, message + "\n")
        self.text.see(tk.END)
        self.text.config(state=tk.DISABLED)
        
        if msg_type == "error":
            self.text.tag_add("error", "end-2l", "end-1l")
        elif msg_type == "success":
            self.text.tag_add("success", "end-2l", "end-1l")
        elif msg_type == "info":
            self.text.tag_add("info", "end-2l", "end-1l")
        elif msg_type == "warning":
            self.text.tag_add("warning", "end-2l", "end-1l")
    
    def _print_command(self, command: str) -> None:
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, self.current_prompt, "prompt")
        self.text.insert(tk.END, command + "\n", "command")
        self.text.see(tk.END)
        self.text.config(state=tk.DISABLED)
    
    def _execute_command(self, event=None) -> None:
        if not self.entry:
            return
        
        command = self.entry.get().strip()
        if not command:
            return
        
        if self.waiting_for_input:
            self._handle_input(command)
            return
        
        if self.waiting_for_preset:
            self._handle_preset_selection(command)
            return
        
        self.history.append(command)
        self.history_index = len(self.history)
        
        self._print_command(command)
        self._parse_and_execute(command)
        self.entry.delete(0, tk.END)
    
    def _handle_input(self, command: str) -> None:
        self.waiting_for_input = False
        if self.input_callback:
            self.input_callback(command)
        self.input_callback = None
    
    def _handle_preset_selection(self, command: str) -> None:
        self.waiting_for_preset = False
        cmd_lower = command.lower().strip()
        
        if cmd_lower == "cancel":
            self._print("Выбор пресета отменён", "info")
            return
        
        parts = cmd_lower.split()
        if len(parts) >= 2 and parts[1] == "delete":
            preset_name = parts[0]
            if preset_name.endswith('.json'):
                preset_name = preset_name[:-5]
            self._confirm_delete_preset(preset_name)
        elif cmd_lower in [p.lower() for p in self.preset_list]:
            for p in self.preset_list:
                if p.lower() == cmd_lower:
                    self._load_preset_file(p)
                    break
        else:
            self._print(f"Неизвестный пресет: {command}", "error")
            self._print("Введите название пресета", "info")
            self.waiting_for_preset = True
    
    def _confirm_delete_preset(self, preset_name: str) -> None:
        self.ask_yes_no(f"Удалить пресет '{preset_name}.json'?", lambda confirmed: self._delete_preset(preset_name, confirmed))
    
    def _delete_preset(self, preset_name: str, confirmed: bool) -> None:
        if confirmed:
            preset_path = os.path.join(self.editor.preset_dir, preset_name + ".json")
            try:
                os.remove(preset_path)
                self._print(f"✓ Пресет '{preset_name}.json' удалён", "success")
            except Exception as e:
                self._print(f"Ошибка удаления: {e}", "error")
        else:
            self._print(f"Удаление пресета '{preset_name}.json' отменено", "info")
    
    def _load_preset_file(self, preset_name: str) -> None:
        self.editor.save_state()
        if self.editor.file.load_preset(preset_name):
            self.editor.ui.update_layer_ui()
            self.editor.layer_manager.current_layer = 0
            self.editor.layer_manager.set_active_layer(0)
            self.editor.draw()
            self._print(f"✓ Пресет '{preset_name}.json' загружен", "success")
        else:
            self._print(f"Ошибка загрузки пресета '{preset_name}.json'", "error")
    
    def ask_input(self, question: str, callback) -> None:
        self._print(question, "warning")
        self.waiting_for_input = True
        self.input_callback = callback
    
    def ask_yes_no(self, question: str, callback) -> None:
        self._print(question + " (yes/no): ", "warning")
        self.waiting_for_input = True
        self.input_callback = lambda answer: callback(answer.lower() in ['yes', 'y', 'да', 'д'])
    
    def show_preset_selection(self, presets: List[str]) -> None:
        if not presets:
            self._print("Нет доступных пресетов", "error")
            return
        
        self.preset_list = presets
        self._print("", "info")
        self._print("Доступные пресеты:", "info")
        self._print("─" * 50, "info")
        for p in sorted(presets):
            self._print(f"  {p}.json", "info")
        self._print("─" * 50, "info")
        self._print("Введите название пресета для загрузки", "info")
        self.waiting_for_preset = True
    
    def _prev_command(self, event=None) -> str:
        if self.history_index > 0:
            self.history_index -= 1
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.history[self.history_index])
        return "break"
    
    def _next_command(self, event=None) -> str:
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.history[self.history_index])
        elif self.history_index == len(self.history) - 1:
            self.history_index = len(self.history)
            self.entry.delete(0, tk.END)
        return "break"
    
    def _parse_and_execute(self, command: str) -> None:
        parts = command.lower().split()
        if not parts:
            return
        
        cmd = parts[0]
        
        if cmd == "help" or cmd == "?":
            self._show_help()
        elif cmd == "circle":
            self._cmd_circle(parts)
        elif cmd == "square":
            self._cmd_square(parts)
        elif cmd == "rect":
            self._cmd_rect(parts)
        elif cmd == "line":
            self._cmd_line(parts)
        elif cmd == "clear":
            self._cmd_clear(parts)
        elif cmd == "layers":
            self._cmd_layers()
        elif cmd == "layer":
            self._cmd_layer(parts)
        elif cmd == "tool":
            self._cmd_tool()
        elif cmd == "clear_console":
            self._clear_console()
        elif cmd == "presets":
            self._cmd_presets()
        elif cmd == "save_preset":
            self._cmd_save_preset()
        elif cmd == "delete_preset":
            self._cmd_delete_preset(parts)
        elif cmd == "load_preset":
            self._cmd_load_preset()
        else:
            self._print(f"Ошибка: неизвестная команда '{cmd}'", "error")
            self._print("Введите 'help' для списка команд", "info")
    
    def _clear_console(self) -> None:
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.config(state=tk.DISABLED)
        self._print("Консоль очищена", "success")
    
    def _show_help(self) -> None:
        help_text = """
Доступные команды:
------------------------------------------
  circle x y radius fill - круг
  square x y size fill - квадрат
  rect x1 y1 x2 y2 fill - прямоугольник
  line x1 y1 x2 y2 толщина - линия
  layers - показать информацию о слоях
  layer <номер> - переключиться на слой
  tool - показать текущий инструмент
  clear [all|layer] - очистить всё или текущий слой
  presets - показать список пресетов
  save_preset - сохранить текущую карту как пресет
  load_preset - загрузить пресет
  delete_preset <имя> - удалить пресет
  clear_console - очистить консоль
  help - показать справку

ПАРАМЕТРЫ:
  fill: true/false - заливка фигуры
  координаты: x, y - в клетках карты
------------------------------------------
        """
        self._print(help_text, "info")
    
    def _check_texture_selected(self) -> bool:
        if not self.editor.tool or self.editor.tool == EMPTY:
            self._print("Ошибка: сначала выберите текстуру для рисования", "error")
            self._print("Нажмите на текстуру в панели инструментов", "info")
            return False
        return True
    
    def _cmd_presets(self) -> None:
        presets = self.editor.file.list_presets()
        if not presets:
            self._print("Нет доступных пресетов", "info")
            return
        self._print("ДОСТУПНЫЕ ПРЕСЕТЫ:", "info")
        self._print("─" * 40, "info")
        for p in sorted(presets):
            self._print(f"  {p}.json", "info")
        self._print("─" * 40, "info")
    
    def _cmd_save_preset(self) -> None:
        self.ask_input("Введите название пресета:", self._save_preset_callback)
    
    def _save_preset_callback(self, name: str) -> None:
        if not name.strip():
            self._print("Ошибка: название не может быть пустым", "error")
            return
        saved = self.editor.file.save_preset(name.strip())
        if saved:
            self._print(f"✓ Пресет сохранён как '{saved}.json'", "success")
        else:
            self._print("Ошибка сохранения пресета", "error")
    
    def _cmd_delete_preset(self, parts: list) -> None:
        if len(parts) != 2:
            self._print("Ошибка использования: delete_preset <имя>", "error")
            self._print("Пример: delete_preset kakoi_to", "info")
            return
        preset_name = parts[1]
        self._confirm_delete_preset(preset_name)
    
    def _cmd_load_preset(self) -> None:
        presets = self.editor.file.list_presets()
        if not presets:
            self._print("Нет доступных пресетов", "error")
            return
        self.show_preset_selection(presets)
    
    def _cmd_circle(self, parts: list) -> None:
        if len(parts) != 5:
            self._print("Ошибка использования: circle x y radius fill", "error")
            self._print("Пример: circle 50 25 10 true", "info")
            return
        
        if not self._check_texture_selected():
            return
        
        try:
            x = int(parts[1])
            y = int(parts[2])
            radius = int(parts[3])
            fill = parts[4].lower() in ['true', '1', 'yes', 't']
            
            if radius < 1:
                self._print("Ошибка: радиус должен быть больше 0", "error")
                return
            
            self.editor.save_state()
            self._draw_circle(x, y, radius, fill)
            self.editor.draw()
            self._print(f"✓ Круг нарисован: центр({x},{y}) радиус={radius} заливка={'да' if fill else 'нет'}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")
    
    def _draw_circle(self, cx: int, cy: int, radius: int, fill: bool) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        tool = self.editor.tool
        
        if fill:
            for y in range(-radius, radius + 1):
                for x in range(-radius, radius + 1):
                    if x*x + y*y <= radius*radius:
                        nx = cx + x
                        ny = cy + y
                        if 0 <= nx < CFG.map_width and 0 <= ny < CFG.map_height:
                            layer.grid[ny][nx] = tool
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
                if 0 <= px < CFG.map_width and 0 <= py < CFG.map_height:
                    layer.grid[py][px] = tool
    
    def _cmd_square(self, parts: list) -> None:
        if len(parts) != 5:
            self._print("Ошибка использования: square x y size fill", "error")
            self._print("Пример: square 50 25 20 true", "info")
            return
        
        if not self._check_texture_selected():
            return
        
        try:
            x = int(parts[1])
            y = int(parts[2])
            size = int(parts[3])
            fill = parts[4].lower() in ['true', '1', 'yes', 't']
            
            if size < 1:
                self._print("Ошибка: размер должен быть больше 0", "error")
                return
            
            half = size // 2
            x1 = x - half
            y1 = y - half
            x2 = x + half
            y2 = y + half
            
            self.editor.save_state()
            self._draw_rectangle(x1, y1, x2, y2, fill)
            self.editor.draw()
            self._print(f"✓ Квадрат нарисован: центр({x},{y}) размер={size} заливка={'да' if fill else 'нет'}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")
    
    def _cmd_rect(self, parts: list) -> None:
        if len(parts) != 6:
            self._print("Ошибка использования: rect x1 y1 x2 y2 fill", "error")
            self._print("Пример: rect 10 10 90 40 true", "info")
            return
        
        if not self._check_texture_selected():
            return
        
        try:
            x1 = int(parts[1])
            y1 = int(parts[2])
            x2 = int(parts[3])
            y2 = int(parts[4])
            fill = parts[5].lower() in ['true', '1', 'yes', 't']
            
            self.editor.save_state()
            self._draw_rectangle(x1, y1, x2, y2, fill)
            self.editor.draw()
            self._print(f"✓ Прямоугольник нарисован: ({x1},{y1})-({x2},{y2}) заливка={'да' if fill else 'нет'}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")
    
    def _draw_rectangle(self, x1: int, y1: int, x2: int, y2: int, fill: bool) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        tool = self.editor.tool
        
        left = max(0, min(x1, x2))
        right = min(CFG.map_width - 1, max(x1, x2))
        top = max(0, min(y1, y2))
        bottom = min(CFG.map_height - 1, max(y1, y2))
        
        if fill:
            for y in range(top, bottom + 1):
                for x in range(left, right + 1):
                    layer.grid[y][x] = tool
        else:
            for x in range(left, right + 1):
                if 0 <= top < CFG.map_height:
                    layer.grid[top][x] = tool
                if 0 <= bottom < CFG.map_height:
                    layer.grid[bottom][x] = tool
            for y in range(top + 1, bottom):
                if 0 <= left < CFG.map_width:
                    layer.grid[y][left] = tool
                if 0 <= right < CFG.map_width:
                    layer.grid[y][right] = tool
    
    def _cmd_line(self, parts: list) -> None:
        if len(parts) != 6:
            self._print("Ошибка использования: line x1 y1 x2 y2 толщина", "error")
            self._print("Пример: line 10 10 90 40 3", "info")
            return
        
        if not self._check_texture_selected():
            return
        
        try:
            x1 = int(parts[1])
            y1 = int(parts[2])
            x2 = int(parts[3])
            y2 = int(parts[4])
            thickness = int(parts[5])
            
            if thickness < 1 or thickness > 10:
                self._print("Ошибка: толщина должна быть от 1 до 10", "error")
                return
            
            self.editor.save_state()
            self._draw_line(x1, y1, x2, y2, thickness)
            self.editor.draw()
            self._print(f"✓ Линия нарисована: ({x1},{y1})→({x2},{y2}) толщина={thickness}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")
    
    def _draw_line(self, x1: int, y1: int, x2: int, y2: int, thickness: int) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        tool = self.editor.tool
        points = self._get_line_points(x1, y1, x2, y2)
        
        for px, py in points:
            for dy in range(-(thickness // 2), (thickness + 1) // 2):
                for dx in range(-(thickness // 2), (thickness + 1) // 2):
                    nx = px + dx
                    ny = py + dy
                    if 0 <= nx < CFG.map_width and 0 <= ny < CFG.map_height:
                        layer.grid[ny][nx] = tool
    
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
    
    def _cmd_layers(self) -> None:
        num_layers = self.editor.map.get_num_layers()
        self._print("------------------------------------------", "info")
        self._print(f"Слои:", "info")
        self._print(f"  Всего слоёв: {num_layers}", "info")
        self._print(f"  Активный слой: {self.editor.layer_manager.current_layer + 1}", "info")
        self._print("", "normal")
        for i in range(num_layers):
            visibility = "✓" if self.editor.map.visible[i] else "✗"
            status = "вид" if self.editor.map.visible[i] else "скрыт"
            self._print(f"  Слой {i+1}: [{visibility}] {status}", "normal")
        self._print("------------------------------------------", "info")
    
    def _cmd_layer(self, parts: list) -> None:
        if len(parts) != 2:
            self._print("Ошибка использования: layer <номер>", "error")
            self._print("Пример: layer 2", "info")
            return
        
        try:
            idx = int(parts[1]) - 1
            if 0 <= idx < self.editor.map.get_num_layers():
                self.editor.layer_manager.set_active_layer(idx)
                self._print(f"✓ Переключились на слой {idx + 1}", "success")
            else:
                self._print(f"Ошибка: слой {idx + 1} не существует", "error")
                self._print(f"Всего слоёв: {self.editor.map.get_num_layers()}", "info")
        except ValueError:
            self._print("Ошибка: неверный номер слоя", "error")
    
    def _cmd_tool(self) -> None:
        if self.editor.tool == EMPTY:
            tool_name = "Ластик"
        elif self.editor.tool is None:
            if self.editor.fence:
                tool_name = "Граница"
            elif self.editor.pipette_mode:
                tool_name = "Пипетка"
            elif self.editor.flood_mode:
                tool_name = "Заливка"
            else:
                tool_name = "Не выбран"
        else:
            tool_name = f"Текстура {self.editor.tool}"
            for name, code in self.editor.tex.codes.items():
                if code == self.editor.tool:
                    tool_name = name
                    break
        
        self._print(f"Текущий инструмент: {tool_name}", "info")
        if self.editor.tool == EMPTY or self.editor.tool is None:
            self._print("Для рисования выберите текстуру на панели инструментов", "warning")
    
    def _cmd_clear(self, parts: list) -> None:
        if len(parts) > 1 and parts[1] == "layer":
            self.ask_yes_no(f"Очистить текущий слой {self.editor.layer_manager.current_layer + 1}?", self._clear_layer_callback)
        else:
            self.ask_yes_no("Очистить все слои?", self._clear_all_callback)
    
    def _clear_layer_callback(self, confirmed: bool) -> None:
        if confirmed:
            self.editor.save_state()
            self.editor.map.clear_layer(self.editor.layer_manager.current_layer)
            self.editor.draw()
            self._print(f"✓ Слой {self.editor.layer_manager.current_layer + 1} очищен", "success")
        else:
            self._print("Очистка слоя отменена", "info")
    
    def _clear_all_callback(self, confirmed: bool) -> None:
        if confirmed:
            self.editor.save_state()
            self.editor.map.clear_all()
            self.editor.draw()
            self._print("✓ Все слои очищены", "success")
        else:
            self._print("Очистка всех слоёв отменена", "info")