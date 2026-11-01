import sqlite3

DB_NAME = "pizza.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица категорий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    # Таблица товаров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            photo_url TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

    # Таблица корзины пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            UNIQUE(user_id, product_id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    # Таблица истории заказов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            customer_name TEXT,
            phone TEXT,
            address TEXT,
            total_price INTEGER NOT NULL,
            items_summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Наполняем начальными данными (если база еще пустая)
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO categories (name) VALUES ('🍕 Піца'), ('🥤 Напої')")
        
        # Товары: Пицца (с прямыми ссылками на красивые фото)
        products = [
            (1, "Пепероні", "Томатний соус, подвійна моцарела, гостра салямі пепероні, базилік.", 245, 
             "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=700"),
            (1, "4 Сири", "Вершковий соус, моцарела, пармезан, дорблю, чедер, горіхи.", 270, 
             "https://images.unsplash.com/photo-1573821663912-569905455b1c?w=700"),
            (1, "Барбекю з куркою", "Соус BBQ, філе курки, мисливські ковбаски, цибуля, сир.", 260, 
             "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=700"),
            (1, "Маргарита", "Класичний томатний соус, ніжна моцарела, томати чері, орегано.", 195, 
             "https://images.unsplash.com/photo-1604382355076-af4b0eb60143?w=700"),
            
            # Товары: Напитки
            (2, "Coca-Cola 0.5L", "Класична освіжаюча Coca-Cola в пляшці.", 45, 
             "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=700"),
            (2, "Крафтовий Лимонад 0.5L", "Натуральний свіжий цитрусовий лимонад із м'ятою.", 65, 
             "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=700")
        ]
        cursor.executemany("""
            INSERT INTO products (category_id, name, description, price, photo_url) 
            VALUES (?, ?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()

# ---------- Функции для работы с товарами ----------

def get_categories():
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT id, name FROM categories").fetchall()

def get_products_by_category(category_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT id, name, price FROM products WHERE category_id = ?", (category_id,)).fetchall()

def get_product(product_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT id, name, description, price, photo_url FROM products WHERE id = ?", (product_id,)).fetchone()

# ---------- Функции для работы с корзиной ----------

def add_to_cart(user_id, product_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = quantity + 1
        """, (user_id, product_id))

def change_cart_quantity(user_id, product_id, delta):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        row = cursor.fetchone()
        if not row:
            return
        new_qty = row[0] + delta
        if new_qty <= 0:
            conn.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        else:
            conn.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (new_qty, user_id, product_id))

def get_user_cart(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        query = """
            SELECT p.id, p.name, p.price, c.quantity, (p.price * c.quantity) as total
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        """
        return conn.execute(query, (user_id,)).fetchall()

def clear_cart(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))

def create_order(user_id, customer_name, phone, address, total_price, items_summary):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("""
            INSERT INTO orders (user_id, customer_name, phone, address, total_price, items_summary)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, customer_name, phone, address, total_price, items_summary))
        order_id = cursor.lastrowid
        conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        return order_id

if __name__ == "__main__":
    init_db()
    print("Базу даних 'pizza.db' успішно створено та заповнено товарами!")