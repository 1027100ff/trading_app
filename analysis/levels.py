import pandas as pd
import logging

logging.basicConfig(filename='logs/trading.log', level=logging.INFO)

class Levels:
    @staticmethod
    def calculate_fibonacci_levels(df):
        """Рассчитывает уровни Фибоначчи на основе максимума и минимума цен."""
        try:
            if df.empty or 'high' not in df.columns or 'low' not in df.columns:
                logging.error("DataFrame пустой или отсутствуют столбцы high/low")
                return {'23.6%': float('nan'), '38.2%': float('nan'), '50%': float('nan'), '61.8%': float('nan'), '78.6%': float('nan')}

            # Фильтрация NaN и некорректных значений
            df = df[df['high'].notna() & df['low'].notna() & (df['high'] > 0) & (df['low'] > 0)]
            logging.info(f"После фильтрации high/low: {len(df)} строк")

            if df.empty:
                logging.error("DataFrame пустой после фильтрации high/low")
                return {'23.6%': float('nan'), '38.2%': float('nan'), '50%': float('nan'), '61.8%': float('nan'), '78.6%': float('nan')}

            high = df['high'].max()
            low = df['low'].min()

            logging.info(f"Расчёт Фибоначчи: high={high}, low={low}")

            if pd.isna(high) or pd.isna(low) or high == low:
                logging.error(f"Невозможно рассчитать уровни Фибоначчи: high={high}, low={low}")
                return {'23.6%': float('nan'), '38.2%': float('nan'), '50%': float('nan'), '61.8%': float('nan'), '78.6%': float('nan')}

            diff = high - low
            levels = {
                '23.6%': high - 0.236 * diff,
                '38.2%': high - 0.382 * diff,
                '50%': high - 0.5 * diff,
                '61.8%': high - 0.618 * diff,
                '78.6%': high - 0.786 * diff
            }

            logging.info(f"Уровни Фибоначчи рассчитаны: {levels}")
            return levels

        except Exception as e:
            logging.error(f"Ошибка расчёта уровней Фибоначчи: {e}")
            return {'23.6%': float('nan'), '38.2%': float('nan'), '50%': float('nan'), '61.8%': float('nan'), '78.6%': float('nan')}