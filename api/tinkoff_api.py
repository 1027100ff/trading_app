import logging
import logging.handlers
import pandas as pd
from tinkoff.invest import Client, CandleInterval
from datetime import datetime, timedelta
import pytz

# Настройка ротации логов
log_handler = logging.handlers.RotatingFileHandler('logs/trading.log', maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TinkoffAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.moscow_tz = pytz.timezone('Europe/Moscow')

    def get_candles(self, ticker, timeframe):
        try:
            with Client(self.api_key) as client:
                instruments = client.instruments.futures()
                instrument = next((i for i in instruments.instruments if i.ticker == ticker), None)
                if not instrument:
                    logging.error(f"Инструмент {ticker} не найден")
                    return pd.DataFrame()

                timeframe_map = {
                    "1min": CandleInterval.CANDLE_INTERVAL_1_MIN,
                    "5min": CandleInterval.CANDLE_INTERVAL_5_MIN,
                    "15min": CandleInterval.CANDLE_INTERVAL_15_MIN,
                    "30min": CandleInterval.CANDLE_INTERVAL_30_MIN,
                    "1hour": CandleInterval.CANDLE_INTERVAL_HOUR
                }
                interval = timeframe_map.get(timeframe, CandleInterval.CANDLE_INTERVAL_5_MIN)

                end_time = datetime.now(self.moscow_tz)
                start_time = end_time - timedelta(days=7)  # Запрашиваем данные за 7 дней

                candles = client.market_data.get_candles(
                    figi=instrument.figi,
                    from_=start_time,
                    to=end_time,
                    interval=interval
                )

                data = []
                for candle in candles.candles:
                    data.append({
                        'time': candle.time.astimezone(self.moscow_tz),
                        'open': float(candle.open.units + candle.open.nano / 1e9),
                        'high': float(candle.high.units + candle.high.nano / 1e9),
                        'low': float(candle.low.units + candle.low.nano / 1e9),
                        'close': float(candle.close.units + candle.close.nano / 1e9),
                        'volume': candle.volume
                    })

                df = pd.DataFrame(data)
                if not df.empty:
                    logging.info(f"Получено {len(df)} свечей для {ticker}, таймфрейм {timeframe}, последняя свеча: {df['time'].iloc[-1]}")
                else:
                    logging.warning(f"Нет данных для {ticker}, таймфрейм {timeframe}")
                return df

        except Exception as e:
            logging.error(f"Ошибка получения свечей: {e}")
            return pd.DataFrame()

    def get_order_book(self, ticker, depth=20):
        try:
            with Client(self.api_key) as client:
                instruments = client.instruments.futures()
                instrument = next((i for i in instruments.instruments if i.ticker == ticker), None)
                if not instrument:
                    logging.error(f"Инструмент {ticker} не найден")
                    return None

                order_book = client.market_data.get_order_book(
                    figi=instrument.figi,
                    depth=depth
                )

                bids = [{'price': float(o.price.units + o.price.nano / 1e9), 'quantity': o.quantity} for o in order_book.bids]
                asks = [{'price': float(o.price.units + o.price.nano / 1e9), 'quantity': o.quantity} for o in order_book.asks]
                return {'bids': bids, 'asks': asks}
        except Exception as e:
            logging.error(f"Ошибка получения стакана: {e}")
            return None