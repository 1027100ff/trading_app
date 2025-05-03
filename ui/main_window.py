import tkinter as tk
from ttkbootstrap import Style, ttk
from api.tinkoff_api import TinkoffAPI
from analysis.indicators import Indicators
from analysis.patterns import Patterns
from analysis.levels import Levels
from trading.strategy import TradingStrategy
from ui.settings_window import SettingsWindow
from ui.account_window import AccountWindow
from ml.trade_predictor import TradePredictor
from utils.backtesting import Backtester
import logging
import logging.handlers
import json
import sys
import os
import shutil
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from telegram import Bot
from telegram.error import TelegramError
import asyncio

# Настройка ротации логов
log_handler = logging.handlers.RotatingFileHandler('logs/trading.log', maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class HistoryWindow:
    def __init__(self, parent, trades, ticker, timeframe):
        self.window = tk.Toplevel(parent)
        self.window.title("История торгов")
        self.window.configure(bg='#1a1a1a')
        self.window.geometry("1000x800")  # Увеличенный размер окна

        self.ticker = ticker
        self.timeframe = timeframe
        self.trades = trades
        self.api = TinkoffAPI(json.load(open('config/settings.json'))['api_key'])

        # Основной фрейм
        frame = ttk.Frame(self.window, padding="10", style='Dark.TFrame')
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        # Статистика в виде таблицы
        stats_frame = ttk.LabelFrame(frame, text="Статистика", padding="5", style='Dark.TLabelframe')
        stats_frame.grid(row=0, column=0, pady=5, sticky=tk.EW)
        stats_frame.columnconfigure(1, weight=1)

        stats_labels = [
            ("Всего сделок", lambda: len(self.trades)),
            ("Успешных", lambda: sum(1 for t in self.trades if t.get('profit', 0) > 0)),
            ("Общая прибыль", lambda: f"{sum(t.get('profit', 0) for t in self.trades):.2f}"),
            ("Средняя прибыль", lambda: f"{sum(t.get('profit', 0) for t in self.trades) / len(self.trades):.2f}" if len(self.trades) > 0 else "0"),
            ("Макс. просадка", lambda: f"{min(0, min([sum([t.get('profit', 0) for t in self.trades][:i+1]) for i in range(len(self.trades))], default=0)):.2f}")
        ]
        for i, (label, func) in enumerate(stats_labels):
            ttk.Label(stats_frame, text=f"{label}:", style='TLabel').grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            ttk.Label(stats_frame, text=func(), style='TLabel').grid(row=i, column=1, padx=5, pady=2, sticky=tk.W)

        # Текстовое поле для сделок
        text_frame = ttk.LabelFrame(frame, text="Сделки", padding="5", style='Dark.TLabelframe')
        text_frame.grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))
        self.text = tk.Text(text_frame, height=10, width=80, bg='#2b2b2b', fg='#fff', font=('Consolas', 12), insertbackground='#fff')
        self.text.grid(row=0, column=0, pady=5, padx=5, sticky=(tk.W, tk.E))
        self.text.bind("<Key>", lambda e: "break")
        self.text.bind("<Control-c>", self.copy_text)

        # График
        chart_frame = ttk.LabelFrame(frame, text="График", padding="5", style='Dark.TLabelframe')
        chart_frame.grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.chart_canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.update_history(trades)
        self.update_chart()

    def copy_text(self, event):
        try:
            selected_text = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.window.clipboard_clear()
            self.window.clipboard_append(selected_text)
            logging.info("Текст истории скопирован в буфер обмена")
            return "break"
        except tk.TclError:
            logging.warning("Ошибка копирования: текст не выделен")
            return "break"

    def update_history(self, trades):
        self.text.config(state='normal')
        self.text.delete(1.0, tk.END)
        for trade in trades:
            timestamp = trade.get('timestamp', 'N/A')
            position = trade['position']
            entry = trade['entry']
            sl = trade['sl']
            tp = trade['tp']
            profit = trade.get('profit', 'Открыта')
            pattern = trade['pattern']
            self.text.insert(tk.END, f"Время: {timestamp}\n"
                                    f"Позиция: {position}\n"
                                    f"Вход: {entry}\n"
                                    f"SL: {sl}\n"
                                    f"TP: {tp}\n"
                                    f"Прибыль: {profit}\n"
                                    f"Паттерн: {pattern}\n"
                                    f"{'-'*50}\n")
        self.text.config(state='disabled')

    def update_chart(self):
        try:
            # Получаем данные для графика
            df = self.api.get_candles(self.ticker, self.timeframe)
            if df.empty:
                logging.warning(f"Пустой DataFrame для графика в History: {self.ticker}, {self.timeframe}")
                return

            df = Indicators.calculate_indicators(df)
            self.fig.clear()
            ax = self.fig.add_subplot(111)

            # Ограничиваем количество свечей для отображения
            df_plot = df.tail(50)
            for i, row in df_plot.iterrows():
                color = 'green' if row['close'] >= row['open'] else 'red'
                ax.plot([row['time'], row['time']], [row['low'], row['high']], color='black')
                ax.add_patch(plt.Rectangle((row['time'], min(row['open'], row['close'])),
                                          pd.Timedelta(minutes=1), abs(row['close'] - row['open']),
                                          color=color))

            # Уровни Фибоначчи
            fib_levels = Levels.calculate_fibonacci_levels(df)
            for level, price in fib_levels.items():
                ax.axhline(price, linestyle='--', alpha=0.5, label=f'Fib {level}')

            # RSI
            ax_rsi = ax.twinx()
            ax_rsi.plot(df_plot['time'], df_plot['RSI'], color='blue', label='RSI')
            ax_rsi.set_ylim(0, 100)
            ax_rsi.axhline(70, linestyle='--', color='red', alpha=0.3)
            ax_rsi.axhline(30, linestyle='--', color='green', alpha=0.3)

            # Настройки графика
            ax.set_title(f"{self.ticker} ({self.timeframe})")
            ax.legend(loc='upper left')
            ax_rsi.legend(loc='upper right')
            ax.grid(True)
            self.fig.tight_layout()
            self.chart_canvas.draw()
        except Exception as e:
            logging.error(f"Ошибка обновления графика в History: {e}")

