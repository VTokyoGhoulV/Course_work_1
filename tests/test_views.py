from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import pytest
import requests

import views


class FakeResponse:
    def __init__(self, payload, *, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(1, "Доброй ночи!"), (8, "Доброе утро!"), (14, "Добрый день!"), (20, "Добрый вечер!")],
)
def test_greetings_by_hour(monkeypatch, hour, expected) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 6, 1, hour)

    monkeypatch.setattr(views, "datetime", FixedDatetime)
    assert views.greetings() == expected


def test_get_cards_info_aggregates_each_card(transactions_df) -> None:
    result = views.get_cards_info(datetime(2026, 6, 30), transactions_df)
    assert result == [
        {"last_digit": "1111", "total_spend": 323, "cashback": 3},
        {"last_digit": "2222", "total_spend": 450, "cashback": 4},
    ]


def test_get_top_transactions_sorts_by_absolute_amount(transactions_df) -> None:
    result = views.get_top_transactions(datetime(2026, 6, 30), transactions_df)
    assert [row["amount"] for row in result] == [1000.0, 400.0, 200.0, 123.0, 91.0]
    assert result[0]["type"] == "income"
    assert result[1]["type"] == "expense"


def test_expense_income_and_transfer_aggregations(transactions_df) -> None:
    date = datetime(2026, 6, 30)
    assert views.get_expenses_by_category(date, transactions_df, "M") == [
        {"category": "Кафе", "amount": 200},
        {"category": "Супермаркеты", "amount": 123},
        {"category": "Наличные", "amount": 80},
        {"category": "Переводы", "amount": 50},
    ]
    assert views.transfers_and_cash(date, transactions_df, "M") == [
        {"category": "Переводы", "amount": 50},
        {"category": "Наличные", "amount": 80},
    ]
    assert views.get_income_by_category(date, transactions_df, "M") == [
        {"category": "Переводы", "amount": 1000},
        {"category": "Бонусы", "amount": 25},
    ]


