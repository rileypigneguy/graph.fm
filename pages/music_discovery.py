import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import random
import networkx as nx
from collections import Counter, defaultdict
import calendar
from utils import menu, redirect_unauthenticated, footer

def music_discovery():
    st.title("🔍 Musical Connections Explorer")

    redirect_unauthenticated()
    menu()

    st.write("""
    Discover hidden patterns and connections in your listening habits. This page analyzes relationships between
    artists, genres, and your listening behavior to help you better understand your musical taste and discover new music.
    """)

    # Initialize session state for filters
    if 'discovery_time_range' not in st.session_state:
        st.session_state.discovery_time_range = 365
    if 'discovery_min_plays' not in st.session_state:
        st.session_state.discovery_min_plays = 5

    # Sidebar for filters
    with st.sidebar:
        st.header("Discovery Filters")
        st.session_state.discovery_time_range = st.slider(
            "Time Range (days)",
            min_value=30, 
            max_value=730,
            value=st.session_state.discovery_time_range,
            step=30
        )

        st.session_state.discovery_min_plays = st.slider(
            "Minimum Plays",
            min_value=2,
            max_value=20,
            value=st.session_state.discovery_min_plays
        )

    # Process the scrobble data
    if 'scrobbles' in st.session_state:
        # Filter data by time range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=st.session_state.discovery_time_range)

        # Convert scrobbles to DataFrame for easier manipulation
        scrobbles_list = []
        for scrobble in st.session_state.scrobbles:
            # Skip if outside time range
            if scrobble["date"] < start_date or scrobble["date"] > end_date:
                continue
            scrobbles_list.append({
                'track_name': scrobble["track_name"],
                'artist_name': scrobble["artist_name"],
                'album_name': scrobble["album_name"],
                'date': scrobble["date"],
                'genre': scrobble["genre"] if "genre" in scrobble and scrobble["genre"] else "Unknown"
            })

        if not scrobbles_list:
            st.warning("No scrobble data available for the selected time range.")
            footer()
            return

        df = pd.DataFrame(scrobbles_list)

        # Extract day of week, hour for temporal analysis
        df['day_of_week'] = df['date'].apply(lambda x: calendar.day_name[x.weekday()])
        df['month'] = df['date'].apply(lambda x: x.month)
        df['month_name'] = df['date'].apply(lambda x: calendar.month_name[x.month])

        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎭 Artist Networks", 
            "🔄 Genre Transitions", 
            "📅 Temporal Patterns",
            "🧩 Discovery Recommendations"
        ])

        with tab1:
            create_artist_network(df)

        with tab2:
            create_genre_transitions(df)

        with tab3:
            create_temporal_patterns(df)

        with tab4:
            create_discovery_recommendations(df)
    else:
        st.warning("Please load your listening data first.")

    footer()

