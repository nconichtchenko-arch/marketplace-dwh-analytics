# DWH Marketplace Analytics

**Pet-проект** по построению корпоративного хранилища данных (DWH) для e-commerce на реальном датасете (397 924 строки). Демонстрирует полный цикл: от ETL и оркестрации до трансформаций, тестов и аналитики.

**Ключевые навыки:** SQL, Python (Pandas, SQLAlchemy), PostgreSQL, Apache Airflow, dbt, ClickHouse, Data Quality (Great Expectations).

---

## 🏗 Архитектура хранилища (Схема Звезда)

В основе проекта лежит модель данных «Звезда» (Star Schema), состоящая из одной таблицы фактов и трех таблиц измерений. Это позволяет аналитикам писать быстрые запросы для расчета бизнес-метрик.

![Схема Звезда](star_schema.png)

- **`fact_sales`** — таблица фактов (транзакции: количество, цена, сумма).
- **`dim_customers`** — измерение «Клиенты» (ID клиента, страна).
- **`dim_products`** — измерение «Товары» (Артикул, описание).
- **`dim_dates`** — измерение «Даты» (Год, месяц, день).

## ⚙️ ETL-процесс

Данные загружаются из сырого CSV-файла (397 924 строки) с помощью Python-скрипта (`etl_star_schema.py`). Скрипт очищает данные от возвратов и пустых значений, после чего раскладывает их по таблицам DWH в PostgreSQL.

## 🚀 Ключевые результаты

- Загружено и обработано **397 924** строк транзакций.
- Спроектирована модель DWH с разделением на Fact/Dim.
- **Оптимизация SQL:** Проведен анализ плана запросов (EXPLAIN ANALYZE). Созданы индексы, позволившие ускорить агрегационные запросы в 6 раз (с 6.3 сек до 0.9 сек).

## 📊 Результаты работы

![Результат SQL-запроса](sql_result.png)

Пример аналитического запроса к модели «Звезда» — выручка по странам:

## 📈 Визуализация (Power BI)

Дашборд на основе витрины `fct_sales` (dbt-модель):
- Топ-10 товаров по выручке.
- Общая выручка (карточка).
- Динамика продаж по месяцам.

![Дашборд](dashboard_dbt.png)

### Визуализация в Metabase

Дашборд на основе витрины `fct_sales` (dbt-модель) в Metabase:
- Топ-10 товаров по выручке.

![Metabase Dashboard](metabase_top10.png)

### Визуализация в Apache Superset

Дашборд на основе витрины `fct_sales` в Apache Superset (Docker, production-образ).
- Топ-10 товаров по выручке.

![Superset Dashboard](superset_top10.png)

### Визуализация в Yandex DataLens
Дашборд на основе витрины `fct_sales` в Yandex DataLens.

![Yandex DataLens Dashboard](datalens_top10.png)

## 🛡️ Безопасность и управление доступом (RLS)

В проекте настроен механизм **Row-Level Security (RLS)** в Apache Superset. 
Это позволяет ограничивать доступ к данным на уровне строк в зависимости от роли пользователя.

**Пример реализации:**
- Создана роль `Germany_Viewer`.
- Создано правило RLS: `stock_code = '23843'` для датасета `fct_sales`.
- Пользователь с этой ролью видит только данные, соответствующие фильтру (один товар), даже если в базе есть данные по всем товарам.
- *Примечание:* В тестовой среде для доступа к интерфейсу пользователю также была назначена роль `Admin` (из-за особенностей прав в Superset 6.0.0). Однако RLS-правило применяется независимо от этого и фильтрует данные на уровне запроса.

<p align="center">
  <img src="rls_rule.png" width="45%" alt="Настройка RLS" />
  <img src="rls_filtered_chart.png" width="45%" alt="График с RLS" />
</p>

## 🛠 Технологии

- **Python** (Pandas, SQLAlchemy) — для ETL и обработки данных.
- **PostgreSQL** — основная база данных хранилища.
- **SQL** — для аналитических запросов и оптимизации (EXPLAIN ANALYZE).
- **Apache Airflow** — оркестрация ETL-пайплайна (Docker).
- **dbt** (data build tool) — трансформация данных (ELT), тесты и Lineage.
- **ClickHouse** — колоночная OLAP-СУБД для аналитики (партиционирование, TTL, Materialized View).
- **Docker** — контейнеризация (Airflow, ClickHouse).
- **BI-инструменты** (Power BI, Metabase, Apache Superset, Yandex DataLens) — визуализация данных и дашборды..

## ⚙️ Оркестрация (Apache Airflow)

Для автоматизации ETL-процесса развернут Apache Airflow (через Docker Compose). Настроен DAG (`marketplace_dwh_etl_pipeline`), который ежедневно запускает скрипт загрузки данных в DWH.

**DAG включает три задачи:**
- `wait_for_etl_script` (FileSensor) — ожидает появления ETL-скрипта.
- `run_etl_script` (BashOperator) — запускает ETL.
- `notify_success` (BashOperator) — уведомляет об успехе.

Настроены `retries` (3 попытки, экспоненциальный backoff) и `catchup=True` (backfill).

![Airflow DAG Graph](airflow_dag_graph.png)

### Ветвление и группы в DAG

DAG использует:
- `BranchPythonOperator` (`check_file_exists`) — выбирает ветку выполнения (ETL или уведомление об ошибке).
- `TaskGroup` (`run_group`) — группирует задачи ETL (`run_etl_script` → `notify_success`).

![Airflow DAG Graph](airflow_dag_branch_group.png)

