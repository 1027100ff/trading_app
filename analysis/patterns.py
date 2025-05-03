import pandas as pd
import pandas_ta as ta
import logging

logging.basicConfig(filename='logs/trading.log', level=logging.INFO)

class Patterns:
    @staticmethod
    def detect_candle_patterns(df):
        """Обнаружение всех свечных паттернов с использованием pandas_ta."""
        try:
            # Получение всех доступных свечных паттернов
            candle_patterns = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name="all")
            patterns = []
            for pattern in candle_patterns.columns:
                if candle_patterns[pattern].iloc[-1] != 0:
                    patterns.append(pattern.replace('CDL_', '').lower())
            return patterns if patterns else "Не найдены"
        except Exception as e:
            logging.error(f"Ошибка обнаружения свечных паттернов: {e}")
            return "Не найдены"

    @staticmethod
    def detect_graphic_patterns(df):
        """Обнаружение графических паттернов."""
        try:
            patterns = []
            for i in range(5, len(df)-5):
                # Двойное дно
                if (df['low'].iloc[i] <= df['low'].iloc[i-1] and 
                    df['low'].iloc[i] <= df['low'].iloc[i+1] and
                    abs(df['low'].iloc[i] - df['low'].iloc[i-3]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Двойное дно", df['low'].iloc[i]))
                
                # Двойная вершина
                elif (df['high'].iloc[i] >= df['high'].iloc[i-1] and 
                      df['high'].iloc[i] >= df['high'].iloc[i+1] and
                      abs(df['high'].iloc[i] - df['high'].iloc[i-3]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Двойная вершина", df['high'].iloc[i]))
                
                # Тройное дно
                elif (df['low'].iloc[i] <= df['low'].iloc[i-2] and 
                      df['low'].iloc[i] <= df['low'].iloc[i+2] and
                      abs(df['low'].iloc[i] - df['low'].iloc[i-4]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Тройное дно", df['low'].iloc[i]))
                
                # Тройная вершина
                elif (df['high'].iloc[i] >= df['high'].iloc[i-2] and 
                      df['high'].iloc[i] >= df['high'].iloc[i+2] and
                      abs(df['high'].iloc[i] - df['high'].iloc[i-4]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Тройная вершина", df['high'].iloc[i]))
                
                # Голова и плечи
                elif (df['high'].iloc[i-2] < df['high'].iloc[i] and 
                      df['high'].iloc[i+2] < df['high'].iloc[i] and
                      abs(df['high'].iloc[i-2] - df['high'].iloc[i+2]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Голова и плечи", df['high'].iloc[i]))
                
                # Обратная голова и плечи
                elif (df['low'].iloc[i-2] > df['low'].iloc[i] and 
                      df['low'].iloc[i+2] > df['low'].iloc[i] and
                      abs(df['low'].iloc[i-2] - df['low'].iloc[i+2]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Обратная голова и плечи", df['low'].iloc[i]))
                
                # Восходящий треугольник
                elif (df['high'].iloc[i] >= df['high'].iloc[i-1] and 
                      df['low'].iloc[i] >= df['low'].iloc[i-1] and
                      df['high'].iloc[i] - df['low'].iloc[i] < df['high'].iloc[i-1] - df['low'].iloc[i-1]):
                    patterns.append(("Восходящий треугольник", df['close'].iloc[i]))
                
                # Нисходящий треугольник
                elif (df['high'].iloc[i] <= df['high'].iloc[i-1] and 
                      df['low'].iloc[i] <= df['low'].iloc[i-1] and
                      df['high'].iloc[i] - df['low'].iloc[i] > df['high'].iloc[i-1] - df['low'].iloc[i-1]):
                    patterns.append(("Нисходящий треугольник", df['close'].iloc[i]))
                
                # Симметричный треугольник
                elif (abs(df['high'].iloc[i] - df['high'].iloc[i-1]) < 0.01 * df['close'].iloc[i] and
                      abs(df['low'].iloc[i] - df['low'].iloc[i-1]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Симметричный треугольник", df['close'].iloc[i]))
                
                # Флаг
                elif (df['high'].iloc[i] - df['low'].iloc[i] < 0.02 * df['close'].iloc[i] and
                      df['volume'].iloc[i] < df['volume'].iloc[i-1]):
                    patterns.append(("Флаг", df['close'].iloc[i]))
                
                # Вымпел
                elif (df['high'].iloc[i] - df['low'].iloc[i] < 0.015 * df['close'].iloc[i] and
                      df['high'].iloc[i-1] - df['low'].iloc[i-1] > 0.03 * df['close'].iloc[i]):
                    patterns.append(("Вымпел", df['close'].iloc[i]))
                
                # Восходящий клин
                elif (df['high'].iloc[i] >= df['high'].iloc[i-1] and 
                      df['low'].iloc[i] >= df['low'].iloc[i-1] and
                      (df['high'].iloc[i] - df['low'].iloc[i]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Восходящий клин", df['close'].iloc[i]))
                
                # Нисходящий клин
                elif (df['high'].iloc[i] <= df['high'].iloc[i-1] and 
                      df['low'].iloc[i] <= df['low'].iloc[i-1] and
                      (df['high'].iloc[i] - df['low'].iloc[i]) < 0.01 * df['close'].iloc[i]):
                    patterns.append(("Нисходящий клин", df['close'].iloc[i]))
                
                # Прямоугольник
                elif (abs(df['high'].iloc[i] - df['high'].iloc[i-1]) < 0.005 * df['close'].iloc[i] and
                      abs(df['low'].iloc[i] - df['low'].iloc[i-1]) < 0.005 * df['close'].iloc[i]):
                    patterns.append(("Прямоугольник", df['close'].iloc[i]))

            return patterns if patterns else "Не найдены"
        except Exception as e:
            logging.error(f"Ошибка обнаружения графических паттернов: {e}")
            return "Не найдены"

    @staticmethod
    def detect_order_blocks(df):
        """Обнаружение ордер блоков."""
        try:
            blocks = []
            for i in range(1, len(df)-1):
                if df['high'].iloc[i] > df['high'].iloc[i-1] and df['high'].iloc[i] > df['high'].iloc[i+1]:
                    blocks.append(("Медвежий", df['high'].iloc[i]))
                elif df['low'].iloc[i] < df['low'].iloc[i-1] and df['low'].iloc[i] < df['low'].iloc[i+1]:
                    blocks.append(("Бычий", df['low'].iloc[i]))
            return blocks
        except Exception as e:
            logging.error(f"Ошибка обнаружения ордер блоков: {e}")
            return []