def create_artist_network(df):
    st.subheader("Artist Connection Network")
    st.write("""
    This visualization shows connections between artists based on your listening patterns. 
    Artists that you tend to listen to around the same time are connected with lines.
    Thicker lines indicate stronger connections.
    """)

    min_plays = st.session_state.discovery_min_plays

    # Get artists with minimum play count
    artist_counts = df['artist_name'].value_counts()
    valid_artists = artist_counts[artist_counts >= min_plays].index.tolist()

    if len(valid_artists) < 2:
        st.warning(f"Not enough artists with at least {min_plays} plays. Try lowering the minimum plays filter.")
        return

    # Limit to a reasonable number for visualization
    if len(valid_artists) > 50:
        valid_artists = valid_artists[:50]
        st.info("Showing only top 50 artists for better visualization clarity.")

    # Create connections between artists that appear close together in listening history    
    # Sort dataframe by date to establish listening sequence
    df_sorted = df.sort_values('date')
    df_filtered = df_sorted[df_sorted['artist_name'].isin(valid_artists)]

    # Create a graph
    G = nx.Graph()

    # Add nodes (artists)
    artist_play_counts = df_filtered['artist_name'].value_counts()
    genre_by_artist = df_filtered.groupby('artist_name')['genre'].agg(lambda x: pd.Series.mode(x)[0])

    for artist in valid_artists:
        if artist in artist_play_counts:
            G.add_node(
                artist, 
                size=artist_play_counts[artist],
                genre=genre_by_artist.get(artist, "Unknown")
            )

    # Find connections - artists that are listened to within a short sequence
    edges = defaultdict(int)
    artist_sequence = df_filtered['artist_name'].tolist()

    for i in range(len(artist_sequence) - 1):
        artist1 = artist_sequence[i]
        artist2 = artist_sequence[i + 1]
        if artist1 != artist2:  # Avoid self-loops
            if artist1 < artist2:  # Keep consistent edge direction
                edges[(artist1, artist2)] += 1
            else:
                edges[(artist2, artist1)] += 1

    # Add edges with weight > 1 (to reduce noise)
    # If we have too few edges, lower the threshold to ensure we have at least some connections
    edge_threshold = 1 if len(edges) < 10 else 2
    significant_edges = {k: v for k, v in edges.items() if v >= edge_threshold}

    for (artist1, artist2), weight in significant_edges.items():
        G.add_edge(artist1, artist2, weight=weight)

    # If we have a graph with edges
    if G.number_of_edges() > 0:
        # Use NetworkX's spring layout for node positioning
        pos = nx.spring_layout(G, seed=42)

        # Create Plotly figure
        edge_x = []
        edge_y = []
        edge_weights = []

        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_weights.append(edge[2]['weight'])

        # Create separate edge traces grouped by weight for better visualization
        edge_traces = []
        for weight in sorted(set(edge_weights)):
            # Group edges by weight class
            weight_edges_x = []
            weight_edges_y = []

            for i, w in enumerate(edge_weights):
                if w == weight:
                    idx = i * 3  # Each edge uses 3 points (x0, x1, None)
                    weight_edges_x.extend([edge_x[idx], edge_x[idx+1], None])
                    weight_edges_y.extend([edge_y[idx], edge_y[idx+1], None])

            # Scale width based on weight
            line_width = 1 + (weight / max(edge_weights) * 4)

            edge_traces.append(go.Scatter(
                x=weight_edges_x, 
                y=weight_edges_y,
                line=dict(width=line_width, color=f'rgba(150,150,150,{min(0.3 + weight/max(edge_weights)*0.7, 0.9)})'),
                hoverinfo='none',
                mode='lines',
                showlegend=False
            ))

        # Edge traces are now created in the loop above

        # Create nodes trace
        node_x = []
        node_y = []
        node_sizes = []
        node_colors = []
        node_texts = []
        node_genres = []

        # Color mapping for genres
        unique_genres = list(set(nx.get_node_attributes(G, 'genre').values()))
        genre_to_color = {genre: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                         for i, genre in enumerate(unique_genres)}

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            size = G.nodes[node]['size']
            node_sizes.append(size)
            genre = G.nodes[node]['genre']
            node_genres.append(genre)
            node_colors.append(genre_to_color.get(genre, 'grey'))
            node_texts.append(f"{node}<br>Plays: {size}<br>Genre: {genre}")

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_texts,
            marker=dict(
                color=node_colors,
                size=[min(20 + s * 0.5, 50) for s in node_sizes],  # Cap size at 50
                line=dict(width=2, color='white')
            )
        )

        # Create figure with all edge traces plus node trace
        fig = go.Figure(data=edge_traces + [node_trace],
                     layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        title="Artist Connections Based on Listening Patterns",
                        height=700
                    )
                )

        # Add legend for genres
        for genre, color in genre_to_color.items():
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=10, color=color),
                name=genre,
                showlegend=True
            ))

        st.plotly_chart(fig, use_container_width=True)

        # Show top connections
        st.subheader("Strongest Artist Connections")
        top_connections = sorted(significant_edges.items(), key=lambda x: x[1], reverse=True)[:10]

        if top_connections:
            connection_data = []
            for (artist1, artist2), weight in top_connections:
                connection_data.append({
                    "Artist 1": artist1,
                    "Artist 2": artist2,
                    "Connection Strength": weight,
                    "Common Genre": "Yes" if genre_by_artist.get(artist1) == genre_by_artist.get(artist2) else "No"
                })

            st.dataframe(pd.DataFrame(connection_data), hide_index=True)
        else:
            st.info("No significant connections found between artists.")
    else:
        st.info("Not enough connections between artists to create a network. Try adjusting the filters.")

