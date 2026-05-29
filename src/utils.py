import pandas as pd
from pathlib import Path


def xlsx_to_python(file_path: str) -> list:
    """Переводит xlsx формат данных в Python формат"""
    data = pd.read_excel(file_path)
    return data.to_dict("records")


def find_project_root(marker_files=('pyproject.toml', '.git', 'requirements.txt')) -> Path:
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