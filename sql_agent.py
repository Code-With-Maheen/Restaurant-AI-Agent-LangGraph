import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
from dotenv import load_dotenv
from google import genai
from datetime import date
from date_resolver import today_pakistan,resolve_date_spec

PROJECT_ROOT=Path(__file__).resolve().parent
DB_PATH=PROJECT_ROOT/'data'/'restaurant.db'
load_dotenv(PROJECT_ROOT/'.env')
api_key=os.getenv('GEMINI_API_KEY')
if not api_key:raise RuntimeError('GEMINI_API_KEY .env file mein nahi mili.')
client=genai.Client(api_key=api_key)
MODEL=os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')

def database_context():
    if not DB_PATH.exists():raise FileNotFoundError(DB_PATH)
    with closing(sqlite3.connect(DB_PATH.as_uri()+'?mode=ro',uri=True)) as conn:
        schema=[r[0] for r in conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('products','orders','order_items','ingredients','recipe_items') ORDER BY name")]
        dates=conn.execute('SELECT MIN(order_date),MAX(order_date) FROM orders').fetchone()
        menu=conn.execute('SELECT product_id,name,category FROM products ORDER BY product_id').fetchall()
        ingredients=conn.execute('SELECT name,unit FROM ingredients ORDER BY name').fetchall()
    return '\n'.join(schema)+f'\nActual dates: {dates}\nActual menu: {menu}\nActual ingredients: {ingredients}'

def generate_plan(question,context,feedback='',reference=None):
    prompt=f'''You answer restaurant database questions by planning SQLite queries.
    Actual schema, dates and catalog:
    {context}
    Return JSON with keys sql, clarification, reason, date_spec.
    Reference date in Pakistan: {reference}. Interpret English and Roman Urdu.
    date_spec kinds and examples:
    {{"kind":"none"}} for menu/recipes; {{"kind":"all"}} for all recorded sales;
    {{"kind":"date","date":"2026-06-01"}};
    {{"kind":"range","start":"2025-01-01","end":"2025-12-31"}};
    {{"kind":"year","year":2025}}; {{"kind":"month","year":2026,"month":6}};
    {{"kind":"relative_day","offset":-2}} day before yesterday, -1 yesterday,
    0 today, 1 tomorrow, 2 day after tomorrow;
    {{"kind":"weekday","weekday":6,"direction":"previous","occurrence":2}}
    for second last Sunday. Weekdays Monday=0 through Sunday=6.
    Last/next weekday excludes today. 'Last two Sundays' needs a clarification
    if user wants separate days rather than a continuous range.
    Python resolves dates. Whenever date_spec is not none, filter o.order_date
    BETWEEN :date_start AND :date_end with BOTH named parameters. Do not calculate
    relative dates in SQL or hardcode resolved dates. For recorded sales without
    a period use all. A full-year request without a specified year is ambiguous.
    For sales summaries include distinct orders, units sold, revenue, estimated
    food cost and estimated gross profit when requested. Revenue is sales before
    subtracting costs, never call revenue 'with profit' or add profit to revenue.
    For an answerable question: sql is ONE SELECT statement; clarification is null.
    For ambiguity: sql is null; clarification is a short question with actual choices.
    For missing data: sql is null; clarification explains exactly what is unavailable.
    Never assume that a broad item name selects one of several menu items.
    Example: recipe of biryani -> ask Chicken Biryani or Beef Biryani.
    Resolve natural wording and spelling from the actual catalog; do not invent names.
    Match names case-insensitively with COLLATE NOCASE. If a spelling cannot be
    resolved confidently, ask a short clarification rather than guess.
    - products is menu; recipe_items is ingredient amount per ONE menu sale unit.
    - Join ingredients for units. Never add quantities with different units.
    - orders is transactions; order_items is sales lines. These counts differ.
    - *_cents columns store PKR paisa (100 = PKR 1). Return money as paisa
      using aliases ending _cents; caller divides by 100. Do not divide in SQL.
    - Revenue=SUM(order_items.quantity*order_items.unit_price_cents).
    - Ingredient consumption calculated from recipes/sales is theoretical.
    - ingredients.cost_per_unit_cents is sample paisa per ingredient unit.
    - order_items.unit_cost_cents is a historical estimated ingredient cost per
      menu unit. Food cost=SUM(quantity*unit_cost_cents); estimated gross profit
      =SUM(quantity*(unit_price_cents-unit_cost_cents)). Use aliases ending _cents.
    - Recipe production cost=SUM(recipe quantity*ingredient cost_per_unit_cents).
    - Customer 'cost/price of five burgers' means selling price, not food cost.
    - Net profit unavailable: rent, wages and other expenses are absent. Clarify
      net profit requests. Actual stock, waste, VAT, refunds and customers absent.
    - Do not modify tables, use WITH, or query sqlite_master.
    - For daily, monthly and yearly summaries, return ALL periods in the
  requested date range, ordered chronologically. Do not use LIMIT.
- Limit other lists to 20 rows.
- Return all recipe lines for the requested item.
    - Infer date expressions only when unambiguous. Ask if period/year is unclear.
    - Out-of-range dates have no records; do not silently substitute another period.
    User question: {question}
    Previous attempt feedback (if any): {feedback}
    '''
    response=client.models.generate_content(model=MODEL,contents=prompt,config={'response_mime_type':'application/json'})
    if not response.text:raise RuntimeError('No model response.')
    return json.loads(response.text)

def execute_readonly(sql,params=None):
    if not isinstance(sql,str):raise ValueError('SQL must be text.')
    sql=sql.strip().removesuffix(';').strip()
    if not sql.split() or sql.split()[0].lower()!='select' or ';' in sql:
        raise ValueError('Only one SELECT query is allowed.')
    with closing(sqlite3.connect(DB_PATH.as_uri()+'?mode=ro',uri=True)) as conn:
        conn.execute('PRAGMA query_only=ON')
        tables={'products','orders','order_items','ingredients','recipe_items'}
        def authorize(action,arg1,arg2,db,trigger):
            if action==sqlite3.SQLITE_READ:return sqlite3.SQLITE_OK if arg1 in tables else sqlite3.SQLITE_DENY
            if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_FUNCTION:return sqlite3.SQLITE_DENY if (arg2 or '').lower() in {'load_extension','readfile','writefile'} else sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        conn.set_authorizer(authorize)
        budget=[300]
        def stop_long_query():
            budget[0]-=1
            return budget[0]<=0
        conn.set_progress_handler(stop_long_query,10000)
        cursor=conn.execute(sql,params or {})
        columns=[r[0] for r in cursor.description]
        rows = cursor.fetchall()
    results=[];money=[]
    for row in rows:
        item={}
        for column,value in zip(columns,row):
            if column.endswith('_cents'):
                label=column.removesuffix('_cents')+'_pkr'
                item[label]=round(value/100,2) if value is not None else None
                if label not in money:money.append(label)
            else:item[column]=value
        results.append(item)
    return sql,results,money

def ask_sql(question,reference_date=None):
    reference=date.fromisoformat(reference_date) if reference_date else today_pakistan()
    with closing(sqlite3.connect(DB_PATH.as_uri()+'?mode=ro',uri=True)) as c:
        first,last=c.execute('SELECT MIN(order_date),MAX(order_date) FROM orders').fetchone()
    context=database_context();feedback='' 
    for attempt in range(2):
        plan=generate_plan(question,context,feedback,reference.isoformat())
        if plan.get('sql') is None:
            return {'question':question,'sql':'','results':[],'money_columns':[],
                    'clarification':plan.get('clarification') or 'Please make the question more specific.'}
        try:
            period=resolve_date_spec(plan.get('date_spec'),reference,first,last)
            params={}
            if period:
                if ':date_start' not in plan['sql'] or ':date_end' not in plan['sql']:
                    raise ValueError('Use both :date_start and :date_end to filter the requested period.')
                params={'date_start':period['start'],'date_end':period['end']}
            sql,rows,money=execute_readonly(plan['sql'],params)
        except (sqlite3.Error,ValueError,KeyError,TypeError) as error:
            if attempt==0:
                feedback=f'SQL failed: {error}. Previous SQL: {plan["sql"]}. Correct it using the actual schema.'
                continue
            raise RuntimeError('The database query could not be completed. Please rephrase the question.') from error
        empty=not rows or all(all(v is None for v in row.values()) for row in rows)
        if empty and attempt==0:
            feedback=f'Query returned no matching data: {sql}. Recheck spelling, case, joins and the requested date. Do not change the user intent or invent data. Ask a clarification if necessary.'
            continue
        return {'question':question,'sql':sql,'results':rows,'money_columns':money,'clarification':None,'period':period,'reference_date':reference.isoformat()}
    raise RuntimeError('No usable query returned.')

if __name__=='__main__':
    for q in ['recipe of chicken biryani','recipe of biryani','What was total revenue in June 2026?']:
        print('\nQUESTION:',q)
        try:print(ask_sql(q))
        except Exception as error:print('ERROR:',error)
