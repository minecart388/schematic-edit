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
        if img:
            return tk.Button(parent, image=img, text=text, compound=compound, relief=tk.SOLID, bd=1, command=cmd)
        else:
            return tk.Button(parent, text=text or "", bg=CFG.colors["WHITE"], relief=tk.SOLID, bd=1, command=cmd)

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
                            command=lambda c=code: self.cb["set_tool"](c, False))
            btn.pack(side=tk.LEFT, padx=2)

    def build_action(self, parent: tk.Frame, callbacks: Dict[str, callable]) -> None:
        down = self.tex.get_icon("download.png")
        up = self.tex.get_icon("upload.png")

        if down:
            btn_export = tk.Button(parent, image=down, text=".png", compound=tk.LEFT, relief=tk.SOLID, bd=1, command=callbacks["save_png"])
        else:
            btn_export = tk.Button(parent, text=".png", bg=CFG.colors["WHITE"], width=5, command=callbacks["save_png"])
        btn_export.pack(side=tk.LEFT, padx=2)

        if down:
            btn_save_json = tk.Button(parent, image=down, text=".json", compound=tk.LEFT, relief=tk.SOLID, bd=1, command=callbacks["save_json"])
        else:
            btn_save_json = tk.Button(parent, text=".json", bg=CFG.colors["WHITE"], width=5, command=callbacks["save_json"])
        btn_save_json.pack(side=tk.LEFT, padx=2)

        if up:
            btn_load_json = tk.Button(parent, image=up, text=".json", compound=tk.LEFT, relief=tk.SOLID, bd=1, command=callbacks["load_json"])
        else:
            btn_load_json = tk.Button(parent, text=".json", bg=CFG.colors["WHITE"], width=5, command=callbacks["load_json"])
        btn_load_json.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        b = self._btn(parent, "clear.png", None, callbacks["clear"])
        b.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        b = self._btn(parent, "undo.png", None, callbacks["undo"])
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "redo.png", None, callbacks["redo"])
        b.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        b = self._btn(parent, "add.png", "files", callbacks["import_textures"])
        b.pack(side=tk.LEFT, padx=2)
        b = self._btn(parent, "remove.png", "files", callbacks["delete_textures"])
        b.pack(side=tk.LEFT, padx=2)

        self._sep(parent)

        tk.Button(parent, text="Загрузить пресет", bg=CFG.colors["WHITE"], width=14, command=callbacks["load_preset"]).pack(side=tk.LEFT, padx=2)
        tk.Button(parent, text="Сохранить пресет", bg=CFG.colors["WHITE"], width=16, command=callbacks["save_preset"]).pack(side=tk.LEFT, padx=2)

    def _sep(self, parent: tk.Frame) -> None:
        tk.Frame(parent, width=1, bg=CFG.colors["GREY"], relief=tk.RAISED).pack(side=tk.LEFT, padx=5, fill=tk.Y)