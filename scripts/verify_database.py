from pathlib import Path
from contextlib import closing
import json,sqlite3
p=Path(__file__).resolve().parent.parent/'data'/'restaurant.db'
with closing(sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)) as c:
    for t in ['products','orders','order_items','ingredients','recipe_items']:
        print(t,c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
    print('Date range:',c.execute('SELECT MIN(order_date),MAX(order_date) FROM orders').fetchone())
    print('Foreign key errors:',c.execute('PRAGMA foreign_key_check').fetchall())
    print('Integrity:',c.execute('PRAGMA integrity_check').fetchone()[0])
print((p.parent/'validation.json').read_text())
