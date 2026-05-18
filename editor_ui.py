# editor_ui.py
import tkinter as tk
from typing import Dict, Optional
from config import CFG, EMPTY
from core import TexMgr

class UIBuilder:
    def __init__(self, tex: TexMgr, callbacks: Dict[str, callable]) -> None:
        self.tex = tex
        self.cb = callbacks

    def _btn(self, parent: tk.Frame, icon: str, text: Optional[str], cmd: callable, compound: str = tk.LEFT) -> tk.Button:
        img = self.tex.get_icon(icon)
        colors = CFG.colors
        if img:
            btn = tk.Button(parent, image=img, text=text, compound=compound, 
                           relief=tk.SOLID, bd=1, command=cmd,
                           bg=colors["BUTTON"], fg=colors["TEXT"],
                           activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn = tk.Button(parent, text=text or "", bg=colors["BUTTON"], 
                           fg=colors["TEXT"], relief=tk.SOLID, bd=1, command=cmd,
                           activebackground=colors["BUTTON_ACTIVE"])
        return btn

    def build_toolbar(self, parent: tk.Frame) -> None:
        b = self._btn(parent, "void.png", None, lambda: self.cb["set_tool"](EMPTY, False))
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "fence.png", None, lambda: self.cb["set_tool"](None, True))
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "find.png", None, lambda: self.cb["set_tool"](-1, False))
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "fill.png", None, lambda: self.cb["set_tool"](-2, False))
        b.pack(side=tk.LEFT, padx=2)
        for code, img in self.tex.thumbs.items():
            btn = tk.Button(parent, image=img, relief=tk.SOLID, bd=1,
                           command=lambda c=code: self.cb["set_tool"](c, False),
                           bg=CFG.colors["BUTTON"], activebackground=CFG.colors["BUTTON_ACTIVE"])
            btn.pack(side=tk.LEFT, padx=2)