class TradingApp:
    def __init__(self, root):
        self.style = Style(theme='darkly')
        self.root = root
        self.root.title("Trading Analysis")
        self.root.configure(bg='#1a1a1a')
        
        with open('config/settings.json', 'r') as f:
            settings = json.load(f)
            self.api_key = settings['api_key']
            self.full_api_key = settings.get('full_api_key', '')
            self.mode = settings['mode']
            self.telegram_token = settings.get('telegram_token')
            self.telegram_chat_id = settings.get('telegram_chat_id')
            self.auto_trading = settings.get('auto_trading', False)
        
        self.tickers = ["GKM5", "WUM5", "VKM5", "TBM5", "RLM5", "YDM5"]
        self.timeframes = ["1min", "5min", "15min", "30min", "1hour"]
        self.running = False
        self.trades = self.load_trades()
        self.active_trade = None
        self.api = TinkoffAPI(self.api_key)
        self.ml_predictor = TradePredictor()
        self.after_id = None
        self.telegram_bot = Bot(token=self.telegram_token) if self.telegram_token else None
        self.request_count = 0
        self.request_limit = 100  # Лимит запросов в минуту
        self.setup_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_trades(self):
        try:
            with open('logs/trades_history.json', 'r') as f:
                trades = json.load(f)
            logging.info(f"Загружено {len(trades)} сделок из trades_history.json")
            return trades
        except FileNotFoundError:
            logging.info("Файл trades_history.json не найден, создаётся новый")
            return []
        except Exception as e:
            logging.error(f"Ошибка загрузки trades_history.json: {e}")
            return []

    def save_trades(self):
        try:
            with open('logs/trades_history.json', 'w') as f:
                json.dump(self.trades, f, default=str, indent=4)
            logging.info(f"Сохранено {len(self.trades)} сделок в trades_history.json")
            self.update_profit_chart_main()
        except Exception as e:
            logging.error(f"Ошибка сохранения trades_history.json: {e}")

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding="10", style='TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.configure(style='Dark.TFrame')
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.columnconfigure(3, weight=1)
        main_frame.rowconfigure(2, weight=1)

        self.style.configure('success.TButton', font=('Arial', 14), background='#28a745', foreground='#fff', bordercolor='#28a745', borderradius=5)
        self.style.configure('danger.TButton', font=('Arial', 14), background='#dc3545', foreground='#fff', bordercolor='#dc3545', borderradius=5)
        self.style.configure('primary.TButton', font=('Arial', 14), background='#007bff', foreground='#fff', bordercolor='#007bff', borderradius=5)
        self.style.configure('TLabel', font=('Arial', 12), foreground='#fff', background='#1a1a1a')
        self.style.configure('TFrame', background='#1a1a1a')
        self.style.configure('TNotebook', background='#1a1a1a', foreground='#fff')
        self.style.configure('TNotebook.Tab', font=('Arial', 12), background='#2b2b2b', foreground='#fff', selectedbackground='#007bff')
        self.style.configure('Dark.TLabelframe', background='#1a1a1a', foreground='#fff')
        self.style.configure('Dark.TLabelframe.Label', background='#1a1a1a', foreground='#fff')

        ttk.Button(main_frame, text="Settings", command=self.open_settings, style='primary.TButton').grid(row=0, column=0, pady=5, padx=5, sticky=tk.EW)
        ttk.Button(main_frame, text="Account", command=self.open_account, style='primary.TButton').grid(row=0, column=1, pady=5, padx=5, sticky=tk.EW)
        ttk.Button(main_frame, text="Start", command=self.start_analysis, style='success.TButton').grid(row=0, column=2, pady=5, padx=5, sticky=tk.EW)
        ttk.Button(main_frame, text="Stop", command=self.stop_analysis, style='danger.TButton').grid(row=0, column=3, pady=5, padx=5, sticky=tk.EW)
        ttk.Button(main_frame, text="History", command=self.open_history, style='primary.TButton').grid(row=0, column=4, pady=5, padx=5, sticky=tk.EW)
        ttk.Button(main_frame, text="Backtest", command=self.run_backtest, style='primary.TButton').grid(row=0, column=5, pady=5, padx=5, sticky=tk.EW)

        self.timeframe_var = tk.StringVar(value="5min")
        ttk.Label(main_frame, text="Таймфрейм:").grid(row=1, column=0, pady=5, padx=5, sticky=tk.E)
        timeframe_menu = ttk.OptionMenu(main_frame, self.timeframe_var, "5min", *self.timeframes)
        timeframe_menu.grid(row=1, column=1, pady=5, padx=5, sticky=tk.EW)

        self.ticker_var = tk.StringVar(value=self.tickers[0] if self.tickers else "")
        ttk.Label(main_frame, text="Тикер:").grid(row=1, column=2, pady=5, padx=5, sticky=tk.E)
        ticker_menu = ttk.OptionMenu(main_frame, self.ticker_var, self.tickers[0] if self.tickers else "", *self.tickers)
        ticker_menu.grid(row=1, column=3, pady=5, padx=5, sticky=tk.EW)

        notebook = ttk.Notebook(main_frame, style='TNotebook')
        notebook.grid(row=2, column=0, columnspan=5, pady=10, padx=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        log_frame = ttk.Frame(notebook, style='Dark.TFrame')
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        notebook.add(log_frame, text="Логи")
        self.log_text = tk.Text(log_frame, height=10, width=50, 
                                bg='#2b2b2b', fg='#fff', font=('Consolas', 12), 
                                insertbackground='#fff', borderwidth=0)
        self.log_text.grid(row=0, column=0, pady=5, padx=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text.bind("<Key>", lambda e: "break")
        self.log_text.bind("<Control-c>", self.copy_log_text)

        self.chart_frame = ttk.Frame(notebook, style='Dark.TFrame')
        self.chart_frame.columnconfigure(0, weight=1)
        self.chart_frame.rowconfigure(0, weight=1)
        notebook.add(self.chart_frame, text="График")
        self.chart_canvas = None
        self.chart_data = None

        profit_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        profit_frame.grid(row=3, column=0, columnspan=5, pady=5, sticky=tk.EW)
        profit_frame.columnconfigure(0, weight=1)
        fig_profit = Figure(figsize=(6, 2), dpi=100)
        self.profit_ax_main = fig_profit.add_subplot(111)
        self.profit_canvas_main = FigureCanvasTkAgg(fig_profit, master=profit_frame)
        self.profit_canvas_main.get_tk_widget().grid(row=0, column=0, sticky=tk.EW)
        self.update_profit_chart_main()

    def copy_log_text(self, event):
        try:
            selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            logging.info("Текст логов скопирован в буфер обмена")
            return "break"
        except tk.TclError:
            logging.warning("Ошибка копирования: текст не выделен")
            return "break"

    def open_settings(self):
        SettingsWindow(self.root, self)

    def open_account(self):
        AccountWindow(self.root)

    def open_history(self):
        HistoryWindow(self.root, self.trades, self.ticker_var.get(), self.timeframe_var.get())

    def update_chart(self, df):
        try:
            if df.empty or 'close' not in df.columns:
                logging.warning("Пустой DataFrame для графика")
                return
            self.chart_data = df
            fig = Figure(figsize=(8, 5), dpi=100)
            ax = fig.add_subplot(111)
            for i, row in df.tail(50).iterrows():
                color = 'green' if row['close'] >= row['open'] else 'red'
                ax.plot([row['time'], row['time']], [row['low'], row['high']], color='black')
                ax.add_patch(plt.Rectangle((row['time'], min(row['open'], row['close'])), 
                                          pd.Timedelta(minutes=1), abs(row['close'] - row['open']), 
                                          color=color))
            fib_levels = Levels.calculate_fibonacci_levels(df)
            for level, price in fib_levels.items():
                ax.axhline(price, linestyle='--', alpha=0.5, label=f'Fib {level}')
            ax_rsi = ax.twinx()
            ax_rsi.plot(df['time'].tail(50), df['RSI'].tail(50), color='blue', label='RSI')
            ax_rsi.set_ylim(0, 100)
            ax_rsi.axhline(70, linestyle='--', color='red', alpha=0.3)
            ax_rsi.axhline(30, linestyle='--', color='green', alpha=0.3)
            ax.set_title(f"{self.ticker_var.get()} ({self.timeframe_var.get()})")
            ax.legend(loc='upper left')
            ax_rsi.legend(loc='upper right')
            if self.chart_canvas:
                self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            self.chart_canvas.draw()
            self.chart_canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        except Exception as e:
            logging.error(f"Ошибка обновления графика: {e}")

    def update_profit_chart_main(self):
        try:
            self.profit_ax_main.clear()
            profits = [t.get('profit', 0) for t in self.trades]
            dates = [pd.to_datetime(t.get('timestamp')) for t in self.trades]
            cumulative_profit = np.cumsum(profits)
            self.profit_ax_main.plot(dates, cumulative_profit, color='blue', label='Чистая прибыль')
            self.profit_ax_main.set_xlabel('Дата')
            self.profit_ax_main.set_ylabel('Прибыль')
            self.profit_ax_main.legend()
            self.profit_ax_main.grid(True)
            self.profit_canvas_main.draw()
        except Exception as e:
            logging.error(f"Ошибка обновления графика прибыли: {e}")

    async def send_telegram_notification(self, message):
        try:
            if self.telegram_bot and self.telegram_chat_id:
                await self.telegram_bot.send_message(chat_id=self.telegram_chat_id, text=message)
                logging.info(f"Отправлено уведомление в Telegram: {message}")
        except TelegramError as e:
            logging.error(f"Ошибка отправки Telegram: {e}")

    def place_order(self, trade):
        try:
            if not self.auto_trading or not self.full_api_key:
                logging.info("Автоматическая торговля отключена или отсутствует полный API-ключ")
                return
            from tinkoff.invest import Client, OrderDirection, OrderType
            with Client(self.full_api_key) as client:
                ticker_info = next((i for i in client.instruments.futures().instruments if i.ticker == self.ticker_var.get()), None)
                if not ticker_info:
                    logging.error(f"Тикер {self.ticker_var.get()} не найден")
                    return
                direction = OrderDirection.ORDER_DIRECTION_BUY if trade['position'] == "Лонг" else OrderDirection.ORDER_DIRECTION_SELL
                response = client.orders.post_order(
                    figi=ticker_info.figi,
                    quantity=1,
                    price={'units': int(trade['entry']), 'nano': int((trade['entry'] % 1) * 1e9)},
                    direction=direction,
                    account_id=client.users.get_accounts().accounts[0].id,
                    order_type=OrderType.ORDER_TYPE_LIMIT
                )
                if response.order_id:
                    logging.info(f"Размещён ордер: {trade['position']}, ID={response.order_id}, цена={trade['entry']}")
                else:
                    logging.error("Не удалось разместить ордер")
                    return
        except Exception as e:
            logging.error(f"Ошибка размещения ордера: {e}")

    def start_analysis(self):
        if self.running:
            return
        self.running = True
        self.request_count = 0
        logging.info("Запуск анализа")

        def analyze():
            if not self.running or not self.root.winfo_exists():
                logging.info("Анализ остановлен: running=False или окно уничтожено")
                return
            if self.request_count >= self.request_limit:
                self.log_message("Достигнут лимит запросов API")
                self.stop_analysis()
                return
            self.request_count += 1

            ticker = self.ticker_var.get()
            timeframe = self.timeframe_var.get()

            logging.info(f"Начало анализа для {ticker}, таймфрейм {timeframe}")
            df = self.api.get_candles(ticker, timeframe)
            if df.empty:
                self.log_message(f"Ошибка получения данных для {ticker} (таймфрейм {timeframe}). Возможно, тикер недоступен или превышен период данных.")
                logging.error(f"Пустой DataFrame для {ticker}, {timeframe}")
                return

            logging.info(f"Получено {len(df)} свечей, последняя свеча: {df['time'].iloc[-1] if not df.empty else 'N/A'}")
            df = Indicators.calculate_indicators(df)
            if df.empty:
                self.log_message(f"DataFrame пустой после расчёта индикаторов для {ticker}")
                logging.error(f"DataFrame пустой после индикаторов для {ticker}")
                return

            self.update_chart(df)

            divergence = Indicators.detect_divergence(df)
            candle_patterns = Patterns.detect_candle_patterns(df)
            graphic_patterns = Patterns.detect_graphic_patterns(df)
            fib_levels = Levels.calculate_fibonacci_levels(df)
            order_blocks = Patterns.detect_order_blocks(df)

            logging.info(f"Дивергенция: {divergence}, Свечные паттерны: {candle_patterns}, Графические паттерны: {graphic_patterns}")

            current_price = df['close'].iloc[-1] if not df.empty and 'close' in df.columns else None
            if current_price is None:
                self.log_message(f"Невозможно получить текущую цену для {ticker}")
                logging.error(f"Текущая цена не определена для {ticker}")
                return

            from analysis.technical_analysis import TechnicalAnalysis
            ta_signals = TechnicalAnalysis.analyze(df, ticker=ticker, api_key=self.api_key)
            logging.info(f"Технический анализ: {ta_signals}")

            if self.active_trade:
                trade = self.active_trade
                position = trade['position']
                entry = trade['entry']
                sl = trade['sl']
                tp = trade['tp']
                activity = self.check_price_activity(df, position)

                if position == "Лонг" and current_price > entry and activity > 0.005:
                    new_tp = current_price + 2 * (current_price - entry)
                    trade['tp'] = new_tp
                    self.log_message(f"Обновлён TP для Лонг: Новый TP={new_tp}, SL={sl}")
                elif position == "Шорт" and current_price < entry and activity < -0.005:
                    new_tp = current_price - 2 * (entry - current_price)
                    trade['tp'] = new_tp
                    self.log_message(f"Обновлён TP для Шорт: Новый TP={new_tp}, SL={sl}")

                if (position == "Лонг" and (current_price >= tp or current_price <= sl)) or \
                   (position == "Шорт" and (current_price <= tp or current_price >= sl)):
                    profit = (tp - entry) if position == "Лонг" else (entry - tp)
                    trade['profit'] = profit
                    self.ml_predictor.save_data(df, trade, profit > 0)
                    self.ml_predictor.train_model()
                    self.log_message(f"Сделка закрыта: {position}, Прибыль={profit}")
                    asyncio.run(self.send_telegram_notification(f"Сделка закрыта: {position}, Прибыль={profit}"))
                    self.trades.append(trade)
                    self.save_trades()
                    self.active_trade = None

            if not self.active_trade and not df.empty and 'close' in df.columns:
                trade = TradingStrategy.calculate_trade(df, divergence, candle_patterns, graphic_patterns, fib_levels, order_blocks, timeframe, self.api, ticker)
                if trade:
                    # Временно отключаем ML-предсказание для отладки
                    # if self.ml_predictor.predict(df):
                    trade['timestamp'] = datetime.now()
                    self.active_trade = trade
                    self.log_trade(trade, divergence)
                    self.place_order(trade)
                    logging.info(f"Сделка создана: {trade}")
                    # else:
                    #     logging.info("Сделка отклонена ML-предсказанием")
                else:
                    logging.info("Сделка не сгенерирована: условия не выполнены")

            if self.running and self.root.winfo_exists():
                logging.info(f"Запланирован следующий анализ для {ticker} через 60 секунд")
                self.after_id = self.root.after(60000, analyze)
            else:
                logging.info("Следующий анализ не запланирован: running=False или окно уничтожено")

        analyze()

    def check_price_activity(self, df, position):
        try:
            if len(df) < 10:
                return 0
            recent_prices = df['close'].tail(10)
            pct_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
            return pct_change if position == "Лонг" else -pct_change
        except Exception as e:
            logging.error(f"Ошибка проверки активности цены: {e}")
            return 0

    def stop_analysis(self):
        self.running = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
            logging.info("Анализ остановлен, after_id отменён")

        profit = 0
        successful = 0
        failed = 0
        for trade in self.trades:
            if 'profit' in trade:
                profit += trade['profit']
                if trade['profit'] > 0:
                    successful += 1
                else:
                    failed += 1

        self.log_message(f"Приunto: Прибыль за сегодня: {profit}\nУспешные сделки: {successful}\nСделки в минус: {failed}")
        self.save_trades()
        self.active_trade = None

    def log_trade(self, trade, divergence):
        log_message = (f"Вход: {trade['position']}\n"
                       f"Паттерн: {trade['pattern']}\n"
                       f"Дивергенция: {divergence}\n"
                       f"Точка входа: {trade['entry']}\n"
                       f"Тейк Профит: {trade['tp']}\n"
                       f"Стоп Лосс: {trade['sl']}\n")
        logging.info(log_message)
        self.log_message(log_message)
        asyncio.run(self.send_telegram_notification(f"Новая сделка:\n{log_message}"))

    def log_message(self, message):
        try:
            if self.log_text.winfo_exists():
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.config(state='disabled')
        except tk.TclError:
            logging.info(f"Tkinter: {message}")

    def run_backtest(self):
        try:
            backtester = Backtester(self.api_key)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            trades = backtester.run_backtest(self.ticker_var.get(), self.timeframe_var.get(), start_date, end_date)
            self.trades.extend(trades)
            self.save_trades()
            self.log_message(f"Бэктестинг завершен: добавлено {len(trades)} сделок")
        except Exception as e:
            logging.error(f"Ошибка бэктестинга: {e}")
            self.log_message(f"Ошибка бэктестинга: {e}")

    def on_closing(self):
        self.running = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
            logging.info("Окно закрывается, after_id отменён")
        
        try:
            for root, dirs, _ in os.walk('.'):
                for dir_name in dirs:
                    if dir_name == '__pycache__':
                        pycache_path = os.path.join(root, dir_name)
                        shutil.rmtree(pycache_path)
                        logging.info(f"Удалена папка: {pycache_path}")
        except Exception as e:
            logging.error(f"Ошибка при очистке __pycache__: {e}")

        self.save_trades()
        self.root.quit()
        self.root.after(100, self.root.destroy)
        logging.info("Программа завершена")
        sys.exit(0)