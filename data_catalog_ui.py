import streamlit as st
import pandas as pd
import urllib.parse
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

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Data Catalog", page_icon="🗂", layout="wide")

st.title("🗂 Data Catalog (Metadata Management)")
st.markdown("Веб-интерфейс для просмотра каталога данных DWH Marketplace Analytics.")

# --- ЗАГРУЗКА ДАННЫХ ---
@st.cache_data(ttl=60)  # Кэшируем на 60 секунд, чтобы не дергать БД при каждом клике
def load_catalog():
    query = """
        SELECT table_name, description, owner, tags, lineage, updated_at
        FROM metadata_catalog.tables_metadata
        ORDER BY table_name;
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

df = load_catalog()

# --- ФИЛЬТРЫ В САЙДБАРЕ ---
st.sidebar.header("🔍 Фильтры")

# Фильтр по тегам
all_tags = sorted(set(tag for tags in df['tags'].dropna() for tag in str(tags).split(',')))
selected_tags = st.sidebar.multiselect("Теги (слой):", all_tags)

# Фильтр по владельцу
all_owners = sorted(df['owner'].dropna().unique())
selected_owners = st.sidebar.multiselect("Владелец:", all_owners)

# Применяем фильтры
filtered_df = df.copy()
if selected_tags:
    filtered_df = filtered_df[filtered_df['tags'].apply(lambda x: any(tag in str(x) for tag in selected_tags))]
if selected_owners:
    filtered_df = filtered_df[filtered_df['owner'].isin(selected_owners)]

# --- ОТОБРАЖЕНИЕ ---
st.subheader(f"Найдено таблиц: {len(filtered_df)}")

# Выводим таблицу в виде карточек
for _, row in filtered_df.iterrows():
    with st.expander(f"**{row['table_name']}**  (Тег: {row['tags'] or '—'})"):
        st.write(f"**Описание:** {row['description'] or '—'}")
        st.write(f"**Владелец:** {row['owner'] or '—'}")
        st.write(f"**Обновлено:** {row['updated_at']}")
        
        # Lineage (если есть)
        if row['lineage'] and row['lineage'] != '[]':
            st.write("**Lineage (зависимости):**")
            st.json(row['lineage'])
        else:
            st.write("**Lineage:** нет данных")

# --- ФУТЕР ---
st.sidebar.markdown("---")
st.sidebar.info(
    "Этот каталог создан автоматически скриптом `catalog_generator.py`. "
    "Данные хранятся в схеме `metadata_catalog` PostgreSQL."
)