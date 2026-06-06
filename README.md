# Project1

Учебный Python-проект для анализа банковских операций из Excel-файла. Приложение формирует JSON-данные для страниц, рассчитывает расходы и доходы, подбирает категории кешбэка, считает потенциальные накопления для «Инвесткопилки», выполняет поиск по операциям и генерирует отчёты.

## Возможности

- чтение банковских операций из `data/operations.xlsx`;
- генерация данных для главной страницы в `data/main_page.json`;
- генерация данных для страницы событий в `data/events_page.json`;
- расчёт расходов по картам и кешбэка;
- вывод топ-5 транзакций за выбранный период;
- расчёт расходов и доходов по категориям;
- подбор выгодных категорий кешбэка;
- расчёт возможных накоплений через округление расходов;
- поиск операций по строке описания;
- поиск операций с номерами телефонов;
- поиск переводов физическим лицам;
- получение курсов валют и стоимости акций через внешние API;
- кеширование курсов валют и акций в `data/cache/`;
- генерация отчётов в `data/reports/`;
- тестирование через `pytest`.

## Стек технологий

- Python 3.14
- Poetry
- pandas
- openpyxl
- requests
- python-dotenv
- pytest
- pytest-cov
- flake8
- black
- isort
- mypy

## Структура проекта

```text
.
├── data/
│   ├── cache/                         # кеш курсов валют и акций
│   ├── reports/                       # сгенерированные отчёты
│   ├── operations.xlsx                # исходные банковские операции
│   ├── user_settings.json             # настройки валют и акций пользователя
│   ├── main_page.json                 # данные главной страницы
│   ├── events_page.json               # данные страницы событий
│   ├── cashback_categories.json       # категории кешбэка
│   ├── investment_bank.json           # расчёт инвесткопилки
│   └── simple_finder.json             # результат поиска по операциям
├── logs/                              # лог-файлы
├── src/
│   ├── main.py                        # точка запуска проекта
│   ├── views.py                       # функции формирования данных страниц
│   ├── services.py                    # сервисные функции
│   ├── reports.py                     # отчёты по операциям
│   ├── decorators.py                  # декоратор сохранения отчётов
│   └── utils.py                       # утилиты, чтение Excel, диапазоны дат
├── tests/                             # тесты проекта
├── .env_example                       # пример переменных окружения
├── pyproject.toml                     # настройки Poetry и инструментов
└── README.md
```

## Установка

1. Клонируйте или распакуйте проект.

2. Перейдите в папку проекта:

```bash
cd Project1
```

3. Установите зависимости через Poetry:

```bash
poetry install
```

4. Создайте файл `.env` на основе `.env_example`:

```bash
cp .env_example .env
```

5. Укажите API-ключи в `.env`:

```env
CURRENCY_API="your API key"
STOCK_API="your API key"
```

`CURRENCY_API` используется для получения курсов валют через API Layer, а `STOCK_API` — для получения стоимости акций через Twelve Data.

## Настройка данных

Основной файл с операциями должен находиться по пути:

```text
data/operations.xlsx
```

Ожидаемые поля в Excel-файле:

- `Дата операции`
- `Дата платежа`
- `Номер карты`
- `Статус`
- `Сумма операции`
- `Валюта операции`
- `Категория`
- `Описание`

Настройки пользователя находятся в файле:

```text
data/user_settings.json
```

Пример структуры:

```json
{
  "user_currencies": ["USD", "EUR"],
  "user_stocks": ["AAPL", "AMZN", "GOOGL"]
}
```

## Запуск проекта

Основной запуск выполняется командой:

```bash
poetry run python -m src.main
```

При запуске выполняются функции из `src/main.py`:

```python
pages(date="31.05.2021", range_type="M")
services(transactions, year=2021, month=5, limit=100, search_string="товар")
reports(df, "Переводы")
```

После выполнения будут обновлены JSON-файлы в папке `data/`, а отчёты сохранятся в `data/reports/`.

## Основные функции

### `pages(date, range_type)`

Генерирует JSON-файлы для страниц приложения:

- `data/main_page.json`
- `data/events_page.json`

Параметры:

- `date` — дата в формате `DD.MM.YYYY`;
- `range_type` — диапазон данных:
  - `W` — неделя;
  - `M` — месяц;
  - `Y` — год;
  - `ALL` — весь период.

### `services(data, year, month, limit, search_string)`

Запускает сервисные расчёты:

- подбор категорий кешбэка;
- расчёт инвесткопилки;
- поиск операций по строке.

### `reports(dataframe, category)`

Генерирует отчёты:

- расходы по категории за последние 3 месяца;
- средние расходы по дням недели;
- средние расходы в рабочие и выходные дни.

## Отчёты

Отчёты формируются функциями из `src/reports.py` и автоматически сохраняются декоратором `@report_to_file()`.

Файлы отчётов создаются в формате JSON:

```text
data/reports/report_<имя_функции>_<дата>.json
```

Примеры:

```text
data/reports/report_spending_by_category_20260606.json
data/reports/report_spending_by_weekday_20260606.json
data/reports/report_spending_by_workday_20260606.json
```

## Тестирование

Запуск тестов:

```bash
poetry run pytest
```

Запуск тестов с покрытием:

```bash
poetry run pytest --cov=src
```

## Проверка качества кода

Форматирование через Black:

```bash
poetry run black src tests
```

Сортировка импортов:

```bash
poetry run isort src tests
```

Проверка Flake8:

```bash
poetry run flake8 src tests
```

Проверка типов через MyPy:

```bash
poetry run mypy src
```

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `CURRENCY_API` | API-ключ для получения курсов валют |
| `STOCK_API` | API-ключ для получения стоимости акций |

## Логи

Логи сохраняются в папке `logs/`:

```text
logs/get_currency_rates.log
logs/investment_bank.log
logs/report_to_file.log
```

## Примечания по безопасности

Файл `.env` не должен попадать в публичный репозиторий, так как он содержит API-ключи. Для примера настроек используется `.env_example`.
