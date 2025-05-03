import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score
import logging
import logging.handlers
import os
import joblib

# Настройка ротации логов
log_handler = logging.handlers.RotatingFileHandler('logs/trading.log', maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TradePredictor:
    def __init__(self, model_path='models/trade_model.pkl', data_path='data/trade_data.csv'):
        self.model_path = model_path
        self.data_path = data_path
        self.model = None
        if os.path.exists(model_path):
            self.load_model()
        else:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            logging.info("Создано новое ML-модель")

    def save_data(self, df, trade, success):
        try:
            features = {
                'rsi': df['RSI'].iloc[-1] if 'RSI' in df.columns else np.nan,
                'macd': df['MACD'].iloc[-1] if 'MACD' in df.columns else np.nan,
                'stoch_k': df['STOCH_k'].iloc[-1] if 'STOCH_k' in df.columns else np.nan,
                'atr': df['ATR'].iloc[-1] if 'ATR' in df.columns else np.nan,
                'sma20': df['SMA20'].iloc[-1] if 'SMA20' in df.columns else np.nan,
                'sma50': df['SMA50'].iloc[-1] if 'SMA50' in df.columns else np.nan,
                'success': 1 if success else 0
            }
            df_data = pd.DataFrame([features])
            if os.path.exists(self.data_path):
                df_data.to_csv(self.data_path, mode='a', header=False, index=False)
            else:
                df_data.to_csv(self.data_path, mode='w', header=True, index=False)
            logging.info(f"Сохранены данные для ML: {features}")
        except Exception as e:
            logging.error(f"Ошибка сохранения данных ML: {e}")

    def train_model(self):
        try:
            if not os.path.exists(self.data_path):
                logging.warning("Нет данных для обучения ML")
                return
            df = pd.read_csv(self.data_path)
            if len(df) < 10:
                logging.warning("Недостаточно данных для обучения ML")
                return
            if len(df[df['success'] == 1]) < 2 or len(df[df['success'] == 0]) < 2:
                logging.warning("Недостаточно данных для сбалансированного обучения")
                return
            X = df[['rsi', 'macd', 'stoch_k', 'atr', 'sma20', 'sma50']].fillna(0)
            y = df['success']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            self.model.fit(X_train, y_train)
            accuracy = accuracy_score(y_test, self.model.predict(X_test))
            scores = cross_val_score(self.model, X, y, cv=5)
            logging.info(f"ML-модель обучена, точность: {accuracy:.2f}, кросс-валидация: {scores.mean():.2f} ± {scores.std():.2f}")
            self.save_model()
        except Exception as e:
            logging.error(f"Ошибка обучения ML: {e}")

    def predict(self, df):
        try:
            features = {
                'rsi': df['RSI'].iloc[-1] if 'RSI' in df.columns else 0,
                'macd': df['MACD'].iloc[-1] if 'MACD' in df.columns else 0,
                'stoch_k': df['STOCH_k'].iloc[-1] if 'STOCH_k' in df.columns else 0,
                'atr': df['ATR'].iloc[-1] if 'ATR' in df.columns else 0,
                'sma20': df['SMA20'].iloc[-1] if 'SMA20' in df.columns else 0,
                'sma50': df['SMA50'].iloc[-1] if 'SMA50' in df.columns else 0
            }
            X = pd.DataFrame([features])
            prob = self.model.predict_proba(X)[0][1]
            logging.info(f"ML-предсказание: вероятность успеха={prob}")
            return prob > 0.6
        except Exception as e:
            logging.error(f"Ошибка ML-предсказания: {e}")
            return False

    def save_model(self):
        try:
            joblib.dump(self.model, self.model_path)
            logging.info(f"ML-модель сохранена в {self.model_path}")
        except Exception as e:
            logging.error(f"Ошибка сохранения ML-модели: {e}")

    def load_model(self):
        try:
            self.model = joblib.load(self.model_path)
            logging.info(f"ML-модель загружена из {self.model_path}")
        except Exception as e:
            logging.error(f"Ошибка загрузки ML-модели: {e}")