import streamlit as st
from utils import menu, redirect_unauthenticated, footer
import datetime
from api import get_uniqued_data
import pandas as pd

st.set_page_config(
    page_title="Graph.fm",
    layout="wide", 
    page_icon="📊",
)

def uniqued():
    if 'uniqued_results' not in st.session_state:
        st.session_state.uniqued_results = None

    with st.form("uniqued_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            option = st.selectbox(
                'Select type:',
                ['Songs', 'Albums']
            )

        with col2:
            top_x = st.number_input(
                'Top X amount:',
                min_value=1,
                value=50,
                step=1
            )

        with col3:
            end_date = st.date_input(
                'Up to date:',
                value=datetime.date.today(),
                format="DD/MM/YYYY"
            )

        if st.form_submit_button('Analyze!'):
            st.session_state.uniqued_results = get_uniqued_data(
                st.session_state.scrobbles, 
                option, 
                top_x,
                end_date
            )

    # Show the stored results if they exist
    if st.session_state.uniqued_results:
        # Convert the list of dictionaries to a pandas DataFrame
        df = pd.DataFrame(st.session_state.uniqued_results)

        # Reset index to start from 1 and make it a column
        df.insert(0, '#', range(1, len(df) + 1))

        # Display the styled DataFrame
        st.dataframe(df, use_container_width=True, height=800, hide_index=True)

st.title("🎵 Uniqued")
redirect_unauthenticated()
menu()
uniqued()
footer()