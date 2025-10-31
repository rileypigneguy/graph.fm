from warnings import formatwarning
from api import genre_dict
import streamlit as st
from utils import menu, redirect_unauthenticated, footer
import plotly.express as px
import pandas as pd
import datetime


def create_treemap2(scrobbles,
                    rank_limit,
                    start_date,
                    end_date,
                    genre_field='genre'):
    records = []
    for scrobble in scrobbles:
        artist_name = scrobble["artist_name"]
        genre = scrobble[genre_field]
        if not genre or genre == "NA":
            print(f"Artist {artist_name} didn't have a valid tag")
            continue
        if scrobble["date"] < start_date or scrobble["date"] > end_date:
            continue
        records.append({'genre': genre, 'artist': artist_name, 'weight': 1})
    df = pd.DataFrame(records)
    # Calculate scrobble count per artist and assign ranks
    artist_counts = df.groupby('artist')['weight'].sum().reset_index()
    # Rank artists by scrobble count (highest count = rank 1)
    artist_counts['rank'] = artist_counts['weight'].rank(method='min',
                                                         ascending=False)
    # Filter out artists whose rank exceeds rank_limit
    valid_artists = artist_counts[artist_counts['rank'] <=
                                  rank_limit]['artist']
    df = df[df['artist'].isin(valid_artists)]

    # Create aggregated dataset for treemap
    artist_genre_counts = df.groupby(['artist',
                                      'genre'])['weight'].sum().reset_index()

    # Create treemap using plotly with a flatter hierarchy
    fig = px.treemap(
        artist_genre_counts,
        path=[px.Constant("Music"), 'artist'],  # Removed genre from path
        values='weight',
        title='Music Listening History',
        color='genre',  # Still color by genre
        color_discrete_sequence=px.colors.qualitative.Set3,
        hover_data=['genre'],  # Add genre to hover info
        branchvalues='total')

    # Update layout
    fig.update_layout(
        width=800,
        height=600,
        margin=dict(t=50, l=25, r=25, b=25),
        treemapcolorway=px.colors.qualitative.Set3,
    )

    # Update traces with corrected tiling property and custom hover template
    fig.update_traces(
        hovertemplate=
        '<b>%{label}</b><br>Genre: %{customdata[0]}<br>Plays: %{value}<extra></extra>',
        textinfo="label+value",
        root_color="lightgrey",
        tiling=dict(pad=5))

    return fig


def create_treemap(scrobbles,
                   rank_limit,
                   start_date,
                   end_date,
                   genre_field='genre'):
    records = []
    for scrobble in scrobbles:
        artist_name = scrobble["artist_name"]
        genre = scrobble[genre_field]
        if not genre or genre == "NA":
            print(f"Artist {artist_name} didn't have a valid tag")
            continue
        if scrobble["date"] < start_date or scrobble["date"] > end_date:
            continue
        records.append({'genre': genre, 'artist': artist_name, 'weight': 1})
    df = pd.DataFrame(records)
    # Calculate scrobble count per artist and assign ranks
    artist_counts = df.groupby('artist')['weight'].sum().reset_index()
    # Rank artists by scrobble count (highest count = rank 1)
    artist_counts['rank'] = artist_counts['weight'].rank(method='min',
                                                         ascending=False)
    # Filter out artists whose rank exceeds rank_limit
    valid_artists = artist_counts[artist_counts['rank'] <=
                                  rank_limit]['artist']
    df = df[df['artist'].isin(valid_artists)]
    # Create treemap using plotly with maxdepth to control visibility levels
    fig = px.treemap(
        df,
        path=[px.Constant("Music"), 'genre', 'artist'],
        values='weight',
        title='Music Listening History',
        color='genre',
        color_discrete_sequence=px.colors.qualitative.Set3,
        branchvalues='total',  # Ensures proper aggregation at each level
        maxdepth=3  # Show down to artist level
    )
    # Update layout
    fig.update_layout(
        width=800,
        height=600,
        margin=dict(t=50, l=25, r=25, b=25),
        treemapcolorway=px.colors.qualitative.Set3,
    )
    # Update traces with corrected tiling property and custom click behavior
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>Plays: %{value}<extra></extra>',
        textinfo="label+value",
        root_color="lightgrey",
        tiling=dict(pad=5))
    return fig


def genres():

    with st.form("rank_compare_form"):
        rank_limit = st.selectbox('Select the Number of Top Artists',
                                  [10, 25, 50, 100, 250, 500, 1000],
                                  index=2)

        # Add date inputs for start and end date
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input('Start Date',
                                       value=datetime.date.today() -
                                       datetime.timedelta(days=365),
                                       format="DD/MM/YYYY")
        with col2:
            end_date = st.date_input('End Date',
                                     value=datetime.date.today(),
                                     format="DD/MM/YYYY")

        form = st.selectbox('Select Treemap type',
                            ["Traditional", "Chaos", "Parent Genre"],
                            index=0)

        if st.form_submit_button('Get genre info!'):
            # Update session state **before** calling genre_dict
            st.session_state.rank_limit = rank_limit
            st.session_state.start_date = start_date
            st.session_state.end_date = end_date
            st.session_state.form = form

            #genre_dict(
            #start_date,
            #end_date
            #)

    if st.session_state.rank_limit:
        data = st.session_state.scrobbles
        #st.write(data)
        #st.write(st.session_state.aritst_tags)

        # Display the treemap based on selected visualization type
        if st.session_state.form == "Traditional":
            fig = create_treemap(data, st.session_state.rank_limit,
                                 st.session_state.start_date,
                                 st.session_state.end_date)
        elif st.session_state.form == "Chaos":
            fig = create_treemap2(data, st.session_state.rank_limit,
                                  st.session_state.start_date,
                                  st.session_state.end_date)
        else:  # Parent Genre view
            fig = create_treemap(data,
                                 st.session_state.rank_limit,
                                 st.session_state.start_date,
                                 st.session_state.end_date,
                                 genre_field='parent_genre')
        container = st.container(border=True)
        container.plotly_chart(fig, use_container_width=True)


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
