import os
import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog

# 1. Настройка каталога (SQLite в папке проекта)
warehouse_path = os.path.abspath("iceberg_warehouse")
os.makedirs(warehouse_path, exist_ok=True)

catalog = SqlCatalog(
    "default",
    **{
        "uri": f"sqlite:///{warehouse_path}/catalog.db",
        "warehouse": f"file://{warehouse_path}",
    },
)

# 2. Создаём namespace (схему)
catalog.create_namespace_if_not_exists("demo")
print("✅ Namespace 'demo' создан.")

# 3. Создаём Iceberg-таблицу
schema = pa.schema([
    pa.field("id", pa.int64()),
    pa.field("event_type", pa.string()),
    pa.field("value", pa.int64()),
])

table = catalog.create_table_if_not_exists(
    "demo.test_iceberg",
    schema=schema,
)
print(f"✅ Таблица создана: {table.name()}")

# 4. Записываем данные (Parquet-файлы под капотом)
data = pa.table({
    "id": [1, 2, 3],
    "event_type": ["click", "view", "click"],
    "value": [10, 20, 30],
})

table.append(data)
print(f"✅ Записано строк: {len(data)}")

# 5. Читаем данные обратно (через pyiceberg)
print("\n📊 Чтение данных из Iceberg-таблицы:")
df = table.scan().to_arrow()
print(df.to_pandas())

# 6. Проверяем историю (time travel)
print("\n📜 История таблицы:")
for snapshot in table.history():
    print(f"  - Snapshot ID: {snapshot.snapshot_id}, Summary: {snapshot.summary}")