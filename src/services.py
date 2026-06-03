import json

from src.utils import find_project_root, transactions


def get_the_best_cashback_categories(data: list, year: int, month: int) -> None:
    """Возвращает список возможных кешбэков по категориям"""

    filtered_transactions = [
        transaction
        for transaction in data
        if transaction.get("Категория")
        and f"{month}.{year}" in transaction.get("Дата операции")
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


if __name__ == "__main__":
    get_the_best_cashback_categories(transactions, 2026, 5)
