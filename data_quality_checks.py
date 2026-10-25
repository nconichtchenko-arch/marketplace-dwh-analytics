import great_expectations as gx
import pandas as pd
import urllib.parse
import json
import os
from sqlalchemy import create_engine, text

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
DB_USER = "dwh_user"
DB_PASSWORD = "dwh_password" 
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dwh_marketplace"

password = urllib.parse.quote_plus(DB_PASSWORD)
DB_URL = f"postgresql+psycopg2://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

# Путь для сохранения эталонного среднего
BASELINE_PATH = "baseline_stats.json"

def check_data_drift(df, baseline_path=BASELINE_PATH):
    """
    Проверяет Data Drift: сравнивает текущее среднее total_revenue с эталонным.
    Если отклонение больше 10% — возвращает False.
    """
    current_mean = df['total_revenue'].mean()
    
    # Если эталонного файла нет — создаём его (первый запуск)
    if not os.path.exists(baseline_path):
        with open(baseline_path, 'w') as f:
            json.dump({'baseline_mean': current_mean}, f)
        print(f"  📊 Эталонное среднее сохранено: {current_mean:.2f}")
        return True
    
    # Читаем эталон
    with open(baseline_path, 'r') as f:
        baseline = json.load(f)
    
    baseline_mean = baseline['baseline_mean']
    deviation = abs(current_mean - baseline_mean) / baseline_mean * 100
    
    print(f"  📊 Текущее среднее: {current_mean:.2f}, Эталон: {baseline_mean:.2f}, Отклонение: {deviation:.2f}%")
    
    if deviation > 10:
        print(f"  ❌ Data Drift обнаружен! Отклонение {deviation:.2f}% > 10%")
        return False
    else:
        print(f"  ✅ Data Drift в норме (отклонение {deviation:.2f}% < 10%)")
        return True

def run_checks():
    print("🚀 Запуск Data Quality checks (Great Expectations)...")

    # 1. Загружаем данные из fct_sales в Pandas DataFrame
    print("  📥 Загрузка данных из fct_sales...")
    query = "SELECT * FROM dbt_schema.fct_sales LIMIT 10000;"  # Для теста берём 10к строк
    df = pd.read_sql(query, engine)
    print(f"  ✅ Загружено строк: {len(df)}")

    # 2. Создаём контекст GX (в памяти, без файловой структуры)
    context = gx.get_context()

    # 3. Создаём Data Source и Asset (в новом API 1.x)
    data_source = context.data_sources.add_pandas("my_pandas_source")
    data_asset = data_source.add_dataframe_asset("fct_sales_asset")

    # 4. Создаём Batch Definition (батч из DataFrame)
    batch_definition = data_asset.add_batch_definition_whole_dataframe("fct_sales_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    # 5. Создаём Suite (набор проверок) и добавляем Expectations
    suite = context.suites.add(gx.ExpectationSuite(name="fct_sales_suite"))

    # Проверка 1: total_revenue не должен быть отрицательным
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="total_revenue")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="total_revenue", min_value=0
        )
    )

    # Проверка 2: invoice_no не должен быть пустым
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="invoice_no")
    )

    # Проверка 3: stock_code не должен быть пустым
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="stock_code")
    )

    # 6. Запускаем проверки
    print("  🔍 Запуск проверок...")
    results = batch.validate(suite)

    # 7. Выводим результат
    if results.success:
        print("  ✅ Все проверки пройдены! Данные качественные.")
    else:
        print("  ❌ Некоторые проверки не пройдены:")
        for res in results.results:
            if not res.success:
                print(f"     - {res.expectation_config.type}: {res.result}")

    # 8. Проверка Data Drift
    print("\n  🔍 Проверка Data Drift...")
    drift_ok = check_data_drift(df)
    if not drift_ok:
        print("  ⚠️ Data Drift: данные отклонились от эталона!")

    return results

if __name__ == "__main__":
    run_checks()