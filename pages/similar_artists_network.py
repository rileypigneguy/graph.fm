import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import requests
import os
from utils import menu, redirect_unauthenticated, footer
import datetime
import numpy as np
import math
from collections import defaultdict

def get_similar_artists(artist_name):
    """Get similar artists for a given artist from Last.fm API"""
    url = "http://ws.audioscrobbler.com/2.0/"

    # Get API key from environment variables for Replit
    api_key = os.environ.get("LASTFM_API_KEY")

    params = {
        "method": "artist.getsimilar",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
        "limit": 10
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if "similarartists" in data and "artist" in data["similarartists"]:
            return data["similarartists"]["artist"]
    return []

def create_artist_network(scrobbles, top_artist_limit, similarity_depth, start_date, end_date):
    """Create network visualization of similar artists"""
    # Filter by date range
    filtered_scrobbles = [s for s in scrobbles if s["date"] >= start_date and s["date"] <= end_date]

    # Count artist plays
    artist_counts = defaultdict(int)
    for scrobble in filtered_scrobbles:
        artist_counts[scrobble["artist_name"]] += 1

    # Get top artists
    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:top_artist_limit]

    # Create graph
    G = nx.Graph()

    # Add nodes for top artists with playcount as node size
    for artist, count in top_artists:
        G.add_node(artist, size=count, type="primary")

    # Only fetch similar artists if requested
    if similarity_depth > 0:
        with st.spinner("Fetching similar artists data from Last.fm API..."):
            for artist, _ in top_artists:
                similar_artists = get_similar_artists(artist)

                # Add similar artists as nodes and edges
                for similar in similar_artists[:similarity_depth]:
                    similar_name = similar["name"]
                    match = float(similar["match"]) * 100
                    if match >= 30:  # Only include reasonably similar artists
                        if similar_name not in G:
                            G.add_node(similar_name, size=30, type="similar")
                        G.add_edge(artist, similar_name, weight=match)

    # Calculate network positions using a force-directed layout
    pos = nx.spring_layout(G, seed=42)

    # Create lists of node data for Plotly
    edge_x = []
    edge_y = []
    edge_weights = []

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_weights.append(G.edges[edge]['weight'])

    # Create edge trace
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    # Create node traces - separate for primary and similar artists
    primary_node_x = []
    primary_node_y = []
    primary_node_text = []
    primary_node_size = []

    similar_node_x = []
    similar_node_y = []
    similar_node_text = []

    for node in G.nodes():
        x, y = pos[node]
        if G.nodes[node]['type'] == 'primary':
            primary_node_x.append(x)
            primary_node_y.append(y)
            primary_node_text.append(f"{node}<br>Plays: {G.nodes[node]['size']}")
            primary_node_size.append(math.sqrt(G.nodes[node]['size']) * 2)
        else:
            similar_node_x.append(x)
            similar_node_y.append(y)
            similar_node_text.append(f"{node} (similar)")

    primary_node_trace = go.Scatter(
        x=primary_node_x, y=primary_node_y,
        mode='markers',
        hoverinfo='text',
        text=primary_node_text,
        marker=dict(
            showscale=False,
            color='#1DB954',  # Spotify green for your artists
            size=primary_node_size,
            line=dict(width=2)
        )
    )

    similar_node_trace = go.Scatter(
        x=similar_node_x, y=similar_node_y,
        mode='markers',
        hoverinfo='text',
        text=similar_node_text,
        marker=dict(
            showscale=False,
            color='#b3b3ff',  # Light blue for similar artists
            size=10,
            line=dict(width=1)
        )
    )

    # Create figure
    fig = go.Figure(data=[edge_trace, primary_node_trace, similar_node_trace],
                 layout=go.Layout(
                    title={'text': 'Your Artist Network', 'font': {'size': 16}},
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    width=900,
                    height=700,
                    plot_bgcolor='rgba(0,0,0,0)',
                )
              )

    return fig, len(G.edges())

def similar_artists_network():
    st.header("🔄 Similar Artists Network")
    st.markdown("""
    This visualization shows the connections between your top artists and artists that are similar to them according to Last.fm.
    The size of your artists (green) indicates how much you've played them, and connecting lines represent similarity connections.
    """)

    if "scrobbles" not in st.session_state or not st.session_state.scrobbles:
        st.warning("Please log in and fetch your listening data first.")
        return

    with st.form("similar_artist_network_form"):
        col1, col2 = st.columns(2)

        with col1:
            top_artist_limit = st.slider(
                "Number of your top artists to include",
                min_value=5,
                max_value=50,
                value=15,
                step=5
            )

            similarity_depth = st.slider(
                "Number of similar artists to include per artist",
                min_value=0,
                max_value=10,
                value=3,
                step=1,
                help="Higher values will make the graph more complex but show more connections"
            )

        with col2:
            start_date = st.date_input(
                "Start Date",
                value=datetime.date.today() - datetime.timedelta(days=365),
                format="DD/MM/YYYY"
            )

            end_date = st.date_input(
                "End Date",
                value=datetime.date.today(),
                format="DD/MM/YYYY"
            )

        submit_button = st.form_submit_button("Generate Network")

    if submit_button or "network_generated" in st.session_state:
        if submit_button:
            st.session_state.top_artist_limit = top_artist_limit
            st.session_state.similarity_depth = similarity_depth
            st.session_state.start_date = start_date
            st.session_state.end_date = end_date
            st.session_state.network_generated = True

        # Generate network visualization
        network_fig, connection_count = create_artist_network(
            st.session_state.scrobbles,
            st.session_state.top_artist_limit,
            st.session_state.similarity_depth,
            st.session_state.start_date,
            st.session_state.end_date
        )

        # Display network metrics
        st.metric("Network Connections", connection_count)

        # Display the network
        network_container = st.container(border=True)
        network_container.plotly_chart(network_fig, use_container_width=True)

        # Exploration tips
        with st.expander("Network Exploration Tips"):
            st.markdown("""
            ### How to use this visualization:
            - **Green nodes** are your top artists
            - **Blue nodes** are similar artists according to Last.fm
            - **Node size** indicates your play count (for your artists)
            - **Hover** over nodes to see artist names and play counts
            - **Click and drag** to move the network around
            - **Zoom** using scroll wheel or pinch gesture

            ### What to look for:
            - **Clusters** indicate related artists/genres in your listening habits
            - **Isolated nodes** might represent unique tastes in your collection
            - **Bridge artists** connect different musical styles in your library
            """)

        # Music discovery suggestions
        with st.expander("Discover New Music"):
            st.markdown("""
            ### Based on your network:
            - Try exploring artists that connect different clusters
            - Look for similar artists (blue nodes) that appear multiple times
            - Consider artists that have strong connections (closer) to multiple favorites
            """)

# Page setup
st.set_page_config(
    page_title="Graph.fm - Similar Artists Network",
    layout="wide",
    page_icon="🔄",
)

redirect_unauthenticated()
st.title("🔄 Similar Artists Network")
menu()
similar_artists_network()
footer()