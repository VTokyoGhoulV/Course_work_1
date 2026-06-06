from __future__ import annotations

import json

from src import services


def test_get_the_best_cashback_categories_writes_sorted_expenses(tmp_path, monkeypatch, sample_transactions) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(services, "find_project_root", lambda: tmp_path)

    services.get_the_best_cashback_categories(sample_transactions, 2026, 6)

    result = json.loads((data_dir / "cashback_categories.json").read_text(encoding="utf-8"))
    assert list(result) == ["Супермаркеты", "Кафе"]
    assert result == {"Супермаркеты": 11, "Кафе": 2}


def test_investment_bank_writes_possible_rounding_sum(tmp_path, monkeypatch, sample_transactions) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(services, "find_project_root", lambda: tmp_path)

    services.investment_bank("2026.06", sample_transactions, 100)

    result = json.loads((data_dir / "investment_bank.json").read_text(encoding="utf-8"))
    assert result == {"possible_investment": 128.0}


def test_investment_bank_with_invalid_limit_does_not_write_file(tmp_path, monkeypatch, sample_transactions) -> None:
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(services, "find_project_root", lambda: tmp_path)

    services.investment_bank("2026.06", sample_transactions, 25)

    assert not (tmp_path / "data" / "investment_bank.json").exists()


def test_simple_finder_searches_description_case_insensitive(tmp_path, monkeypatch, sample_transactions) -> None:
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(services, "find_project_root", lambda: tmp_path)

    services.simple_finder(sample_transactions, "покупка")

    result = json.loads((tmp_path / "data" / "simple_finder.json").read_text(encoding="utf-8"))
    assert [item["Описание"] for item in result] == ["Покупка продуктов", "Отмененная покупка +7 999 123-45-67"]


def test_mobile_phone_finder_writes_only_successful_phone_transactions(tmp_path, monkeypatch) -> None:
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(services, "find_project_root", lambda: tmp_path)
    data = [
        {"Описание": "Оплата +7 999 123-45-67", "Статус": "OK"},
        {"Описание": "Оплата +7 999 000 00 00", "Статус": "FAILED"},
        {"Описание": "Без телефона", "Статус": "OK"},
    ]

    services.mobile_phone_finder(data)

    result = json.loads((tmp_path / "data" / "mobile_phone_finder.json").read_text(encoding="utf-8"))
    assert result == [{"Описание": "Оплата +7 999 123-45-67", "Статус": "OK"}]


def test_individual_transaction_finder_writes_only_successful_person_transfers(tmp_path, monkeypatch) -> None:
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(services, "find_project_root", lambda: tmp_path)
    data = [
        {"Категория": "Переводы", "Описание": "Перевод Иванов И.", "Статус": "OK"},
        {"Категория": "Переводы", "Описание": "Перевод Иванов И.", "Статус": "FAILED"},
        {"Категория": "Кафе", "Описание": "Иванов И.", "Статус": "OK"},
    ]

    services.individual_transaction_finder(data)

    result = json.loads((tmp_path / "data" / "individual_transaction_finder.json").read_text(encoding="utf-8"))
    assert result == [{"Категория": "Переводы", "Описание": "Перевод Иванов И.", "Статус": "OK"}]
