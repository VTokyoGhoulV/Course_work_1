from datetime import datetime

from src.services import get_the_best_cashback_categories
from src.utils import transactions
from src.views import page_events_json, page_main_json


def pages(date: str, range_type: str = "M") -> None:
    """
    Принимает дату в формате DD.MM.YYYY, диапазон данных("W", "M", "Y", "ALL")
    и генерирует данные в JSON формате для главной страницы и старицы событий
    """

    page_main_json(datetime.strptime(date, "%d.%m.%Y"))
    page_events_json(date, range_type)


def services(data: list, year: int, month: int) -> None:
    """Принимает данные транзакций, год и месяц для обработки и генерирует JSON файлы для сервисов"""

    get_the_best_cashback_categories(data, year, month)


if __name__ == "__main__":
    pages("31.05.2026", "M")
    services(transactions, 2026, 5)
