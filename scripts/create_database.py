"""Fictional restaurant demo: exactly 5,000 sales line items."""

from contextlib import closing
from datetime import date, timedelta, datetime
from pathlib import Path
import csv
import json
import random
import sqlite3


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "restaurant.db"

START = date(2025, 6, 1)
END = date(2026, 6, 30)

# Simplified sample recipes per one sold menu item.
# Prices are stored in hundredths of PKR.
MENU = [
    ("Chicken Biryani", "Food", 250,
     {"Rice": 180, "Chicken": 200, "Onion": 50,
      "Tomato": 40, "Cooking oil": 20, "Spice mix": 12}),

    ("Beef Biryani", "Food", 300,
     {"Rice": 180, "Beef": 180, "Onion": 50,
      "Tomato": 40, "Cooking oil": 20, "Spice mix": 12}),

    ("Chicken Karahi", "Food", 350,
     {"Chicken": 250, "Tomato": 100,
      "Cooking oil": 25, "Spice mix": 15}),

    ("Mutton Karahi", "Food", 500,
     {"Mutton": 250, "Tomato": 100,
      "Cooking oil": 25, "Spice mix": 15}),

    ("Chicken Tikka", "Food", 250,
     {"Chicken": 250, "Yogurt": 40,
      "Spice mix": 15, "Cooking oil": 10}),

    ("Beef Kebab", "Food", 220,
     {"Beef": 180, "Onion": 40,
      "Spice mix": 10, "Cooking oil": 10}),

    ("Grilled Chicken", "Food", 350,
     {"Chicken": 300, "Spice mix": 12, "Cooking oil": 10}),

    ("Chicken Shawarma", "Food", 120,
     {"Chicken": 120, "Flatbread": 1,
      "Garlic sauce": 25, "Lettuce": 20}),

    ("Beef Shawarma", "Food", 150,
     {"Beef": 120, "Flatbread": 1,
      "Garlic sauce": 25, "Lettuce": 20}),

    ("Zinger Burger", "Food", 180,
     {"Chicken": 120, "Burger bun": 1, "Flour": 25,
      "Cooking oil": 15, "Lettuce": 20, "Garlic sauce": 20}),

    ("Beef Burger", "Food", 200,
     {"Beef": 120, "Burger bun": 1,
      "Lettuce": 20, "Garlic sauce": 20}),

    ("Chicken Pizza", "Food", 350,
     {"Flour": 200, "Chicken": 100, "Cheese": 80,
      "Tomato sauce": 60, "Yeast": 3}),

    ("Vegetable Pizza", "Food", 300,
     {"Flour": 200, "Bell pepper": 50, "Onion": 40,
      "Cheese": 80, "Tomato sauce": 60, "Yeast": 3}),

    ("French Fries", "Food", 80,
     {"Potato": 180, "Cooking oil": 20, "Salt": 2}),

    ("Chicken Nuggets", "Food", 150,
     {"Chicken": 100, "Breadcrumbs": 30, "Cooking oil": 15}),

    ("Hummus", "Food", 120,
     {"Chickpeas": 150, "Tahini": 25,
      "Lemon juice": 15, "Cooking oil": 10}),

    ("Garlic Bread", "Food", 100,
     {"Bread": 100, "Butter": 20, "Garlic": 5}),

    ("Fattoush Salad", "Food", 120,
     {"Tomato": 60, "Cucumber": 60, "Lettuce": 40,
      "Flatbread": 1, "Lemon juice": 15}),

    ("Greek Salad", "Food", 150,
     {"Tomato": 60, "Cucumber": 60, "Lettuce": 40,
      "Feta cheese": 40, "Olives": 20}),

    ("Lentil Soup", "Food", 100,
     {"Lentils": 70, "Onion": 20, "Carrot": 30,
      "Water": 250, "Spice mix": 5}),

    ("Chicken Soup", "Food", 120,
     {"Chicken": 80, "Carrot": 30,
      "Water": 250, "Spice mix": 5}),

    ("Fresh Orange Juice", "Drinks", 120, {"Orange": 250}),

    ("Mango Juice", "Drinks", 120,
     {"Mango puree": 100, "Water": 150, "Sugar": 10}),

    ("Lemon Mint", "Drinks", 100,
     {"Lemon juice": 30, "Mint": 5, "Water": 200, "Sugar": 15}),

    ("Soft Drink", "Drinks", 40, {"Soft drink can": 1}),
    ("Mineral Water", "Drinks", 20, {"Water bottle": 1}),

    ("Tea", "Drinks", 30,
     {"Tea leaves": 3, "Water": 200, "Sugar": 5}),

    ("Coffee", "Drinks", 80,
     {"Coffee powder": 8, "Water": 200, "Sugar": 5}),

    ("Chocolate Cake", "Dessert", 150,
     {"Flour": 35, "Cocoa": 8, "Sugar": 25,
      "Butter": 20, "Egg": 0.5}),

    ("Ice Cream", "Dessert", 100, {"Ice cream base": 100}),
]

