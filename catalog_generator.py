import json
import urllib.parse
from sqlalchemy import create_engine, text

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
# ВАЖНО: Замени 'dwh_password' на пароль пользователя dwh_user, который мы создавали
DB_USER = "dwh_user"
DB_PASSWORD = "dwh_password" 
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dwh_marketplace"

password = urllib.parse.quote_plus(DB_PASSWORD)
DB_URL = f"postgresql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

def generate_catalog():
    print("🚀 Генерация Data Catalog...")
    
    catalog = {
        "project": "DWH Marketplace Analytics",
        "version": "1.0",
        "generated_at": "2026-10-21",
        "tables": {}
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

    # Сохраняем в JSON
    with open("data_catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)

    print("🎉 Data Catalog успешно создан! Файл: data_catalog.json")

if __name__ == "__main__":
    generate_catalog()