import json
from typing import TypedDict
from langgraph.graph import START,END,StateGraph
from sql_agent import ask_sql,client,MODEL
from rag_agent import ask_rag

class AgentState(TypedDict):
    reference_date:str
    period:dict
    question:str
    route:str
    answer:str
    sql:str
    results:list[dict]
    sources:list[str]

def router_node(state):
    prompt=f'''Classify the user's restaurant question. Return JSON with key "route".
    sql: recorded sales/revenue, orders, menu/prices, recipe ingredients and amounts,
    branches, dates, payments, theoretical recipe ingredient consumption.
    rag: restaurant policies, complaints, refunds, cancellations, SOPs, food handling.
    clarify: unrelated questions, unclear topic, or questions needing both sources.
    Send ambiguous menu names and missing financial data questions to sql so it can
    clarify using the actual catalog. Recipes are sql; procedural policies are rag.
    Example: {{"route":"sql"}}
    Question: {state['question']}'''
    response=client.models.generate_content(model=MODEL,contents=prompt,config={'response_mime_type':'application/json'})
    route=json.loads(response.text or '{}').get('route')
    if route not in {'sql','rag','clarify'}:raise ValueError('Invalid router response.')
    return {'route':route}

def sql_node(state):
    result=ask_sql(state['question'],state.get('reference_date'))
    if result.get('clarification'):
        return {'route':'clarify','answer':result['clarification'],'sql':'','results':[],'sources':[]}
    rows=result['results']
    if not rows or all(all(v is None for v in r.values()) for r in rows):
        answer='No matching records were found for that request.'
    elif len(rows)==1:
        answer='\n\n'.join(f"{k.replace('_',' ').capitalize()}: {v:,.2f}" if k in result['money_columns'] and isinstance(v,(int,float)) else f"{k.replace('_',' ').capitalize()}: {v}" for k,v in rows[0].items())
    else:answer=f'Found {len(rows)} results. See the table below.'
    period=result.get('period')
    if period:answer=f"Period: {period['start']} to {period['end']}\n\n"+answer
    if any('cost' in k or 'profit' in k for r in rows for k in r):
        answer+='\n\nEstimated food cost and gross profit use sample ingredient costs. Net profit requires operating expenses.'
    return {'period':period,'answer':answer,'sql':result['sql'],'results':rows,'sources':['restaurant.db (fictional sample; all money in PKR; future-dated rows are demo records)']}

def rag_node(state):
    result=ask_rag(state['question'])
    return {'answer':result['answer'],'sources':list(dict.fromkeys(result['sources'])),'sql':'','results':[]}

def clarify_node(state):
    return {'answer':'Please ask one menu, recipe, sales or policy question at a time.','sources':[],'sql':'','results':[]}

builder=StateGraph(AgentState)
builder.add_node('router',router_node)
builder.add_node('sql_agent',sql_node)
builder.add_node('rag_agent',rag_node)
builder.add_node('clarify',clarify_node)
builder.add_edge(START,'router')
builder.add_conditional_edges('router',lambda s:s['route'],{'sql':'sql_agent','rag':'rag_agent','clarify':'clarify'})
for node in ['sql_agent','rag_agent','clarify']:builder.add_edge(node,END)
graph=builder.compile()
