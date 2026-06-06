from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from src import utils


def test_normalize_excel_date_formats_dates_and_keeps_strings() -> None:
    assert utils.normalize_excel_date(date(2026, 6, 1), "%d.%m.%Y") == "01.06.2026"
    assert utils.normalize_excel_date(datetime(2026, 6, 1, 12, 30), "%d.%m.%Y %H:%M:%S") == "01.06.2026 12:30:00"
    assert utils.normalize_excel_date("01.06.2026", "%d.%m.%Y") == "01.06.2026"
    assert pd.isna(utils.normalize_excel_date(pd.NA, "%d.%m.%Y"))


def test_xlsx_to_python_converts_excel_dates_to_original_export_strings(tmp_path) -> None:
    file_path = tmp_path / "operations.xlsx"
    pd.DataFrame(
        [
            {
                "Дата операции": datetime(2026, 6, 1, 12, 30),
                "Дата платежа": date(2026, 6, 1),
                "Описание": "Покупка",
            }
        ]
    ).to_excel(file_path, index=False)

    result = utils.xlsx_to_python(str(file_path))

    assert result == [
        {"Дата операции": "01.06.2026 12:30:00", "Дата платежа": "01.06.2026", "Описание": "Покупка"}
    ]


def test_find_project_root_searches_parent_directories(tmp_path, monkeypatch) -> None:
    project_root = tmp_path / "project"
    nested = project_root / "src" / "package"
    nested.mkdir(parents=True)
    (project_root / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    monkeypatch.chdir(nested)

    assert utils.find_project_root() == project_root


def test_find_project_root_raises_when_marker_is_missing(tmp_path, monkeypatch) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)

    with pytest.raises(RuntimeError):
        utils.find_project_root(marker_files=("missing.marker",))


@pytest.mark.parametrize(
    ("range_type", "expected_start"),
    [
        ("M", datetime(2026, 6, 1)),
        ("W", datetime(2026, 6, 1)),
        ("Y", datetime(2026, 1, 1)),
        ("ALL", datetime(1900, 1, 1)),
    ],
)
def test_get_date_range_returns_expected_period(range_type: str, expected_start: datetime) -> None:
    start, end = utils.get_date_range("06.06.2026", range_type)

    assert start == expected_start
    assert end == datetime(2026, 6, 6, 23, 59, 59, 999999)


def test_get_date_range_rejects_unknown_range() -> None:
    with pytest.raises(ValueError, match="Неверный тип диапазона"):
        utils.get_date_range("06.06.2026", "BAD")
