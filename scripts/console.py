# console.py
import tkinter as tk
from typing import Optional, List, Tuple
from .config import CFG, EMPTY
import os

class ConsoleManager:
    def __init__(self, editor):
        self.editor = editor
        self.frame: Optional[tk.Frame] = None
        self.text: Optional[tk.Text] = None
        self.input_text: Optional[tk.Text] = None
        self.line_numbers: Optional[tk.Text] = None
        self.history: List[str] = []
        self.history_index = 0
        self.current_prompt = ">> "
        self.waiting_for_input = False
        self.input_callback = None
        self.waiting_for_preset = False
        self.preset_list = []

    def create(self, parent) -> None:
        colors = CFG.colors

        self.frame = tk.Frame(parent, bg=colors["BG_PANEL"], bd=1, relief=tk.SUNKEN, width=350)
        self.frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        self.frame.pack_propagate(False)

        self.text = tk.Text(self.frame, bg=colors["BG_CANVAS"], 
                            fg=colors["TEXT"], relief=tk.FLAT, bd=0,
                            font=("Consolas", 9), wrap=tk.WORD, height=20)
        self.text.pack(fill=tk.BOTH, expand=True, padx=(5, 0), pady=(5, 0))

        self.text.tag_config("prompt", foreground="#00AA00", font=("Consolas", 9, "bold"))
        self.text.tag_config("command", foreground="#FFFF00")
        self.text.tag_config("error", foreground="red")
        self.text.tag_config("success", foreground="green")
        self.text.tag_config("info", foreground="#66CCFF")
        self.text.tag_config("warning", foreground="#FFA500")

        self.text.config(state=tk.DISABLED)

        input_container = tk.Frame(self.frame, bg=colors["BG_CANVAS"])
        input_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.line_numbers = tk.Text(input_container, width=6, padx=2, takefocus=0,
                                     bg=colors["BG_CANVAS"], fg=colors["GREY"],
                                     relief=tk.FLAT, bd=0, font=("Consolas", 9))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.line_numbers.config(state=tk.DISABLED)

        self.input_text = tk.Text(input_container, bg=colors["BG_CANVAS"], fg=colors["TEXT"],
                                   relief=tk.FLAT, bd=0, font=("Consolas", 9),
                                   wrap=tk.NONE, height=8, undo=False,
                                   insertbackground=colors["TEXT"])
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.input_text.bind("<Control-Return>", self._execute_multiline)
        self.input_text.bind("<Control-v>", self._on_paste)
        self.input_text.bind("<Control-V>", self._on_paste)
        self.input_text.bind("<MouseWheel>", self._on_mousewheel)
        self.input_text.bind("<Button-4>", self._on_mousewheel)
        self.input_text.bind("<Button-5>", self._on_mousewheel)
        self.input_text.bind("<KeyRelease>", self._update_line_numbers)
        self.input_text.bind("<Up>", self._history_up)
        self.input_text.bind("<Down>", self._history_down)

        self.input_text.focus_set()

        self._update_line_numbers()

        self._print("Консоль управления", "success")
        self._print("Команды: help, circle, square, rect, line, clear, layers, layer, tool", "info")

    def _history_up(self, event):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self._set_input_text(self.history[self.history_index])
        return "break"

    def _history_down(self, event):
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._set_input_text(self.history[self.history_index])
        elif self.history_index == len(self.history) - 1:
            self.history_index += 1
            self._set_input_text("")
        return "break"

    def _set_input_text(self, text: str):
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)
        self._update_line_numbers()

    def _on_paste(self, event):
        try:
            text = self.input_text.clipboard_get()
            self.input_text.insert(tk.INSERT, text)
            self._update_line_numbers()
        except:
            pass
        return "break"

    def _on_mousewheel(self, event):
        if event.delta:
            self.input_text.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.input_text.yview_scroll(-1, "units")
        elif event.num == 5:
            self.input_text.yview_scroll(1, "units")
        self._update_line_numbers()
        return "break"

    def _update_line_numbers(self, event=None):
        if not self.line_numbers or not self.input_text:
            return

        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete(1.0, tk.END)

        line_count = int(self.input_text.index('end-1c').split('.')[0])

        for i in range(1, line_count + 1):
            self.line_numbers.insert(tk.END, f"{i} {self.current_prompt}\n")

        self.line_numbers.config(state=tk.DISABLED)

    def update_theme(self) -> None:
        colors = CFG.colors
        if self.frame:
            self.frame.configure(bg=colors["BG_PANEL"])
        if self.text:
            self.text.configure(bg=colors["BG_CANVAS"], fg=colors["TEXT"])
        if self.input_text:
            self.input_text.configure(bg=colors["BG_CANVAS"], fg=colors["TEXT"],
                                    insertbackground=colors["TEXT"])
        if self.line_numbers:
            self.line_numbers.configure(bg=colors["BG_CANVAS"], fg=colors["GREY"])

    def _execute_multiline(self, event=None) -> None:
        if not self.input_text:
            return

        full_text = self.input_text.get("1.0", "end-1c")
        if not full_text.strip():
            return "break"

        lines = []
        for line in full_text.splitlines():
            line = line.strip()
            if line:
                lines.append(line)

        for line in lines:
            self._execute_command_line(line)

        self.input_text.delete("1.0", tk.END)
        self._update_line_numbers()
        return "break"

    def _print(self, message: str, msg_type: str = "normal") -> None:
        self.text.config(state=tk.NORMAL)
        start_pos = self.text.index("end-1c")
        self.text.insert(tk.END, message + "\n")
        end_pos = self.text.index("end-1c")
        self.text.see(tk.END)
        if msg_type == "error":
            self.text.tag_add("error", start_pos, end_pos)
        elif msg_type == "success":
            self.text.tag_add("success", start_pos, end_pos)
        elif msg_type == "info":
            self.text.tag_add("info", start_pos, end_pos)
        elif msg_type == "warning":
            self.text.tag_add("warning", start_pos, end_pos)
        self.text.config(state=tk.DISABLED)

    def _print_command(self, command: str) -> None:
        self.text.config(state=tk.NORMAL)
        start_prompt = self.text.index("end-1c")
        self.text.insert(tk.END, self.current_prompt, "prompt")
        end_prompt = self.text.index("end-1c")
        self.text.insert(tk.END, command + "\n", "command")
        self.text.see(tk.END)
        self.text.config(state=tk.DISABLED)

    def _execute_command_line(self, command: str) -> None:
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
        self._print("Доступные пресеты:", "info")
        for p in sorted(presets):
            self._print(f"  {p}.json", "info")
        self._print("Введите название пресета для загрузки", "info")
        self.waiting_for_preset = True

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
  circle x y radius fill [texture.png] - круг
  square x y size fill [texture.png] - квадрат
  rect x1 y1 x2 y2 fill [texture.png] - прямоугольник
  line x1 y1 x2 y2 толщина [texture.png] - линия
  layers - показать информацию о слоях
  layer <номер> - переключиться на слой
  layer <номер> show - показать детали слоя
  layer <номер> del - удалить слой (с подтверждением)
  tool - показать текущий инструмент
  clear [all|layer] - очистить всё или текущий слой
  presets - показать список пресетов
  save_preset - сохранить текущую карту как пресет
  load_preset - загрузить пресет
  delete_preset <имя> - удалить пресет
  clear_console - очистить консоль
  help - показать справку

