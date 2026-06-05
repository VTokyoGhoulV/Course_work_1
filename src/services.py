import json
from datetime import datetime

from src.utils import find_project_root


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
    Дату в формате YYYY.MM, информацию по транзакциям и лимит округления.
    Возвращает суммы возможных округлений за месяц
    """

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
