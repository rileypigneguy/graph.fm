import streamlit as st
import pandas as pd
import datetime
from utils import menu, redirect_unauthenticated, footer

def top_achievers():
    st.title("🏆 Top Achievers")

    with st.form("top_achievers_form"):
        # Single input field for the achievement threshold
        threshold = st.number_input(
            'To achieve:',
            min_value=1,
            value=100,
            step=1,
            help="Enter the number of scrobbles an artist needs to be considered a 'Top Achiever'"
        )

        # Submit button for the form
        if st.form_submit_button('Show Achievers'):
            st.session_state.threshold = threshold

    # Process and display data if threshold is set in session state
    if 'threshold' in st.session_state and 'scrobbles' in st.session_state:
        display_top_achievers(st.session_state.scrobbles, st.session_state.threshold)

def display_top_achievers(scrobbles, threshold):
    # Create a DataFrame from the scrobbles
    df = pd.DataFrame(scrobbles)

    # Ensure date is in a usable format for sorting
    if df.empty:
        st.warning("No scrobble data available.")
        return

    # Handle date conversion for sorting
    try:
        if isinstance(df['date'].iloc[0], str):
            df['date'] = pd.to_datetime(df['date'])
        elif isinstance(df['date'].iloc[0], (int, float)) and df['date'].iloc[0] > 1e11:
            # Convert millisecond timestamps to datetime
            df['date'] = pd.to_datetime(df['date'], unit='ms')
        elif isinstance(df['date'].iloc[0], (int, float)):
            # Convert second timestamps to datetime
            df['date'] = pd.to_datetime(df['date'], unit='s')
    except Exception as e:
        st.warning(f"Date conversion issue: {e}")
        # Continue with original format if conversion fails

    # Sort by date to process chronologically
    try:
        df = df.sort_values('date')
    except:
        st.warning("Couldn't sort by date, processing in original order.")

    # Group by artist and count scrobbles
    artist_scrobble_counts = {}
    artist_achievement_dates = {}

    # Process each row chronologically to find when artists hit the threshold
    for _, row in df.iterrows():
        artist = row['artist_name']
        date = row['date']

        # Initialize if this is the first time seeing this artist
        if artist not in artist_scrobble_counts:
            artist_scrobble_counts[artist] = 0

        # Increment the count for this artist
        artist_scrobble_counts[artist] += 1

        # Check if the artist just reached the threshold
        if artist_scrobble_counts[artist] == threshold and artist not in artist_achievement_dates:
            # Format the date as a human-readable string
            if isinstance(date, (datetime.datetime, pd.Timestamp)):
                formatted_date = date.strftime('%Y-%m-%d')
            else:
                # Try to convert to datetime first if it's a timestamp number
                try:
                    if isinstance(date, (int, float)):
                        # Convert milliseconds to seconds if needed
                        if date > 1e11:  # Likely milliseconds
                            date = date / 1000
                        formatted_date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%d')
                    else:
                        formatted_date = str(date)
                except:
                    formatted_date = str(date)

            artist_achievement_dates[artist] = formatted_date

    # Create a list of artists who achieved the threshold
    achievers = []
    for artist, date in artist_achievement_dates.items():
        # Get the current total for this artist
        current_total = artist_scrobble_counts[artist]
        achievers.append({
            'Artist': artist,
            'Date Achieved': date,
            'Current Total': current_total
        })

    # Create DataFrame from achievers list
    achievers_df = pd.DataFrame(achievers)

    # Sort by achievement date (earliest first)
    if not achievers_df.empty:
        achievers_df = achievers_df.sort_values('Date Achieved')

        # Date is already stored as a string from earlier processing
        # No need to format with dt accessor

        # Add rank column
        achievers_df.insert(0, 'Rank', range(1, len(achievers_df) + 1))

        # Display results
        st.subheader(f"Artists who achieved {threshold}+ scrobbles")
        st.write(f"Total artists: {len(achievers_df)}")

        # Display the table with custom formatting
        st.dataframe(
            achievers_df,
            hide_index=True,
            column_config={
                "Rank": st.column_config.NumberColumn(format="%d"),
                "Artist": st.column_config.TextColumn("Artist"),
                "Date Achieved": st.column_config.TextColumn("Date Achieved"),
                "Current Total": st.column_config.NumberColumn("Current Total", format="%d")
            },
            height=800,
            use_container_width=True
        )
    else:
        st.info(f"No artists have achieved {threshold} scrobbles yet.")

# Page configuration
st.set_page_config(
    page_title="Graph.fm - Top Achievers",
    layout="wide", 
    page_icon="🏆",
)

# Authentication check
redirect_unauthenticated()

# Display menu
menu()

# Main function
top_achievers()

# Footer
footer()