# PKR_SAMPLE_PRICES
PKR_PRICES = {'Chicken Biryani': 450, 'Beef Biryani': 550, 'Chicken Karahi': 1200, 'Mutton Karahi': 2200, 'Chicken Tikka': 600, 'Beef Kebab': 500, 'Grilled Chicken': 900, 'Chicken Shawarma': 350, 'Beef Shawarma': 450, 'Zinger Burger': 550, 'Beef Burger': 650, 'Chicken Pizza': 1400, 'Vegetable Pizza': 1100, 'French Fries': 250, 'Chicken Nuggets': 450, 'Hummus': 400, 'Garlic Bread': 350, 'Fattoush Salad': 450, 'Greek Salad': 550, 'Lentil Soup': 250, 'Chicken Soup': 350, 'Fresh Orange Juice': 350, 'Mango Juice': 300, 'Lemon Mint': 250, 'Soft Drink': 150, 'Mineral Water': 100, 'Tea': 120, 'Coffee': 300, 'Chocolate Cake': 400, 'Ice Cream': 250}
MENU = [(name, category, PKR_PRICES[name] * 100, recipe) for name, category, price, recipe in MENU]

PIECES = {
    "Flatbread", "Burger bun", "Soft drink can",
    "Water bottle", "Egg"
}

LIQUIDS = {"Water", "Lemon juice"}


def validate(conn):
    counts = {
        table: conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        for table in (
            "products", "orders", "order_items",
            "ingredients", "recipe_items"
        )
    }

    if counts["order_items"] != 5000:
        raise RuntimeError("Sales row count must be 5000.")

    if counts["orders"] != 2500:
        raise RuntimeError("Order count must be 2500.")

    if counts["products"] != len(MENU):
        raise RuntimeError("Menu count does not match.")

    actual_dates = conn.execute(
        "SELECT MIN(order_date), MAX(order_date) FROM orders"
    ).fetchone()

    if actual_dates != (START.isoformat(), END.isoformat()):
        raise RuntimeError("Date range does not match.")

    expected_days = (END - START).days + 1
    actual_days = conn.execute(
        "SELECT COUNT(DISTINCT order_date) FROM orders"
    ).fetchone()[0]

    if actual_days != expected_days:
        raise RuntimeError("Some dates are missing.")

    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Database relationship check failed.")

    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise RuntimeError("Database integrity check failed.")

    recipe_products = conn.execute(
        "SELECT COUNT(DISTINCT product_id) FROM recipe_items"
    ).fetchone()[0]

    if recipe_products != len(MENU):
        raise RuntimeError("Some menu items have no recipe.")

    return counts


def export_csv(conn, filename, query):
    folder = DATA / "exports"
    folder.mkdir(parents=True, exist_ok=True)

    cursor = conn.execute(query)

    with (folder / filename).open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)
        writer.writerow([column[0] for column in cursor.description])
        writer.writerows(cursor.fetchall())