class UIManager:
    def __init__(self, editor):
        self.editor = editor
        self.canvas: Optional[tk.Canvas] = None
        self.status: Optional[tk.Label] = None
        self.toolbar_frame: Optional[tk.Frame] = None
        self.toolbar: Optional[tk.Frame] = None
        self.layer_frame: Optional[tk.Frame] = None
        self.layer_spinbox: Optional[tk.Spinbox] = None
        self.visible_var: Optional[tk.BooleanVar] = None
        self.visible_check: Optional[tk.Checkbutton] = None
        self.bottom_frame: Optional[tk.Frame] = None
        self.brush_size_label: Optional[tk.Label] = None
        self.grid_var: Optional[tk.BooleanVar] = None
        self.grid_check: Optional[tk.Checkbutton] = None
    
    def setup(self, parent: tk.Frame) -> None:
        self._setup_canvas(parent)
        self._setup_toolbar_area(parent)
        self._setup_layer_panel(parent)
        self._setup_bottom_panel(parent)
        self._setup_status_bar(parent)
        self._rebuild_toolbar()
    
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
    
    def _setup_toolbar_area(self, parent: tk.Frame) -> None:
        self.toolbar_frame = tk.Frame(parent, bg=CFG.colors["BG_PANEL"])
        self.toolbar_frame.pack(fill=tk.X, pady=2)
        self.editor.theme.register_widget("toolbar_frame", self.toolbar_frame)
    
    def _setup_layer_panel(self, parent: tk.Frame) -> None:
        colors = CFG.colors
        
        self.layer_frame = tk.Frame(parent, bg=colors["BG_PANEL"], pady=5)
        self.layer_frame.pack(fill=tk.X)
        
        tk.Label(self.layer_frame, text="Слой:", bg=colors["BG_PANEL"], 
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
        
        self._sep(self.bottom_frame)
        
        tk.Label(self.bottom_frame, text="Кисть:", bg=colors["BG_PANEL"], 
                fg=colors["TEXT"]).pack(side=tk.LEFT, padx=5)
        
        self.brush_size_label = tk.Label(self.bottom_frame, text=f"{self.editor.brush_size}", 
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
        
        self.editor.theme.register_widget("bottom_frame", self.bottom_frame)
        self.editor.theme.register_widget("brush_size_label", self.brush_size_label)
        self.editor.theme.register_widget("grid_check", self.grid_check)
    
    def _build_action_buttons(self) -> None:
        colors = CFG.colors
        tex = self.editor.tex
        
        down = tex.get_icon("download.png")
        up = tex.get_icon("upload.png")
        
        if down:
            btn_export = tk.Button(self.bottom_frame, image=down, text=".png", compound=tk.LEFT, 
                                  relief=tk.SOLID, bd=1, command=self.editor.save_png,
                                  bg=colors["BUTTON"], fg=colors["TEXT"],
                                  activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn_export = tk.Button(self.bottom_frame, text=".png", bg=colors["BUTTON"], 
                                  fg=colors["TEXT"], width=5, command=self.editor.save_png,
                                  activebackground=colors["BUTTON_ACTIVE"])
        btn_export.pack(side=tk.LEFT, padx=2)
        
        if down:
            btn_save_json = tk.Button(self.bottom_frame, image=down, text=".json", compound=tk.LEFT, 
                                     relief=tk.SOLID, bd=1, command=self.editor.save_json,
                                     bg=colors["BUTTON"], fg=colors["TEXT"],
                                     activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn_save_json = tk.Button(self.bottom_frame, text=".json", bg=colors["BUTTON"], 
                                     fg=colors["TEXT"], width=5, command=self.editor.save_json,
                                     activebackground=colors["BUTTON_ACTIVE"])
        btn_save_json.pack(side=tk.LEFT, padx=2)
        
        if up:
            btn_load_json = tk.Button(self.bottom_frame, image=up, text=".json", compound=tk.LEFT, 
                                     relief=tk.SOLID, bd=1, command=self.editor.load_json,
                                     bg=colors["BUTTON"], fg=colors["TEXT"],
                                     activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn_load_json = tk.Button(self.bottom_frame, text=".json", bg=colors["BUTTON"], 
                                     fg=colors["TEXT"], width=5, command=self.editor.load_json,
                                     activebackground=colors["BUTTON_ACTIVE"])
        btn_load_json.pack(side=tk.LEFT, padx=2)
        
        self._sep(self.bottom_frame)
        
        clear_img = tex.get_icon("clear.png")
        if clear_img:
            btn_clear = tk.Button(self.bottom_frame, image=clear_img, relief=tk.SOLID, bd=1,
                                 command=self._clear_callback, bg=colors["BUTTON"],
                                 activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn_clear = tk.Button(self.bottom_frame, text="Очистить", command=self._clear_callback,
                                 bg=colors["BUTTON"], fg=colors["TEXT"],
                                 activebackground=colors["BUTTON_ACTIVE"])
        btn_clear.pack(side=tk.LEFT, padx=2)
        
        self._sep(self.bottom_frame)
        
        undo_img = tex.get_icon("undo.png")
        if undo_img:
            btn_undo = tk.Button(self.bottom_frame, image=undo_img, relief=tk.SOLID, bd=1,
                                command=self.editor.undo_op, bg=colors["BUTTON"],
                                activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn_undo = tk.Button(self.bottom_frame, text="Отмена", command=self.editor.undo_op,
                                bg=colors["BUTTON"], fg=colors["TEXT"],
                                activebackground=colors["BUTTON_ACTIVE"])
        btn_undo.pack(side=tk.LEFT, padx=2)
        
        redo_img = tex.get_icon("redo.png")
        if redo_img:
            btn_redo = tk.Button(self.bottom_frame, image=redo_img, relief=tk.SOLID, bd=1,
                                command=self.editor.redo_op, bg=colors["BUTTON"],
                                activebackground=colors["BUTTON_ACTIVE"])
        else:
            btn_redo = tk.Button(self.bottom_frame, text="Повтор", command=self.editor.redo_op,
                                bg=colors["BUTTON"], fg=colors["TEXT"],
                                activebackground=colors["BUTTON_ACTIVE"])
        btn_redo.pack(side=tk.LEFT, padx=2)
        
        self._sep(self.bottom_frame)

        btn_import = tk.Button(self.bottom_frame, text="Загрузить текстуры", command=self.editor.import_tex,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_import.pack(side=tk.LEFT, padx=2)

        btn_delete = tk.Button(self.bottom_frame, text="Удалить текстуры", command=self.editor.del_tex,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_delete.pack(side=tk.LEFT, padx=2)
        
        self._sep(self.bottom_frame)
        
        btn_theme = tk.Button(self.bottom_frame, text="Тема", command=self.editor.toggle_theme,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_theme.pack(side=tk.LEFT, padx=2)
        
        self._sep(self.bottom_frame)

        btn_load_preset = tk.Button(self.bottom_frame, text="Загрузить пресет", command=self.editor.load_preset,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_load_preset.pack(side=tk.LEFT, padx=2)

        btn_save_preset = tk.Button(self.bottom_frame, text="Сохранить пресет", command=self.editor.save_preset,
                             bg=colors["BUTTON"], fg=colors["TEXT"],
                             activebackground=colors["BUTTON_ACTIVE"])
        btn_save_preset.pack(side=tk.LEFT, padx=2)
    
    def _clear_callback(self) -> None:
        self.editor.console.ask_yes_no("Очистить все слои?", self._confirm_clear_all)
    
    def _confirm_clear_all(self, confirmed: bool) -> None:
        if confirmed:
            self.editor.save_state()
            self.editor.map.clear_all()
            self.editor.draw()
            self.editor.console._print("✓ Все слои очищены", "success")
        else:
            self.editor.console._print("Очистка отменена", "info")
    
    def _sep(self, parent: tk.Frame) -> None:
        tk.Frame(parent, width=1, bg=CFG.colors["GREY"], relief=tk.RAISED).pack(side=tk.LEFT, padx=5, fill=tk.Y)
    
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
        LayerManagerDialog(self.editor.root, self.editor)
    
    def update_layer_ui(self) -> None:
        self.layer_spinbox.delete(0, tk.END)
        self.layer_spinbox.insert(0, str(self.editor.layer_manager.current_layer + 1))
        self.visible_var.set(self.editor.map.visible[self.editor.layer_manager.current_layer])
    
    def update_visibility_check(self) -> None:
        self.visible_var.set(self.editor.map.visible[self.editor.layer_manager.current_layer])
    
    def _rebuild_toolbar(self) -> None:
        if self.toolbar:
            self.toolbar.destroy()
        self.toolbar = tk.Frame(self.toolbar_frame, bg=CFG.colors["BG_PANEL"])
        self.toolbar.pack(fill=tk.X)
        
        ui = UIBuilder(self.editor.tex, {"set_tool": self.editor.set_tool})
        ui.build_toolbar(self.toolbar)
    
    def rebuild_toolbar(self) -> None:
        self._rebuild_toolbar()
    
    def rebuild_all(self) -> None:
        self.toolbar_frame.configure(bg=CFG.colors["BG_PANEL"])
        self._rebuild_toolbar()
        for widget in self.toolbar_frame.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=CFG.colors["BG_PANEL"])
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button):
                        child.configure(bg=CFG.colors["BUTTON"], activebackground=CFG.colors["BUTTON_ACTIVE"])
        self.layer_frame.configure(bg=CFG.colors["BG_PANEL"])
        self.bottom_frame.configure(bg=CFG.colors["BG_PANEL"])
        self.status.configure(bg=CFG.colors["L_GREY"], fg=CFG.colors["TEXT"])
    
    def update_status(self, text: str) -> None:
        if self.status:
            self.status.config(text=text)

class LayerManagerDialog:
    def __init__(self, parent: tk.Tk, editor):
        self.editor = editor
        self.window = tk.Toplevel(parent)
        self.window.title("Управление слоями")
        self.window.geometry("370x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        colors = CFG.colors
        self.window.configure(bg=colors["BG_PANEL"])
        
        self.listbox = tk.Listbox(self.window, height=20, bg=colors["BUTTON"], 
                                   fg=colors["TEXT"], selectbackground=colors["GREY"])
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.listbox.bind("<Double-Button-1>", self.on_layer_double_click)
        
        self.visibility_var = tk.BooleanVar()
        self.visibility_check = tk.Checkbutton(
            self.window, text="Вид", variable=self.visibility_var,
            command=self.toggle_visibility, bg=colors["BG_PANEL"],
            fg=colors["TEXT"], selectcolor=colors["BG_PANEL"]
        )
        self.visibility_check.pack(pady=5)
        
        btn_frame = tk.Frame(self.window, bg=colors["BG_PANEL"])
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Переключиться на выбранный", command=self.switch_to_selected,
                 bg=colors["BUTTON"], fg=colors["TEXT"],
                 activebackground=colors["BUTTON_ACTIVE"]).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить выбранный слой", command=self.delete_selected,
                 bg=colors["BUTTON"], fg=colors["TEXT"],
                 activebackground=colors["BUTTON_ACTIVE"]).pack(side=tk.LEFT, padx=5)
        
        self.refresh_list()
    
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i in range(self.editor.map.get_num_layers()):
            visibility = "✓" if self.editor.map.visible[i] else "✗"
            text = f"Слой {i+1} [{visibility}]"
            self.listbox.insert(tk.END, text)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(self.editor.layer_manager.current_layer)
        self.listbox.see(self.editor.layer_manager.current_layer)
        self.visibility_var.set(self.editor.map.visible[self.editor.layer_manager.current_layer])
    
    def on_layer_double_click(self, event):
        self.switch_to_selected()
    
    def switch_to_selected(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.editor.layer_manager.set_active_layer(idx)
            self.refresh_list()
    
    def toggle_visibility(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.editor.map.visible[idx] = self.visibility_var.get()
            self.editor.draw()
            self.refresh_list()
        else:
            self.visibility_var.set(self.editor.map.visible[self.editor.layer_manager.current_layer])
    
    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if self.editor.map.get_num_layers() <= 1:
            self.editor.console._print("Ошибка: нельзя удалить единственный слой", "error")
            return
        self.editor.console.ask_yes_no(f"Удалить слой {idx + 1}?", lambda confirmed: self._confirm_delete(confirmed, idx))
    
    def _confirm_delete(self, confirmed: bool, idx: int):
        if confirmed:
            self.editor.layer_manager.current_layer = idx
            self.editor.layer_manager.remove_layer()
            self.refresh_list()
            self.editor.console._print(f"✓ Слой {idx + 1} удалён", "success")