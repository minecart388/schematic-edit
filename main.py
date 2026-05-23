# main.py
import tkinter as tk
from scripts.editor import Editor

if __name__ == "__main__":
    root = tk.Tk()
    app = Editor(root)
    root.mainloop()