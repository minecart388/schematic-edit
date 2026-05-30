# console.py
import tkinter as tk
from typing import Optional, List, Tuple
from .config import CFG, EMPTY
from .console_cmd import ConsoleCommands

class ConsoleManager:
    def __init__(self, editor):
        self.editor = editor
        self.frame: Optional[tk.Frame] = None
        self.text: Optional[tk.Text] = None
        self.input_text: Optional[tk.Text] = None
        self.line_numbers: Optional[tk.Text] = None
        self.scrollbar: Optional[tk.Scrollbar] = None
        self.history: List[str] = []
        self.history_index = 0
        self.current_prompt = ">> "
        self.waiting_for_input = False
        self.input_callback = None
        self.waiting_for_preset = False
        self.preset_list = []
        self.completion_index = 0
        self.completion_matches: List[str] = []
        self.completion_popup: Optional[tk.Toplevel] = None
        self.completion_listbox: Optional[tk.Listbox] = None

        self.commands = ConsoleCommands(self)
        self._console_has_focus = False

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

        self.text.bind("<MouseWheel>", self.on_mousewheel)
        self.text.bind("<Button-4>", self.on_mousewheel)
        self.text.bind("<Button-5>", self.on_mousewheel)

        input_container = tk.Frame(self.frame, bg=colors["BG_CANVAS"])
        input_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.line_numbers = tk.Text(input_container, width=6, padx=2, takefocus=0,
                                     bg=colors["BG_CANVAS"], fg=colors["GREY"],
                                     relief=tk.FLAT, bd=0, font=("Consolas", 9))
        self.line_numbers.config(state=tk.DISABLED)

        self.input_text = tk.Text(input_container, bg=colors["BG_CANVAS"], fg=colors["TEXT"],
                                   relief=tk.FLAT, bd=0, font=("Consolas", 9),
                                   wrap=tk.NONE, undo=False,
                                   insertbackground=colors["TEXT"])

        self.scrollbar = tk.Scrollbar(input_container, orient=tk.VERTICAL, command=self._sync_scroll)
        self.input_text.config(yscrollcommand=self.scrollbar.set)
        self.line_numbers.config(yscrollcommand=self.scrollbar.set)

        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.input_text.bind("<MouseWheel>", self.on_mousewheel)
        self.input_text.bind("<Button-4>", self.on_mousewheel)
        self.input_text.bind("<Button-5>", self.on_mousewheel)
        self.line_numbers.bind("<MouseWheel>", self.on_mousewheel)
        self.line_numbers.bind("<Button-4>", self.on_mousewheel)
        self.line_numbers.bind("<Button-5>", self.on_mousewheel)
        self.input_text.bind("<Control-Return>", self._execute_multiline)
        self.input_text.bind("<Control-v>", self._on_paste)
        self.input_text.bind("<Control-V>", self._on_paste)
        self.input_text.bind("<KeyRelease>", self._update_line_numbers)
        self.input_text.bind("<Up>", self._history_up)
        self.input_text.bind("<Down>", self._history_down)
        self.input_text.bind("<Tab>", self._auto_complete)
        self.input_text.bind("<FocusIn>", self._on_console_focus)
        self.input_text.bind("<FocusOut>", self._on_console_blur)

        self.input_text.focus_set()

        self._update_line_numbers()

        self._print("Консоль управления", "success")

    def _sync_scroll(self, *args):
        if self.input_text and self.line_numbers:
            self.input_text.yview(*args)
            self.line_numbers.yview(*args)

    def on_mousewheel(self, event: tk.Event):
        if event.widget == self.text:
            if event.delta:
                self.text.yview_scroll(int(-event.delta/120), "units")
            elif event.num == 4:
                self.text.yview_scroll(-1, "units")
            elif event.num == 5:
                self.text.yview_scroll(1, "units")
        elif event.widget in (self.input_text, self.line_numbers):
            if event.delta:
                self.input_text.yview_scroll(int(-event.delta/120), "units")
                self.line_numbers.yview_scroll(int(-event.delta/120), "units")
            elif event.num == 4:
                self.input_text.yview_scroll(-1, "units")
                self.line_numbers.yview_scroll(-1, "units")
            elif event.num == 5:
                self.input_text.yview_scroll(1, "units")
                self.line_numbers.yview_scroll(1, "units")
        return "break"

    def _on_console_focus(self, event=None):
        self._console_has_focus = True

    def _on_console_blur(self, event=None):
        self._console_has_focus = False

    def console_has_focus(self) -> bool:
        return self._console_has_focus

    def _get_current_word(self) -> Tuple[str, str, int, int]:
        cursor_pos = self.input_text.index(tk.INSERT)
        line_start = f"{cursor_pos.split('.')[0]}.0"
        line_text = self.input_text.get(line_start, cursor_pos)
        words = line_text.split()
        if not words:
            return "", "", 0, 0
        last_word = words[-1] if words else ""
        word_start = line_text.rfind(last_word)
        return last_word, line_text, word_start, len(last_word)

    def _get_completions(self, prefix: str) -> List[str]:
        if not prefix:
            return list(self.commands.commands.keys())
        prefix_lower = prefix.lower()
        matches = [cmd for cmd in self.commands.commands.keys() if cmd.startswith(prefix_lower)]
        if self.waiting_for_preset and self.preset_list:
            matches.extend([p for p in self.preset_list if p.lower().startswith(prefix_lower)])
        return sorted(matches)

    def _hide_completion_popup(self):
        if self.completion_popup and self.completion_popup.winfo_exists():
            self.completion_popup.destroy()
        self.completion_popup = None
        self.completion_listbox = None
        self.scrollbar = None

    def _show_completion_popup(self, matches: List[str], prefix: str):
        self._hide_completion_popup()
        if not matches:
            return
        try:
            cursor_bbox = self.input_text.bbox(tk.INSERT)
            if not cursor_bbox:
                return
            x = self.input_text.winfo_rootx() + cursor_bbox[0]
            y = self.input_text.winfo_rooty() + cursor_bbox[1] + cursor_bbox[3] + 2
            self.completion_popup = tk.Toplevel(self.input_text)
            self.completion_popup.wm_overrideredirect(True)
            self.completion_popup.configure(bg=CFG.colors["SLOT_BORDER"])
            main_frame = tk.Frame(self.completion_popup, bg=CFG.colors["SLOT_BORDER"], bd=1, relief=tk.SUNKEN)
            main_frame.pack(fill=tk.BOTH, expand=True)
            listbox_frame = tk.Frame(main_frame, bg=CFG.colors["BUTTON"])
            listbox_frame.pack(fill=tk.BOTH, expand=True)
            self.completion_listbox = tk.Listbox(listbox_frame, 
                                                  bg=CFG.colors["BUTTON"], 
                                                  fg=CFG.colors["TEXT"],
                                                  font=("Consolas", 9), 
                                                  selectbackground="#4CAF50",
                                                  selectforeground="white",
                                                  relief=tk.FLAT,
                                                  bd=0,
                                                  activestyle="none",
                                                  highlightthickness=0)
            self.completion_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            for match in matches:
                display_text = match
                if match in self.commands.commands:
                    display_text = f"{match:<15}"
                self.completion_listbox.insert(tk.END, display_text)
            if matches:
                self.completion_listbox.select_set(0)
            self.scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.completion_listbox.yview)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.completion_listbox.config(yscrollcommand=self.scrollbar.set)
            max_visible = 12
            visible_count = min(len(matches), max_visible)
            item_height = 18
            height = visible_count * item_height + 4
            max_width = 0
            for match in matches[:max_visible]:
                display_len = len(match) if len(match) <= 15 else 15
                width_px = display_len * 8 + 25
                if width_px > max_width:
                    max_width = width_px
            max_width = max(max_width, 120)
            self.completion_popup.geometry(f"{max_width}x{height}+{x}+{y}")

            def on_select(event):
                if self.completion_listbox and self.completion_listbox.curselection():
                    selected = self.completion_listbox.get(self.completion_listbox.curselection()[0]).strip()
                    self._replace_current_word(selected)
                    self._hide_completion_popup()

            def on_key(event):
                if not self.completion_listbox:
                    return
                if event.keysym == 'Down':
                    current = self.completion_listbox.curselection()
                    if current:
                        idx = current[0] + 1
                        if idx < self.completion_listbox.size():
                            self.completion_listbox.select_clear(0, tk.END)
                            self.completion_listbox.select_set(idx)
                            self.completion_listbox.see(idx)
                    else:
                        self.completion_listbox.select_set(0)
                        self.completion_listbox.see(0)
                elif event.keysym == 'Up':
                    current = self.completion_listbox.curselection()
                    if current:
                        idx = current[0] - 1
                        if idx >= 0:
                            self.completion_listbox.select_clear(0, tk.END)
                            self.completion_listbox.select_set(idx)
                            self.completion_listbox.see(idx)
                    else:
                        last_idx = self.completion_listbox.size() - 1
                        self.completion_listbox.select_set(last_idx)
                        self.completion_listbox.see(last_idx)
                elif event.keysym == 'Next':
                    self.completion_listbox.yview_scroll(1, "pages")
                elif event.keysym == 'Prior':
                    self.completion_listbox.yview_scroll(-1, "pages")
                elif event.keysym == 'Return':
                    on_select(None)
                    self._hide_completion_popup()
                elif event.keysym == 'Escape':
                    self._hide_completion_popup()
                elif event.keysym == 'Tab':
                    self._hide_completion_popup()
                    self._auto_complete()

            self.completion_listbox.bind('<Double-Button-1>', on_select)
            self.completion_listbox.bind('<Return>', on_select)
            self.completion_popup.bind('<Escape>', lambda e: self._hide_completion_popup())
            self.completion_popup.bind('<FocusOut>', lambda e: self._hide_completion_popup())
            self.completion_listbox.bind('<Key>', on_key)

            def on_destroy(e):
                self._hide_completion_popup()

            self.input_text.bind('<Key>', on_destroy, add='+')
            self.input_text.bind('<Button-1>', on_destroy, add='+')
            self.completion_listbox.focus_set()
        except Exception as e:
            print(f"Error showing completion: {e}")

    def _auto_complete(self, event=None):
        if self.waiting_for_input:
            return "break"
        self._hide_completion_popup()
        prefix, line_text, word_start, word_len = self._get_current_word()
        matches = self._get_completions(prefix)
        if not matches:
            return "break"
        if len(matches) == 1:
            self._replace_current_word(matches[0])
        else:
            self._show_completion_popup(matches, prefix)
        return "break"

    def _replace_current_word(self, new_word: str):
        cursor_pos = self.input_text.index(tk.INSERT)
        line_num = int(cursor_pos.split('.')[0])
        line_start = f"{line_num}.0"
        line_text = self.input_text.get(line_start, cursor_pos)
        words = line_text.split()
        if words:
            last_word = words[-1]
            word_start_in_line = line_text.rfind(last_word)
            word_end_in_line = word_start_in_line + len(last_word)
            new_char_pos = word_start_in_line + len(new_word)
            self.input_text.delete(f"{line_num}.{word_start_in_line}", f"{line_num}.{word_end_in_line}")
            self.input_text.insert(f"{line_num}.{word_start_in_line}", new_word)
            self.input_text.mark_set(tk.INSERT, f"{line_num}.{new_char_pos}")
        self._update_line_numbers()

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
        if self.completion_popup and self.completion_popup.winfo_exists():
            self.completion_popup.configure(bg=CFG.colors["SLOT_BORDER"])
            if self.completion_listbox:
                self.completion_listbox.configure(bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"])

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
        parts = command.lower().split()
        if not parts:
            return
        if not self.commands.execute(command, parts):
            self._print(f"Ошибка: неизвестная команда '{parts[0]}'", "error")
            self._print("Введите 'help' для списка команд", "info")

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
            if self.editor.file.delete_preset(preset_name):
                self._print(f"✓ Пресет '{preset_name}.json' удалён", "success")
            else:
                self._print(f"Ошибка удаления пресета '{preset_name}.json'", "error")
        elif cmd_lower in [p.lower() for p in self.preset_list]:
            for p in self.preset_list:
                if p.lower() == cmd_lower:
                    self._load_preset_file(p)
                    break
        else:
            self._print(f"Неизвестный пресет: {command}", "error")
            self._print("Введите название пресета", "info")
            self.waiting_for_preset = True

    def _load_preset_file(self, preset_name: str) -> None:
        self.editor.save_state()
        if self.editor.file.load_preset(preset_name):
            self.editor.ui.update_layer_ui()
            self.editor.layer_manager.current_layer = 0
            self.editor.layer_manager.set_active_layer(0)
            self.editor.drawing.redraw_visible_tiles()
            self._print(f"✓ Пресет '{preset_name}.json' загружен", "success")
        else:
            self._print(f"Ошибка загрузки пресета '{preset_name}.json'", "error")

    def ask_input(self, question: str, callback) -> None:
        self._print(question, "warning")
        self.waiting_for_input = True
        self.input_callback = callback

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