def test_currency_rates_uses_fresh_cache(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "data" / "cache"
    cache.mkdir(parents=True)
    today = datetime.now().strftime("%d.%m.%Y")
    (cache / "currency_rates.json").write_text(
        json.dumps(
            {"date": today, "currency_rates": [{"currency": "USD", "rate": 90}, {"currency": "EUR", "rate": 100}]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_currencies": ["USD"]})
    monkeypatch.setattr(views.requests, "get", lambda *args, **kwargs: pytest.fail("API should not be called"))
    assert views.get_currency_rates() == [{"currency": "USD", "rate": 90}]


def test_currency_rates_fetches_and_writes_cache(tmp_path, monkeypatch) -> None:
    (tmp_path / "data" / "cache").mkdir(parents=True)
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_currencies": ["USD", "EUR"]})
    monkeypatch.setenv("CURRENCY_API", "key")
    monkeypatch.setattr(
        views.requests, "get", lambda *args, **kwargs: FakeResponse({"rates": {"USD": 0.01, "EUR": 0.02}})
    )
    assert views.get_currency_rates() == [{"currency": "USD", "rate": 100.0}, {"currency": "EUR", "rate": 50.0}]
    assert (tmp_path / "data" / "cache" / "currency_rates.json").exists()


def test_currency_rates_merges_same_day_partial_cache(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "data" / "cache"
    cache.mkdir(parents=True)
    today = datetime.now().strftime("%d.%m.%Y")
    (cache / "currency_rates.json").write_text(
        json.dumps({"date": today, "currency_rates": [{"currency": "USD", "rate": 90}]}), encoding="utf-8"
    )
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_currencies": ["USD", "EUR"]})
    monkeypatch.setenv("CURRENCY_API", "key")
    monkeypatch.setattr(
        views.requests, "get", lambda *args, **kwargs: FakeResponse({"rates": {"USD": 0.01, "EUR": 0.02}})
    )
    assert views.get_currency_rates() == [{"currency": "USD", "rate": 100.0}, {"currency": "EUR", "rate": 50.0}]


def test_currency_rates_returns_empty_without_key(tmp_path, monkeypatch) -> None:
    (tmp_path / "data" / "cache").mkdir(parents=True)
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_currencies": ["USD"]})
    monkeypatch.delenv("CURRENCY_API", raising=False)
    assert views.get_currency_rates() == []


def test_currency_rates_handles_request_error(tmp_path, monkeypatch) -> None:
    (tmp_path / "data" / "cache").mkdir(parents=True)
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_currencies": ["USD"]})
    monkeypatch.setenv("CURRENCY_API", "key")
    monkeypatch.setattr(
        views.requests, "get", lambda *args, **kwargs: FakeResponse({}, error=requests.RequestException("boom"))
    )
    assert views.get_currency_rates() == []


def test_stocks_use_cache_fetch_and_skip_failed_symbol(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "data" / "cache"
    cache.mkdir(parents=True)
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_stocks": ["AAPL", "BAD"]})
    monkeypatch.setenv("STOCK_API", "key")

    def fake_get(url, **kwargs):
        if "AAPL" in url:
            return FakeResponse({"close": "201.235"})
        return FakeResponse({}, error=requests.RequestException("bad symbol"))

    monkeypatch.setattr(views.requests, "get", fake_get)
    assert views.get_stocks_info() == [{"stock": "AAPL", "price": 201.24, "currency": "USD"}]
    assert (cache / "stocks_rates.json").exists()


def test_stocks_use_fresh_cache(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "data" / "cache"
    cache.mkdir(parents=True)
    today = datetime.now().strftime("%d.%m.%Y")
    expected = [{"stock": "AAPL", "price": 200, "currency": "USD"}]
    (cache / "stocks_rates.json").write_text(json.dumps({"date": today, "stocks_rates": expected}), encoding="utf-8")
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_stocks": ["AAPL"]})
    monkeypatch.setattr(views.requests, "get", lambda *args, **kwargs: pytest.fail("API should not be called"))
    assert views.get_stocks_info() == expected


def test_stocks_merge_partial_same_day_cache(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "data" / "cache"
    cache.mkdir(parents=True)
    today = datetime.now().strftime("%d.%m.%Y")
    (cache / "stocks_rates.json").write_text(
        json.dumps({"date": today, "stocks_rates": [{"stock": "OLD", "price": 10, "currency": "USD"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_stocks": ["AAPL"]})
    monkeypatch.setenv("STOCK_API", "key")
    monkeypatch.setattr(views.requests, "get", lambda *args, **kwargs: FakeResponse({"close": "201"}))
    assert views.get_stocks_info() == [{"stock": "AAPL", "price": 201.0, "currency": "USD"}]


def test_expenses_add_other_after_seven_categories() -> None:
    frame = pd.DataFrame(
        [
            {
                "Дата операции": datetime(2026, 6, day),
                "Номер карты": "*1111",
                "Статус": "OK",
                "Сумма операции": -amount,
                "Валюта операции": "RUB",
                "Категория": f"Категория {day}",
                "Описание": "Покупка",
            }
            for day, amount in enumerate(range(10, 90, 10), start=1)
        ]
    )
    result = views.get_expenses_by_category(datetime(2026, 6, 30), frame, "M")
    assert result[-1] == {"category": "Остальное", "amount": 10}


def test_stocks_return_empty_without_key(tmp_path, monkeypatch) -> None:
    (tmp_path / "data" / "cache").mkdir(parents=True)
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "user_settings", {"user_stocks": ["AAPL"]})
    monkeypatch.delenv("STOCK_API", raising=False)
    assert views.get_stocks_info() == []


def test_page_json_builders(tmp_path, monkeypatch, transactions_df) -> None:
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(views, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(views, "greetings", lambda: "Добрый день!")
    monkeypatch.setattr(views, "get_currency_rates", lambda: [])
    monkeypatch.setattr(views, "get_stocks_info", lambda: [])

    date = datetime(2026, 6, 30)
    views.page_main_json(date, transactions_df)
    main = json.loads((tmp_path / "data" / "main_page.json").read_text(encoding="utf-8"))
    assert main["greetings"] == "Добрый день!"
    assert len(main["cards"]) == 2
    assert len(main["top_transactions"]) == 5

    views.page_events_json(date, transactions_df, "M")
    events = json.loads((tmp_path / "data" / "events_page.json").read_text(encoding="utf-8"))
    assert events["expenses"]["total_amount"] == 453
    assert events["income"]["total_amount"] == 1025
    assert events["currency_rates"] == []
