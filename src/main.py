from datetime import datetime

import pandas as pd

from src.reports import spending_by_category, spending_by_weekday, spending_by_workday
from src.services import get_the_best_cashback_categories, investment_bank, simple_finder
from src.utils import df, transactions
from src.views import page_events_json, page_main_json


def pages(date: str, range_type: str = "M") -> None:
    """
    Принимает дату в формате DD.MM.YYYY, диапазон данных("W", "M", "Y", "ALL")
    и генерирует данные в JSON формате для главной страницы и старицы событий
    """

    page_main_json(datetime.strptime(date, "%d.%m.%Y"))
    page_events_json(date, range_type)


def services(data: list, year: int, month: int, limit: int, search_string: str) -> None:
    """Принимает данные транзакций, год и месяц для обработки и генерирует JSON файлы для сервисов"""

    get_the_best_cashback_categories(data, year, month)
    investment_bank("2026.05", transactions, limit)
    simple_finder(data, search_string)


def reports(dataframe: pd.DataFrame, category: str) -> None:
    """Генерирует отчёты"""

    spending_by_category(dataframe, category)
    spending_by_weekday(dataframe)
    spending_by_workday(dataframe)


if __name__ == "__main__":
    pages(date="31.05.2026", range_type="M")
    services(transactions, year=2026, month=6, limit=100, search_string="товар")
    reports(df, "Переводы")
