from datetime import datetime

from src.views import page_events_json, page_main_json


def main(date: str, range_type: str = "M"):
    """
    Принимает дату в формате DD.MM.YYYY, диапазон данных("W", "M", "Y", "ALL")
    и генерирует данные в JSON формате для главной страницы и старицы событий
    """

    page_main_json(datetime.strptime(date, "%d.%m.%Y"))
    page_events_json(date, range_type)


if __name__ == "__main__":
    main("23.12.2021", "M")
