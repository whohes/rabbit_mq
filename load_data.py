import json
import random
import os
import psycopg2

# === 1. Подключение к PostgreSQL ===
conn = psycopg2.connect(
    dbname="cars_db",
    user="postgres",
    password="rms100605",  
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# === 2. Создаём таблицы, если их нет ===

# Таблица дилеров
cursor.execute("""
CREATE TABLE IF NOT EXISTS dealers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    city VARCHAR(50),
    address VARCHAR(100),
    area VARCHAR(50),
    rating NUMERIC(3,1)
);
""")

# Таблица автомобилей
cursor.execute("""
CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    firm VARCHAR(50),
    model VARCHAR(50),
    year INT,
    power INT,
    color VARCHAR(30),
    price NUMERIC(12,2),
    dealer_id INT REFERENCES dealers(id)
);
""")

# Фиксируем создание схемы/таблиц отдельно, чтобы они сохранились, даже если загрузка данных упадёт позже
conn.commit()

# === 3. Загружаем дилеров из JSON ===
# Поддерживаем имена файлов с пробелом перед .json и обычные имена
script_dir = os.path.dirname(os.path.abspath(__file__))

def resolve_json_path(preferred_name: str) -> str:
    """Возвращает путь к существующему JSON в корне проекта.
    Проверяет варианты имени с и без пробела перед .json.
    """
    name_with_space = preferred_name.replace('.json', ' .json') if preferred_name.endswith('.json') else preferred_name
    candidates = [
        os.path.join(script_dir, preferred_name),
        os.path.join(script_dir, name_with_space),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Не найден файл среди кандидатов: {candidates}")

dilers_path = resolve_json_path("dilers.json")
with open(dilers_path, "r", encoding="utf-8") as f:
    dealers_data = json.load(f)

for d in dealers_data:
    cursor.execute("""
        INSERT INTO dealers (name, city, address, area, rating)
        VALUES (%s, %s, %s, %s, %s)
    """, (d["Name"], d["City"], d["Address"], d["Area"], d["Rating"]))

conn.commit()

# === 4. Загружаем автомобили ===
cars_path = resolve_json_path("cars.json")
with open(cars_path, "r", encoding="utf-8") as f:
    cars_data = json.load(f)["cars"]

# Получаем список ID всех дилеров
cursor.execute("SELECT id FROM dealers;")
dealer_ids = [row[0] for row in cursor.fetchall()]

# Добавляем автомобили в таблицу и связываем случайным дилером
for car in cars_data:
    dealer_id = random.choice(dealer_ids)
    cursor.execute("""
        INSERT INTO cars (firm, model, year, power, color, price, dealer_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        car["firm"],
        car["model"],
        car["year"],
        car["power"],
        car["color"],
        car["price"],
        dealer_id
    ))

conn.commit()

print(f"✅ Загрузка завершена: {len(dealers_data)} дилеров и {len(cars_data)} автомобилей.")

# === 5. Проверка связи ===
cursor.execute("""
SELECT c.firm, c.model, d.name AS dealer_name, d.city
FROM cars c
JOIN dealers d ON c.dealer_id = d.id
LIMIT 10;
""")

for row in cursor.fetchall():
    print(row)

cursor.close()
conn.close()
