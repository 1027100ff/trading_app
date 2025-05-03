import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

class History:
    @staticmethod
    def update_history(ax, canvas, trades):
        """Обновление гистограммы с прибылью по дням месяца."""
        try:
            if not trades:
                ax.clear()
                ax.set_facecolor('#2b2b2b')
                ax.tick_params(colors='#fff')
                ax.set_title("История прибыли", color='#fff')
                canvas.draw()
                return

            # Преобразуем trades в DataFrame
            df_trades = pd.DataFrame(trades)
            df_trades['timestamp'] = pd.to_datetime(df_trades.get('timestamp', [datetime.now() for _ in range(len(trades))]))

            # Извлекаем день месяца
            df_trades['day'] = df_trades['timestamp'].dt.day

            # Рассчитываем прибыль для каждой сделки
            df_trades['profit'] = df_trades.apply(
                lambda row: row['tp'] - row['entry'] if row['position'] == "Лонг" else row['entry'] - row['tp'],
                axis=1
            )

            # Группируем по дню и суммируем прибыль
            daily_profit = df_trades.groupby('day')['profit'].sum().reset_index()

            # Очищаем график
            ax.clear()

            # Создаём гистограмму
            ax.bar(daily_profit['day'], daily_profit['profit'], color='#007bff', edgecolor='#fff')

            # Настраиваем оси
            current_month = datetime.now().month
            current_year = datetime.now().year
            import calendar
            _, num_days = calendar.monthrange(current_year, current_month)
            ax.set_xticks(range(1, num_days + 1))  # Дни месяца
            ax.set_xlabel("День месяца", color='#fff')
            ax.set_ylabel("Суммарная прибыль (руб.)", color='#fff')
            ax.set_title(f"Прибыль за {calendar.month_name[current_month]} {current_year}", color='#fff')
            ax.set_facecolor('#2b2b2b')
            ax.tick_params(colors='#fff')
            ax.grid(True, color='#444', linestyle='--', alpha=0.5)

            # Обновляем канвас
            canvas.draw()

        except Exception as e:
            print(f"Ошибка обновления истории: {e}")