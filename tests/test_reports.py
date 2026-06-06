from __future__ import annotations

from datetime import datetime

import pandas as pd

from src import reports


def _prepare_report_output_dir(tmp_path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    report_dir = tmp_path / "data" / "reports"
    project_dir.mkdir()
    report_dir.mkdir(parents=True)
    monkeypatch.chdir(project_dir)


def test_spending_by_category_sums_expenses_for_last_three_months(tmp_path, monkeypatch, sample_dataframe) -> None:
    _prepare_report_output_dir(tmp_path, monkeypatch)

    result = reports.spending_by_category(sample_dataframe.copy(), "Кафе", date="2026-06-30")

    assert result.to_dict("records") == [{"Категория": "Кафе", "Сумма расходов": 600.0}]
    assert list((tmp_path / "data" / "reports").glob("report_spending_by_category_*.json"))


def test_spending_by_weekday_returns_average_expense_by_russian_weekday(tmp_path, monkeypatch, sample_dataframe) -> None:
    _prepare_report_output_dir(tmp_path, monkeypatch)

    result = reports.spending_by_weekday(sample_dataframe.copy(), date="2026-06-30")

    assert result.to_dict("records") == [
        {"День недели": "Понедельник", "Средние траты": 100.0},
        {"День недели": "Вторник", "Средние траты": 200.0},
        {"День недели": "Среда", "Средние траты": 999.0},
        {"День недели": "Пятница", "Средние траты": 400.0},
        {"День недели": "Суббота", "Средние траты": 300.0},
    ]


def test_spending_by_workday_returns_workday_and_weekend_averages(tmp_path, monkeypatch, sample_dataframe) -> None:
    _prepare_report_output_dir(tmp_path, monkeypatch)

    result = reports.spending_by_workday(sample_dataframe.copy(), date="2026-06-30")

    assert result.to_dict("records") == [
        {"day_type": "workday", "avg_spending": 424.75},
        {"day_type": "weekend", "avg_spending": 300.0},
    ]


def test_report_to_file_decorator_keeps_non_dataframe_result() -> None:
    decorator = reports.report_to_file()

    @decorator
    def returns_dict() -> dict:
        return {"ok": True}

    assert returns_dict() == {"ok": True}


def test_report_to_file_decorator_writes_datetime_as_formatted_string(tmp_path) -> None:
    output_file = tmp_path / "report.json"
    decorator = reports.report_to_file(filename=str(output_file))

    @decorator
    def build_report() -> pd.DataFrame:
        return pd.DataFrame([{"created_at": datetime(2026, 6, 1, 12, 30), "value": 10}])

    result = build_report()

    assert result.loc[0, "created_at"] == "01.06.2026 12:30:00"
    assert '"created_at":"01.06.2026 12:30:00"' in output_file.read_text(encoding="utf-8")