def build_database(conn):
    rng = random.Random(20251005)

    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK (price_cents > 0)
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            order_date TEXT NOT NULL,
            branch TEXT NOT NULL,
            payment_method TEXT NOT NULL
        );

        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(order_id),
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0)
        );

        CREATE TABLE ingredients (
            ingredient_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            unit TEXT NOT NULL
        );

        CREATE TABLE recipe_items (
            recipe_item_id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            ingredient_id INTEGER NOT NULL REFERENCES ingredients(ingredient_id),
            quantity REAL NOT NULL CHECK (quantity > 0),
            UNIQUE (product_id, ingredient_id)
        );

        CREATE INDEX idx_orders_date ON orders(order_date);
        CREATE INDEX idx_items_order ON order_items(order_id);
        CREATE INDEX idx_items_product ON order_items(product_id);
    """)

    ingredient_names = sorted({
        ingredient
        for menu_item in MENU
        for ingredient in menu_item[3]
    })

    ingredient_ids = {
        name: index
        for index, name in enumerate(ingredient_names, start=1)
    }

    for name, ingredient_id in ingredient_ids.items():
        if name in PIECES:
            unit = "piece"
        elif name in LIQUIDS:
            unit = "ml"
        else:
            unit = "g"

        conn.execute(
            "INSERT INTO ingredients VALUES (?, ?, ?)",
            (ingredient_id, name, unit),
        )

    for product_id, item in enumerate(MENU, start=1):
        name, category, price, recipe = item

        conn.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?)",
            (product_id, name, category, price),
        )

        for ingredient, quantity in recipe.items():
            conn.execute("""
                INSERT INTO recipe_items
                    (product_id, ingredient_id, quantity)
                VALUES (?, ?, ?)
            """, (
                product_id,
                ingredient_ids[ingredient],
                quantity,
            ))

    days = [
        START + timedelta(days=index)
        for index in range((END - START).days + 1)
    ]

    dates = days + rng.choices(
        days,
        weights=[
            1.6 if day.weekday() in (4, 5) else 1
            for day in days
        ],
        k=2500 - len(days),
    )
    dates.sort()

    sizes = [1] * 1000 + [2] * 500 + [3] * 1000
    rng.shuffle(sizes)

    weights = [
        6, 4, 4, 2, 4, 3, 3, 9, 5, 6,
        4, 3, 2, 8, 3, 2, 2, 2, 2, 2,
        2, 4, 4, 4, 10, 12, 8, 4, 2, 3,
    ]

    item_id = 0

    for order_id, (day, size) in enumerate(
        zip(dates, sizes), start=1
    ):
        branch = rng.choices(
            ["Suwaiq", "Farid"], weights=[60, 40]
        )[0]

        payment_method = rng.choices(
            ["Cash", "Card"], weights=[35, 65]
        )[0]

        conn.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            (order_id, day.isoformat(), branch, payment_method),
        )

        selected_products = []

        while len(selected_products) < size:
            product_id = rng.choices(
                range(1, len(MENU) + 1),
                weights=weights,
            )[0]

            if product_id not in selected_products:
                selected_products.append(product_id)

        for product_id in selected_products:
            item_id += 1

            quantity = rng.choices(
                [1, 2, 3, 4], weights=[65, 25, 8, 2]
            )[0]

            conn.execute(
                "INSERT INTO order_items VALUES (?, ?, ?, ?, ?)",
                (
                    item_id,
                    order_id,
                    product_id,
                    quantity,
                    MENU[product_id - 1][2],
                ),
            )

    conn.commit()


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    temporary_db = DATA / "restaurant_build.db"
    resume_existing = temporary_db.exists()

    # closing() explicitly closes SQLite before Windows renames the file.
    with closing(sqlite3.connect(temporary_db)) as conn:
        if resume_existing:
            print("Checking previously built database...")
        else:
            build_database(conn)

        counts = validate(conn)

        export_csv(conn, "sales_5000.csv", """
            SELECT
                i.item_id,
                o.order_id,
                o.order_date,
                o.branch,
                o.payment_method,
                p.name AS menu_item,
                i.quantity,
                i.unit_price_cents / 100.0 AS unit_price_pkr,
                i.quantity * i.unit_price_cents / 100.0 AS line_total_pkr
            FROM order_items i
            JOIN orders o USING (order_id)
            JOIN products p USING (product_id)
            ORDER BY i.item_id
        """)

        export_csv(conn, "menu.csv", """
            SELECT product_id, name, category,
                   price_cents / 100.0 AS selling_price_pkr
            FROM products
        """)

        export_csv(conn, "recipes.csv", """
            SELECT p.name AS menu_item,
                   n.name AS ingredient,
                   r.quantity,
                   n.unit
            FROM recipe_items r
            JOIN products p USING (product_id)
            JOIN ingredients n USING (ingredient_id)
            ORDER BY p.product_id, r.recipe_item_id
        """)

        total_sales = conn.execute("""
            SELECT SUM(quantity * unit_price_cents)
            FROM order_items
        """).fetchone()[0] / 100

        report = {
            "data_type": "fictional sample",
            "currency": "PKR",
            "sales_lines": 5000,
            "start_date": str(START),
            "end_date": str(END),
            "counts": counts,
            "total_sales_pkr": total_sales,
            "validation": "PASSED",
        }

        (DATA / "validation.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

    # Both backup connections close before replacing the database.
    if DB.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = DATA / f"restaurant_backup_{timestamp}.db"

        with closing(sqlite3.connect(DB)) as old:
            with closing(sqlite3.connect(backup)) as saved:
                old.backup(saved)

        print("Old database backup:", backup)

    try:
        temporary_db.replace(DB)
    except PermissionError:
        raise RuntimeError(
            "Database is open in another app. Stop Streamlit and close "
            "database viewers, then run this script again. "
            "The ready database and backup remain safe."
        ) from None

    print("Sample database:", DB)
    print(json.dumps(report, indent=2))
    print("Database updated successfully.")
    print("Clear saved answers and restart Streamlit.")


if __name__ == "__main__":
    main()