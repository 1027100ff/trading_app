import logging
import logging.handlers
import pandas as pd
import json
from api.tinkoff_api import TinkoffAPI

# Настройка ротации логов
log_handler = logging.handlers.RotatingFileHandler('logs/trading.log', maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TechnicalAnalysis:
    @staticmethod
    def load_settings():
        """Загрузка параметров стратегии из settings.json."""
        try:
            with open('config/settings.json', 'r') as f:
                settings = json.load(f)
            return {
                'imbalance_bullish': settings.get('strategy', {}).get('imbalance_bullish', 1.2),
                'imbalance_bearish': settings.get('strategy', {}).get('imbalance_bearish', 0.8)
            }
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек анализа: {e}")
            return {
                'imbalance_bullish': 1.2,
                'imbalance_bearish': 0.8
            }

    @staticmethod
    def analyze(df, ticker, api_key):
        """Технический анализ с улучшенным анализом стакана."""
        params = TechnicalAnalysis.load_settings()
        try:
            ta_signals = {}
            api = TinkoffAPI(api_key)
            
            if not df.empty and 'RSI' in df.columns:
                ta_signals['rsi'] = df['RSI'].iloc[-1]
                ta_signals['macd'] = df['MACD'].iloc[-1] if 'MACD' in df.columns else None
                ta_signals['stoch_k'] = df['STOCH_k'].iloc[-1] if 'STOCH_k' in df.columns else None
                ta_signals['atr'] = df['ATR'].iloc[-1] if 'ATR' in df.columns else None
            
            order_book = api.get_order_book(ticker, depth=20)
            if order_book:
                bids_volume = sum(b['quantity'] for b in order_book['bids'])
                asks_volume = sum(a['quantity'] for a in order_book['asks'])
                if asks_volume == 0:
                    ta_signals['order_book_imbalance'] = None
                    ta_signals['order_book_signal'] = None
                    logging.warning(f"Нулевой объём asks для {ticker}")
                else:
                    imbalance = bids_volume / asks_volume
                    ta_signals['order_book_imbalance'] = imbalance
                    ta_signals['order_book_signal'] = (
                        'bullish' if imbalance > params['imbalance_bullish'] else 
                        'bearish' if imbalance < params['imbalance_bearish'] else 'neutral'
                    )
                    logging.info(f"Анализ стакана для {ticker}: imbalance={imbalance}, signal={ta_signals['order_book_signal']}")
            else:
                ta_signals['order_book_imbalance'] = None
                ta_signals['order_book_signal'] = None
                logging.warning(f"Не удалось получить стакан для {ticker}")

            return ta_signals
        except Exception as e:
            logging.error(f"Ошибка в техническом анализе: {e}")
            return {}