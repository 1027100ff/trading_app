import tkinter as tk
from ui.main_window import TradingApp

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()