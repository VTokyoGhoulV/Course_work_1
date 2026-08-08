import json
import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

from logger import logger
from utils import find_project_root, get_date_range, user_settings

load_dotenv()


# Набор функций для основной страницы
def greetings() -> str:
    """Возвращает приветствие в зависимости от текущего времени"""

    if 23 <= datetime.now().hour or datetime.now().hour < 6:
        return "Доброй ночи!"

    elif 6 <= datetime.now().hour < 12:
        return "Доброе утро!"

    elif 12 <= datetime.now().hour < 18:
        return "Добрый день!"

    else:
        return "Добрый вечер!"


def get_cards_info(date: datetime, transactions: pd.DataFrame) -> list:
    """Возвращает данные по каждой карте в диапазоне дат с первого числа по указанное"""

    first_day, last_day = get_date_range(date)

    operation_dates = pd.to_datetime(transactions["Дата операции"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    period_mask = operation_dates.between(first_day, last_day) & transactions["Номер карты"].notna()

    spending_mask = (
        period_mask
        & transactions["Сумма операции"].lt(0)
        & transactions["Статус"].ne("FAILED")
        & ~transactions["Описание"].str.contains("инвесткопилк", na=False, case=False)
    )

    cards = transactions.loc[period_mask, "Номер карты"].drop_duplicates()

    card_spending = (
        transactions.loc[spending_mask]
        .groupby("Номер карты")["Сумма операции"]
        .sum()
        .abs()
        .reindex(cards, fill_value=0)
    )

    result = [
        {
            "last_digit": str(card)[-4:],
            "total_spend": round(spend_counter),
            "cashback": round(abs(spend_counter) / 100),
        }
        for card, spend_counter in card_spending.items()
    ]

    return result


def get_top_transactions(date: datetime, transactions: pd.DataFrame) -> list:
    """Возвращает топ 5 транзакций"""

    first_day, last_day = get_date_range(date)

    mask = (
        transactions["Дата операции"].between(first_day, last_day)
        & transactions["Статус"].ne("FAILED")
        & ~transactions["Описание"].str.contains("инвесткопилк", na=False, case=False)
    )

    transactions = (
        transactions.loc[mask]
        .sort_values(by="Сумма операции", key=lambda column: column.abs(), ascending=False)
        .head(5)
    )

    result = [
        {
            "date": str(transaction["Дата операции"]),
            "amount": abs(transaction["Сумма операции"]),
            "type": "expense" if transaction["Сумма операции"] < 0 else "income",
            "currency": transaction["Валюта операции"],
            "category": transaction["Категория"],
            "description": transaction["Описание"],
        }
        for transaction in transactions.to_dict("records")
    ]
    return result


def get_currency_rates() -> list:
    """Возвращает актуальный курс валют по настройкам пользователя"""
    cache_path = f"{find_project_root()}/data/cache/currency_rates.json"
    today = datetime.now().strftime("%d.%m.%Y")
    user_currencies = user_settings.get("user_currencies", [])  # глобальная переменная

    cached_data = None
    # Чтение кэша, если файл существует
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as file:
            cached_data = json.load(file)

    # Проверка свежести и наличия всех нужных валют
    if (
        cached_data is not None
        and cached_data.get("date") == today
        and all(currency in [c["currency"] for c in cached_data["currency_rates"]] for currency in user_currencies)
    ):
        logger.info("Берем из кэша")
        return [c for c in cached_data["currency_rates"] if c["currency"] in user_currencies]

    # Иначе загружаем из API
    api_key = os.getenv("CURRENCY_API")
    if not api_key or not user_currencies:
        logger.error("Нет API ключа для валют или нет настроек пользователя")
        return []

    url = f"https://api.apilayer.com/exchangerates_data/latest?symbols={','.join(user_currencies)}&base=RUB"
    try:
        response = requests.get(url, headers={"apikey": api_key}, timeout=10)
        response.raise_for_status()
        rates = response.json().get("rates", {})

        # Новые курсы из API (после конвертации 1/rate)
        new_rates = {cur: round(1 / rates[cur], 2) for cur in user_currencies if cur in rates and rates[cur] > 0}

        # Загружаем старые курсы за сегодня (если есть)
        old_rates = {}
        if cached_data is not None and cached_data.get("date") == today:
            old_rates = {item["currency"]: item["rate"] for item in cached_data.get("currency_rates", [])}

        # Объединяем: новые перезаписывают старые, старые валюты, которых нет в запросе, остаются
        merged_rates = {**old_rates, **new_rates}

        # Формируем данные для сохранения
        actual_rates = {
            "currency_rates": [{"currency": cur, "rate": rate} for cur, rate in merged_rates.items()],
            "date": today,
        }

        with open(cache_path, "w", encoding="utf-8") as file:
            json.dump(actual_rates, file, ensure_ascii=False, indent=4)

        logger.info("Кэш обновлён (добавлены новые валюты, старые сохранены)")
        # Возвращаем только запрошенные пользователем валюты (с актуальными курсами из API)
        return [{"currency": cur, "rate": new_rates[cur]} for cur in user_currencies if cur in new_rates]

    except (requests.RequestException, KeyError, ZeroDivisionError, ValueError) as e:
        logger.error(e)
        return []


def get_stocks_info() -> list:
    """Возвращает актуальную цену акций в USD по настройкам пользователя"""

    cache_path = f"{find_project_root()}/data/cache/stocks_rates.json"
    today = datetime.now().strftime("%d.%m.%Y")
    user_stocks = user_settings.get("user_stocks", [])  # глобальная переменная

    # Чтение кэша, если файл существует
    cached_data = None
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as file:
            cached_data = json.load(file)

    # Проверка свежести и наличия всех нужных акций
    if (
        cached_data
        and cached_data.get("date") == today
        and all(stock in [item["stock"] for item in cached_data.get("stocks_rates", [])] for stock in user_stocks)
    ):
        logger.info("Берем из кэша")
        return [item for item in cached_data["stocks_rates"] if item["stock"] in user_stocks]

    # Иначе загружаем из API
    api_key = os.getenv("STOCK_API")
    if not api_key or not user_stocks:
        logger.error("Нет API ключа для акций или нет настроек пользователя")
        return []

    # Загружаем старые данные за сегодня (если есть)
    old_stocks = {}
    if cached_data and cached_data.get("date") == today:
        old_stocks = {
            item["stock"]: {"price": item["price"], "currency": item["currency"]}
            for item in cached_data.get("stocks_rates", [])
        }

    # Получаем новые данные для запрошенных акций
    new_stocks = {}
    for stock in user_stocks:
        url = f"https://api.twelvedata.com/eod?symbol={stock}&apikey={api_key}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = round(float(data["close"]), 2)
            new_stocks[stock] = {"stock": stock, "price": price, "currency": "USD"}
        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            logger.error(f"Ошибка при загрузке {stock}: {e}")
            continue

    # Объединяем старые и новые: новые перезаписывают старые по тикеру
    merged = {**old_stocks}  # копируем старые
    for stock, data in new_stocks.items():
        merged[stock] = data  # новые заменяют или добавляются

    # Преобразуем обратно в список
    merged_stocks_rates = list(merged.values())

    # Формируем данные для кэша
    actual_rates = {
        "stocks_rates": merged_stocks_rates,
        "date": today,
    }

    # Сохраняем в кэш
    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(actual_rates, file, ensure_ascii=False, indent=4)

    logger.info("Кэш обновлён (добавлены новые акции, старые сохранены)")
    # Возвращаем только запрошенные пользователем акции (с новыми ценами)
    return [new_stocks[stock] for stock in user_stocks if stock in new_stocks]


def page_main_json(date: datetime, transactions: pd.DataFrame) -> None:
    """Возвращает данные по картам, валютам, акциям и топ транзакций клиента для главной страницы"""

    json_format = {
        "greetings": greetings(),
        "cards": list(get_cards_info(date, transactions)),
        "top_transactions": list(get_top_transactions(date, transactions)),
        "currency_rates": list(get_currency_rates()),
        "stock_prices": list(get_stocks_info()),
    }

    with open(f"{find_project_root()}/data/views/main_page.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)


# Набор функций для ивент страницы
def get_expenses_by_category(date: datetime, transactions: pd.DataFrame, range_type: str) -> list:
    first_day, last_day = get_date_range(date, range_type)

    operation_dates = pd.to_datetime(transactions["Дата операции"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    period_mask = operation_dates.between(first_day, last_day)

    spending_mask = (
        period_mask
        & transactions["Сумма операции"].lt(0)
        & transactions["Статус"].ne("FAILED")
        & ~transactions["Описание"].str.contains("инвесткопилк", na=False, case=False)
        & ~transactions["Описание"].str.contains("брокерск", na=False, case=False)
    )

    categories_spend = (
        transactions.loc[spending_mask].groupby("Категория")["Сумма операции"].sum().abs().sort_values(ascending=False)
    )

    top_categories = categories_spend.head(7)
    other_spend = categories_spend.iloc[7:].sum()

    result = [{"category": category, "amount": round(spend)} for category, spend in top_categories.items()]

    if other_spend > 0:
        result.append(
            {
                "category": "Остальное",
                "amount": round(other_spend),
            }
        )

    return result


def transfers_and_cash(date: datetime, transactions: pd.DataFrame, range_type: str) -> list:

    first_day, last_day = get_date_range(date, range_type)

    operation_dates = pd.to_datetime(transactions["Дата операции"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    period_mask = operation_dates.between(first_day, last_day)

    mask = (
        period_mask
        & transactions["Категория"].isin(["Переводы", "Наличные"])
        & transactions["Сумма операции"].lt(0)
        & transactions["Статус"].ne("FAILED")
        & ~transactions["Описание"].str.contains("инвесткопилк", na=False, case=False)
        & ~transactions["Описание"].str.contains("брокерск", na=False, case=False)
    )

    categories_spend = (
        transactions.loc[mask]
        .groupby("Категория")["Сумма операции"]
        .sum()
        .abs()
        .reindex(["Переводы", "Наличные"], fill_value=0)
    )

    result = [{"category": category, "amount": round(spend)} for category, spend in categories_spend.items()]

    return result


def get_income_by_category(date: datetime, transactions: pd.DataFrame, range_type: str) -> list:

    first_day, last_day = get_date_range(date, range_type)

    operation_dates = pd.to_datetime(transactions["Дата операции"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    period_mask = operation_dates.between(first_day, last_day)

    mask = (
        period_mask
        & transactions["Сумма операции"].gt(0)
        & ~transactions["Описание"].str.contains("инвесткопилк", na=False, case=False)
        & ~transactions["Описание"].str.contains("брокерск", na=False, case=False)
        & transactions["Категория"].ne("Маркетплейсы")
    )

    category_income = (
        transactions.loc[mask].groupby("Категория")["Сумма операции"].sum().abs().sort_values(ascending=False)
    )

    result = [{"category": category, "amount": round(spend)} for category, spend in category_income.items()]

    return result


def page_events_json(date: datetime, transactions: pd.DataFrame, range_type: str = "M") -> None:
    """Возвращает данные по расходам по категориям для страницы событий"""

    total_amount_expenses = abs(
        round(sum(transaction["amount"] for transaction in get_expenses_by_category(date, transactions, range_type)))
    )

    total_amount_income = abs(
        round(sum(transaction["amount"] for transaction in get_income_by_category(date, transactions, range_type)))
    )

    json_format = {
        "expenses": {
            "total_amount": total_amount_expenses,
            "main": get_expenses_by_category(date, transactions, range_type),
            "transfers_and_cash": transfers_and_cash(date, transactions, range_type),
        },
        "income": {
            "total_amount": total_amount_income,
            "main": get_income_by_category(date, transactions, range_type),
        },
        "currency_rates": get_currency_rates(),
        "stock_prices": get_stocks_info(),
    }

    with open(f"{find_project_root()}/data/views/events_page.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)
