import json
from datetime import datetime
from typing import Optional

import pandas as pd

from utils import get_date_range, find_project_root


def get_the_best_cashback_categories(transactions: pd.DataFrame, date: Optional[datetime] = None) -> None:

    if date is None:
        first_day, last_day = get_date_range(datetime.today())
    else:
        first_day, last_day = get_date_range(date)

    operation_dates = pd.to_datetime(transactions["Дата операции"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    period_mask = operation_dates.between(first_day, last_day) & transactions["Номер карты"].notna()

    mask = (
        period_mask
        & ~transactions["Категория"].isin(["Переводы", "Наличные", "Услуги банка"])
        & transactions["Сумма операции"].lt(0)
        & transactions["Статус"].eq("OK")
    )

    categories_spend = (
        transactions.loc[mask]
        .groupby("Категория")["Сумма операции"]
        .sum()
        .abs()
        .div(100)
        .round()
        .sort_values(ascending=False)
    )

    result = {category: cashback for category, cashback in categories_spend.items()}

    with open(f"{find_project_root()}/data/services/cashback_categories.json", "w", encoding="utf-8") as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=2)


def investment_bank(date: datetime, transactions: pd.DataFrame, limit: int) -> None:

    if limit not in [10, 50, 100]:
        raise ValueError("Лимит должен быть 10, 50 или 100")

    first_day, last_day = get_date_range(date)

    operation_dates = pd.to_datetime(transactions["Дата операции"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    period_mask = operation_dates.between(first_day, last_day) & transactions["Номер карты"].notna()

    mask = period_mask & transactions["Сумма операции"].lt(0) & transactions["Статус"].eq("OK")

    investment_counter = transactions.loc[mask, "Сумма операции"].mod(limit).sum().round()

    result = {"possible_investment": round(investment_counter)}

    with open(f"{find_project_root()}/data/services/investment_bank.json", "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


def simple_finder(transactions: pd.DataFrame, search_string: str) -> None:

    mask = transactions["Описание"].str.contains(search_string, case=False, na=False, regex=False)

    filtered = transactions.loc[mask].copy()

    filtered = filtered.astype(object).where(filtered.notna(), None)

    result = filtered.to_dict("records")

    with open(f"{find_project_root()}/data/services/simple_finder.json", "w", encoding="utf-8") as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=2, default=str)


def mobile_phone_finder(transactions: pd.DataFrame) -> None:

    phone_pattern = r"\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"

    mask = transactions["Описание"].str.contains(phone_pattern, case=False, na=False, regex=True)

    filtered = transactions.loc[mask].copy()

    filtered = filtered.astype(object).where(filtered.notna(), None)

    result = filtered.to_dict("records")

    with open(f"{find_project_root()}/data/services/mobile_phone_finder.json", "w", encoding="utf-8") as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=2, default=str)


def individual_transaction_finder(transactions: pd.DataFrame) -> None:

    name_pattern = r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\."

    mask = transactions["Описание"].str.contains(name_pattern, case=False, na=False, regex=True)

    filtered = transactions.loc[mask].copy()

    filtered = filtered.astype(object).where(filtered.notna(), None)

    result = filtered.to_dict("records")

    with open(
        f"{find_project_root()}/data/services/individual_transaction_finder.json",
        "w",
        encoding="utf-8",
    ) as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=2, default=str)
