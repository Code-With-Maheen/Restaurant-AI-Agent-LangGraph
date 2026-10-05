"""Replace fictional sample sales with 7,000 lines across 2025-2027."""
from contextlib import closing
from datetime import date,datetime,timedelta
from pathlib import Path
import csv,json,random,sqlite3

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data';DB=DATA/'restaurant.db'
START=date(2025,1,1);END=date(2027,12,31)
# Sample ingredient cost in PKR paisa per stored g/ml/piece unit.
COSTS={'Rice':45,'Chicken':100,'Beef':160,'Mutton':240,'Onion':20,'Tomato':25,
 'Cooking oil':65,'Spice mix':180,'Yogurt':35,'Flatbread':3000,'Garlic sauce':80,
 'Lettuce':40,'Burger bun':4500,'Flour':20,'Cheese':220,'Tomato sauce':65,
 'Yeast':250,'Bell pepper':50,'Potato':18,'Salt':10,'Breadcrumbs':40,
 'Chickpeas':50,'Tahini':180,'Lemon juice':60,'Bread':40,'Butter':240,'Garlic':120,
 'Cucumber':20,'Feta cheese':250,'Olives':220,'Lentils':60,'Carrot':20,'Water':1,
 'Orange':35,'Mango puree':70,'Sugar':20,'Mint':120,'Soft drink can':10000,
 'Water bottle':6000,'Tea leaves':180,'Coffee powder':550,'Cocoa':250,
 'Egg':3000,'Ice cream base':100}

def export(c,path,query):
    cur=c.execute(query)
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow([v[0] for v in cur.description]);w.writerows(cur.fetchall())

