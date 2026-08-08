from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import pytest

import services


def _data_dir(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(services, "find_project_root", lambda: tmp_path)
    return tmp_path / "data"


def test_best_cashback_categories_filters_and_sorts(tmp_path, monkeypatch, transactions_df) -> None:
    data_dir = _data_dir(tmp_path, monkeypatch)
    services.get_the_best_cashback_categories(transactions_df, datetime(2026, 6, 30))
    result = json.loads((data_dir / "cashback_categories.json").read_text(encoding="utf-8"))
    assert result == {"Супермаркеты": 11.0, "Кафе": 2.0}


def test_best_cashback_categories_uses_today_by_default(tmp_path, monkeypatch, transactions_df) -> None:
    data_dir = _data_dir(tmp_path, monkeypatch)

    class FixedDatetime(datetime):
        @classmethod
        def today(cls):
            return cls(2026, 6, 30)

    monkeypatch.setattr(services, "datetime", FixedDatetime)
    services.get_the_best_cashback_categories(transactions_df)
    assert (data_dir / "cashback_categories.json").exists()


@pytest.mark.parametrize("limit", [10, 50, 100])
def test_investment_bank_supports_valid_limits(tmp_path, monkeypatch, transactions_df, limit) -> None:
    data_dir = _data_dir(tmp_path, monkeypatch)
    services.investment_bank(datetime(2026, 6, 30), transactions_df, limit)
    result = json.loads((data_dir / "investment_bank.json").read_text(encoding="utf-8"))
    expected = round(transactions_df.loc[[0, 1, 2, 4, 6], "Сумма операции"].mod(limit).sum().round())
    assert result == {"possible_investment": expected}


def test_investment_bank_rejects_invalid_limit(transactions_df) -> None:
    with pytest.raises(ValueError, match="10, 50 или 100"):
        services.investment_bank(datetime(2026, 6, 30), transactions_df, 25)


def test_simple_finder_is_case_insensitive_and_serializes_null(tmp_path, monkeypatch, transactions_df) -> None:
    data_dir = _data_dir(tmp_path, monkeypatch)
    services.simple_finder(transactions_df, "ЗАРПЛАТА")
    result = json.loads((data_dir / "simple_finder.json").read_text(encoding="utf-8"))
    assert len(result) == 1
    assert result[0]["Описание"] == "Зарплата"
    assert result[0]["Номер карты"] is None


def test_mobile_phone_finder_matches_supported_format(tmp_path, monkeypatch, transactions_df) -> None:
    data_dir = _data_dir(tmp_path, monkeypatch)
    services.mobile_phone_finder(transactions_df)
    result = json.loads((data_dir / "mobile_phone_finder.json").read_text(encoding="utf-8"))
    assert [row["Описание"] for row in result] == ["Обед +7 (999) 123-45-67"]


def test_individual_transaction_finder_matches_name(tmp_path, monkeypatch, transactions_df) -> None:
    data_dir = _data_dir(tmp_path, monkeypatch)
    services.individual_transaction_finder(transactions_df)
    result = json.loads((data_dir / "individual_transaction_finder.json").read_text(encoding="utf-8"))
    assert [row["Описание"] for row in result] == ["Иванов И."]
