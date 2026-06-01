from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


def xlsx_to_python(file_path: str) -> list:
    """Переводит xlsx формат данных в Python формат"""
    data = pd.read_excel(file_path)
    return data.to_dict("records")


def find_project_root(marker_files=("pyproject.toml", ".git", "requirements.txt")) -> Path:
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


def get_date_range(date_str: str, range_type="M"):
    end_date = datetime.strptime(date_str, "%d.%m.%Y")

    if range_type == "M":
        start_date = end_date.replace(day=1)
    elif range_type == "W":
        start_date = end_date - timedelta(days=end_date.weekday())
    elif range_type == "Y":
        start_date = end_date.replace(month=1, day=1)
    elif range_type == "ALL":
        start_date = datetime(1900, 1, 1)  # пример
    else:
        raise ValueError("Неверный тип диапазона")

    return start_date, end_date
