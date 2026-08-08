from __future__ import annotations

from datetime import datetime

import pandas as pd

from src import reports


def _report_workspace(tmp_path, monkeypatch) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    (tmp_path / "data" / "reports").mkdir(parents=True)
    monkeypatch.chdir(workdir)


def _report_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Дата операции": datetime(2026, 6, 1, 10), "Категория": "Кафе", "Сумма операции": -100.0, "Статус": "OK"},
            {"Дата операции": datetime(2026, 6, 2, 10), "Категория": "Кафе", "Сумма операции": -200.0, "Статус": "OK"},
            {"Дата операции": datetime(2026, 6, 6, 10), "Категория": "Кафе", "Сумма операции": -300.0, "Статус": "OK"},
            {
                "Дата операции": datetime(2026, 6, 3, 10),
                "Категория": "Кафе",
                "Сумма операции": -999.0,
                "Статус": "FAILED",
            },
            {
                "Дата операции": datetime(2026, 5, 1, 10),
                "Категория": "Переводы",
                "Сумма операции": -400.0,
                "Статус": "OK",
            },
            {"Дата операции": datetime(2026, 4, 1, 10), "Категория": "Кафе", "Сумма операции": 500.0, "Статус": "OK"},
            {"Дата операции": datetime(2026, 2, 1, 10), "Категория": "Кафе", "Сумма операции": -777.0, "Статус": "OK"},
        ]
    )


def test_spending_by_category_filters_category_status_and_period(tmp_path, monkeypatch) -> None:
    _report_workspace(tmp_path, monkeypatch)
    result = reports.spending_by_category(_report_df(), "Кафе", date="2026-06-30")
    assert result.to_dict("records") == [{"Категория": "Кафе", "Сумма расходов": 600.0}]


def test_spending_by_weekday_returns_ordered_russian_weekdays(tmp_path, monkeypatch) -> None:
    _report_workspace(tmp_path, monkeypatch)
    result = reports.spending_by_weekday(_report_df(), date="2026-06-30")
    assert result.to_dict("records") == [
        {"День недели": "Понедельник", "Средние траты": 100.0},
        {"День недели": "Вторник", "Средние траты": 200.0},
        {"День недели": "Среда", "Средние траты": 999.0},
        {"День недели": "Пятница", "Средние траты": 400.0},
        {"День недели": "Суббота", "Средние траты": 300.0},
    ]


def test_spending_by_workday_returns_workday_then_weekend(tmp_path, monkeypatch) -> None:
    _report_workspace(tmp_path, monkeypatch)
    result = reports.spending_by_workday(_report_df(), date="2026-06-30")
    assert result.to_dict("records") == [
        {"day_type": "workday", "avg_spending": 424.75},
        {"day_type": "weekend", "avg_spending": 300.0},
    ]


def test_reports_use_current_time_when_date_is_omitted(tmp_path, monkeypatch) -> None:
    _report_workspace(tmp_path, monkeypatch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 6, 30)

    monkeypatch.setattr(reports, "datetime", FixedDatetime)
    assert reports.spending_by_category(_report_df(), "Кафе").loc[0, "Сумма расходов"] == 600
    assert not reports.spending_by_weekday(_report_df()).empty
    assert not reports.spending_by_workday(_report_df()).empty
