import pandas as pd
import pandas_ta as ta
import logging

logging.basicConfig(filename='logs/trading.log', level=logging.DEBUG)

class Indicators:
    @staticmethod
    def calculate_indicators(df):
        """Рассчитать технические индикаторы, включая ATR."""
        try:
            if df.empty:
                logging.warning("Пустой DataFrame при расчёте индикаторов")
                return df

            df['SMA20'] = ta.sma(df['close'], length=20)
            df['SMA50'] = ta.sma(df['close'], length=50)
            df['RSI'] = ta.rsi(df['close'], length=14)
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            if macd is not None:
                df['MACD'] = macd['MACD_12_26_9']
                df['MACD_signal'] = macd['MACDs_12_26_9']
            stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
            if stoch is not None:
                df['STOCH_k'] = stoch['STOCHk_14_3_3']
                df['STOCH_d'] = stoch['STOCHd_14_3_3']
            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            logging.info(f"Рассчитаны индикаторы: {list(df.columns)}")
            return df
        except Exception as e:
            logging.error(f"Ошибка при расчёте индикаторов: {e}")
            return df

    @staticmethod
    def detect_divergence(df):
        """Обнаружение дивергенций RSI."""
        try:
            if 'RSI' not in df.columns or 'close' not in df.columns:
                return None
            rsi = df['RSI'].tail(10)
            price = df['close'].tail(10)
            if len(rsi) < 2 or len(price) < 2:
                return None
            rsi_diff = rsi.iloc[-1] - rsi.iloc[-2]
            price_diff = price.iloc[-1] - price.iloc[-2]
            if rsi_diff > 0 and price_diff < 0:
                return "bullish"
            elif rsi_diff < 0 and price_diff > 0:
                return "bearish"
            return None
        except Exception as e:
            logging.error(f"Ошибка при обнаружении дивергенции: {e}")
            return None