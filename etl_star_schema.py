import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
DB_USER = "dwh_user"
DB_PASSWORD = "dwh_password" # <-- ЗАМЕНИ НА СВОЙ ПАРОЛЬ ОТ PGADMIN
DB_HOST = "localhost"
DB_PORT = "5432" 
DB_NAME = "dwh_marketplace"

# Кодируем пароль на случай спецсимволов
password = urllib.parse.quote_plus(DB_PASSWORD)
DB_URL = f"postgresql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

def run_etl():
    print("🚀 Начинаем ETL-процесс...")
    
    # 1. Читаем CSV
    try:
        df = pd.read_csv("online_retail.csv", encoding='latin1')
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        print("Убедись, что файл online_retail.csv лежит в этой же папке!")
        return

    # 2. Очистка данных
    df.dropna(subset=['CustomerID', 'Description'], inplace=True)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df = df[df['Quantity'] > 0] # Убираем возвраты
    
    print(f"✅ Загружено строк: {len(df)}")

    # 3. Создаем таблицы (Схема Звезда)
    print("🏗 Создаем структуру БД...")
    with engine.connect() as conn:
        # Удаляем старые таблицы, если есть
        conn.execute(text("DROP TABLE IF EXISTS fact_sales, dim_customers, dim_products, dim_dates CASCADE;"))
        
        # Измерение: Клиенты
        conn.execute(text("""
            CREATE TABLE dim_customers (
                customer_id INT PRIMARY KEY,
                country VARCHAR(100)
            );
        """))
        # Измерение: Товары
        conn.execute(text("""
            CREATE TABLE dim_products (
                stock_code VARCHAR(50) PRIMARY KEY,
                description TEXT
            );
        """))
        # Измерение: Дата
        conn.execute(text("""
            CREATE TABLE dim_dates (
                date_id DATE PRIMARY KEY,
                year INT,
                month INT,
                day INT
            );
        """))
        # Факт: Продажи
        conn.execute(text("""
            CREATE TABLE fact_sales (
                id SERIAL PRIMARY KEY,
                invoice_no VARCHAR(50),
                customer_id INT REFERENCES dim_customers(customer_id),
                stock_code VARCHAR(50) REFERENCES dim_products(stock_code),
                date_id DATE REFERENCES dim_dates(date_id),
                quantity INT,
                price NUMERIC(10,2),
                total_amount NUMERIC(10,2)
            );
        """))
        conn.commit()

    # 4. Заполняем таблицы измерений
    print("📦 Заполняем измерения (Клиенты, Товары, Даты)...")
    # Клиенты
    dim_customers = df[['CustomerID', 'Country']].drop_duplicates('CustomerID')
    dim_customers.columns = ['customer_id', 'country']
    dim_customers.to_sql('dim_customers', engine, if_exists='append', index=False)

    # Товары
    dim_products = df[['StockCode', 'Description']].drop_duplicates('StockCode')
    dim_products.columns = ['stock_code', 'description']
    dim_products = dim_products.drop_duplicates('stock_code') 
    dim_products.to_sql('dim_products', engine, if_exists='append', index=False)

    # Даты
    df['date_id'] = df['InvoiceDate'].dt.date
    dim_dates = pd.DataFrame({'date_id': df['date_id'].unique()})
    dim_dates['year'] = pd.to_datetime(dim_dates['date_id']).dt.year
    dim_dates['month'] = pd.to_datetime(dim_dates['date_id']).dt.month
    dim_dates['day'] = pd.to_datetime(dim_dates['date_id']).dt.day
    dim_dates.to_sql('dim_dates', engine, if_exists='append', index=False)

    # 5. Заполняем таблицу фактов
    print("💰 Заполняем таблицу фактов (Продажи)...")
    fact_sales = df[['InvoiceNo', 'CustomerID', 'StockCode', 'date_id', 'Quantity', 'UnitPrice']].copy()
    fact_sales.columns = ['invoice_no', 'customer_id', 'stock_code', 'date_id', 'quantity', 'price']
    fact_sales['total_amount'] = fact_sales['quantity'] * fact_sales['price']
    
    fact_sales.to_sql('fact_sales', engine, if_exists='append', index=False)

    print("🎉 ETL успешно завершен! Данные в базе.")

if __name__ == "__main__":
    run_etl()