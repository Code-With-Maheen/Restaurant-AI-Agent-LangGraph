"""Reprice fictional sample records in PKR and preserve a backup."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import csv
import json
import re
import sqlite3

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'
DB=DATA/'restaurant.db'
# Illustrative sample prices, not verified market rates or currency conversion.
PRICES={
 'Chicken Biryani':450,'Beef Biryani':550,'Chicken Karahi':1200,
 'Mutton Karahi':2200,'Chicken Tikka':600,'Beef Kebab':500,
 'Grilled Chicken':900,'Chicken Shawarma':350,'Beef Shawarma':450,
 'Zinger Burger':550,'Beef Burger':650,'Chicken Pizza':1400,
 'Vegetable Pizza':1100,'French Fries':250,'Chicken Nuggets':450,
 'Hummus':400,'Garlic Bread':350,'Fattoush Salad':450,'Greek Salad':550,
 'Lentil Soup':250,'Chicken Soup':350,'Fresh Orange Juice':350,
 'Mango Juice':300,'Lemon Mint':250,'Soft Drink':150,'Mineral Water':100,
 'Tea':120,'Coffee':300,'Chocolate Cake':400,'Ice Cream':250,
}

def export(conn,name,query):
    folder=DATA/'exports';folder.mkdir(exist_ok=True)
    cursor=conn.execute(query)
    with (folder/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow([c[0] for c in cursor.description]);w.writerows(cursor.fetchall())

def main():
    if not DB.exists():raise FileNotFoundError(DB)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=DATA/f'restaurant_before_pkr_{stamp}.db'
    temporary=DATA/f'restaurant_pkr_build_{stamp}.db'
    with closing(sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)) as old:
        names={r[0] for r in old.execute('SELECT name FROM products')}
        if names!=set(PRICES):raise RuntimeError('Menu differs from the expected sample menu. No data changed.')
        before={t:old.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['products','orders','order_items','ingredients','recipe_items']}
        dump='\n'.join(old.iterdump())
        with closing(sqlite3.connect(backup)) as saved:old.backup(saved)
    # Enforce case-insensitive name comparisons in the database itself.
    dump=re.sub(r'\bname\s+TEXT\b(?!\s+COLLATE)', 'name TEXT COLLATE NOCASE',dump,flags=re.I)
    with closing(sqlite3.connect(temporary)) as conn:
        conn.executescript(dump)
        conn.execute('PRAGMA foreign_keys=ON')
        with conn:
            for name,price in PRICES.items():
                conn.execute('UPDATE products SET price_cents=? WHERE name=?',(price*100,name))
            conn.execute('''UPDATE order_items SET unit_price_cents=(SELECT p.price_cents FROM products p WHERE p.product_id=order_items.product_id)''')
            conn.execute('CREATE TABLE IF NOT EXISTS app_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            conn.executemany('INSERT OR REPLACE INTO app_metadata VALUES(?,?)',[('currency','PKR'),('data_type','fictional sample'),('pricing_basis','illustrative PKR menu prices, not FX conversion')])
        after={t:conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in before}
        if after!=before or after['order_items']!=5000:raise RuntimeError('Row validation failed; original database retained.')
        if conn.execute('PRAGMA foreign_key_check').fetchall():raise RuntimeError('Foreign key validation failed.')
        if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Integrity check failed.')
        if conn.execute("SELECT COUNT(*) FROM products WHERE name='chicken biryani'").fetchone()[0]!=1:raise RuntimeError('Case-insensitive match test failed.')
        total=conn.execute('SELECT SUM(quantity*unit_price_cents)/100.0 FROM order_items').fetchone()[0]
        june=conn.execute("SELECT SUM(i.quantity*i.unit_price_cents)/100.0 FROM order_items i JOIN orders o USING(order_id) WHERE o.order_date BETWEEN '2026-06-01' AND '2026-06-30'").fetchone()[0]
    try:temporary.replace(DB)
    except PermissionError:
        raise RuntimeError('Stop Streamlit and close database viewers, then run again. Original database and backup are safe.') from None
    with closing(sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)) as conn:
        export(conn,'sales_5000.csv','''SELECT i.item_id,o.order_id,o.order_date,o.branch,o.payment_method,p.name AS menu_item,i.quantity,i.unit_price_cents/100.0 AS unit_price_pkr,i.quantity*i.unit_price_cents/100.0 AS line_total_pkr FROM order_items i JOIN orders o USING(order_id) JOIN products p USING(product_id) ORDER BY i.item_id''')
        export(conn,'menu.csv','SELECT product_id,name,category,price_cents/100.0 AS selling_price_pkr FROM products')
    report={'data_type':'fictional sample','currency':'PKR','sales_lines':5000,'start_date':'2025-06-01','end_date':'2026-06-30','counts':after,'total_sales_pkr':total,'june_2026_sales_pkr':june,'validation':'PASSED'}
    (DATA/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # Keep future sample regeneration in PKR as well.
    generator=ROOT/'scripts'/'create_database.py'
    if generator.exists():
        text=generator.read_text(encoding='utf-8')
        if '# PKR_SAMPLE_PRICES' not in text:
            match=re.search(r'^PIECES\s*=',text,re.M)
            if match:
                block='# PKR_SAMPLE_PRICES\nPKR_PRICES = '+repr(PRICES)+'\nMENU = [(name, category, PKR_PRICES[name] * 100, recipe) for name, category, price, recipe in MENU]\n\n'
                text=text[:match.start()]+block+text[match.start():]
            else:print('NOTE: Re-run update_pkr.py after regenerating data.')
        text=text.replace('OMR','PKR').replace('_omr','_pkr')
        generator.write_text(text,encoding='utf-8')
    print('Backup:',backup)
    print(json.dumps(report,indent=2))
    print('PKR UPDATE PASSED. Restart Streamlit and clear saved answers.')

if __name__=='__main__':main()
