import json
import os
from collections import Counter
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import xlsx_to_python

transactions = xlsx_to_python("../data/operations.xlsx")

with open("../user_settings.json", "r", encoding="utf-8") as file:
    user_settings = json.load(file)

user_stocks = user_settings["user_stocks"]


def hello(time: datetime) -> str:
    """Возвращает приветствие в зависимости от текущего времени"""

    if 0 <= time.hour < 6:
        return "Доброй ночи!"

    elif 6 <= time.hour < 12:
        return "Доброе утро!"

    elif 12 <= time.hour < 18:
        return "Добрый день!"

    else:
        return "Добрый вечер!"


def get_cards_info():
    """Возвращает данные по каждой карте"""

    unique_cards = {
        transaction.get("Номер карты") for transaction in transactions if pd.notna(transaction.get("Номер карты"))
    }

    for card in unique_cards:

        spend_counter = 0

        for transaction in transactions:

            if transaction.get("Номер карты") == card and transaction.get("Сумма операции") < 0:

                spend_counter += transaction.get("Сумма операции")

        yield {
            "last_digit": card[-4:],
            "total_spend": round(spend_counter * -1, 2),
            "cashback": round(spend_counter / 100 * -1, 2),
        }


def get_top_transactions():
    """Возвращает топ 5 транзакций"""

    for transaction in sorted(
        transactions,
        key=lambda transaction_: abs(transaction_.get("Сумма операции", 0)),
        reverse=True,
    )[:5]:

        yield {
            "date": transaction.get("Дата"),
            "amount": round(transaction.get("Сумма операции"), 2),
            "category": transaction.get("Категория"),
            "description": transaction.get("Описание"),
        }


def get_currency_rates(currency: list):
    """Возвращает актуальный курс валют по настройкам пользователя"""

    load_dotenv()
    api_key = os.getenv("API_KEY")
    url = f"https://api.apilayer.com/exchangerates_data/latest?symbols={",".join(currency)}&base=RUB"
    headers = {"apikey": api_key}

    request = requests.get(url, headers=headers)  # type: ignore

    for currency in user_settings["user_currencies"]:
        yield {"currency": currency, "rate": round(1 / request.json()["rates"][currency], 2)}


def get_stocks_info():
    """Возвращает актуальную цену акций по настройкам пользователя"""
    pass


def python_to_json():
    """Переводит Python формат данных в JSON"""

    json_format = {
        "greetings": hello(datetime.now()),
        "cards": list(get_cards_info()),
        "top_transactions": list(get_top_transactions()),
        "currency_rates": list(get_currency_rates(user_settings["user_currencies"])),
    }

    with open("../test.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)