def create_genre_transitions(df):
    st.subheader("Genre Flow Analysis")
    st.write("""
    This analysis shows how you transition between music genres. The thicker the line, 
    the more frequently you switch from one genre to another.
    """)

    # Create sequence of genres from chronologically sorted scrobbles
    df_sorted = df.sort_values('date')
    genre_sequence = df_sorted['genre'].tolist()

    # Count transitions between genres
    transitions = defaultdict(int)
    for i in range(len(genre_sequence) - 1):
        genre1 = genre_sequence[i]
        genre2 = genre_sequence[i + 1]
        if genre1 != genre2:  # Only count actual transitions
            transitions[(genre1, genre2)] += 1

    # Get top genres by play count
    genre_counts = df['genre'].value_counts()
    top_genres = genre_counts.head(10).index.tolist()

    # Filter transitions to only include top genres
    filtered_transitions = {k: v for k, v in transitions.items() 
                          if k[0] in top_genres and k[1] in top_genres}

    if filtered_transitions:
        # Convert to format for Sankey diagram
        source = []
        target = []
        value = []

        # Create mapping of genre names to indices
        genre_to_idx = {genre: i for i, genre in enumerate(top_genres)}

        for (genre1, genre2), count in filtered_transitions.items():
            if genre1 in genre_to_idx and genre2 in genre_to_idx:
                source.append(genre_to_idx[genre1])
                target.append(genre_to_idx[genre2])
                value.append(count)

        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=top_genres,
                color=px.colors.qualitative.Plotly[:len(top_genres)]
            ),
            link=dict(
                source=source,
                target=target,
                value=value
            )
        )])

        fig.update_layout(
            title="Genre Flow Transitions",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        # Display additional insights
        total_transitions = sum(filtered_transitions.values())
        most_common = max(filtered_transitions.items(), key=lambda x: x[1])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Genre Transitions", f"{total_transitions:,}")
        with col2:
            st.metric("Most Common Transition", f"{most_common[0][0]} → {most_common[0][1]} ({most_common[1]} times)")

    else:
        st.info("Not enough genre transitions found. Try adjusting the time range.")

def create_temporal_patterns(df):
    st.subheader("Temporal Listening Patterns")
    st.write("""
    Discover when you listen to different genres and artists. These visualizations reveal
    your listening patterns across days of the week and months of the year.
    """)

    # Ensure the day of week is ordered correctly
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    month_order = [calendar.month_name[i] for i in range(1, 13)]

    # Create a 2x2 subplot grid
    col1, col2 = st.columns(2)

    with col1:
        # Day of week distribution by genre
        pivot_day = pd.crosstab(df['day_of_week'], df['genre'])
        pivot_day = pivot_day.reindex(day_order)

        # Select top 5 genres for clarity
        top_genres = df['genre'].value_counts().head(5).index.tolist()
        pivot_day = pivot_day[top_genres]

        fig = px.bar(
            pivot_day, 
            title="Listening by Day of Week and Genre",
            color_discrete_sequence=px.colors.qualitative.Plotly,
            height=400
        )

        fig.update_layout(
            xaxis_title="Day of Week",
            yaxis_title="Number of Plays",
            legend_title="Genre"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Month distribution by genre
        pivot_month = pd.crosstab(df['month_name'], df['genre'])
        pivot_month = pivot_month.reindex(month_order)

        # Use same top 5 genres for consistency
        pivot_month = pivot_month[top_genres]

        fig = px.bar(
            pivot_month, 
            title="Listening by Month and Genre",
            color_discrete_sequence=px.colors.qualitative.Plotly,
            height=400
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Number of Plays",
            legend_title="Genre"
        )

        st.plotly_chart(fig, use_container_width=True)

    # Create genre "moods" by time
    st.subheader("Genre Mood Map")
    st.write("""
    Your genre preferences often shift throughout the week. This visualization shows which 
    genres you prefer on different days, revealing your musical "mood map".
    """)

    # Get dominant genre by day of week
    day_genre = df.groupby('day_of_week')['genre'].agg(pd.Series.mode)
    day_genre = day_genre.reindex(day_order)

    # Create color mapping for genres
    all_genres = df['genre'].unique()
    genre_colors = {genre: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                   for i, genre in enumerate(all_genres)}

    # Create a figure
    fig = go.Figure()

    # Add a trace for each day
    for day in day_order:
        if day in day_genre:
            dominant_genre = day_genre[day]
            if isinstance(dominant_genre, (list, pd.Series)):
                dominant_genre = dominant_genre[0]  # Take first if there are multiple modes

            genre_count = df[(df['day_of_week'] == day) & (df['genre'] == dominant_genre)].shape[0]
            total_count = df[df['day_of_week'] == day].shape[0]
            percentage = (genre_count / total_count * 100) if total_count > 0 else 0

            fig.add_trace(go.Bar(
                x=[day],
                y=[100],  # Full height bar
                marker=dict(
                    color=genre_colors.get(dominant_genre, 'grey'),
                    line=dict(width=1, color='black')
                ),
                text=f"{dominant_genre}<br>{percentage:.1f}%",
                textposition='inside',
                hoverinfo='text',
                name=dominant_genre
            ))

    fig.update_layout(
        title="Dominant Genre by Day of Week",
        xaxis_title="Day of Week",
        yaxis=dict(
            title="",
            showticklabels=False,
            showgrid=False
        ),
        showlegend=False,
        height=400,
        uniformtext=dict(minsize=10, mode='hide')
    )

    st.plotly_chart(fig, use_container_width=True)

def create_discovery_recommendations(df):
    st.subheader("Music Discovery Insights")
    st.write("""
    Based on your listening patterns, here are some insights to help you discover new music that
    aligns with your tastes.
    """)

    # Calculate genre diversity score
    genre_counts = df['genre'].value_counts()
    genre_proportion = genre_counts / genre_counts.sum()
    genre_diversity = -(genre_proportion * np.log(genre_proportion)).sum()
    normalized_diversity = min(genre_diversity / np.log(len(genre_counts)) if len(genre_counts) > 1 else 0, 1)

    # Artist loyalty - ratio of plays of top artists to total plays
    artist_counts = df['artist_name'].value_counts()
    top_artists_plays = artist_counts.head(5).sum()
    artist_loyalty = top_artists_plays / len(df)

    # Create metrics
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Genre Diversity Score", 
            f"{normalized_diversity:.2f}", 
            help="1.0 means maximum diversity across genres, 0.0 means you listen to only one genre"
        )

    with col2:
        st.metric(
            "Top 5 Artist Loyalty", 
            f"{artist_loyalty:.2f}", 
            help="Proportion of your listening coming from your top 5 artists"
        )

    # Generate recommendations based on patterns
    st.subheader("Music Discovery Recommendations")

    # Find genres that are underexplored but present
    genre_plays = df['genre'].value_counts()
    underexplored_genres = genre_plays[(genre_plays > 3) & (genre_plays < 20)].index.tolist()

    # Find unusual but positive genre transitions
    transition_counts = defaultdict(int)
    genre_sequence = df.sort_values('date')['genre'].tolist()

    for i in range(len(genre_sequence) - 1):
        if genre_sequence[i] != genre_sequence[i+1]:
            transition_counts[(genre_sequence[i], genre_sequence[i+1])] += 1

    # Create an engaging format for recommendations
    if underexplored_genres or transition_counts:
        # Recommendation cards
        rec_col1, rec_col2 = st.columns(2)

        with rec_col1:
            st.markdown("### 🌱 Genres to Explore")
            if underexplored_genres:
                for i, genre in enumerate(underexplored_genres[:5]):
                    with st.container(border=True):
                        st.markdown(f"**{genre}**")
                        plays = genre_plays[genre]
                        st.caption(f"You've listened to this genre {plays} times. Dig deeper!")

                        # Find most played artist in this genre
                        genre_df = df[df['genre'] == genre]
                        top_artist = genre_df['artist_name'].value_counts().idxmax()
                        st.caption(f"Your top artist: {top_artist}")
            else:
                st.info("No underexplored genres found. You have a very balanced listening habit!")

        with rec_col2:
            st.markdown("### 🌟 Genre Connections")
            transitions = sorted(transition_counts.items(), key=lambda x: x[1], reverse=True)
            displayed = 0

            for (genre1, genre2), count in transitions:
                # Only show interesting transitions with moderate counts
                if 3 <= count <= 15 and displayed < 5:
                    with st.container(border=True):
                        st.markdown(f"**{genre1}** → **{genre2}**")
                        st.caption(f"You've made this transition {count} times")
                        st.caption("This pattern suggests you might enjoy genre-blending artists")
                    displayed += 1

            if displayed == 0:
                st.info("No notable genre transitions found. Try increasing your time range.")
    else:
        st.info("Not enough data to generate recommendations. Try increasing your time range.")

    # Create a personalized playlist recommendation
    st.subheader("🎧 Your Discovery Playlist")
    st.write("Based on your listening patterns, here's a personalized discovery playlist:")

    # Find artists you don't listen to very often but have some plays
    moderate_artists = artist_counts[(artist_counts >= 2) & (artist_counts <= 5)].index.tolist()

    if moderate_artists:
        # Create a virtual playlist of track recommendations
        playlist_items = []

        # Get one track from each moderate artist
        for artist in moderate_artists[:10]:  # Limit to 10 artists
            artist_tracks = df[df['artist_name'] == artist]['track_name'].unique()
            if len(artist_tracks) > 0:
                track = random.choice(artist_tracks)
                genre = df[(df['artist_name'] == artist) & (df['track_name'] == track)]['genre'].iloc[0]
                playlist_items.append({
                    "Track": track,
                    "Artist": artist,
                    "Genre": genre
                })

        if playlist_items:
            st.dataframe(pd.DataFrame(playlist_items), hide_index=True)
        else:
            st.info("Not enough track data to create a discovery playlist.")
    else:
        st.info("Not enough artist variety to create a discovery playlist. Try listening to more artists!")

# Add necessary imports
import numpy as np

# Entry point for the page
def main():
    st.set_page_config(
        page_title="Musical Connections - Graph.fm",
        layout="wide", 
        page_icon="🔍",
    )

    music_discovery()

if __name__ == "__main__":
    main()