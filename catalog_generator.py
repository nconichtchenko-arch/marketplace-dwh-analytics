import json
import os
import yaml
import urllib.parse
from sqlalchemy import create_engine, text

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
# ВАЖНО: Замени 'dwh_password' на пароль пользователя dwh_user, если он другой
DB_USER = "dwh_user"
DB_PASSWORD = "dwh_password" 
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dwh_marketplace"

password = urllib.parse.quote_plus(DB_PASSWORD)
DB_URL = f"postgresql+psycopg2://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

# Путь к dbt-проекту (для парсинга Lineage)
DBT_PROJECT_PATH = r"H:\Projects\marketplace-dwh-analytics\marketplace_dwh"

def parse_dbt_lineage(dbt_project_path):
    """
    Парсит sources.yml, schema.yml и manifest.json из dbt-проекта.
    Извлекает связи между моделями и источниками.
    Возвращает словарь: {модель: [список зависимостей]}.
    """
    lineage = {}

    # 1. Парсим sources.yml (источники)
    sources_path = os.path.join(dbt_project_path, 'models', 'staging', 'sources.yml')
    if os.path.exists(sources_path):
        with open(sources_path, 'r', encoding='utf-8') as f:
            sources_data = yaml.safe_load(f)
            if sources_data and 'sources' in sources_data:
                for source in sources_data['sources']:
                    for table in source.get('tables', []):
                        table_name = f"{source['name']}.{table['name']}"
                        lineage.setdefault(table_name, [])
                        # Источники — корень, они ни от чего не зависят

    # 2. Парсим schema.yml (модели + relationships)
    schema_path = os.path.join(dbt_project_path, 'models', 'marts', 'schema.yml')
    if os.path.exists(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_data = yaml.safe_load(f)
            if schema_data and 'models' in schema_data:
                for model in schema_data['models']:
                    model_name = model['name']
                    lineage.setdefault(model_name, [])
                    # Ищем тесты relationships, чтобы понять зависимости
                    for column in model.get('columns', []):
                        for test in column.get('tests', []):
                            if isinstance(test, dict) and 'relationships' in test:
                                rel = test['relationships']
                                if 'arguments' in rel:
                                    to_model = rel['arguments'].get('to', '')
                                    # Извлекаем имя модели из "ref('dim_products')"
                                    if 'ref(' in to_model:
                                        dep = to_model.split("'")[1]
                                        lineage[model_name].append(dep)

    # 3. Парсим manifest.json (если есть) — для зависимостей между моделями
    manifest_path = os.path.join(dbt_project_path, 'target', 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            for node_id, node in manifest.get('nodes', {}).items():
                if node.get('resource_type') == 'model':
                    model_name = node['name']
                    for dep in node.get('depends_on', {}).get('nodes', []):
                        # Извлекаем имя из "model.marketplace_dwh.stg_sales"
                        dep_name = dep.split('.')[-1]
                        if model_name in lineage and dep_name not in lineage[model_name]:
                            lineage[model_name].append(dep_name)

    return lineage

def generate_catalog():
    print("🚀 Генерация Data Catalog...")
    
    catalog = {
        "project": "DWH Marketplace Analytics",
        "version": "1.0",
        "generated_at": "2026-10-25",
        "tables": {},
        "lineage": {}  # Новый раздел для связей
    }

    with engine.connect() as conn:
        # Получаем список всех таблиц в схеме public
        tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        tables = conn.execute(tables_query).fetchall()

        for (table_name,) in tables:
            print(f"  📦 Обработка таблицы: {table_name}")
            
            # Получаем колонки для каждой таблицы
            cols_query = text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = conn.execute(cols_query).fetchall()

            # Формируем описание таблицы
            catalog["tables"][table_name] = {
                "description": f"Таблица {table_name}",
                "columns": []
            }

            for col_name, data_type in columns:
                catalog["tables"][table_name]["columns"].append({
                    "name": col_name,
                    "type": data_type
                })

    # --- ДОБАВЛЯЕМ LINEAGE ИЗ DBT ---
    print("\n🔗 Парсинг dbt-моделей для Lineage...")
    lineage = parse_dbt_lineage(DBT_PROJECT_PATH)
    catalog["lineage"] = lineage
    print(f"  ✅ Найдено связей: {len(lineage)} моделей/источников")

    # Сохраняем в JSON
    with open("data_catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)

    print("\n🎉 Data Catalog успешно создан! Файл: data_catalog.json")

if __name__ == "__main__":
    generate_catalog()