*Скриншот графа DAG с ветвлением (`BranchPythonOperator`) и группой задач (`TaskGroup`).*

## 🧱 Трансформация данных (dbt)

В проект интегрирован **dbt (data build tool)** для организации слоя трансформаций (ELT) поверх готового DWH.

**Реализованные модели:**
- `stg_sales` (staging) — очистка и подготовка данных из `fact_sales`.
- `dim_products`, `dim_customers`, `dim_dates` (marts) — измерения для модели «Звезда».
- `fct_sales` (marts) — **инкрементальная** витрина продаж (выручка и количество по чекам и товарам).

**Тестирование и качество данных:**
- Настроены тесты `not_null` для ключевых полей (`invoice_no`, `stock_code`, `total_revenue`).
- Настроены тесты `relationships` для проверки ссылочной целостности:
  - `fct_sales.stock_code` → `dim_products.stock_code`
  - `fct_sales.customer_id` → `dim_customers.customer_id`
  - `fct_sales.order_date` → `dim_dates.date_id`

**Результат:** все тесты проходят (PASS=5), данные в витрине консистентны.

### SCD Type 2 (dbt snapshot)

Настроен снапшот `dim_customers_snapshot` (стратегия `check` по колонке `country`). dbt отслеживает изменения страны клиента и создаёт новую версию записи, сохраняя историю (SCD Type 2).

Скрипт: `snapshots/dim_customers_snapshot.sql`.

![SCD Type 2 snapshot](scd_type2_snapshot.png)

**Стек dbt:** `dbt-core` 1.12.6, `dbt-postgres` 1.11.0.

![Результаты dbt test](dbt_test_results.png)

## ✅ Data Quality (Great Expectations)

Настроены проверки качества данных для витрины `fct_sales` с помощью **Great Expectations**:
- `total_revenue` не отрицательный и не пустой.
- `invoice_no` не пустой.
- `stock_code` не пустой.

Скрипт: `data_quality_checks.py`. Все проверки проходят (23/23 метрики).

**Data Drift:** Скрипт также проверяет отклонение среднего `total_revenue` от эталонного значения (`baseline_stats.json`). Если отклонение больше 10% — тест падает.

![Результат проверок Data Quality](data_quality_check_result.png)

Пример вывода:
📊 Текущее среднее: 25.07, Эталон: 22.89, Отклонение: 9.55%
✅ Data Drift в норме (отклонение 9.55% < 10%)

## 🏎️ Продвинутая работа с ClickHouse

Помимо бенчмарка (PostgreSQL vs ClickHouse — ускорение 6.8x), были отработаны продвинутые механизмы хранения и обработки данных:

- **Партиционирование** (`MergeTree`, `PARTITION BY toYYYYMM(event_date)`) — данные автоматически разбиваются на партиции (202610, 202611).
- **TTL** — автоматическое удаление устаревших данных (старше 30 дней).
- **Materialized View** (`SummingMergeTree`) — предагрегация данных при вставке.

![ClickHouse партиции и TTL](clickhouse_partitions_ttl.png)

---

## 🧪 Дополнительные эксперименты (Pet-исследования)

Эти разделы не входят в основной DWH-пайплайн, но демонстрируют широту навыков и понимание современных инструментов.

### 🔄 CDC (Change Data Capture) 
Настроена логическая репликация PostgreSQL (`wal_level = logical`, публикация `sales_pub`, слот `sales_slot`). Python-скрипт ловит изменения в `fct_sales` в реальном времени и выводит их (INSERT, UPDATE, DELETE).

![CDC Demo](cdc_demo.png)

### ⚡ PySpark 
Практический опыт анализа данных в Google Colab (DataFrame API, агрегации, сортировка). Пример: топ-10 товаров по выручке.

![PySpark Analysis](pyspark_colab.png)

### 🗂 Data Governance (Каталогизация данных)

Скрипт `catalog_generator.py` автоматически подключается к DWH, анализирует структуру таблиц (`information_schema`) и генерирует **Data Catalog** в формате JSON. Скрипт также парсит dbt-модели (`schema.yml`, `sources.yml`, `manifest.json`) и добавляет в каталог связи между таблицами (Lineage).

**Пример Lineage:** `fct_sales` зависит от `dim_products`, `dim_customers`, `dim_dates`, `stg_sales`.

Пример каталога: [`data_catalog.json`](data_catalog.json).

### 🧊 Lakehouse (Apache Iceberg)

Реализован pet-пример работы с **Apache Iceberg** (формат таблиц поверх Parquet):
- Создана Iceberg-таблица `demo.test_iceberg` (каталог SQLite, данные в Parquet).
- Записаны и прочитаны данные (3 строки).
- Показана история таблицы (snapshots).

Скрипт: `iceberg_demo.py`. Демонстрирует понимание Lakehouse (ACID-транзакции, time travel, schema evolution).

![Результат работы с Iceberg](iceberg_demo_result.png)

### 🦆 DuckDB + Parquet Analytics

Мини-проект по аналитике Parquet через DuckDB (без ETL). CSV → Parquet, сжатие в 11,4 раза. Вынесен в отдельный репозиторий: [duckdb-parquet-analytics](https://github.com/nconichtchenko-arch/duckdb-parquet-analytics).

---

## 📫 Контакты

- **Email:** pavloni@mail.ru
- **GitHub:** [github.com/nconichtchenko-arch](https://github.com/nconichtchenko-arch)
- **Проживание:** Воронеж
- **Формат работы:** удалённо
