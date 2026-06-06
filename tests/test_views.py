from __future__ import annotations

import json
from datetime import datetime

from src import views


def test_get_cards_info_aggregates_successful_card_spending(monkeypatch, sample_transactions) -> None:
    monkeypatch.setattr(views, "transactions", sample_transactions)

    result = sorted(views.get_cards_info(datetime(2026, 6, 30)), key=lambda item: item["last_digit"])

    assert result == [
        {"last_digit": "3456", "total_spend": 323, "cashback": 3},
        {"last_digit": "8888", "total_spend": 50, "cashback": 0},
    ]


def test_get_top_transactions_returns_top_five_by_absolute_amount(monkeypatch, sample_transactions) -> None:
    monkeypatch.setattr(views, "transactions", sample_transactions)

    result = list(views.get_top_transactions(datetime(2026, 6, 30, 23, 59, 59)))

    assert [item["amount"] for item in result] == [1000.0, 300.0, 200.0, 123.0, 50.0]
    assert result[0]["type"] == "income"
    assert result[1]["type"] == "expense"


def test_get_expenses_by_category_excludes_failed_and_investment_transactions(monkeypatch, sample_transactions) -> None:
    monkeypatch.setattr(views, "transactions", sample_transactions)

    result = views.get_expenses_by_category(datetime(2026, 6, 1), datetime(2026, 6, 30, 23, 59, 59))

    assert {item["category"]: item["total_spend"] for item in result} == {
        "Кафе": 200,
        "Супермаркеты": 123,
        "Переводы": 50,
        "Зарплата": 0,
        "Наличные": 0,
        "Остальное": 0,
    }


def test_transfers_and_cash_sums_selected_categories(monkeypatch, sample_transactions) -> None:
    monkeypatch.setattr(views, "transactions", sample_transactions)

    result = views.transfers_and_cash(datetime(2026, 5, 1), datetime(2026, 6, 30, 23, 59, 59))

    assert result == [
        {"category": "Переводы", "total_spend": 50},
        {"category": "Наличные", "total_spend": 80},
    ]


def test_get_income_by_category_excludes_internal_investment_withdrawals(monkeypatch) -> None:
    data = [
        {"Дата операции": "01.06.2026 10:00:00", "Категория": "Зарплата", "Сумма операции": 1000, "Описание": "Зарплата"},
        {
            "Дата операции": "02.06.2026 10:00:00",
            "Категория": "Инвестиции",
            "Сумма операции": 500,
            "Описание": "Вывод с Инвесткопилки",
        },
    ]
    monkeypatch.setattr(views, "transactions", data)

    result = views.get_income_by_category(datetime(2026, 6, 1), datetime(2026, 6, 30, 23, 59, 59))

    assert result == [{"category": "Зарплата", "total_income": 1000}]


def test_get_currency_rates_uses_fresh_cache(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "data" / "cache"
    cache_dir.mkdir(parents=True)
    today = datetime.now().strftime("%d.%m.%Y")
    (cache_dir / "currency_rates.json").write_text(
        json.dumps(
            {
                "date": today,
                "currency_rates": [
                    {"currency": "USD", "rate": 90},
                    {"currency": "EUR", "rate": 100},
                    {"currency": "GBP", "rate": 110},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_currencies": ["USD", "EUR"]})

    assert views.get_currency_rates() == [{"currency": "USD", "rate": 90}, {"currency": "EUR", "rate": 100}]


def test_get_stocks_info_returns_empty_without_api_key(tmp_path, monkeypatch) -> None:
    (tmp_path / "data" / "cache").mkdir(parents=True)
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_stocks": ["AAPL"]})
    monkeypatch.delenv("STOCK_API", raising=False)

    assert views.get_stocks_info() == []


def test_page_main_json_writes_expected_payload(tmp_path, monkeypatch) -> None:
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "hello", lambda: "Добрый день!")
    monkeypatch.setattr(views, "get_cards_info", lambda date: iter([{"last_digit": "3456"}]))
    monkeypatch.setattr(views, "get_top_transactions", lambda date: iter([{"amount": 100}]))
    monkeypatch.setattr(views, "get_currency_rates", lambda: [{"currency": "USD", "rate": 90}])
    monkeypatch.setattr(views, "get_stocks_info", lambda: [{"stock": "AAPL", "price": 200, "currency": "USD"}])

    views.page_main_json(datetime(2026, 6, 30))

    result = json.loads((tmp_path / "data" / "main_page.json").read_text(encoding="utf-8"))
    assert result == {
        "greetings": "Добрый день!",
        "cards": [{"last_digit": "3456"}],
        "top_transactions": [{"amount": 100}],
        "currency_rates": [{"currency": "USD", "rate": 90}],
        "stock_prices": [{"stock": "AAPL", "price": 200, "currency": "USD"}],
    }


def test_page_events_json_writes_expected_payload(tmp_path, monkeypatch) -> None:
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "get_expenses_by_category", lambda start, end: [{"category": "Кафе", "total_spend": 200}])
    monkeypatch.setattr(views, "transfers_and_cash", lambda start, end: [{"category": "Наличные", "total_spend": 80}])
    monkeypatch.setattr(views, "get_income_by_category", lambda start, end: [{"category": "Зарплата", "total_income": 1000}])
    monkeypatch.setattr(views, "get_currency_rates", lambda: [])
    monkeypatch.setattr(views, "get_stocks_info", lambda: [])

    views.page_events_json("30.06.2026", "M")

    result = json.loads((tmp_path / "data" / "events_page.json").read_text(encoding="utf-8"))
    assert result == {
        "expenses": {
            "total_amount": 200,
            "main": [{"category": "Кафе", "total_spend": 200}],
            "transfers_and_cash": [{"category": "Наличные", "total_spend": 80}],
        },
        "income": {"total_amount": 1000, "main": [{"category": "Зарплата", "total_income": 1000}]},
        "currency_rates": [],
        "stock_prices": [],
    }
