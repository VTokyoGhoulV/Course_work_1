from datetime import datetime
from collections import Counter
import pandas as pd
import json

from src.utils import xlsx_to_python

transactions = xlsx_to_python("../data/operations.xlsx")


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


def get_cards_info():
    """Возвращает данные по каждой карте"""

    unique_cards = {
        transaction.get("Номер карты")
        for transaction in transactions
        if pd.notna(transaction.get("Номер карты"))
    }

    for card in unique_cards:

        spend_counter = 0

        for transaction in transactions:

            if (
                transaction.get("Номер карты") == card
                and transaction.get("Сумма операции") < 0
            ):

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
        key=lambda transaction: transaction.get("Сумма операции"),
        reverse=False,
    )[:5]:

        yield {
            "date": transaction.get("Дата"),
            "amount": round(transaction.get("Сумма операции"), 2),
            "category": transaction.get("Категория"),
            "description": transaction.get("Описание"),

        }


json_format = {
    "greetings": hello(),
    "cards": list(get_cards_info()),
    "top_transactions": list(get_top_transactions()),
}

with open ("../user_settings.json", 'w', encoding="utf-8") as json_file:
    json.dump(json_format, json_file, ensure_ascii=False, indent=2)