Параметры:
  fill: true/false - заливка фигуры
  texture.png - имя файла текстуры
------------------------------------------
        """
        self._print(help_text, "info")

    def _get_current_texture_or_default(self, provided_name: Optional[str]) -> Optional[str]:
        if provided_name and provided_name in self.editor.tex.blocks:
            return provided_name
        if isinstance(self.editor.tool_manager.tool, str) and self.editor.tool_manager.tool in self.editor.tex.blocks:
            return self.editor.tool_manager.tool
        self._print("Ошибка: не выбрана текстура или текстура не найдена", "error")
        return None

    def _cmd_circle(self, parts: list) -> None:
        if len(parts) < 5 or len(parts) > 6:
            self._print("Ошибка использования: circle x y radius fill [texture.png]", "error")
            self._print("Пример: circle 50 25 10 true stone.png", "info")
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
                self._print("Ошибка: радиус должен быть больше 0", "error")
                return

            self.editor.save_state()
            self._draw_circle(x, y, radius, fill, tool)
            self.editor.draw()
            self._print(f"✓ Круг нарисован: центр({x},{y}) радиус={radius} заливка={'да' if fill else 'нет'} текстура={tool}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")

    def _draw_circle(self, cx: int, cy: int, radius: int, fill: bool, tex_name: str) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()

        if fill:
            for y in range(-radius, radius + 1):
                for x in range(-radius, radius + 1):
                    if x*x + y*y <= radius*radius:
                        nx = cx + x
                        ny = cy + y
                        if 0 <= nx < CFG.map_width and 0 <= ny < CFG.map_height:
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
                if 0 <= px < CFG.map_width and 0 <= py < CFG.map_height:
                    layer.grid[py][px] = tex_name

    def _cmd_square(self, parts: list) -> None:
        if len(parts) < 5 or len(parts) > 6:
            self._print("Ошибка использования: square x y size fill [texture.png]", "error")
            self._print("Пример: square 50 25 20 true stone.png", "info")
            return

        try:
            x = int(parts[1])
            y = int(parts[2])
            size = int(parts[3])
            fill = parts[4].lower() in ['true', '1', 'yes', 't']
            tex_name = parts[5] if len(parts) == 6 else None
            tool = self._get_current_texture_or_default(tex_name)
            if tool is None:
                return
            if size < 1:
                self._print("Ошибка: размер должен быть больше 0", "error")
                return

            half = size // 2
            x1 = x - half
            y1 = y - half
            x2 = x + half
            y2 = y + half

            self.editor.save_state()
            self._draw_rectangle(x1, y1, x2, y2, fill, tool)
            self.editor.draw()
            self._print(f"✓ Квадрат нарисован: центр({x},{y}) размер={size} заливка={'да' if fill else 'нет'} текстура={tool}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")

    def _cmd_rect(self, parts: list) -> None:
        if len(parts) < 6 or len(parts) > 7:
            self._print("Ошибка использования: rect x1 y1 x2 y2 fill [texture.png]", "error")
            self._print("Пример: rect 10 10 90 40 true stone.png", "info")
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
            self.editor.draw()
            self._print(f"✓ Прямоугольник нарисован: ({x1},{y1})-({x2},{y2}) заливка={'да' if fill else 'нет'} текстура={tool}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")

    def _draw_rectangle(self, x1: int, y1: int, x2: int, y2: int, fill: bool, tex_name: str) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()

        left = max(0, min(x1, x2))
        right = min(CFG.map_width - 1, max(x1, x2))
        top = max(0, min(y1, y2))
        bottom = min(CFG.map_height - 1, max(y1, y2))

        if fill:
            for y in range(top, bottom + 1):
                for x in range(left, right + 1):
                    layer.grid[y][x] = tex_name
        else:
            for x in range(left, right + 1):
                if 0 <= top < CFG.map_height:
                    layer.grid[top][x] = tex_name
                if 0 <= bottom < CFG.map_height:
                    layer.grid[bottom][x] = tex_name
            for y in range(top + 1, bottom):
                if 0 <= left < CFG.map_width:
                    layer.grid[y][left] = tex_name
                if 0 <= right < CFG.map_width:
                    layer.grid[y][right] = tex_name

    def _cmd_line(self, parts: list) -> None:
        if len(parts) < 6 or len(parts) > 7:
            self._print("Ошибка использования: line x1 y1 x2 y2 толщина [texture.png]", "error")
            self._print("Пример: line 10 10 90 40 3 stone.png", "info")
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
                self._print(f"Ошибка: толщина должна быть от {CFG.brush_min} до {CFG.brush_max}", "error")
                return

            self.editor.save_state()
            self._draw_line(x1, y1, x2, y2, thickness, tool)
            self.editor.draw()
            self._print(f"✓ Линия нарисована: ({x1},{y1})→({x2},{y2}) толщина={thickness} текстура={tool}", "success")
        except ValueError:
            self._print("Ошибка: неверный формат чисел", "error")

    def _draw_line(self, x1: int, y1: int, x2: int, y2: int, thickness: int, tex_name: str) -> None:
        layer = self.editor.layer_manager.get_active_layer_obj()
        points = self._get_line_points(x1, y1, x2, y2)

        for px, py in points:
            for dy in range(-(thickness // 2), (thickness + 1) // 2):
                for dx in range(-(thickness // 2), (thickness + 1) // 2):
                    nx = px + dx
                    ny = py + dy
                    if 0 <= nx < CFG.map_width and 0 <= ny < CFG.map_height:
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

    def _cmd_layers(self) -> None:
        num_layers = self.editor.map.get_num_layers()
        self._print(f"Слои:", "info")
        self._print(f"  Всего слоёв: {num_layers}", "info")
        self._print(f"  Активный слой: {self.editor.layer_manager.current_layer + 1}", "info")
        for i in range(num_layers):
            visibility = "✓" if self.editor.map.visible[i] else "✗"
            status = "вид" if self.editor.map.visible[i] else "скрыт"
            self._print(f"  Слой {i+1}: [{visibility}] {status}", "normal")

    def _show_layer_details(self, idx: int) -> None:
        layer = self.editor.map.layers[idx]
        visible = self.editor.map.visible[idx]
        filled = 0
        for row in layer.grid:
            for cell in row:
                if cell != EMPTY:
                    filled += 1
        total = CFG.map_width * CFG.map_height
        self._print(f"Слой {idx + 1}:", "info")
        self._print(f"  Видимость: {'да' if visible else 'нет'}", "info")
        self._print(f"  Заполнено: {filled} / {total} ({filled*100//total if total else 0}%)", "info")
        self._print(f"  Размер сетки: {CFG.map_width} x {CFG.map_height}", "info")

    def _confirm_delete_layer(self, idx: int) -> None:
        if self.editor.map.get_num_layers() <= 1:
            self._print("Ошибка: нельзя удалить единственный слой", "error")
            return
        self.ask_yes_no(f"Удалить слой {idx + 1}?", lambda confirmed: self._do_delete_layer(idx, confirmed))

    def _do_delete_layer(self, idx: int, confirmed: bool) -> None:
        if not confirmed:
            self._print("Удаление слоя отменено", "info")
            return
        self.editor.save_state()
        self.editor.map.remove_layer(idx)
        if self.editor.layer_manager.current_layer >= self.editor.map.get_num_layers():
            self.editor.layer_manager.current_layer = self.editor.map.get_num_layers() - 1
        self.editor.layer_manager.set_active_layer(self.editor.layer_manager.current_layer)
        self.editor.ui.update_layer_ui()
        self.editor.draw()
        self._print(f"✓ Слой {idx + 1} удалён", "success")

    def _cmd_layer(self, parts: list) -> None:
        if len(parts) < 2:
            self._print("Ошибка использования: layer <номер> [show|del]", "error")
            self._print("Примеры: layer 2, layer 2 show, layer 2 del", "info")
            return

        try:
            idx = int(parts[1]) - 1
            if idx < 0 or idx >= self.editor.map.get_num_layers():
                self._print(f"Ошибка: слой {idx + 1} не существует", "error")
                self._print(f"Всего слоёв: {self.editor.map.get_num_layers()}", "info")
                return

            if len(parts) == 2:
                self.editor.layer_manager.set_active_layer(idx)
                self._print(f"✓ Переключились на слой {idx + 1}", "success")
            elif len(parts) == 3:
                subcmd = parts[2].lower()
                if subcmd == "show":
                    self._show_layer_details(idx)
                elif subcmd == "del":
                    self._confirm_delete_layer(idx)
                else:
                    self._print(f"Ошибка: неизвестная подкоманда '{subcmd}'", "error")
            else:
                self._print("Ошибка: слишком много аргументов", "error")
        except ValueError:
            self._print("Ошибка: неверный номер слоя", "error")

    def _cmd_tool(self) -> None:
        tool_name = self.editor.tool_manager.get_tool_name()
        self._print(f"Текущий инструмент: {tool_name}", "info")
        if self.editor.tool_manager.tool == EMPTY or self.editor.tool_manager.tool is None:
            self._print("Для рисования выберите текстуру на панели инструментов", "warning")

    def _cmd_clear(self, parts: list) -> None:
        if len(parts) > 1 and parts[1] == "layer":
            self.editor.clear_layer(self.editor.layer_manager.current_layer, ask_confirm=True)
        else:
            self.editor.clear_all_layers(ask_confirm=True)

    def _cmd_presets(self) -> None:
        presets = self.editor.file.list_presets()
        if not presets:
            self._print("Нет доступных пресетов", "info")
            return
        self._print("Доступные пресеты:", "info")
        for p in sorted(presets):
            self._print(f"  {p}.json", "info")

    def _cmd_save_preset(self) -> None:
        self.ask_input("Введите название пресета:", self.editor.save_preset_with_name)

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