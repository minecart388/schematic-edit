# editor_ui.py
import tkinter as tk
from typing import Optional
from .config import CFG, EMPTY
from .hotbar import HotbarWidget, HotbarConfigWindow, HotbarManager


class UIManager:
    def __init__(self, editor):
        self.editor = editor
        self.canvas: Optional[tk.Canvas] = None
        self.status: Optional[tk.Label] = None
        self.toolbar_frame: Optional[tk.Frame] = None
        self.left_block: Optional[tk.Frame] = None          # сохранённая ссылка
        self.layer_frame: Optional[tk.Frame] = None
        self.layer_spinbox: Optional[tk.Spinbox] = None
        self.visible_var: Optional[tk.BooleanVar] = None
        self.visible_check: Optional[tk.Checkbutton] = None
        self.bottom_frame: Optional[tk.Frame] = None
        self.brush_size_label: Optional[tk.Label] = None
        self.grid_var: Optional[tk.BooleanVar] = None
        self.grid_check: Optional[tk.Checkbutton] = None
        self.hotbar_widget: Optional[HotbarWidget] = None
        self.hotbar_settings_btn: Optional[tk.Button] = None
        self.theme_btn: Optional[tk.Button] = None

    def setup(self, parent: tk.Frame) -> None:
        self._setup_canvas(parent)
        self._setup_toolbar_panel(parent)
        self._setup_layer_panel(parent)
        self._setup_bottom_panel(parent)
        self._setup_status_bar(parent)
        self._bind_hotbar_keys()

    def _bind_hotbar_keys(self) -> None:
        def on_key(event):
            if event.char.isdigit() and event.char != '0':
                idx = int(event.char) - 1
                if self.hotbar_widget and 0 <= idx < 9:
                    tex = self.editor.hotbar_mgr.get_slot(idx)
                    if tex:
                        self.hotbar_widget.select_slot(idx)
                        self.editor.tool_manager.set_tool(tex, False)
        self.editor.root.bind_all("<Key>", on_key)

    def clear_hotbar_selection(self) -> None:
        if self.hotbar_widget:
            self.hotbar_widget.clear_selection()

    def _setup_toolbar_panel(self, parent: tk.Frame) -> None:
        colors = CFG.colors
        self.toolbar_frame = tk.Frame(parent, bg=colors["BG_PANEL"])
        self.toolbar_frame.pack(fill=tk.X, pady=2)

        self.left_block = tk.Frame(self.toolbar_frame, bg=colors["BG_PANEL"])
        self.left_block.pack(side=tk.LEFT, padx=5)

        self._add_tool_button(self.left_block, "void.png", "Ластик", lambda: self.editor.tool_manager.set_tool(EMPTY, False))
        self._add_tool_button(self.left_block, "fence.png", "Граница", lambda: self.editor.tool_manager.set_tool(None, True))
        self._add_tool_button(self.left_block, "find.png", "Пипетка", lambda: self.editor.tool_manager.set_tool(-1, False))
        self._add_tool_button(self.left_block, "fill.png", "Заливка", lambda: self.editor.tool_manager.set_tool(-2, False))

        self.hotbar_widget = HotbarWidget(
            self.toolbar_frame,
            self.editor.tex,
            self.editor.hotbar_mgr,
            on_select_callback=lambda tex: self.editor.tool_manager.set_tool(tex, False)
        )

        self.hotbar_settings_btn = tk.Button(self.toolbar_frame, text="Заменить хотбар", command=self._open_hotbar_settings,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        self.hotbar_settings_btn.pack(side=tk.LEFT, padx=2)

    def _add_tool_button(self, parent, icon: str, tooltip: str, command) -> None:
        img = self.editor.tex.get_icon(icon)
        colors = CFG.colors
        if img:
            btn = tk.Button(parent, image=img, relief=tk.SOLID, bd=1, command=command,
                           bg=colors["BUTTON"], fg=colors["TEXT"],
                           activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn = tk.Button(parent, text=icon.split('.')[0], relief=tk.SOLID, bd=1, command=command,
                           bg=colors["BUTTON"], fg=colors["TEXT"],
                           activebackground=colors["BUTTON_ACTIVE"])
        btn.pack(side=tk.LEFT, padx=2)

    def refresh_hotbar(self) -> None:
        if self.hotbar_widget:
            self.hotbar_widget.refresh()

    def highlight_hotbar_slot(self, index: int) -> None:
        if self.hotbar_widget:
            self.hotbar_widget.select_slot(index)

    def _open_hotbar_settings(self) -> None:
        if self.hotbar_widget:
            HotbarConfigWindow(self.editor.root, self.editor.tex, self.editor.hotbar_mgr, self.hotbar_widget)

    def _setup_status_bar(self, parent: tk.Frame) -> None:
        colors = CFG.colors
        self.status = tk.Label(parent, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                               bg=colors["L_GREY"], fg=colors["TEXT"])
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        self.editor.theme.register_widget("status", self.status)

    def _setup_canvas(self, parent: tk.Frame) -> None:
        colors = CFG.colors
        self.canvas = tk.Canvas(parent, width=CFG.width_px, height=CFG.height_px, 
                                bg=colors["BG_CANVAS"], highlightthickness=0)
        self.canvas.pack(pady=5)

        self.canvas.bind("<ButtonPress-1>", self.editor.drawing.on_press)
        self.canvas.bind("<B1-Motion>", self.editor.drawing.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.editor.drawing.on_release)
        self.canvas.bind("<Motion>", self.editor.on_mouse_move)
        self.canvas.bind("<Alt-Button-1>", self.editor.drawing.pick_texture)

        self.editor.theme.register_widget("canvas", self.canvas)

    def _setup_layer_panel(self, parent: tk.Frame) -> None:
        colors = CFG.colors

        self.layer_frame = tk.Frame(parent, bg=colors["BG_PANEL"], pady=5)
        self.layer_frame.pack(fill=tk.X)

        tk.Label(self.layer_frame, text="Слои:", bg=colors["BG_PANEL"], 
                fg=colors["TEXT"]).pack(side=tk.LEFT, padx=5)

        self.layer_spinbox = tk.Spinbox(
            self.layer_frame, from_=1, to=CFG.max_layers, width=5,
            command=self._spinbox_changed,
            bg=colors["BUTTON"], fg=colors["TEXT"],
            buttonbackground=colors["BUTTON"],
            selectbackground=colors["GREY"],
            selectforeground=colors["TEXT"]
        )
        self.layer_spinbox.pack(side=tk.LEFT, padx=2)
        self.layer_spinbox.bind("<Return>", lambda e: self._spinbox_changed())

        btn_add = tk.Button(self.layer_frame, text="+", width=2, command=self._add_layer_callback,
                           bg=colors["BUTTON"], fg=colors["TEXT"],
                           activebackground=colors["BUTTON_ACTIVE"])
        btn_add.pack(side=tk.LEFT, padx=5)

        btn_remove = tk.Button(self.layer_frame, text="-", width=2, command=self._remove_layer_callback,
                              bg=colors["BUTTON"], fg=colors["TEXT"],
                              activebackground=colors["BUTTON_ACTIVE"])
        btn_remove.pack(side=tk.LEFT, padx=2)

        self.visible_var = tk.BooleanVar(value=True)
        self.visible_check = tk.Checkbutton(
            self.layer_frame, text="Вид", variable=self.visible_var,
            command=self.editor.layer_manager.toggle_visibility,
            bg=colors["BG_PANEL"], fg=colors["TEXT"], selectcolor=colors["BG_PANEL"]
        )
        self.visible_check.pack(side=tk.LEFT, padx=10)

        btn_manager = tk.Button(self.layer_frame, text="Список слоёв", command=self._open_layer_manager,
                               bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
        btn_manager.pack(side=tk.LEFT, padx=5)

        self.editor.theme.register_widget("layer_frame", self.layer_frame)
        self.editor.theme.register_widget("layer_spinbox", self.layer_spinbox)
        self.editor.theme.register_widget("visible_check", self.visible_check)

        self.update_layer_ui()

    def _add_layer_callback(self) -> None:
        if self.editor.map.get_num_layers() >= CFG.max_layers:
            self.editor.console._print(f"Ошибка: максимальное количество слоёв {CFG.max_layers}", "error")
        else:
            self.editor.layer_manager.add_layer()

    def _remove_layer_callback(self) -> None:
        if self.editor.map.get_num_layers() <= 1:
            self.editor.console._print("Ошибка: нельзя удалить единственный слой", "error")
        else:
            self.editor.console.ask_yes_no(f"Удалить слой {self.editor.layer_manager.current_layer + 1}?", self._confirm_remove_layer)

    def _confirm_remove_layer(self, confirmed: bool) -> None:
        if confirmed:
            self.editor.layer_manager.remove_layer()
            self.editor.console._print(f"✓ Слой удалён", "success")

    def _setup_bottom_panel(self, parent: tk.Frame) -> None:
        colors = CFG.colors

        self.bottom_frame = tk.Frame(parent, bg=colors["BG_PANEL"], pady=5)
        self.bottom_frame.pack(fill=tk.X)

        self._build_action_buttons()

        self._add_separator(self.bottom_frame)

        tk.Label(self.bottom_frame, text="Кисть:", bg=colors["BG_PANEL"], 
                fg=colors["TEXT"]).pack(side=tk.LEFT, padx=5)

        self.brush_size_label = tk.Label(self.bottom_frame, text=f"{self.editor.tool_manager.brush_size}", 
                                        width=3, bg=colors["BUTTON"], fg=colors["TEXT"],
                                        relief=tk.SUNKEN)
        self.brush_size_label.pack(side=tk.LEFT, padx=2)

        btn_minus = tk.Button(self.bottom_frame, text="-", width=2, command=self.editor.dec_brush,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_minus.pack(side=tk.LEFT, padx=1)

        btn_plus = tk.Button(self.bottom_frame, text="+", width=2, command=self.editor.inc_brush,
                            bg=colors["BUTTON"], fg=colors["TEXT"],
                            activebackground=colors["BUTTON_ACTIVE"])
        btn_plus.pack(side=tk.LEFT, padx=1)

        self.grid_var = tk.BooleanVar(value=self.editor.show_grid)
        self.grid_check = tk.Checkbutton(self.bottom_frame, text="Сетка", variable=self.grid_var, 
                                         command=self.editor.toggle_grid, bg=colors["BG_PANEL"],
                                         fg=colors["TEXT"], selectcolor=colors["BG_PANEL"])
        self.grid_check.pack(side=tk.LEFT, padx=10)

        self.theme_btn = tk.Button(self.bottom_frame, text="Тема", command=self.editor.toggle_theme,
                                   bg=colors["BUTTON"], fg=colors["TEXT"],
                                   activebackground=colors["BUTTON_ACTIVE"])
        self.theme_btn.pack(side=tk.LEFT, padx=5)

        self.editor.theme.register_widget("bottom_frame", self.bottom_frame)
        self.editor.theme.register_widget("brush_size_label", self.brush_size_label)
        self.editor.theme.register_widget("grid_check", self.grid_check)

    def _make_button(self, parent: tk.Frame, icon: str, text: str, cmd: callable, compound: str = tk.LEFT) -> tk.Button:
        img = self.editor.tex.get_icon(icon)
        colors = CFG.colors
        if img:
            btn = tk.Button(parent, image=img, text=text, compound=compound,
                           relief=tk.SOLID, bd=1, command=cmd,
                           bg=colors["BUTTON"], fg=colors["TEXT"],
                           activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn = tk.Button(parent, text=text, bg=colors["BUTTON"], fg=colors["TEXT"],
                           relief=tk.SOLID, bd=1, command=cmd,
                           activebackground=colors["BUTTON_ACTIVE"])
        return btn

    def _build_action_buttons(self) -> None:
        btn_export = self._make_button(self.bottom_frame, "download.png", ".png", self.editor.save_png)
        btn_export.pack(side=tk.LEFT, padx=2)
        btn_save_json = self._make_button(self.bottom_frame, "download.png", ".json", self.editor.save_json)
        btn_save_json.pack(side=tk.LEFT, padx=2)
        btn_load_json = self._make_button(self.bottom_frame, "upload.png", ".json", self.editor.load_json)
        btn_load_json.pack(side=tk.LEFT, padx=2)

        self._add_separator(self.bottom_frame)

        btn_clear = self._make_button(self.bottom_frame, "clear.png", "", self._clear_callback)
        btn_clear.pack(side=tk.LEFT, padx=2)

        self._add_separator(self.bottom_frame)

        btn_undo = self._make_button(self.bottom_frame, "undo.png", "", self.editor.undo_op)
        btn_undo.pack(side=tk.LEFT, padx=2)
        btn_redo = self._make_button(self.bottom_frame, "redo.png", "", self.editor.redo_op)
        btn_redo.pack(side=tk.LEFT, padx=2)

        self._add_separator(self.bottom_frame)

        btn_import = tk.Button(self.bottom_frame, text="Загрузить текстуры", command=self.editor.import_tex,
                             bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"],
                             activebackground=CFG.colors["BUTTON_ACTIVE"])
        btn_import.pack(side=tk.LEFT, padx=2)
        btn_delete = tk.Button(self.bottom_frame, text="Удалить текстуры", command=self.editor.del_tex,
                             bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"],
                             activebackground=CFG.colors["BUTTON_ACTIVE"])
        btn_delete.pack(side=tk.LEFT, padx=2)

        self._add_separator(self.bottom_frame)

        btn_load_preset = tk.Button(self.bottom_frame, text="Загрузить пресет", command=self.editor.load_preset,
                                   bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"],
                                   activebackground=CFG.colors["BUTTON_ACTIVE"])
        btn_load_preset.pack(side=tk.LEFT, padx=2)
        btn_save_preset = tk.Button(self.bottom_frame, text="Сохранить пресет", command=self.editor.save_preset,
                                   bg=CFG.colors["BUTTON"], fg=CFG.colors["TEXT"],
                                   activebackground=CFG.colors["BUTTON_ACTIVE"])
        btn_save_preset.pack(side=tk.LEFT, padx=2)

    def _add_separator(self, parent) -> None:
        tk.Frame(parent, width=2, bg=CFG.colors["GREY"], relief=tk.RAISED).pack(side=tk.LEFT, padx=5, fill=tk.Y)

    def _clear_callback(self) -> None:
        self.editor.clear_all_layers(ask_confirm=True)

    def _spinbox_changed(self) -> None:
        try:
            new = int(self.layer_spinbox.get()) - 1
            if 0 <= new < self.editor.map.get_num_layers():
                self.editor.layer_manager.set_active_layer(new)
            else:
                self.update_layer_ui()
        except ValueError:
            self.update_layer_ui()

    def _open_layer_manager(self) -> None:
        self.editor.console._cmd_layers()

    def update_layer_ui(self) -> None:
        self.layer_spinbox.delete(0, tk.END)
        self.layer_spinbox.insert(0, str(self.editor.layer_manager.current_layer + 1))
        self.visible_var.set(self.editor.map.visible[self.editor.layer_manager.current_layer])

    def update_visibility_check(self) -> None:
        self.visible_var.set(self.editor.map.visible[self.editor.layer_manager.current_layer])

    def update_status(self, text: str) -> None:
        if self.status:
            self.status.config(text=text)

    def update_theme(self) -> None:
        colors = CFG.colors
        
        self.toolbar_frame.config(bg=colors["BG_PANEL"])
        self.layer_frame.config(bg=colors["BG_PANEL"])
        self.bottom_frame.config(bg=colors["BG_PANEL"])
        self.canvas.config(bg=colors["BG_CANVAS"])
        self.status.config(bg=colors["L_GREY"], fg=colors["TEXT"])
        
        # Обновляем все прямые дочерние элементы toolbar_frame, layer_frame, bottom_frame
        for frame in [self.toolbar_frame, self.layer_frame, self.bottom_frame]:
            for child in frame.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                 activebackground=colors["BUTTON_ACTIVE"])
                elif isinstance(child, tk.Label):
                    child.config(bg=colors["BG_PANEL"], fg=colors["TEXT"])
                elif isinstance(child, tk.Checkbutton):
                    child.config(bg=colors["BG_PANEL"], fg=colors["TEXT"],
                                 selectcolor=colors["BG_PANEL"])
                elif isinstance(child, tk.Spinbox):
                    child.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                 buttonbackground=colors["BUTTON"],
                                 selectbackground=colors["GREY"],
                                 selectforeground=colors["TEXT"])
        
        # Отдельно обновляем left_block и его кнопки (инструменты)
        if self.left_block:
            self.left_block.config(bg=colors["BG_PANEL"])
            for btn in self.left_block.winfo_children():
                if isinstance(btn, tk.Button):
                    btn.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
        
        # Обновляем специфические элементы
        if self.layer_spinbox:
            self.layer_spinbox.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                       buttonbackground=colors["BUTTON"],
                                       selectbackground=colors["GREY"],
                                       selectforeground=colors["TEXT"])
        if self.brush_size_label:
            self.brush_size_label.config(bg=colors["BUTTON"], fg=colors["TEXT"])
        if self.grid_check:
            self.grid_check.config(bg=colors["BG_PANEL"], fg=colors["TEXT"],
                                   selectcolor=colors["BG_PANEL"])
        if self.theme_btn:
            self.theme_btn.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                  activebackground=colors["BUTTON_ACTIVE"])
        if self.hotbar_settings_btn:
            self.hotbar_settings_btn.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                            activebackground=colors["BUTTON_ACTIVE"])