from pathlib import Path
import streamlit as st
from date_resolver import today_pakistan
from graph import graph

st.set_page_config(page_title='Restaurant AI Agent',layout='wide')
st.title('Restaurant AI Agent')
st.caption('Fictional restaurant sample · 7,000 sales lines · 2025–2027 · PKR')
reference=today_pakistan()
with st.sidebar:
    st.header('Date reference')
    if st.checkbox('Use a demo reference date'):
        reference=st.date_input('Reference date',value=reference)
    st.caption(f'Today / yesterday queries use: {reference} (Pakistan)')
    if st.button('Clear saved answers'):
        st.session_state.answers={}
        st.session_state.pop('last_result',None)
if 'answers' not in st.session_state:st.session_state.answers={}
with st.form('question_form'):
    question=st.text_input('Ask about sales, menu, recipes or restaurant policies')
    submitted=st.form_submit_button('Ask')
if submitted and question.strip():
    db=Path(__file__).parent/'data'/'restaurant.db'
    info=db.stat()
    key=(question.strip(),str(reference),info.st_mtime_ns,info.st_size)
    try:
        with st.spinner('Checking your question…'):
            result=st.session_state.answers.get(key)
            if result is None:
                result=graph.invoke({'question':question.strip(),'reference_date':str(reference)})
                if result.get('route')!='clarify':st.session_state.answers[key]=result
            st.session_state.last_result=result
    except Exception as error:st.error(f'Could not answer: {error}')
result=st.session_state.get('last_result')
if result:
    st.caption('Selected route: '+result.get('route','').upper())
    st.write(result.get('answer',''))
    if result.get('results'):st.dataframe(result['results'],use_container_width=True)
    if result.get('sql'):
        with st.expander('SQL query'):st.code(result['sql'],language='sql')
    if result.get('sources'):st.caption('Sources: '+ '; '.join(result['sources']))
