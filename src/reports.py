from datetime import datetime
from typing import Optional

import pandas as pd

from src.decorators import report_to_file
from src.utils import df


@report_to_file()
def spending_by_category(
    transactions: pd.DataFrame, category: str, date: Optional[pd.Timestamp | str] = None
) -> pd.DataFrame:
    """Подсчет расходов по категории за 3 месяца"""

    if date is None:

        end_date = datetime.now()

    else:

        end_date = pd.to_datetime(date)

    start_date = end_date - pd.DateOffset(months=3)

    transactions["Дата операции"] = pd.to_datetime(transactions["Дата операции"])

    mask = (
        (transactions["Категория"] == category)
        & (transactions["Сумма операции"] < 0)
        & (transactions["Статус"] != "FAILED")
        & (transactions["Дата операции"] >= start_date)
        & (transactions["Дата операции"] <= end_date)
    )

    filtered = transactions.loc[mask]

    total_spent = abs(filtered["Сумма операции"].sum())

    return pd.DataFrame(
        {"Категория": [category], "Сумма расходов": [total_spent]}
    )


@report_to_file()  # type: ignore
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """Подсчет расходов по дням недели за 3 месяца (названия дней на русском)"""
    if date is None:

        end_date = datetime.now()

    else:

        end_date = pd.to_datetime(date)

    start_date = end_date - pd.DateOffset(months=3)

    transactions["Дата операции"] = pd.to_datetime(transactions["Дата операции"])

    mask_date = (transactions["Дата операции"] >= start_date) & (transactions["Дата операции"] <= end_date)
    mask_expense = transactions["Сумма операции"] < 0

    df_filtered = transactions[mask_date & mask_expense].copy()

    eng_days = df_filtered["Дата операции"].dt.day_name()

    ru_days = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }
    df_filtered["День недели"] = eng_days.map(ru_days)

    avg_spending = df_filtered.groupby("День недели")["Сумма операции"].mean().abs().round(2)
    weekday_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    avg_spending = avg_spending.reindex(weekday_order).dropna()

    return avg_spending.reset_index(name="Средние траты")


@report_to_file()  # type: ignore
def spending_by_workday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """Подсчет средних расходов в рабочие и не рабочие дни за последние 3 месяца"""

    if date is None:
        end_date = datetime.now()
    else:
        end_date = pd.to_datetime(date)

    start_date = end_date - pd.DateOffset(months=3)

    transactions["Дата операции"] = pd.to_datetime(transactions["Дата операции"])
    mask_date = (transactions["Дата операции"] >= start_date) & (transactions["Дата операции"] <= end_date)
    mask_expense = transactions["Сумма операции"] < 0

    df_filtered = transactions[mask_date & mask_expense].copy()

    df_filtered["day_of_week"] = df_filtered["Дата операции"].dt.dayofweek
    df_filtered["day_type"] = df_filtered["day_of_week"].apply(lambda x: "workday" if x < 5 else "weekend")

    df_filtered["spending_abs"] = df_filtered["Сумма операции"].abs()

    result = df_filtered.groupby("day_type")["spending_abs"].mean().reset_index().round(2)
    result.rename(columns={"spending_abs": "avg_spending"}, inplace=True)

    result["day_type"] = pd.Categorical(result["day_type"], categories=["workday", "weekend"], ordered=True)
    result = result.sort_values("day_type").reset_index(drop=True)

    return result
