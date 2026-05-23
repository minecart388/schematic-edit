# hotbar.py
import tkinter as tk
import json
import os
from typing import List, Optional
from dataclasses import dataclass
from PIL import Image, ImageTk
from .config import CFG
from .core import TexMgr


@dataclass
class HotbarSlot:
    texture_name: str = ""
    is_empty: bool = True


class HotbarManager:
    def __init__(self, config_path: str = os.path.join("assets", "hotbar_config.json")):
        self.config_path = config_path
        self.slots: List[HotbarSlot] = [HotbarSlot() for _ in range(9)]
        os.makedirs("assets", exist_ok=True)
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for i, slot_data in enumerate(data.get("slots", [])):
                    if i < 9 and slot_data.get("texture_name"):
                        self.slots[i].texture_name = slot_data["texture_name"]
                        self.slots[i].is_empty = False
        except (json.JSONDecodeError, IOError):
            pass

    def save(self) -> None:
        data = {
            "slots": [
                {"texture_name": slot.texture_name if not slot.is_empty else ""}
                for slot in self.slots
            ]
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def set_slot(self, index: int, texture_name: str) -> None:
        if 0 <= index < 9:
            if texture_name:
                self.slots[index].texture_name = texture_name
                self.slots[index].is_empty = False
            else:
                self.slots[index].is_empty = True
                self.slots[index].texture_name = ""
            self.save()

    def get_slot(self, index: int) -> Optional[str]:
        if 0 <= index < 9 and not self.slots[index].is_empty:
            return self.slots[index].texture_name
        return None

    def clear_slot(self, index: int) -> None:
        self.set_slot(index, "")

    def clear_all(self) -> None:
        for i in range(9):
            self.clear_slot(i)

    def is_empty(self, index: int) -> bool:
        return 0 <= index < 9 and self.slots[index].is_empty

    def find_empty_slot(self) -> Optional[int]:
        for i in range(9):
            if self.is_empty(i):
                return i
        return None

    def get_first_filled_slot(self) -> Optional[int]:
        for i in range(9):
            if not self.is_empty(i):
                return i
        return None


class HotbarWidget:
    def __init__(self, parent, tex_mgr: TexMgr, hotbar_mgr: HotbarManager,
                 on_select_callback):
        self.parent = parent
        self.tex_mgr = tex_mgr
        self.hotbar_mgr = hotbar_mgr
        self.on_select = on_select_callback
        self.slots: List[tk.Frame] = []
        self.buttons: List[tk.Button] = []
        self.photos: List[Optional[ImageTk.PhotoImage]] = [None] * 9
        self.selected_index: Optional[int] = None
        self.slots_frame = None
        self._build()

    def _build(self):
        self.container = tk.Frame(self.parent, bg=CFG.colors["BG_PANEL"])
        self.container.pack(side=tk.LEFT, padx=10)

        self.title_label = tk.Label(self.container, text="Хотбар",
                                    bg=CFG.colors["BG_PANEL"], fg=CFG.colors["TEXT"],
                                    font=("Arial", 9, "bold"))
        self.title_label.pack(side=tk.LEFT, padx=5)

        self.slots_frame = tk.Frame(self.container, bg=CFG.colors["SLOT_BORDER"], bd=1, relief=tk.SUNKEN)
        self.slots_frame.pack(side=tk.LEFT, padx=5, pady=2)

        for i in range(9):
            slot = self._create_slot(self.slots_frame, i)
            slot.pack(side=tk.LEFT, padx=1, pady=1)
            self.slots.append(slot)

    def _create_slot(self, parent, idx: int) -> tk.Frame:
        colors = CFG.colors
        frame = tk.Frame(parent, bg=colors["SLOT_BORDER"], bd=1, relief=tk.RAISED,
                         width=36, height=36)
        frame.pack_propagate(False)

        btn = tk.Button(frame, width=4, height=2, bg=colors["BUTTON"],
                       fg=colors["TEXT"], relief=tk.FLAT,
                       command=lambda i=idx: self._on_click(i))
        btn.pack(fill=tk.BOTH, expand=True)

        btn.bind("<ButtonPress-1>", lambda e, i=idx: self._on_press(i, e))
        btn.bind("<ButtonRelease-1>", lambda e, i=idx: self._on_release(i, e))

        frame.btn = btn
        frame.index = idx
        self.buttons.append(btn)
        self._update_slot(idx)
        return frame

    def _on_click(self, idx: int):
        tex = self.hotbar_mgr.get_slot(idx)
        if tex:
            self.select_slot(idx)
            self.on_select(tex)

    def _on_press(self, idx: int, event):
        self.drag_start_idx = idx
        self.drag_start_tex = self.hotbar_mgr.get_slot(idx)

    def _on_release(self, idx: int, event):
        if hasattr(self, 'drag_start_idx') and self.drag_start_idx != idx:
            target_tex = self.hotbar_mgr.get_slot(idx)
            source_tex = self.drag_start_tex
            self.hotbar_mgr.set_slot(idx, source_tex if source_tex else "")
            self.hotbar_mgr.set_slot(self.drag_start_idx, target_tex if target_tex else "")
            self.refresh()
            if self.selected_index == self.drag_start_idx:
                self.select_slot(idx)
            elif self.selected_index == idx:
                self.select_slot(self.drag_start_idx)
        if hasattr(self, 'drag_start_idx'):
            delattr(self, 'drag_start_idx')
        if hasattr(self, 'drag_start_tex'):
            delattr(self, 'drag_start_tex')

    def clear_selection(self):
        if self.selected_index is not None:
            self.slots[self.selected_index].config(bg=CFG.colors["SLOT_BORDER"])
            self.selected_index = None

    def _update_slot(self, idx: int):
        colors = CFG.colors
        tex_name = self.hotbar_mgr.get_slot(idx)
        btn = self.buttons[idx]
        if tex_name and tex_name in self.tex_mgr.originals:
            orig = self.tex_mgr.originals[tex_name]
            img = orig.resize((32, 32), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(img)
            self.photos[idx] = photo
            btn.config(image=photo, text="", bg=colors["BUTTON"],
                      activebackground=colors["BUTTON_ACTIVE"])
            btn.image = photo
        else:
            btn.config(image="", text="", bg=colors["BUTTON"],
                      activebackground=colors["BUTTON_ACTIVE"])

    def select_slot(self, idx: int):
        if self.selected_index is not None:
            self.slots[self.selected_index].config(bg=CFG.colors["SLOT_BORDER"])
        self.selected_index = idx
        self.slots[idx].config(bg="#4CAF50")

    def refresh(self):
        for i in range(9):
            self._update_slot(i)
        if self.selected_index is not None:
            self.slots[self.selected_index].config(bg=CFG.colors["SLOT_BORDER"])
            self.selected_index = None

    def update_slot(self, idx: int):
        self._update_slot(idx)

    def update_theme(self):
        colors = CFG.colors
        self.container.config(bg=colors["BG_PANEL"])
        self.title_label.config(bg=colors["BG_PANEL"], fg=colors["TEXT"])
        if self.slots_frame:
            self.slots_frame.config(bg=colors["SLOT_BORDER"])
        for btn in self.buttons:
            btn.config(bg=colors["BUTTON"], activebackground=colors["BUTTON_ACTIVE"])
        for i, slot in enumerate(self.slots):
            slot.config(bg=colors["SLOT_BORDER"])
            if self.selected_index == i:
                slot.config(bg="#4CAF50")
        self.refresh()


class HotbarConfigWindow:
    def __init__(self, parent, tex_mgr: TexMgr, hotbar_mgr: HotbarManager,
                 hotbar_widget: HotbarWidget):
        self.tex_mgr = tex_mgr
        self.hotbar_mgr = hotbar_mgr
        self.hotbar_widget = hotbar_widget

        self.window = tk.Toplevel(parent)
        self.window.title("Управление хотбаром")
        self.window.geometry("900x550")
        self.window.minsize(800, 450)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.configure(bg=CFG.colors["BG_PANEL"])

        self._build()
        self._apply_theme()

    def _apply_theme(self):
        colors = CFG.colors
        self.window.configure(bg=colors["BG_PANEL"])
        for child in self.window.winfo_children():
            if isinstance(child, (tk.Frame, tk.LabelFrame)):
                child.configure(bg=colors["BG_PANEL"])
            elif isinstance(child, tk.Button):
                child.configure(bg=colors["BUTTON"], fg=colors["TEXT"],
                               activebackground=colors["BUTTON_ACTIVE"])
        if hasattr(self, 'slots_container'):
            self.slots_container.configure(bg=colors["BG_PANEL"])
            for slot_frame in self.slot_frames:
                slot_frame["frame"].configure(bg=colors["BG_PANEL"])
                if "icon_label" in slot_frame:
                    slot_frame["icon_label"].configure(bg=colors["BG_PANEL"])

    def _build(self):
        colors = CFG.colors

        main_frame = tk.Frame(self.window, bg=colors["BG_PANEL"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(main_frame, text="Управление слотами хотбара", font=("Arial", 12, "bold"),
                bg=colors["BG_PANEL"], fg=colors["TEXT"]).pack(pady=5)

        self.slots_container = tk.Frame(main_frame, bg=colors["BG_PANEL"])
        self.slots_container.pack(fill=tk.X, pady=10)

        self.slot_frames = []
        for i in range(9):
            col_frame = tk.Frame(self.slots_container, bg=colors["BG_PANEL"], bd=1, relief=tk.RAISED)
            col_frame.grid(row=0, column=i, padx=4, pady=4, sticky="nsew")

            icon_frame = tk.Frame(col_frame, bg=colors["BG_PANEL"], bd=1, relief=tk.SUNKEN,
                                  width=64, height=64)
            icon_frame.pack(pady=5, padx=5)
            icon_frame.pack_propagate(False)

            icon_label = tk.Label(icon_frame, bg=colors["BG_PANEL"])
            icon_label.pack(fill=tk.BOTH, expand=True)

            clear_btn = tk.Button(col_frame, text="Очистить", width=10,
                                 command=lambda idx=i: self._clear_slot(idx),
                                 bg=colors["BUTTON"], fg=colors["TEXT"])
            clear_btn.pack(pady=2)

            self.slot_frames.append({
                "frame": col_frame,
                "icon_label": icon_label,
                "clear_btn": clear_btn
            })

        for i in range(9):
            self.slots_container.grid_columnconfigure(i, weight=1)

        btn_clear_all = tk.Button(main_frame, text="Очистить все слоты", command=self._clear_all_slots,
                                 bg=colors["BUTTON"], fg=colors["TEXT"])
        btn_clear_all.pack(pady=5)

        self._update_slots_display()

        texture_frame = tk.LabelFrame(main_frame, text="Доступные текстуры", font=("Arial", 10, "bold"),
                                      bg=colors["BG_PANEL"], fg=colors["TEXT"])
        texture_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        search_frame = tk.Frame(texture_frame, bg=colors["BG_PANEL"])
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Поиск:", bg=colors["BG_PANEL"],
                fg=colors["TEXT"]).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30,
                               bg=colors["BUTTON"], fg=colors["TEXT"])
        search_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Сброс", command=lambda: self.search_var.set(""),
                 bg=colors["BUTTON"], fg=colors["TEXT"]).pack(side=tk.LEFT, padx=5)

        canvas_frame = tk.Frame(texture_frame, bg=colors["BG_PANEL"])
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg=colors["BG_CANVAS"], highlightthickness=0)
        self.textures_container = tk.Frame(canvas, bg=colors["BG_CANVAS"])
        self.textures_container.bind("<Configure>", self._on_container_configure)
        canvas.create_window((0,0), window=self.textures_container, anchor="nw")
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        self._populate_textures()

        self.search_var.trace('w', lambda *_: self._filter_textures())

        btn_close = tk.Button(main_frame, text="Закрыть", command=self.window.destroy,
                             bg=colors["BUTTON"], fg=colors["TEXT"], width=10)
        btn_close.pack(pady=5)

    def _update_slots_display(self):
        colors = CFG.colors
        for i, slot in enumerate(self.slot_frames):
            tex_name = self.hotbar_mgr.get_slot(i)
            icon_label = slot["icon_label"]
            if tex_name and tex_name in self.tex_mgr.originals:
                orig = self.tex_mgr.originals[tex_name]
                img = orig.resize((60, 60), Image.Resampling.NEAREST)
                photo = ImageTk.PhotoImage(img)
                icon_label.config(image=photo, text="", bg=colors["BG_PANEL"])
                icon_label.image = photo
                slot["photo"] = photo
            else:
                icon_label.config(image="", text="Пусто", bg=colors["BG_PANEL"],
                                 fg=colors["TEXT"], font=("Arial", 8))
                if "photo" in slot:
                    del slot["photo"]

    def _clear_slot(self, slot_index: int):
        self.hotbar_mgr.clear_slot(slot_index)
        self.hotbar_widget.update_slot(slot_index)
        self._update_slots_display()

    def _clear_all_slots(self):
        self.hotbar_mgr.clear_all()
        for i in range(9):
            self.hotbar_widget.update_slot(i)
        self._update_slots_display()

    def _on_container_configure(self, event):
        canvas = self.textures_container.master
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _populate_textures(self):
        for widget in self.textures_container.winfo_children():
            widget.destroy()

        textures = sorted(self.tex_mgr.blocks.keys())
        if not textures:
            lbl = tk.Label(self.textures_container,
                          bg=CFG.colors["BG_CANVAS"], fg=CFG.colors["TEXT"])
            lbl.pack(pady=20)
            return

        max_cols = 8
        row = col = 0
        self.texture_widgets = []

        for tex_name in textures:
            frame = tk.Frame(self.textures_container, bg=CFG.colors["BG_CANVAS"])
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            img = self.tex_mgr.get_thumb(tex_name)
            btn = tk.Button(frame, image=img,
                           command=lambda n=tex_name: self._assign_to_first_empty_slot(n),
                           bg=CFG.colors["BUTTON"], relief=tk.RAISED)
            btn.pack()
            lbl = tk.Label(frame, text=tex_name if len(tex_name)<=15 else tex_name[:12]+"...",
                          bg=CFG.colors["BG_CANVAS"], fg=CFG.colors["TEXT"])
            lbl.pack()
            frame.texture_name = tex_name
            self.texture_widgets.append(frame)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        for i in range(max_cols):
            self.textures_container.grid_columnconfigure(i, weight=1)

    def _filter_textures(self):
        query = self.search_var.get().lower()
        for w in self.texture_widgets:
            if query in w.texture_name.lower():
                w.grid()
            else:
                w.grid_remove()

    def _assign_to_first_empty_slot(self, tex_name: str):
        empty_slot = self.hotbar_mgr.find_empty_slot()
        if empty_slot is None:
            empty_slot = 0
        self.hotbar_mgr.set_slot(empty_slot, tex_name)
        self.hotbar_widget.update_slot(empty_slot)
        self._update_slots_display()