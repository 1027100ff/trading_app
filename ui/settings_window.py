import tkinter as tk
from ttkbootstrap import Style, ttk
import json
import logging

logging.basicConfig(filename='logs/trading.log', level=logging.DEBUG)

class SettingsWindow:
    def __init__(self, parent, app):
        self.app = app
        self.window = tk.Toplevel(parent)
        self.window.title("Настройки")
        self.window.configure(bg='#1a1a1a')
        self.window.geometry("400x300")

        frame = ttk.Frame(self.window, padding="10", style='Dark.TFrame')
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="API ключ:").grid(row=0, column=0, pady=5, padx=5, sticky=tk.W)
        self.api_key_var = tk.StringVar(value=self.app.api_key)
        ttk.Entry(frame, textvariable=self.api_key_var).grid(row=0, column=1, pady=5, padx=5, sticky=tk.EW)

        ttk.Label(frame, text="API ключ (полный доступ):").grid(row=1, column=0, pady=5, padx=5, sticky=tk.W)
        self.full_api_key_var = tk.StringVar(value=self.app.full_api_key if hasattr(self.app, 'full_api_key') else "")
        ttk.Entry(frame, textvariable=self.full_api_key_var).grid(row=1, column=1, pady=5, padx=5, sticky=tk.EW)

        ttk.Label(frame, text="Режим:").grid(row=2, column=0, pady=5, padx=5, sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.app.mode)
        ttk.OptionMenu(frame, self.mode_var, self.app.mode, "sandbox", "real").grid(row=2, column=1, pady=5, padx=5, sticky=tk.EW)

        ttk.Label(frame, text="Автоматическая торговля:").grid(row=3, column=0, pady=5, padx=5, sticky=tk.W)
        self.auto_trading_var = tk.BooleanVar(value=self.app.auto_trading if hasattr(self.app, 'auto_trading') else False)
        ttk.Checkbutton(frame, variable=self.auto_trading_var).grid(row=3, column=1, pady=5, padx=5, sticky=tk.W)

        ttk.Button(frame, text="Сохранить", command=self.save_settings, style='primary.TButton').grid(row=4, column=0, columnspan=2, pady=10, sticky=tk.EW)
        ttk.Button(frame, text="Отмена", command=self.window.destroy, style='danger.TButton').grid(row=5, column=0, columnspan=2, pady=5, sticky=tk.EW)

    def save_settings(self):
        try:
            settings = {
                "api_key": self.api_key_var.get(),
                "full_api_key": self.full_api_key_var.get(),
                "mode": self.mode_var.get(),
                "telegram_token": self.app.telegram_token,
                "telegram_chat_id": self.app.telegram_chat_id,
                "auto_trading": self.auto_trading_var.get()
            }
            with open('config/settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            self.app.api_key = self.api_key_var.get()
            self.app.full_api_key = self.full_api_key_var.get()
            self.app.mode = self.mode_var.get()
            self.app.auto_trading = self.auto_trading_var.get()
            self.app.api = TinkoffAPI(self.api_key)
            logging.info("Настройки сохранены")
            self.window.destroy()
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек: {e}")