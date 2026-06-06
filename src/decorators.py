import logging
from datetime import datetime
from functools import wraps

import pandas as pd

from src.utils import find_project_root

report_to_file_logger = logging.getLogger("report_to_file")

file_handler = logging.FileHandler(f"{find_project_root()}/logs/report_to_file.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

report_to_file_logger.addHandler(file_handler)


def report_to_file(filename=None):  # type: ignore
    """
    Декоратор для функций отчётов, возвращающих DataFrame.
    Сохраняет результат в CSV-файл.
    """

    def decorator(func):  # type: ignore

        @wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore

            result = func(*args, **kwargs)

            if not isinstance(result, pd.DataFrame):

                report_to_file_logger.warning(
                    "Предупреждение: результат не является DataFrame, сохранение может быть некорректным"
                )

                return result

            # Преобразуем все столбцы с типом datetime в строки нужного формата
            result = result.copy()
            for col in result.select_dtypes(include=["datetime64[ns]", "datetime64"]).columns:
                result[col] = result[col].dt.strftime("%d.%m.%Y %H:%M:%S")

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d")
                out_filename = f"../data/reports/report_{func.__name__}_{timestamp}.json"
            else:
                out_filename = filename

            # Теперь to_json не будет преобразовывать даты в timestamps
            result.to_json(out_filename, orient="records", force_ascii=False, indent=2)
            report_to_file_logger.info(f"Отчёт сохранён в файл: {out_filename}")

            return result

        return wrapper

    return decorator
