import streamlit as st
from utils import menu, redirect_unauthenticated, footer
import pandas as pd
import datetime
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from collections import Counter



st.set_page_config(
  page_title="Graph.fm",
  layout="wide", 
  page_icon="📊",
)

def generate_stats_graph(period):
    # Dictionary to map period to pandas resample frequency
    period_freq = {
        'Day': 'D',
        'Week': 'W',
        'Month': 'M',
        'Quarter': 'Q',
        'Year': 'Y'
    }

    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.scrobbles)
    # Convert 'date' to datetime
    df['date'] = pd.to_datetime(df['date'])

    # Aggregate counts based on selected period
    df_counts = df.groupby(pd.Grouper(key='date', freq=period_freq[period])).agg(
        scrobbles=('track_name', 'count'),
        unique_artists=('artist_name', 'nunique'),
        unique_albums=('album_name', 'nunique'),
        unique_tracks=('track_name', 'nunique'),
        unique_genres=('genre', 'nunique')
    ).reset_index()

    # Initialize cumulative sets
    seen_tracks, seen_artists, seen_albums, seen_genres = set(), set(), set(), set()
    cumulative_data = []

    # Calculate cumulative unique counts based on period
    for date, group in df.groupby(pd.Grouper(key='date', freq=period_freq[period])):
        seen_tracks.update(group["track_name"])
        seen_artists.update(group["artist_name"])
        seen_albums.update(group["album_name"])
        seen_genres.update(group["genre"])
        cumulative_data.append({
            "date": date,
            "scrobbles": df[df["date"] <= date].shape[0],  # Total scrobbles seen so far
            "unique_tracks": len(seen_tracks),
            "unique_artists": len(seen_artists),
            "unique_albums": len(seen_albums),
            "unique_genres": len(seen_genres),
        })

    # Convert cumulative data to DataFrame
    df_cumulative = pd.DataFrame(cumulative_data)

    # Create period-specific title suffix
    period_title = f"by {period}" if period != 'Day' else "(Daily)"

    # Plotly line chart (Periodic Trends)
    fig_daily = px.line(df_counts, x="date",
                        y=["scrobbles", "unique_artists", "unique_albums", "unique_tracks", "unique_genres"],
                        markers=True, 
                        title=f"Music Trends {period_title}",
                        labels={"value": "Count", "variable": "Metric"})

    # Create cumulative figure with secondary y-axis
    fig_cumulative = go.Figure()

    # Add scrobbles to primary y-axis
    fig_cumulative.add_trace(
        go.Scatter(x=df_cumulative['date'], y=df_cumulative['scrobbles'],
                  name="scrobbles", mode='lines+markers')
    )

    # Add unique counts to secondary y-axis
    unique_metrics = ['unique_artists', 'unique_albums', 'unique_tracks', 'unique_genres']
    for metric in unique_metrics:
        fig_cumulative.add_trace(
            go.Scatter(x=df_cumulative['date'], y=df_cumulative[metric],
                      name=metric, mode='lines+markers',
                      yaxis='y2')
        )

    # Update layout with secondary y-axis and legend position
    fig_cumulative.update_layout(
        title=f"Cumulative Music Trends {period_title}",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Total Scrobbles",
                   side="left"),
        yaxis2=dict(title="Total remaning metrics",
                    side="right",
                    overlaying="y"),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.05
        ),
        # Adjust margins to accommodate legend
        margin=dict(r=150)
    )

    # Store in session state
    st.session_state.listening_stats_chart = fig_daily
    st.session_state.cumulative_listening_chart = fig_cumulative


def listening_stats():
    if not st.session_state.listening_stats_chart or not st.session_state.cumulative_listening_chart:
        generate_stats_graph("Day")

    with st.form("rank_compare_form"):
        # Add date inputs for start and end date
        smoothing_period = st.selectbox(
          'Choose period length',
          ['Day','Week','Month','Quarter','Year'],
          index=0
        )

        if st.form_submit_button('Customize Graph!'):
            generate_stats_graph(
                smoothing_period,
              )

    # Display in Streamlit
    container = st.container(border=True)
    container.plotly_chart(st.session_state.listening_stats_chart )
    container.plotly_chart(st.session_state.cumulative_listening_chart)

    

redirect_unauthenticated()
st.title("🎶 Scrobbles/Artist/Album/Track/Genre Stats!")
menu()
listening_stats()
footer()