def main():
    if not DB.exists():raise FileNotFoundError(DB)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=DATA/f'restaurant_before_7000_{stamp}.db'
    tmp=DATA/f'restaurant_7000_build_{stamp}.db'
    with closing(sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)) as old:
        if old.execute("SELECT value FROM app_metadata WHERE key='currency'").fetchone()!=('PKR',):
            raise RuntimeError('Run the previous PKR update first.')
        ingredients={r[0] for r in old.execute('SELECT name FROM ingredients')}
        if ingredients!=set(COSTS):raise RuntimeError('Ingredient catalog differs from the sample; no data changed.')
        with closing(sqlite3.connect(backup)) as saved:old.backup(saved)
        with closing(sqlite3.connect(tmp)) as built:old.backup(built)
    rng=random.Random(70002027)
    with closing(sqlite3.connect(tmp)) as c:
        c.execute('PRAGMA foreign_keys=ON')
        columns={r[1] for r in c.execute('PRAGMA table_info(ingredients)')}
        if 'cost_per_unit_cents' not in columns:c.execute('ALTER TABLE ingredients ADD COLUMN cost_per_unit_cents INTEGER NOT NULL DEFAULT 0')
        columns={r[1] for r in c.execute('PRAGMA table_info(order_items)')}
        if 'unit_cost_cents' not in columns:c.execute('ALTER TABLE order_items ADD COLUMN unit_cost_cents INTEGER NOT NULL DEFAULT 0')
        with c:
            c.execute('DELETE FROM order_items');c.execute('DELETE FROM orders')
            for name,cost in COSTS.items():c.execute('UPDATE ingredients SET cost_per_unit_cents=? WHERE name=?',(cost,name))
            menu=c.execute('''SELECT p.product_id,p.price_cents,SUM(r.quantity*n.cost_per_unit_cents) FROM products p JOIN recipe_items r USING(product_id) JOIN ingredients n USING(ingredient_id) GROUP BY p.product_id ORDER BY p.product_id''').fetchall()
            costs={pid:int(round(cost)) for pid,price,cost in menu};prices={pid:price for pid,price,cost in menu}
            if any(costs[pid]>=price for pid,price,_ in menu):raise RuntimeError('Sample ingredient cost must be below selling price.')
            days=[START+timedelta(days=i) for i in range((END-START).days+1)]
            dates=days+rng.choices(days,weights=[1.6 if d.weekday() in (4,5) else 1 for d in days],k=3500-len(days));dates.sort()
            sizes=[1]*1400+[2]*700+[3]*1400;rng.shuffle(sizes)
            item_id=0
            weights=[6,4,4,2,4,3,3,9,5,6,4,3,2,8,3,2,2,2,2,2,2,4,4,4,10,12,8,4,2,3]
            ids=[m[0] for m in menu]
            for oid,(day,size) in enumerate(zip(dates,sizes),1):
                branch=rng.choices(['Suwaiq','Farid'],weights=[60,40])[0]
                payment=rng.choices(['Cash','Card'],weights=[35,65])[0]
                c.execute('INSERT INTO orders VALUES(?,?,?,?)',(oid,day.isoformat(),branch,payment))
                chosen=[]
                while len(chosen)<size:
                    pid=rng.choices(ids,weights=weights)[0]
                    if pid not in chosen:chosen.append(pid)
                for pid in chosen:
                    item_id+=1;qty=rng.choices([1,2,3,4],weights=[65,25,8,2])[0]
                    c.execute('''INSERT INTO order_items(item_id,order_id,product_id,quantity,unit_price_cents,unit_cost_cents) VALUES(?,?,?,?,?,?)''',(item_id,oid,pid,qty,prices[pid],costs[pid]))
            c.executemany('INSERT OR REPLACE INTO app_metadata VALUES(?,?)',[('data_type','fictional sample, including future-dated demo records'),('cost_basis','estimated recipe ingredients only; excludes expenses, tax, waste, discounts, refunds and commissions'),('sample_version','7000_2025_2027')])
        counts={t:c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['products','orders','order_items','ingredients','recipe_items']}
        assert counts['order_items']==7000 and counts['orders']==3500
        assert c.execute('SELECT MIN(order_date),MAX(order_date) FROM orders').fetchone()==(str(START),str(END))
        assert c.execute('SELECT COUNT(DISTINCT order_date) FROM orders').fetchone()[0]==len(days)
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
        totals=c.execute('SELECT SUM(quantity*unit_price_cents)/100.0,SUM(quantity*unit_cost_cents)/100.0,SUM(quantity*(unit_price_cents-unit_cost_cents))/100.0 FROM order_items').fetchone()
        yearly=c.execute("SELECT strftime('%Y',o.order_date),COUNT(DISTINCT o.order_id),SUM(i.quantity),SUM(i.quantity*i.unit_price_cents)/100.0,SUM(i.quantity*i.unit_cost_cents)/100.0,SUM(i.quantity*(i.unit_price_cents-i.unit_cost_cents))/100.0 FROM orders o JOIN order_items i USING(order_id) GROUP BY strftime('%Y',o.order_date)").fetchall()
        report={'currency':'PKR','data_type':'fictional sample; future-dated rows are demo records','counts':counts,'start_date':str(START),'end_date':str(END),'revenue_pkr':totals[0],'estimated_food_cost_pkr':totals[1],'estimated_gross_profit_pkr':totals[2],'yearly_columns':['year','orders','units','revenue_pkr','estimated_food_cost_pkr','estimated_gross_profit_pkr'],'yearly':yearly,'validation':'PASSED'}
    try:tmp.replace(DB)
    except PermissionError:raise RuntimeError('Stop Streamlit/DB viewers before running. Original DB and backup are safe.') from None
    folder=DATA/'exports';folder.mkdir(exist_ok=True)
    with closing(sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)) as c:
        export(c,folder/'sales_7000.csv','''SELECT o.order_id,o.order_date,o.branch,o.payment_method,p.name,i.quantity,i.unit_price_cents/100.0 AS unit_price_pkr,i.unit_cost_cents/100.0 AS estimated_unit_food_cost_pkr,i.quantity*i.unit_price_cents/100.0 AS revenue_pkr,i.quantity*i.unit_cost_cents/100.0 AS estimated_food_cost_pkr,i.quantity*(i.unit_price_cents-i.unit_cost_cents)/100.0 AS estimated_gross_profit_pkr FROM order_items i JOIN orders o USING(order_id) JOIN products p USING(product_id) ORDER BY i.item_id''')
        export(c,folder/'ingredient_costs.csv','SELECT ingredient_id,name,unit,cost_per_unit_cents/100.0 AS sample_cost_per_unit_pkr FROM ingredients')
    (DATA/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Backup:',backup);print(json.dumps(report,indent=2));print('7,000 ENTRY UPDATE PASSED. Restart Streamlit and clear saved answers.')

if __name__=='__main__':main()
