# editor_ui.py
import tkinter as tk
from typing import Optional
from .config import CFG, EMPTY
from .hotbar import HotbarWidget, HotbarConfigWindow

class UIManager:
    def __init__(self, editor):
        self.editor = editor
        self.canvas: Optional[tk.Canvas] = None
        self.status: Optional[tk.Label] = None
        self.toolbar_frame: Optional[tk.Frame] = None
        self.left_block: Optional[tk.Frame] = None
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
        self.resize_btn: Optional[tk.Button] = None
        self.center_btn: Optional[tk.Button] = None

    def setup(self, parent: tk.Frame) -> None:
        self._setup_canvas(parent)
        self._setup_toolbar_panel(parent)
        self._setup_layer_panel(parent)
        self._setup_bottom_panel(parent)
        self._setup_status_bar(parent)
        self._bind_hotbar_keys()
        self._bind_escape()

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

    def _bind_escape(self) -> None:
        def on_escape(event):
            if self.editor.selection.active:
                self.editor.selection.clear()
                self.editor.drawing.redraw_visible_tiles()
                self.editor.update_status()
                self.editor.console._print("Выделение снято", "info")
            if self.editor.drawing._primitive_type:
                self.editor.drawing.cancel_primitive()
        self.editor.root.bind_all("<Escape>", on_escape)

    def clear_hotbar_selection(self) -> None:
        if self.hotbar_widget:
            self.hotbar_widget.clear_selection()

    def highlight_hotbar_slot_by_texture(self, texture_name: str) -> None:
        if self.hotbar_widget:
            self.hotbar_widget.select_slot_by_texture(texture_name)

    def _setup_toolbar_panel(self, parent: tk.Frame) -> None:
        colors = CFG.colors
        self.toolbar_frame = tk.Frame(parent, bg=colors["BG_PANEL"])
        self.toolbar_frame.pack(fill=tk.X, pady=2)
        self.left_block = tk.Frame(self.toolbar_frame, bg=colors["BG_PANEL"])
        self.left_block.pack(side=tk.LEFT, padx=5)
        btn_eraser = tk.Button(self.left_block, image=self.editor.tex.get_icon("void.png"),
                               command=lambda: self.editor.tool_manager.set_tool(EMPTY, False),
                               bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
        btn_eraser.pack(side=tk.LEFT, padx=2)
        btn_pipette = tk.Button(self.left_block, image=self.editor.tex.get_icon("find.png"),
                                command=lambda: self.editor.tool_manager.set_tool(-1, False),
                                bg=colors["BUTTON"], fg=colors["TEXT"],
                                activebackground=colors["BUTTON_ACTIVE"])
        btn_pipette.pack(side=tk.LEFT, padx=2)
        btn_fill = tk.Button(self.left_block, image=self.editor.tex.get_icon("fill.png"),
                             command=lambda: self.editor.tool_manager.set_tool(-2, False),
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_fill.pack(side=tk.LEFT, padx=2)

        btn_circle = tk.Button(self.left_block, image=self.editor.tex.get_icon("circle.png"),
                               command=lambda: self._activate_primitive("circle"),
                               bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
        btn_circle.pack(side=tk.LEFT, padx=2)
        btn_rect = tk.Button(self.left_block, image=self.editor.tex.get_icon("rect.png"),
                             command=lambda: self._activate_primitive("rect"),
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_rect.pack(side=tk.LEFT, padx=2)
        btn_line = tk.Button(self.left_block, image=self.editor.tex.get_icon("line.png"),
                             command=lambda: self._activate_primitive("line"),
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_line.pack(side=tk.LEFT, padx=2)

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

    def _activate_primitive(self, prim_type: Optional[str]):
        self.editor.drawing.cancel_primitive()
        if prim_type:
            self.editor.drawing.start_primitive(prim_type)
        else:
            pass

    def refresh_hotbar(self) -> None:
        if self.hotbar_widget:
            self.hotbar_widget.refresh()

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
        self.canvas = tk.Canvas(parent, bg=colors["BG_CANVAS"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.editor.drawing.on_press)
        self.canvas.bind("<B1-Motion>", self.editor.drawing.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.editor.drawing.on_release)
        self.canvas.bind("<Motion>", self.editor.on_mouse_move)
        self.canvas.bind("<Alt-Button-1>", self.editor.drawing.pick_texture)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self.editor.on_mousewheel)
        self.canvas.bind("<Button-4>", self.editor.on_mousewheel)
        self.canvas.bind("<Button-5>", self.editor.on_mousewheel)
        self.editor.theme.register_widget("canvas", self.canvas)

    def _on_canvas_resize(self, event: tk.Event) -> None:
        if event.widget == self.canvas:
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            if w > 0 and h > 0:
                self.editor.camera.set_canvas_size(w, h)
                self.editor.camera.clamp()
                self.editor.drawing.redraw_visible_tiles()

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
            self.editor.layer_manager.remove_layer()
            self.editor.console._print(f"✓ Слой удалён", "success")

    def _open_layer_manager(self) -> None:
        num_layers = self.editor.map.get_num_layers()
        self.editor.console._print(f"Слои:", "info")
        self.editor.console._print(f"  Всего слоёв: {num_layers}", "info")
        self.editor.console._print(f"  Активный слой: {self.editor.layer_manager.current_layer + 1}", "info")
        for i in range(num_layers):
            visibility = "✓" if self.editor.map.visible[i] else "✗"
            status = "вид" if self.editor.map.visible[i] else "скрыт"
            self.editor.console._print(f"  Слой {i+1}: [{visibility}] {status}", "normal")

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
        self.resize_btn = tk.Button(self.bottom_frame, text="Размер карты", command=self.editor.resize_map,
                                    bg=colors["BUTTON"], fg=colors["TEXT"],
                                    activebackground=colors["BUTTON_ACTIVE"])
        self.resize_btn.pack(side=tk.LEFT, padx=5)
        self.center_btn = tk.Button(self.bottom_frame, text="Оцентровать", command=self.editor.center_map,
                                    bg=colors["BUTTON"], fg=colors["TEXT"],
                                    activebackground=colors["BUTTON_ACTIVE"])
        self.center_btn.pack(side=tk.LEFT, padx=5)
        self.editor.theme.register_widget("bottom_frame", self.bottom_frame)
        self.editor.theme.register_widget("brush_size_label", self.brush_size_label)
        self.editor.theme.register_widget("grid_check", self.grid_check)

    def _build_action_buttons(self) -> None:
        colors = CFG.colors
        img_export = self.editor.tex.get_icon("download.png")
        btn_export = tk.Button(self.bottom_frame, image=img_export, text=".png", compound=tk.LEFT,
                               command=self.editor.save_png, bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
        btn_export.pack(side=tk.LEFT, padx=2)
        img_save_json = self.editor.tex.get_icon("download.png")
        btn_save_json = tk.Button(self.bottom_frame, image=img_save_json, text=".json", compound=tk.LEFT,
                                  command=self.editor.save_json, bg=colors["BUTTON"], fg=colors["TEXT"],
                                  activebackground=colors["BUTTON_ACTIVE"])
        btn_save_json.pack(side=tk.LEFT, padx=2)
        img_load_json = self.editor.tex.get_icon("upload.png")
        btn_load_json = tk.Button(self.bottom_frame, image=img_load_json, text=".json", compound=tk.LEFT,
                                  command=self.editor.load_json, bg=colors["BUTTON"], fg=colors["TEXT"],
                                  activebackground=colors["BUTTON_ACTIVE"])
        btn_load_json.pack(side=tk.LEFT, padx=2)
        self._add_separator(self.bottom_frame)
        img_clear = self.editor.tex.get_icon("clear.png")
        btn_clear = tk.Button(self.bottom_frame, image=img_clear, text="", command=self._clear_callback,
                              bg=colors["BUTTON"], fg=colors["TEXT"],
                              activebackground=colors["BUTTON_ACTIVE"])
        btn_clear.pack(side=tk.LEFT, padx=2)
        self._add_separator(self.bottom_frame)
        img_undo = self.editor.tex.get_icon("undo.png")
        btn_undo = tk.Button(self.bottom_frame, image=img_undo, text="", command=self.editor.undo_op,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_undo.pack(side=tk.LEFT, padx=2)
        img_redo = self.editor.tex.get_icon("redo.png")
        btn_redo = tk.Button(self.bottom_frame, image=img_redo, text="", command=self.editor.redo_op,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_redo.pack(side=tk.LEFT, padx=2)
        self._add_separator(self.bottom_frame)
        btn_select = tk.Button(self.bottom_frame, text="Выделить", command=self.editor.enable_selection_tool,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_select.pack(side=tk.LEFT, padx=2)
        btn_copy = tk.Button(self.bottom_frame, text="Копировать", command=self.editor.copy_selection,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_copy.pack(side=tk.LEFT, padx=2)
        btn_cut = tk.Button(self.bottom_frame, text="Вырезать", command=self.editor.cut_selection,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_cut.pack(side=tk.LEFT, padx=2)
        btn_paste = tk.Button(self.bottom_frame, text="Вставить", command=self.editor.paste_selection,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_paste.pack(side=tk.LEFT, padx=2)
        self._add_separator(self.bottom_frame)
        btn_import = tk.Button(self.bottom_frame, text="Загрузить текстуры", command=self.editor.import_tex,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_import.pack(side=tk.LEFT, padx=2)
        btn_delete = tk.Button(self.bottom_frame, text="Удалить текстуры", command=self.editor.del_tex,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_delete.pack(side=tk.LEFT, padx=2)
        self._add_separator(self.bottom_frame)
        btn_load_preset = tk.Button(self.bottom_frame, text="Загрузить пресет", command=self.editor.load_preset,
                                   bg=colors["BUTTON"], fg=colors["TEXT"],
                                   activebackground=colors["BUTTON_ACTIVE"])
        btn_load_preset.pack(side=tk.LEFT, padx=2)
        btn_save_preset = tk.Button(self.bottom_frame, text="Сохранить пресет", command=self.editor.save_preset,
                                   bg=colors["BUTTON"], fg=colors["TEXT"],
                                   activebackground=colors["BUTTON_ACTIVE"])
        btn_save_preset.pack(side=tk.LEFT, padx=2)

    def _add_separator(self, parent) -> None:
        tk.Frame(parent, width=2, bg=CFG.colors["GREY"], relief=tk.RAISED).pack(side=tk.LEFT, padx=5, fill=tk.Y)

    def _clear_callback(self) -> None:
        self.editor.clear_all_layers()

    def _spinbox_changed(self) -> None:
        try:
            new = int(self.layer_spinbox.get()) - 1
            if 0 <= new < self.editor.map.get_num_layers():
                self.editor.layer_manager.set_active_layer(new)
            else:
                self.update_layer_ui()
        except ValueError:
            self.update_layer_ui()

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
        if self.left_block:
            self.left_block.config(bg=colors["BG_PANEL"])
            for btn in self.left_block.winfo_children():
                if isinstance(btn, tk.Button):
                    btn.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
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
        if self.resize_btn:
            self.resize_btn.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                   activebackground=colors["BUTTON_ACTIVE"])
        if self.center_btn:
            self.center_btn.config(bg=colors["BUTTON"], fg=colors["TEXT"],
                                   activebackground=colors["BUTTON_ACTIVE"])