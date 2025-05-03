import tkinter as tk
from ttkbootstrap import ttk
from tkinter import filedialog

class AccountWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Account")
        self.window.configure(bg='#1a1a1a')  # Темный фон из CSS

        # Настройка стилей
        self.window.style = ttk.Style()
        self.window.style.configure('TLabel', font=('Arial', 12), foreground='#fff', background='#1a1a1a')
        self.window.style.configure('TEntry', font=('Arial', 12), fieldbackground='#2b2b2b', foreground='#fff')

        ttk.Label(self.window, text="Аватарка:").grid(row=0, column=0, pady=5, padx=5)
        ttk.Button(self.window, text="Загрузить", command=lambda: filedialog.askopenfilename(), style='primary.TButton').grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(self.window, text="Никнейм:").grid(row=1, column=0, pady=5, padx=5)
        ttk.Entry(self.window).grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(self.window, text="Телефон:").grid(row=2, column=0, pady=5, padx=5)
        ttk.Entry(self.window).grid(row=2, column=1, pady=5, padx=5)

        ttk.Label(self.window, text="Почта:").grid(row=3, column=0, pady=5, padx=5)
        ttk.Entry(self.window).grid(row=3, column=1, pady=5, padx=5)

        ttk.Button(self.window, text="Сохранить", command=self.window.destroy, style='primary.TButton').grid(row=4, column=0, columnspan=2, pady=5, padx=5)