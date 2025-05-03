import pandas as pd
import logging
import logging.handlers
import json
from api.tinkoff_api import TinkoffAPI
from trading.strategy import TradingStrategy
from analysis.indicators import Indicators
from analysis.patterns import Patterns
from analysis.levels import Levels
from datetime import timedelta

# Настройка ротации логов
log_handler = logging.handlers.RotatingFileHandler('logs/trading.log', maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Backtester:
    def __init__(self, api_key):
        self.api = TinkoffAPI(api_key)

    def run_backtest(self, ticker, timeframe, start_date, end_date):
        try:
            logging.info(f"Запуск бэктестинга: {ticker}, {timeframe}, {start_date} - {end_date}")
            # Запрашиваем исторические данные
            df = self.api.get_candles(ticker, timeframe)
            if df.empty:
                logging.error(f"Не удалось получить данные для {ticker}")
                return []

            # Фильтруем данные по указанному периоду
            df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
            if df.empty:
                logging.warning(f"Нет данных в периоде {start_date} - {end_date} для {ticker}")
                return []

            logging.info(f"Получено {len(df)} свечей для бэктестинга, последняя свеча: {df['time'].iloc[-1]}")
            # Рассчитываем индикаторы
            df = Indicators.calculate_indicators(df)
            if df.empty:
                logging.error("DataFrame пустой после расчёта индикаторов")
                return []

            trades = []
            active_trade = None

            # Итерация по данным для симуляции торгов
            for i in range(1, len(df)):
                df_slice = df.iloc[:i+1]
                divergence = Indicators.detect_divergence(df_slice)
                candle_patterns = Patterns.detect_candle_patterns(df_slice)
                graphic_patterns = Patterns.detect_graphic_patterns(df_slice)
                fib_levels = Levels.calculate_fibonacci_levels(df_slice)
                order_blocks = Patterns.detect_order_blocks(df_slice)

                current_price = df_slice['close'].iloc[-1]
                logging.debug(f"Обработка свечи {i}: Цена={current_price}, Дивергенция={divergence}, Паттерны={candle_patterns}")

                # Проверяем активную сделку
                if active_trade:
                    position = active_trade['position']
                    entry = active_trade['entry']
                    sl = active_trade['sl']
                    tp = active_trade['tp']

                    # Проверяем условия закрытия сделки
                    if (position == "Лонг" and (current_price >= tp or current_price <= sl)) or \
                       (position == "Шорт" and (current_price <= tp or current_price >= sl)):
                        profit = (tp - entry) if position == "Лонг" else (entry - tp)
                        active_trade['profit'] = profit
                        active_trade['timestamp'] = df_slice['time'].iloc[-1]
                        trades.append(active_trade)
                        logging.info(f"Бэктест: Сделка закрыта: {position}, Прибыль={profit}")
                        active_trade = None

                # Проверяем возможность открытия новой сделки
                if not active_trade:
                    trade = TradingStrategy.calculate_trade(
                        df_slice, divergence, candle_patterns, graphic_patterns,
                        fib_levels, order_blocks, timeframe, self.api, ticker
                    )
                    if trade:
                        trade['timestamp'] = df_slice['time'].iloc[-1]
                        active_trade = trade
                        logging.info(f"Бэктест: Новая сделка: {trade['position']}, Вход={trade['entry']}")
                    else:
                        logging.debug("Сделка не открыта: условия не выполнены")

            # Сохраняем результаты бэктестинга
            try:
                with open('logs/backtest_trades.json', 'w') as f:
                    json.dump(trades, f, default=str, indent=4)
                logging.info(f"Сохранено {len(trades)} сделок бэктестинга в backtest_trades.json")
            except Exception as e:
                logging.error(f"Ошибка сохранения результатов бэктестинга: {e}")

            logging.info(f"Бэктестинг завершен: {len(trades)} сделок")
            return trades

        except Exception as e:
            logging.error(f"Ошибка бэктестинга: {e}")
            return []