import streamlit as st
from utils import menu, redirect_unauthenticated, footer
import pandas as pd
import datetime
import plotly.express as px
from collections import Counter



st.set_page_config(
  page_title="Graph.fm",
  layout="wide", 
  page_icon="📊",
)


def genre_trend():

  with st.form("rank_compare_form"):
    # Add date inputs for start and end date
    col1, col2 = st.columns(2)
    with col1:
      genre_amount = st.selectbox(
          'Select the Number of Top Genres',
          [5,10, 25, 50, 100, 1000],
          index=1
      )

    with col2:
      smoothing_period = st.selectbox(
          'Choose period length',
          ['Day','Week','Month','Quarter','Year'],
          index=2
      )

    if st.form_submit_button('Get genre trends!'):
      # Update session state **before** calling genre_dict
      
      generate_graphs(
        smoothing_period,
        genre_amount
      )

    
  # Convert to DataFrame (date is already a datetime.date object)
  if ("genre_tread1" in st.session_state and 
      "genre_tread2" in st.session_state and
      st.session_state.genre_tread2 and 
      st.session_state.genre_tread1
     ):
    
    container = st.container(border=True)
    container.plotly_chart(st.session_state.genre_tread1)
    container.plotly_chart(st.session_state.genre_tread2)
    container.plotly_chart(st.session_state.genre_tread3)
    container.plotly_chart(st.session_state.genre_tread4)


mapping = {
    'Day': 'D',
    'Month': 'M',    
    'Week': 'W',   
    'Quarter': 'Q',     
    'Year': 'Y',     
}

def generate_graphs(smoothing, top_x):
  # Convert to DataFrame
  df = pd.DataFrame(st.session_state.scrobbles)
  # Ensure 'date' is a datetime object
  if not pd.api.types.is_datetime64_any_dtype(df["date"]):
      df["date"] = pd.to_datetime(df["date"])

  # For cumulative graphs, group by the selected period
  df["period"] = df["date"].dt.to_period(mapping[smoothing]).apply(lambda r: r.start_time)
  genre_counts_cumulative = df.groupby(["period", "genre"]).size().unstack(fill_value=0)
  genre_cumulative = genre_counts_cumulative.cumsum()

  # Get top X genres based on FINAL cumulative totals (last row)
  final_totals = genre_cumulative.iloc[-1] if len(genre_cumulative) > 0 else genre_cumulative.sum()
  top_genres = final_totals.nlargest(top_x).index.tolist()

  # Generate first graph (cumulative counts)
  other_genres = genre_cumulative.drop(columns=top_genres, errors='ignore').sum(axis=1)
  genre_data1 = genre_cumulative[top_genres].copy()
  genre_data1["Other"] = other_genres
  # Order: period, then top genres in reverse, then Other on top
  columns_order = ["period"] + top_genres[::-1] + ["Other"]
  genre_data1 = genre_data1.reset_index()[columns_order]
  fig1 = px.area(
      genre_data1,
      x="period",
      y=genre_data1.columns[1:],
      title="Cumulative Music Genre Listens Over Time",
      labels={"value": "Total Listens", "period": "Date"},
  )
  fig1.update_layout(legend=dict(traceorder='reversed'))

  # Generate second graph (cumulative percentages)
  genre_percentage = genre_cumulative.div(genre_cumulative.sum(axis=1), axis=0) * 100
  genre_data2 = genre_percentage[top_genres].copy()
  genre_data2["Other"] = genre_percentage.drop(columns=top_genres, errors='ignore').sum(axis=1)
  genre_data2 = genre_data2.reset_index()[columns_order]
  fig2 = px.area(
      genre_data2,
      x="period",
      y=genre_data2.columns[1:],
      title="Cumulative Music Genre Distribution Over Time",
      labels={"value": "Percentage (%)", "period": "Date"},
  )
  fig2.update_layout(legend=dict(traceorder='reversed'))

  # For rolling graphs, group by day to ensure a data point per day
  df["day"] = df["date"].dt.date
  genre_counts_daily = df.groupby(["day", "genre"]).size().unstack(fill_value=0)
  genre_counts_daily.index = pd.to_datetime(genre_counts_daily.index)

  # Define window sizes in days based on smoothing period
  window_sizes = {
      'D': 1,      # 1 day
      'W': 7,      # 1 week
      'M': 30,     # ~1 month
      'Q': 90,     # ~1 quarter
      'Y': 365     # ~1 year
  }
  window_size = window_sizes[mapping[smoothing]]

  # Generate third graph (rolling window counts)
  all_rolling_counts = genre_counts_daily.rolling(window=f"{window_size}D", min_periods=1).sum()
  available_top_genres = [c for c in top_genres if c in all_rolling_counts.columns]
  rolling_top_counts = all_rolling_counts[available_top_genres].copy()
  rolling_other_counts = all_rolling_counts.drop(columns=available_top_genres, errors='ignore').sum(axis=1)
  rolling_top_counts["Other"] = rolling_other_counts
  rolling_counts_data = rolling_top_counts.reset_index()
  rolling_cols = ["day"] + available_top_genres[::-1] + ["Other"]
  rolling_counts_data = rolling_counts_data[rolling_cols]

  # Fixed period label logic
  period_labels = {
      'D': 'Day',
      'W': 'Week',
      'M': 'Month',
      'Q': 'Quarter',
      'Y': 'Year'
  }
  period_label = period_labels[mapping[smoothing]]

  # Proper pluralization
  if window_size == 1:
      window_text = f"1 {period_label}"
  else:
      window_text = f"{window_size} {period_label}s"

  fig3 = px.area(
      rolling_counts_data,
      x="day",
      y=rolling_counts_data.columns[1:],
      title=f"Rolling Music Genre Listens Over {window_text}",
      labels={"value": "Listens", "day": "Date"},
  )
  fig3.update_layout(legend=dict(traceorder='reversed'))

  # Generate fourth graph (rolling window percentages)
  rolling_percentages = all_rolling_counts.div(all_rolling_counts.sum(axis=1), axis=0) * 100
  rolling_top_pct = rolling_percentages[available_top_genres].copy()
  rolling_other_pct = rolling_percentages.drop(columns=available_top_genres, errors='ignore').sum(axis=1)
  rolling_top_pct["Other"] = rolling_other_pct
  rolling_pct_data = rolling_top_pct.reset_index()
  rolling_pct_data = rolling_pct_data[rolling_cols]

  fig4 = px.area(
      rolling_pct_data,
      x="day",
      y=rolling_pct_data.columns[1:],
      title=f"Rolling Music Genre Distribution Over {window_text}",
      labels={"value": "Percentage (%)", "day": "Date"},
  )
  fig4.update_layout(legend=dict(traceorder='reversed'))

  # Store figures in session state
  st.session_state.genre_tread1 = fig1
  st.session_state.genre_tread2 = fig2
  st.session_state.genre_tread3 = fig3
  st.session_state.genre_tread4 = fig4

redirect_unauthenticated()
st.title("🎸 Genre Trends!")
menu()
genre_trend()
footer()