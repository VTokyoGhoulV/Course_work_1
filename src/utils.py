import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


def normalize_excel_date(value: object, date_format: str) -> object:
    """Приводит настоящие Excel-даты к строковому формату исходной выгрузки."""
    if pd.isna(value) or isinstance(value, str):  # type: ignore
        return value
    if isinstance(value, date):
        return value.strftime(date_format)
    return value


def xlsx_to_python(file_path: str) -> list:
    """Переводит xlsx формат данных в Python формат"""
    data = pd.read_excel(file_path)

    date_columns = {
        "Дата операции": "%d.%m.%Y %H:%M:%S",
        "Дата платежа": "%d.%m.%Y",
    }
    for column, date_format in date_columns.items():
        if column in data.columns:
            data[column] = data[column].map(lambda value: normalize_excel_date(value, date_format))

    return data.to_dict("records")


def find_project_root(marker_files: str | tuple = ("pyproject.toml", ".git", "requirements.txt")) -> Path:
    """
    Ищет корневую директорию проекта, поднимаясь по дереву папок,
    пока не найдет один из маркерных файлов/папок.
    """
    current_path = Path.cwd()  # Начинаем с текущей рабочей директории
    for parent in [current_path] + list(current_path.parents):
        for marker in marker_files:
            if (parent / marker).exists():
                return parent
    raise RuntimeError("Не удалось найти корень проекта. Убедитесь, что один из маркерных файлов присутствует.")


def get_date_range(
    date: datetime,
    range_type: str = "M",
) -> tuple[datetime, datetime]:
    """Возвращает начало и конец выбранного периода."""

    end_date = date

    if range_type == "M":
        start_date = end_date.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    elif range_type == "W":
        start_date = (end_date - timedelta(days=end_date.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    elif range_type == "Y":
        start_date = end_date.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    elif range_type == "ALL":
        start_date = datetime(1900, 1, 1)
    else:
        raise ValueError("Неверный тип диапазона")

    end_date = end_date.replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )

    return start_date, end_date


def data_with_normalized_spacebars():

    transactions = pd.read_excel(f"{find_project_root()}/data/MyOperations.xlsx")

    text_columns = transactions.select_dtypes(include=["object", "string"]).columns

    transactions[text_columns] = transactions[text_columns].apply(
        lambda column: (column.str.replace("\u00a0", " ", regex=False).str.strip())
    )

    return transactions


with open(f"{find_project_root()}/data/user_settings.json", "r", encoding="utf-8") as file:
    user_settings = json.load(file)
