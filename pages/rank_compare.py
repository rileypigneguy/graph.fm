import streamlit as st
from utils import menu, redirect_unauthenticated, footer
import datetime
from api import compare_ranks
import pandas as pd

st.set_page_config(
    page_title="Graph.fm",
    layout="wide", 
    page_icon="📊",
)

def rank_compare():

    if not st.session_state.rank_comparison_results:
        st.session_state.rank_comparison_results = compare_ranks(
            st.session_state.scrobbles, 
            datetime.date.today() - datetime.timedelta(days=365), 
            datetime.date.today(), 
            'Artist'
        )
        
    with st.form("rank_compare_form"):
        date1 = st.date_input(
            'Enter comparison date:', 
            value = datetime.date.today() - datetime.timedelta(days=365),
            format="DD/MM/YYYY"
        )
        
        option = st.selectbox(
            'Select type:',
            ['Artist', 'Album', 'Track', 'Genre']
        )
        
        date2 = datetime.date.today()
    
        # Only run the comparison and show results when Compare is clicked
        if st.form_submit_button('Compare!'):
            st.session_state.rank_comparison_results = compare_ranks(st.session_state.scrobbles, date1, date2, option)
    
    # Show the stored results if they exist
    if st.session_state.rank_comparison_results:
        # Convert the list of dictionaries to a pandas DataFrame
        df = pd.DataFrame(st.session_state.rank_comparison_results)

        # Style the DataFrame
        def color_rank_change(val):
            color = '#f25e5e' if val < 0 else '#33b550' if val > 0 else 'white'
            return f'color: {color}'

        def color_scrobbles(val):
            color = 'white' if val == 0 else 'white'
            return f'color: {color}'

        # Apply the styling to both 'Rank Change' and 'Scrobbles (old)' columns
        styled_df = df.style\
            .map(color_rank_change, subset=['Rank Change'])\
            .map(color_scrobbles, subset=['Scrobbles (old)'])

        # Display the styled DataFrame
        st.dataframe(styled_df, use_container_width=True, height=800, hide_index=True)

st.title("📊 Rank Comparison")
redirect_unauthenticated()
menu()
rank_compare()
footer()