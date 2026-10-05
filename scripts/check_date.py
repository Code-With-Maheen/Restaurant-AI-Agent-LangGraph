from pathlib import Path
from contextlib import closing
import sqlite3

db = Path(__file__).resolve().parent.parent / "data" / "restaurant.db"
day = "2026-11-28"

with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as conn:
    row = conn.execute("""
        SELECT
            COUNT(DISTINCT o.order_id),
            COUNT(i.item_id),
            COALESCE(SUM(i.quantity), 0),
            COALESCE(SUM(i.quantity * i.unit_price_cents), 0),
            COALESCE(SUM(i.quantity * i.unit_cost_cents), 0),
            COALESCE(SUM(
                i.quantity * (i.unit_price_cents - i.unit_cost_cents)
            ), 0)
        FROM orders o
        LEFT JOIN order_items i ON i.order_id = o.order_id
        WHERE o.order_date = ?
    """, (day,)).fetchone()

print("Date:", day)
print("Orders:", row[0])
print("Sales lines:", row[1])
print("Units sold:", row[2])
print(f"Revenue: PKR {row[3] / 100:,.2f}")
print(f"Estimated food cost: PKR {row[4] / 100:,.2f}")
print(f"Estimated gross profit: PKR {row[5] / 100:,.2f}")