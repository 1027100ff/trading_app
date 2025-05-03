import logging
import logging.handlers
import pandas as pd
import json
from analysis.indicators import Indicators
from analysis.patterns import Patterns
from analysis.levels import Levels
from api.tinkoff_api import TinkoffAPI

# Настройка ротации логов
log_handler = logging.handlers.RotatingFileHandler('logs/trading.log', maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TradingStrategy:
    @staticmethod
    def load_settings():
        """Загрузка параметров стратегии из settings.json."""
        try:
            with open('config/settings.json', 'r') as f:
                settings = json.load(f)
            return {
                'rsi_long': settings.get('strategy', {}).get('rsi_long', 50),
                'rsi_short': settings.get('strategy', {}).get('rsi_short', 50),
                'stoch_long': settings.get('strategy', {}).get('stoch_long', 30),
                'stoch_short': settings.get('strategy', {}).get('stoch_short', 70),
                'imbalance_bullish': settings.get('strategy', {}).get('imbalance_bullish', 1.2),
                'imbalance_bearish': settings.get('strategy', {}).get('imbalance_bearish', 0.8)
            }
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек стратегии: {e}")
            return {
                'rsi_long': 50,
                'rsi_short': 50,
                'stoch_long': 30,
                'stoch_short': 70,
                'imbalance_bullish': 1.2,
                'imbalance_bearish': 0.8
            }

    @staticmethod
    def calculate_trade(df, divergence, candle_patterns, graphic_patterns, fib_levels, order_blocks, timeframe, api, ticker):
        """Рассчитать торговый сигнал с мультимасштабным анализом."""
        reasons = []
        params = TradingStrategy.load_settings()
        try:
            # Основной анализ на текущем таймфрейме
            if not df.empty and 'close' in df.columns:
                current_price = df['close'].iloc[-1]
                rsi = df['RSI'].iloc[-1] if 'RSI' in df.columns else None
                macd = df['MACD'].iloc[-1] if 'MACD' in df.columns else None
                stoch_k = df['STOCH_k'].iloc[-1] if 'STOCH_k' in df.columns else None
                atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else None
                atr_mean = df['ATR'].rolling(window=20).mean().iloc[-1] if 'ATR' in df.columns else None

                logging.debug(f"Анализ: RSI={rsi}, Stoch_k={stoch_k}, ATR={atr}, ATR_mean={atr_mean}")

                # Фильтрация по волатильности
                if atr and atr_mean and atr < atr_mean * 0.5:
                    reasons.append("Низкая волатильность (ATR)")
                    logging.info("Сделка отклонена: низкая волатильность")
                    return None

                # Мультимасштабный анализ
                higher_timeframe = TradingStrategy.get_higher_timeframe(timeframe)
                trend_higher = None
                rsi_higher = None
                if higher_timeframe:
                    df_higher = api.get_candles(ticker, higher_timeframe)
                    if not df_higher.empty:
                        df_higher = Indicators.calculate_indicators(df_higher)
                        trend_higher = TradingStrategy.detect_trend(df_higher)
                        rsi_higher = df_higher['RSI'].iloc[-1] if 'RSI' in df_higher.columns else None
                        logging.info(f"Мультимасштабный анализ: {ticker}, старший таймфрейм {higher_timeframe}, тренд {trend_higher}, RSI {rsi_higher}")
                    else:
                        logging.warning(f"Не удалось получить данные для старшего таймфрейма {higher_timeframe}")

                # Технический анализ
                from analysis.technical_analysis import TechnicalAnalysis
                ta_signals = TechnicalAnalysis.analyze(df, ticker=ticker, api_key=api.api_key)
                logging.debug(f"Тех. анализ: {ta_signals}")

                # Условия для лонга
                if (rsi and rsi < params['rsi_long'] and 
                    stoch_k and stoch_k < params['stoch_long'] and 
                    (divergence == "bullish" or divergence is None) and
                    (trend_higher == "bullish" or rsi_higher is None or rsi_higher < 50) and
                    ta_signals.get('order_book_signal') == 'bullish'):
                    entry = current_price
                    sl = current_price - (fib_levels['23.6'] - fib_levels['0.0']) if fib_levels else current_price * 0.98
                    tp = current_price + 2 * (current_price - sl)
                    logging.info("Создана сделка Лонг")
                    return {
                        'position': "Лонг",
                        'entry': entry,
                        'sl': sl,
                        'tp': tp,
                        'pattern': f"RSI+Support/Stoch, Divergence={divergence}"
                    }
                # Условия для шорта
                elif (rsi and rsi > params['rsi_short'] and 
                      stoch_k and stoch_k > params['stoch_short'] and 
                      (divergence == "bearish" or divergence is None) and
                      (trend_higher == "bearish" or rsi_higher is None or rsi_higher > 50) and
                      ta_signals.get('order_book_signal') == 'bearish'):
                    entry = current_price
                    sl = current_price + (fib_levels['100.0'] - fib_levels['76.4']) if fib_levels else current_price * 1.02
                    tp = current_price - 2 * (sl - current_price)
                    logging.info("Создана сделка Шорт")
                    return {
                        'position': "Шорт",
                        'entry': entry,
                        'sl': sl,
                        'tp': tp,
                        'pattern': f"RSI+Resistance/Stoch, Divergence={divergence}"
                    }
                else:
                    reasons.extend([
                        f"RSI={rsi} (требуется <{params['rsi_long']} для лонга, >{params['rsi_short']} для шорта)",
                        f"Stoch_k={stoch_k} (требуется <{params['stoch_long']} для лонга, >{params['stoch_short']} для шорта)",
                        f"Дивергенция={divergence} (требуется bullish/bearish)",
                        f"Старший тренд={trend_higher}, RSI={rsi_higher}",
                        f"Сигнал стакана={ta_signals.get('order_book_signal')}"
                    ])
            else:
                reasons.append("Пустой DataFrame или нет столбца 'close'")
        except Exception as e:
            reasons.append(f"Ошибка: {e}")
            logging.error(f"Ошибка в calculate_trade: {e}")
        
        logging.info(f"Сделка не сгенерирована: {', '.join(reasons)}")
        return None

    @staticmethod
    def get_higher_timeframe(timeframe):
        """Получить старший таймфрейм."""
        timeframe_map = {
            "1min": "5min",
            "5min": "15min",
            "15min": "30min",
            "30min": "1hour",
            "1hour": None
        }
        return timeframe_map.get(timeframe)

    @staticmethod
    def detect_trend(df):
        """Определить тренд на основе скользящих средних."""
        try:
            if 'SMA20' in df.columns and 'SMA50' in df.columns:
                sma20 = df['SMA20'].iloc[-1]
                sma50 = df['SMA50'].iloc[-1]
                if sma20 > sma50:
                    return "bullish"
                elif sma20 < sma50:
                    return "bearish"
            return None
        except Exception as e:
            logging.error(f"Ошибка определения тренда: {e}")
            return None