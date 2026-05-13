import json
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

CELL = 20
W = 80
H = 40
WIDTH = W * CELL
HEIGHT = H * CELL

WHITE = "#FFFFFF"
BLACK = "#000000"
GREY = "#D3D3D3"

EMPTY = 0

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class Editor:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор карты")
        self.root.geometry(f"{WIDTH+20}x{HEIGHT+100}")

        self.texture_dir = resource_path(os.path.join("assets", "block"))
        self.textures = {}
        self.texture_codes = {}

        self.load_textures()

        self.grid = [[EMPTY for _ in range(W)] for _ in range(H)]
        self.fh = [[False]*W for _ in range(H+1)]
        self.fv = [[False]*(W+1) for _ in range(H)]

        self.tool = EMPTY
        self.fence_mode = False

        self.setup_ui()
        self.draw()

    def load_textures(self):
        if not os.path.isdir(self.texture_dir):
            messagebox.showerror(
                "Ошибка",
                f"Папка с текстурами не найдена:\n{self.texture_dir}\n\n"
            )
            return

        try:
            from PIL import Image, ImageTk
        except ImportError:
            messagebox.showerror("Ошибка", "Установите Pillow")
            return

        png_files = [f for f in os.listdir(self.texture_dir) if f.lower().endswith('.png')]
        if not png_files:
            messagebox.showwarning("Предупреждение", f"В папке нет PNG файлов.")
            return

        png_files.sort()
        code = 1
        for filename in png_files:
            path = os.path.join(self.texture_dir, filename)
            try:
                img = Image.open(path).resize((CELL, CELL), Image.Resampling.LANCZOS)
                self.textures[code] = ImageTk.PhotoImage(img)
                self.texture_codes[filename] = code
                code += 1
            except Exception:
                pass

    def setup_ui(self):
        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg=WHITE)
        self.canvas.pack(pady=5)
        self.canvas.bind("<Button-1>", self.click)

        panel = tk.Frame(self.root, bg=GREY, pady=5)
        panel.pack(fill=tk.X)

        tk.Button(panel, text="Пустой", bg=WHITE, relief=tk.SOLID, bd=1, width=6,
                  command=lambda: self.set_tool(EMPTY, fence=False)).pack(side=tk.LEFT, padx=2)

        for code, img in self.textures.items():
            btn = tk.Button(panel, image=img, relief=tk.SOLID, bd=1,
                            command=lambda c=code: self.set_tool(c, fence=False))
            btn.pack(side=tk.LEFT, padx=2)

        tk.Button(panel, text="Граница", bg=WHITE, relief=tk.SOLID, bd=1, width=7,
                  command=lambda: self.set_tool(None, fence=True)).pack(side=tk.LEFT, padx=10)

        action_frame = tk.Frame(self.root, bg=GREY, pady=5)
        action_frame.pack(fill=tk.X)

        tk.Button(action_frame, text="Сохранить PNG", bg=WHITE, width=12,
                  command=self.save_png).pack(side=tk.LEFT, padx=2)
        tk.Button(action_frame, text="Сохранить JSON", bg=WHITE, width=13,
                  command=self.save_json).pack(side=tk.LEFT, padx=2)
        tk.Button(action_frame, text="Загрузить JSON", bg=WHITE, width=13,
                  command=self.load_json).pack(side=tk.LEFT, padx=2)
        tk.Button(action_frame, text="Очистить", bg=WHITE, width=7,
                  command=self.clear).pack(side=tk.LEFT, padx=10)

        self.status = tk.Label(self.root, text="Инструмент: Пустой", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def set_tool(self, tool_code, fence):
        self.fence_mode = fence
        if fence:
            self.tool = None
            self.status.config(text="Инструмент: Граница")
        else:
            self.tool = tool_code
            if tool_code == EMPTY:
                self.status.config(text="Инструмент: Пустой")
            else:
                name = [n for n, c in self.texture_codes.items() if c == tool_code]
                self.status.config(text=f"Инструмент: {name[0] if name else 'Текстура'}")

    def draw(self):
        self.canvas.delete("all")
        for y in range(H):
            for x in range(W):
                x1, y1 = x*CELL, y*CELL
                x2, y2 = x1+CELL, y1+CELL
                t = self.grid[y][x]
                if t == EMPTY:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=WHITE, outline="gray")
                elif t in self.textures:
                    self.canvas.create_image(x1, y1, anchor=tk.NW, image=self.textures[t])
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1)
                else:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="gray", outline="gray")

        for y in range(H+1):
            for x in range(W):
                if self.fh[y][x]:
                    self.canvas.create_line(x*CELL, y*CELL, (x+1)*CELL, y*CELL, fill=BLACK, width=2)
        for y in range(H):
            for x in range(W+1):
                if self.fv[y][x]:
                    self.canvas.create_line(x*CELL, y*CELL, x*CELL, (y+1)*CELL, fill=BLACK, width=2)

    def click(self, e):
        x, y = e.x//CELL, e.y//CELL
        if not (0 <= y < H and 0 <= x < W):
            return
        if self.fence_mode:
            x0, y0 = x*CELL, y*CELL
            d = [abs(e.y - y0), abs(e.y - (y0+CELL)), abs(e.x - x0), abs(e.x - (x0+CELL))]
            m = min(d)
            if m > 6:
                return
            if m == d[0] and y>0:
                self.fh[y][x] = not self.fh[y][x]
            elif m == d[1] and y<H:
                self.fh[y+1][x] = not self.fh[y+1][x]
            elif m == d[2] and x>0:
                self.fv[y][x] = not self.fv[y][x]
            elif m == d[3] and x<W:
                self.fv[y][x+1] = not self.fv[y][x+1]
            self.draw()
            return
        if self.tool is not None:
            self.grid[y][x] = self.tool
            self.draw()

    def save_png(self):
        f = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG","*.png")])
        if f:
            try:
                from PIL import ImageGrab
                x = self.root.winfo_rootx() + self.canvas.winfo_x()
                y = self.root.winfo_rooty() + self.canvas.winfo_y()
                img = ImageGrab.grab((x, y, x+WIDTH, y+HEIGHT))
                img.save(f)
                messagebox.showinfo("Готово", "PNG сохранён")
            except:
                messagebox.showerror("Ошибка", "Не удалось сохранить PNG")

    def save_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if f:
            with open(f, "w", encoding="utf-8") as fp:
                json.dump({"grid": self.grid, "fh": self.fh, "fv": self.fv}, fp, indent=2)
            messagebox.showinfo("Готово", "JSON сохранён")

    def load_json(self):
        f = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if f:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    d = json.load(fp)
                if "grid" in d:
                    self.grid = d["grid"]
                if "fh" in d and "fv" in d:
                    self.fh = d["fh"]
                    self.fv = d["fv"]
                elif "fences_h" in d and "fences_v" in d:
                    self.fh = d["fences_h"]
                    self.fv = d["fences_v"]
                if len(self.grid) != H or len(self.grid[0]) != W:
                    new = [[EMPTY]*W for _ in range(H)]
                    for i in range(min(H, len(self.grid))):
                        for j in range(min(W, len(self.grid[0]))):
                            new[i][j] = self.grid[i][j]
                    self.grid = new
                self.draw()
                messagebox.showinfo("Готово", "Карта загружена")
            except Exception:
                messagebox.showerror("Ошибка", "Не удалось загрузить JSON")

    def clear(self):
        self.grid = [[EMPTY]*W for _ in range(H)]
        self.fh = [[False]*W for _ in range(H+1)]
        self.fv = [[False]*(W+1) for _ in range(H)]
        self.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = Editor(root)
    root.mainloop()