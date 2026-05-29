import json
import os
from datetime import datetime
from typing import Iterator

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import xlsx_to_python, find_project_root

transactions = xlsx_to_python(f"{find_project_root()}/data/operations.xlsx")
load_dotenv()

with open(f"{find_project_root()}/user_settings.json", "r", encoding="utf-8") as file:
    user_settings = json.load(file)


def hello(date: datetime) -> str:
    """Возвращает приветствие в зависимости от текущего времени"""

    if 0 <= date.hour < 6:
        return "Доброй ночи!"

    elif 6 <= date.hour < 12:
        return "Доброе утро!"

    elif 12 <= date.hour < 18:
        return "Добрый день!"

    else:
        return "Добрый вечер!"


def get_cards_info() -> Iterator:
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


def get_top_transactions() -> Iterator:
    """Возвращает топ 5 транзакций"""

    for transaction in sorted(
        transactions,
        key=lambda transaction_: abs(transaction_.get("Сумма операции", 0)),
        reverse=True,
    )[:5]:

        yield {
            "date": transaction.get("Дата"),
            "amount": abs(round(transaction.get("Сумма операции"), 2)),
            "category": transaction.get("Категория"),
            "description": transaction.get("Описание"),
        }


def get_currency_rates() -> Iterator:
    """Возвращает актуальный курс валют по настройкам пользователя"""

    api_key = os.getenv("CURRENCY_API")
    url = f"https://api.apilayer.com/exchangerates_data/latest?symbols={",".join(user_settings["user_currencies"])}&base=RUB"
    headers = {"apikey": api_key}

    request = requests.get(url, headers=headers)  # type: ignore

    for currency in user_settings["user_currencies"]:
        yield {"currency": currency, "rate": round(1 / request.json()["rates"][currency], 2)}


def get_stocks_info() -> Iterator:
    """Возвращает актуальную цену акций в USD по настройкам пользователя"""

    api_key = os.getenv("STOCK_API")

    for stock in user_settings["user_stocks"]:

        url = f"https://api.twelvedata.com/eod?symbol={stock}&apikey={api_key}"
        response = requests.get(url)

        yield {"stock": stock, "price": round(float(response.json()["close"]), 2)}


def get_user_bank_info_json(date: datetime) -> None:
    """Переводит Python формат данных в JSON"""

    json_format = {
        "greetings": hello(date),
        "cards": list(get_cards_info()),
        "top_transactions": list(get_top_transactions()),
        "currency_rates": list(get_currency_rates()),
        "stock_prices": list(get_stocks_info()),
    }

    with open(f"{find_project_root()}/test.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)
