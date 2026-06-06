import json
import logging
import re
from datetime import datetime

from src.utils import find_project_root, transactions

investment_bank_logger = logging.getLogger("investment_bank")

file_handler = logging.FileHandler(f"{find_project_root()}/logs/investment_bank.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

investment_bank_logger.addHandler(file_handler)


def get_the_best_cashback_categories(data: list, year: int, month_: int) -> None:
    """Возвращает список возможных кешбэков по категориям"""

    filtered_transactions = [
        transaction
        for transaction in data
        if transaction.get("Категория")
        and f"{month_}.{year}" in transaction.get("Дата операции")
        and transaction.get("Категория") not in ["Переводы", "Наличные", "Услуги банка"]
        and transaction.get("Сумма операции") < 0
        and transaction.get("Статус") != "FAILED"
    ]

    unique_categories = set(transaction.get("Категория") for transaction in filtered_transactions)

    expenses = {
        category: abs(
            round(sum(t["Сумма операции"] for t in filtered_transactions if t.get("Категория") == category) / 100)
        )
        for category in unique_categories
    }

    sorted_data = dict(sorted(expenses.items(), key=lambda item: item[1], reverse=True))

    with open(f"{find_project_root()}/data/cashback_categories.json", "w", encoding="utf-8") as json_file:
        json.dump(sorted_data, json_file, ensure_ascii=False, indent=2)


def investment_bank(date: str, transaction_data: list[dict], limit: int) -> None:
    """
    Дату в формате YYYY.MM, информацию по транзакциям и лимит округления(10, 50, 100).
    Возвращает суммы возможных округлений за месяц
    """
    try:
        if limit not in [10, 50, 100]:
            raise ValueError("Некорректный лимит округления")

        target_date = datetime.strptime(date, "%Y.%m")

        filtered_transactions = [
            transaction
            for transaction in transaction_data
            if (operation_date := transaction.get("Дата операции"))
            and (parsed_date := datetime.strptime(operation_date, "%d.%m.%Y %H:%M:%S"))
            and parsed_date.year == target_date.year
            and parsed_date.month == target_date.month
            and transaction.get("Сумма операции") < 0
            and transaction.get("Статус") != "FAILED"
        ]

        investment_counter = 0
        for transaction in filtered_transactions:

            if transaction.get("Сумма операции") % limit > 0:

                investment_counter += transaction.get("Сумма операции") % limit

        with open(f"{find_project_root()}/data/investment_bank.json", "w", encoding="utf-8") as file:
            json.dump({"possible_investment": round(investment_counter, 2)}, file, ensure_ascii=False, indent=2)

    except ValueError as e:
        investment_bank_logger.error(e)


# 3 вопрос
def simple_finder(data: list, search_string: str) -> None:
    """
    Поиск по строке в данных (без учета регистра)
    """
    search_lower = search_string.lower()
    filtered_transactions = [
        transaction for transaction in data if search_lower in transaction.get("Описание", "").lower()
    ]

    with open(f"{find_project_root()}/data/simple_finder.json", "w", encoding="utf-8") as json_file:
        json.dump(filtered_transactions, json_file, ensure_ascii=False, indent=2)


# 3 вопрос
def mobile_phone_finder(data: list) -> None:
    """Генерирует JSON файл с транзакциями в описании которых есть номер телефона"""

    phone_pattern = re.compile(r"\+7[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")

    filtered__transactions = [
        transaction
        for transaction in data
        if phone_pattern.search(transaction.get("Описание", "")) and transaction.get("Статус") != "FAILED"
    ]

    with open(f"{find_project_root()}/data/mobile_phone_finder.json", "w", encoding="utf-8") as json_file:
        json.dump(filtered__transactions, json_file, ensure_ascii=False, indent=2)


# 3 вопрос
def individual_transaction_finder(data: list) -> None:
    """Генерирует JSON файл с переводами физ лицами"""

    name_pattern = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.")

    filtered_transactions = [
        transaction
        for transaction in data
        if transaction.get("Категория") == "Переводы"
        and name_pattern.search(transaction.get("Описание", ""))
        and transaction.get("Статус") != "FAILED"
    ]

    with open(f"{find_project_root()}/data/individual_transaction_finder.json", "w", encoding="utf-8") as json_file:
        json.dump(filtered_transactions, json_file, ensure_ascii=False, indent=2)
