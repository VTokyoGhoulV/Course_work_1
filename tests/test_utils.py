from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from src import utils


def test_normalize_excel_date() -> None:
    assert utils.normalize_excel_date(date(2026, 6, 1), "%d.%m.%Y") == "01.06.2026"
    assert utils.normalize_excel_date(datetime(2026, 6, 1, 12, 30), "%d.%m.%Y %H:%M:%S") == "01.06.2026 12:30:00"
    assert utils.normalize_excel_date("готовая строка", "%d.%m.%Y") == "готовая строка"
    assert pd.isna(utils.normalize_excel_date(pd.NA, "%d.%m.%Y"))
    assert utils.normalize_excel_date(42, "%d.%m.%Y") == 42


def test_xlsx_to_python_normalizes_date_columns(tmp_path) -> None:
    path = tmp_path / "operations.xlsx"
    pd.DataFrame(
        [{"Дата операции": datetime(2026, 6, 1, 12, 30), "Дата платежа": date(2026, 6, 1), "Описание": "Покупка"}]
    ).to_excel(path, index=False)

    assert utils.xlsx_to_python(str(path)) == [
        {"Дата операции": "01.06.2026 12:30:00", "Дата платежа": "01.06.2026", "Описание": "Покупка"}
    ]


def test_find_project_root_searches_parents(tmp_path, monkeypatch) -> None:
    root = tmp_path / "project"
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]", encoding="utf-8")
    monkeypatch.chdir(nested)
    assert utils.find_project_root() == root


def test_find_project_root_raises_without_marker(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        utils.find_project_root(("missing",))


@pytest.mark.parametrize(
    ("range_type", "start"),
    [
        ("M", datetime(2026, 6, 1)),
        ("W", datetime(2026, 6, 15)),
        ("Y", datetime(2026, 1, 1)),
        ("ALL", datetime(1900, 1, 1)),
    ],
)
def test_get_date_range(range_type, start) -> None:
    actual_start, end = utils.get_date_range(datetime(2026, 6, 17, 8), range_type)
    assert actual_start == start
    assert end == datetime(2026, 6, 17, 23, 59, 59, 999999)


def test_get_date_range_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="Неверный тип диапазона"):
        utils.get_date_range(datetime(2026, 6, 1), "BAD")


def test_data_with_normalized_spacebars(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([{"Категория": "  Гаджеты\u00a0и техника  ", "Сумма": 1}]).to_excel(
        data_dir / "MyOperations.xlsx", index=False
    )
    monkeypatch.setattr(utils, "find_project_root", lambda: tmp_path)
    result = utils.data_with_normalized_spacebars()
    assert result.loc[0, "Категория"] == "Гаджеты и техника"
