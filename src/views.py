import json
import logging
import os
from datetime import datetime
from typing import Iterator

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import find_project_root, get_date_range, transactions, user_settings

load_dotenv()

get_currency_rates_logger = logging.getLogger("get_currency_rates")

file_handler = logging.FileHandler(f"{find_project_root()}/logs/get_currency_rates.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

get_currency_rates_logger.addHandler(file_handler)


# Набор функций для основной страницы
def hello() -> str:
    """Возвращает приветствие в зависимости от текущего времени"""

    if 23 <= datetime.now().hour or datetime.now().hour < 6:
        return "Доброй ночи!"

    elif 6 <= datetime.now().hour < 12:
        return "Доброе утро!"

    elif 12 <= datetime.now().hour < 18:
        return "Добрый день!"

    else:
        return "Добрый вечер!"


# Тут есть вопрос потому что не все транзакции имеют карту из-за этого недосчет (вопрос 2)
def get_cards_info(date: datetime) -> Iterator:
    """Возвращает данные по каждой карте в диапазоне дат с первого числа по указанное"""

    first_day = datetime(date.year, date.month, 1)
    date = date.replace(hour=23, minute=59, second=59, microsecond=999999)

    cards = {
        transaction["Номер карты"]
        for transaction in transactions
        if first_day <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= date
        and pd.notna(transaction["Номер карты"])
    }

    for card in cards:
        spend_counter = sum(
            transaction["Сумма операции"]
            for transaction in transactions
            if transaction["Номер карты"] == card
            and transaction["Сумма операции"] < 0
            and first_day <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= date
            and transaction.get("Статус") != "FAILED"
            and "Инвесткопилк" not in transaction.get("Описание")
        )

        yield {
            "last_digit": str(card)[-4:],
            "total_spend": round(abs(spend_counter)),
            "cashback": round(abs(spend_counter) / 100),
        }


def get_top_transactions(date: datetime) -> Iterator:
    """Возвращает топ 5 транзакций"""

    first_day = datetime(date.year, date.month, 1)

    filtered_transactions = [
        transaction
        for transaction in transactions
        if transaction.get("Дата операции")
        and first_day <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= date
        and "Инвесткопилк" not in transaction.get("Описание", "")
    ]

    for trans in sorted(filtered_transactions, key=lambda x: abs(x["Сумма операции"]), reverse=True)[:5]:

        yield {
            "date": trans["Дата операции"],
            "amount": abs(trans["Сумма операции"]),
            "type": "expense" if trans["Сумма операции"] < 0 else "income",
            "currency": trans["Валюта операции"],
            "category": trans["Категория"],
            "description": trans["Описание"],
        }


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
        get_currency_rates_logger.info("Берем из кэша")
        return [c for c in cached_data["currency_rates"] if c["currency"] in user_currencies]

    # Иначе загружаем из API
    api_key = os.getenv("CURRENCY_API")
    if not api_key or not user_currencies:
        get_currency_rates_logger.error("Нет API ключа для валют или нет настроек пользователя")
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

        get_currency_rates_logger.info("Кэш обновлён (добавлены новые валюты, старые сохранены)")
        # Возвращаем только запрошенные пользователем валюты (с актуальными курсами из API)
        return [{"currency": cur, "rate": new_rates[cur]} for cur in user_currencies if cur in new_rates]

    except (requests.RequestException, KeyError, ZeroDivisionError, ValueError) as e:
        get_currency_rates_logger.error(e)
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
        get_currency_rates_logger.info("Берем из кэша")
        return [item for item in cached_data["stocks_rates"] if item["stock"] in user_stocks]

    # Иначе загружаем из API
    api_key = os.getenv("STOCK_API")
    if not api_key or not user_stocks:
        get_currency_rates_logger.error("Нет API ключа для акций или нет настроек пользователя")
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
            get_currency_rates_logger.error(f"Ошибка при загрузке {stock}: {e}")
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

    get_currency_rates_logger.info("Кэш обновлён (добавлены новые акции, старые сохранены)")
    # Возвращаем только запрошенные пользователем акции (с новыми ценами)
    return [new_stocks[stock] for stock in user_stocks if stock in new_stocks]


def page_main_json(date: datetime) -> None:
    """Возвращает данные по картам, валютам, акциям и топ транзакций клиента для главной страницы"""

    json_format = {
        "greetings": hello(),
        "cards": list(get_cards_info(date)),
        "top_transactions": list(get_top_transactions(date)),
        "currency_rates": list(get_currency_rates()),
        "stock_prices": list(get_stocks_info()),
    }

    with open(f"{find_project_root()}/data/main_page.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)


# Набор функций для ивент страницы
def get_expenses_by_category(start_date: datetime, end_date: datetime) -> list:
    """Возвращает расходы по категориям"""

    unique_categories = set()

    for transaction in transactions:
        if transaction.get("Категория"):
            unique_categories.add(transaction["Категория"])

    expenses = []

    for category in unique_categories:

        spend_counter = 0

        for transaction in transactions:

            if (
                transaction.get("Категория") == category
                and transaction.get("Сумма операции") < 0
                and start_date <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= end_date
                and "Инвесткопилк" not in transaction.get("Описание")
                and transaction.get("Статус") != "FAILED"
            ):
                spend_counter += transaction.get("Сумма операции")

        expenses.append(
            {
                "category": category,
                "total_spend": round(abs(spend_counter)),
            }
        )

    sorted_data = sorted(expenses, key=lambda x: x["total_spend"], reverse=True)
    result = [{"category": x["category"], "total_spend": x["total_spend"]} for x in sorted_data[:7]]
    result.append({"category": "Остальное", "total_spend": sum(x["total_spend"] for x in sorted_data[7:])})

    return result


def transfers_and_cash(start_date: datetime, end_date: datetime) -> list:
    """Возвращает наличные транзакции и переводы за определенный срок"""

    filtered_transactions = [
        transaction
        for transaction in transactions
        if start_date <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= end_date
    ]

    transfers = [
        transaction
        for transaction in filtered_transactions
        if transaction.get("Категория") == "Переводы"
        and transaction.get("Сумма операции") < 0
        and "Инвесткопилк" not in transaction.get("Описание")
    ]

    cash = [
        transaction
        for transaction in filtered_transactions
        if transaction.get("Категория") == "Наличные" and transaction.get("Сумма операции") < 0
    ]

    result = [
        {
            "category": "Переводы",
            "total_spend": abs(round(sum(transaction["Сумма операции"] for transaction in transfers))),
        },
        {
            "category": "Наличные",
            "total_spend": abs(round(sum(transaction["Сумма операции"] for transaction in cash))),
        },
    ]

    return result


def get_income_by_category(start_date: datetime, end_date: datetime) -> list:
    """Возвращает доходы по категориям"""

    unique_categories = set()

    for transaction in transactions:
        if transaction.get("Категория"):
            unique_categories.add(transaction["Категория"])

    income = []

    for category in unique_categories:

        income_counter = 0

        for transaction in transactions:

            if (
                transaction.get("Категория") == category
                and transaction.get("Сумма операции") > 0
                and start_date <= datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S") <= end_date
                and transaction.get("Описание") != "Вывод с Инвесткопилки"
                and transaction.get("Описание") != "Вывод с брокерского счета"
            ):
                income_counter += transaction.get("Сумма операции")

        income.append(
            {
                "category": category,
                "total_income": round(abs(income_counter)),
            }
        )

    sorted_data = sorted(income, key=lambda x: x["total_income"], reverse=True)
    result = [
        {"category": x["category"], "total_income": x["total_income"]} for x in sorted_data if x["total_income"] > 0
    ]

    return result


def page_events_json(date: str, range_type: str = "M") -> None:
    """Возвращает данные по расходам по категориям для страницы событий"""

    start_date, end_date = get_date_range(date, range_type)

    total_amount_expenses = abs(
        round(sum(transaction["total_spend"] for transaction in get_expenses_by_category(start_date, end_date)))
    )

    total_amount_income = abs(
        round(sum(transaction["total_income"] for transaction in get_income_by_category(start_date, end_date)))
    )

    json_format = {
        "expenses": {
            "total_amount": total_amount_expenses,
            "main": get_expenses_by_category(start_date, end_date),
            "transfers_and_cash": transfers_and_cash(start_date, end_date),
        },
        "income": {"total_amount": total_amount_income, "main": get_income_by_category(start_date, end_date)},
        "currency_rates": list(get_currency_rates()),
        "stock_prices": list(get_stocks_info()),
    }

    with open(f"{find_project_root()}/data/events_page.json", "w", encoding="utf-8") as json_file:
        json.dump(json_format, json_file, ensure_ascii=False, indent=2)
