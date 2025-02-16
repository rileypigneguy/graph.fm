from api import get_artist_tags
import streamlit as st
from utils import menu, redirect_unauthenticated, footer
import plotly.express as px
import pandas as pd


def create_treemap(data, rank_limit):
  # Convert the nested dictionary to a DataFrame
  records = []
  for artist, info in data.items():
      if info["rank"] > rank_limit:
        continue
      records.append({
          'artist': artist,
          'genre': info['tag_name'],
          'weight': info['weight']
      })

  df = pd.DataFrame(records)

  # Create treemap using plotly
  fig = px.treemap(
      df,
      path=[px.Constant("Music"), 'genre', 'artist'],
      values='weight',
      title='Music Artists by Genre',
      color='genre',
      color_discrete_sequence=px.colors.qualitative.Set3
  )

  # Update layout
  fig.update_layout(
      width=800,
      height=600,
      margin=dict(t=50, l=25, r=25, b=25)
  )

  # Update traces
  fig.update_traces(
      hovertemplate='<b>%{label}</b><br>Weight: %{value}<extra></extra>',
      textinfo="label+value"
  )

  return fig
  
def genres():
  with st.form("rank_compare_form"):
    rank_limit = st.selectbox(
        'Select type:',
        [25, 50, 100, 250, 500, 1000]
    )

    if st.form_submit_button('Get genre info!'):
      st.session_state.rank_limit = rank_limit
      if not st.session_state.artist_tags:
        data = get_artist_tags(1000)
        if data:
          aritst_tags, tag_relevance = data
          st.session_state.artist_tags = aritst_tags
          st.session_state.tag_relevance = tag_relevance
    

  if st.session_state.artist_tags:
    data = st.session_state.artist_tags
    #st.write(st.session_state.aritst_tags)
  
    # Display the treemap
    fig = create_treemap(data, st.session_state.rank_limit)
    st.plotly_chart(fig, use_container_width=True)



st.set_page_config(
    page_title="Graph.fm",
    layout="wide", 
    page_icon="📊",
)

redirect_unauthenticated()
st.title("🎸 Genre Analysis")
menu()
genres()
footer()