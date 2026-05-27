import pandas as pd


def xlsx_to_python(file_path: str) -> list:
    """Переводит xlsx формат данных в Python формат"""
    data = pd.read_excel(file_path)
    return data.to_dict("records")
