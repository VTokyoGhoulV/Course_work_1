import json
import os
from datetime import datetime
from typing import Iterator

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import find_project_root, get_date_range, xlsx_to_python

transactions = xlsx_to_python(f"{find_project_root()}/data/operations.xlsx")
load_dotenv()

with open(f"{find_project_root()}/data/user_settings.json", "r", encoding="utf-8") as file:
    user_settings = json.load(file)


# Набор функций для основной страницы
def hello() -> str:
    """Возвращает приветствие в зависимости от текущего времени"""

    if 0 <= datetime.now().hour < 6:
        return "Доброй ночи!"

    elif 6 <= datetime.now().hour < 12:
        return "Доброе утро!"

    elif 12 <= datetime.now().hour < 18:
        return "Добрый день!"

    else:
        return "Добрый вечер!"


def get_cards_info(date: datetime):
    """Возвращает данные по каждой карте в диапазоне дат с первого числа по указанное"""

    first_day = datetime(date.year, date.month, 1)

    cards = set()

    for transaction in transactions:

        if first_day <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= date and pd.notna(
            transaction["Номер карты"]
        ):

            cards.add(transaction["Номер карты"])

    for card in cards:

        spend_counter = 0

        for transaction in transactions:

            if (
                card == transaction["Номер карты"]
                and transaction["Сумма операции"] < 0
                and first_day <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= date
            ):

                spend_counter += transaction["Сумма операции"]

        yield {
            "last_digit": str(card)[-4:],
            "total_spend": round(abs(spend_counter)),
            "cashback": round(abs(spend_counter) / 100),
        }


def get_top_transactions(date: datetime) -> Iterator:
    """Возвращает топ 5 транзакций"""

    first_day = datetime(date.year, date.month, 1)
    filtered_transactions = []

    for transaction in transactions:

        if not transaction.get("Дата операции"):

            continue

        elif first_day <= datetime.strptime(transaction.get("Дата операции"), "%d.%m.%Y %H:%M:%S") <= date:
            filtered_transactions.append(transaction)

    for trans in sorted(filtered_transactions, key=lambda x: x["Сумма операции"], reverse=True)[:5]:
        yield {
            "date": trans["Дата операции"],
            "amount": abs(trans["Сумма операции"]),
            "type": "expense" if trans["Сумма операции"] < 0 else "income",
            "currency": trans["Валюта операции"],
            "category": trans["Категория"],
            "description": trans["Описание"],
        }


def get_currency_rates() -> Iterator:
    """Возвращает актуальный курс валют по настройкам пользователя"""

    api_key = os.getenv("CURRENCY_API")
    url = (
        f"https://api.apilayer.com/exchangerates_data/latest?symbols="
        f"{",".join(user_settings["user_currencies"])}&base=RUB"
    )
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

        yield {"stock": stock, "price": round(float(response.json()["close"]), 2), "currency": "USD"}


def page_main_json(date: datetime) -> None:
    """Возвращает данные по картам, валютам, акциям и топ транзакций клиента для главной страницы"""

    json_format = {
        "greetings": hello(),
        "cards": list(get_cards_info(date)),
        "top_transactions": list(get_top_transactions(date)),
        "currency_rates": list(get_currency_rates()),
        "stock_prices": list(get_stocks_info()),
    }

    with open(f"{find_project_root()}/data/main_page.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)


# Набор функций для ивент страницы
def get_expenses_by_category(start_date: datetime, end_date: datetime) -> list:
    """Возвращает расходы по категориям"""

    unique_categories = set()

    for transaction in transactions:
        if transaction.get("Категория"):
            unique_categories.add(transaction["Категория"])

    expenses = []

    for category in unique_categories:

        spend_counter = 0

        for transaction in transactions:

            if (
                transaction.get("Категория") == category
                and transaction.get("Сумма операции") < 0
                and start_date <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= end_date
            ):
                spend_counter += transaction.get("Сумма операции")

        expenses.append(
            {
                "category": category,
                "total_spend": round(abs(spend_counter)),
            }
        )

    sorted_data = sorted(expenses, key=lambda x: x["total_spend"], reverse=True)
    result = [{"category": x["category"], "total_spend": x["total_spend"]} for x in sorted_data[:7]]
    result.append({"category": "Остальное", "total_spend": sum(x["total_spend"] for x in sorted_data[7:])})

    return result


def transfers_and_cash(start_date: datetime, end_date: datetime) -> list:
    """Возвращает наличные транзакции и переводы за определенный срок"""

    filtered_transactions = [
        transaction
        for transaction in transactions
        if start_date <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= end_date
    ]

    transfers = [transaction for transaction in filtered_transactions if transaction.get("Категория") == "Переводы"]
    cash = [transaction for transaction in filtered_transactions if transaction.get("Категория") == "Наличные"]

    result = [
        {
            "category": "Переводы",
            "total_spend": abs(round(sum(transaction["Сумма операции"] for transaction in transfers))),
        },
        {
            "category": "Наличные",
            "total_spend": abs(round(sum(transaction["Сумма операции"] for transaction in cash))),
        },
    ]

    return result


def get_income_by_category(start_date: datetime, end_date: datetime) -> list:
    """Возвращает доходы по категориям"""

    unique_categories = set()

    for transaction in transactions:
        if transaction.get("Категория"):
            unique_categories.add(transaction["Категория"])

    income = []

    for category in unique_categories:

        income_counter = 0

        for transaction in transactions:

            if (
                transaction.get("Категория") == category
                and transaction.get("Сумма операции") > 0
                and start_date <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= end_date
            ):
                income_counter += transaction.get("Сумма операции")

        income.append(
            {
                "category": category,
                "total_income": round(abs(income_counter)),
            }
        )

    sorted_data = sorted(income, key=lambda x: x["total_income"], reverse=True)
    result = [
        {"category": x["category"], "total_income": x["total_income"]} for x in sorted_data if x["total_income"] > 0
    ]

    return result


def page_events_json(date: str, range_type="M"):
    """Возвращает данные по расходам по категориям для страницы событий"""

    start_date, end_date = get_date_range(date, range_type)

    total_amount_expenses = abs(
        round(sum(transaction["total_spend"] for transaction in get_expenses_by_category(start_date, end_date)))
    )

    total_amount_income = abs(
        round(sum(transaction["total_income"] for transaction in get_income_by_category(start_date, end_date)))
    )

    json_format = {
        "expenses": {
            "total_amount": total_amount_expenses,
            "main": get_expenses_by_category(start_date, end_date),
            "transfers_and_cash": transfers_and_cash(start_date, end_date),
        },
        "income": {"total_amount": total_amount_income, "main": get_income_by_category(start_date, end_date)},
        "currency_rates": list(get_currency_rates()),
        "stock_prices": list(get_stocks_info()),
    }

    with open(f"{find_project_root()}/data/events_page.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)
