import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import calendar
from utils import menu, redirect_unauthenticated, footer
import os
import numpy as np
from collections import defaultdict

def generate_calendar_heatmap(scrobbles, year, colorscale, highlight_weekends):
    """Generate a calendar heatmap of listening activity for the specified year"""

    # Create a DataFrame from scrobbles
    records = []
    for scrobble in scrobbles:
        date = scrobble["date"]
        if date.year == year:
            records.append({
                "date": date,
                "artist": scrobble["artist_name"],
                "track": scrobble["track_name"],
                "album": scrobble.get("album_name", "")
            })

    # If no scrobbles for this year, return empty figure
    if not records:
        fig = go.Figure()
        fig.update_layout(
            title=f"No listening data found for {year}",
            xaxis={"visible": False},
            yaxis={"visible": False}
        )
        return fig, 0, 0, 0

    df = pd.DataFrame(records)

    # Ensure the 'date' column is in datetime format
    df["date"] = pd.to_datetime(df["date"])

    # Count scrobbles per day
    daily_counts = df.groupby(df["date"].dt.date).size().reset_index(name="count")
    daily_counts["date"] = pd.to_datetime(daily_counts["date"])

    # Create a complete calendar (all days in the year)
    all_days = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31", freq="D")
    complete_calendar = pd.DataFrame({"date": all_days})

    # Merge with actual counts
    calendar_df = pd.merge(complete_calendar, daily_counts, on="date", how="left")
    calendar_df["count"] = calendar_df["count"].fillna(0)

    # Extract week and day information
    calendar_df["weekday"] = calendar_df["date"].dt.day_name()
    calendar_df["week_num"] = calendar_df["date"].dt.isocalendar().week
    calendar_df["month"] = calendar_df["date"].dt.month
    calendar_df["month_name"] = calendar_df["date"].dt.month_name()
    calendar_df["day"] = calendar_df["date"].dt.day

    # Handle week numbers that overlap years
    calendar_df.loc[(calendar_df["month"] == 12) & (calendar_df["week_num"] < 10), "week_num"] += 52
    calendar_df.loc[(calendar_df["month"] == 1) & (calendar_df["week_num"] > 50), "week_num"] -= 52

    # Create a stable week order
    week_to_order = {week: idx for idx, week in enumerate(calendar_df["week_num"].unique().tolist())}
    calendar_df["week_order"] = calendar_df["week_num"].map(week_to_order)

    # Create a weekday order (Monday first, Sunday last)
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    calendar_df["weekday_order"] = calendar_df["weekday"].apply(lambda x: weekday_order.index(x))

    # Calculate weekend days if highlighting is enabled
    if highlight_weekends:
        calendar_df["is_weekend"] = calendar_df["weekday"].isin(["Saturday", "Sunday"])

    # Calculate stats
    total_tracks = int(calendar_df["count"].sum())
    active_days = int((calendar_df["count"] > 0).sum())
    max_day = calendar_df.loc[calendar_df["count"].idxmax()]

    # Create heatmap
    fig = px.imshow(
        calendar_df.pivot(index="weekday_order", columns="week_order", values="count"),
        labels=dict(x="Week", y="Day", color="Tracks"),
        y=[weekday_order[i] for i in range(7)],
        aspect="auto",
        color_continuous_scale=colorscale
    )

    # Add month separators and labels
    month_positions = {}
    for month in range(1, 13):
        # Get the weeks in this month
        month_weeks = calendar_df[calendar_df["month"] == month]["week_order"].unique()
        if len(month_weeks) > 0:
            month_positions[month] = month_weeks.min()

    # Draw month separators
    for month, pos in month_positions.items():
        if month > 1:  # Don't draw separator for January
            fig.add_shape(
                type="line",
                x0=pos - 0.5, y0=-0.5, x1=pos - 0.5, y1=6.5,
                line=dict(color="gray", width=1)
            )

    # Add month labels
    month_texts = []
    for month, pos in month_positions.items():
        month_name = calendar.month_name[month]
        month_texts.append(
            dict(
                x=pos + 1,
                y=-0.5,
                text=month_name,
                showarrow=False,
                font=dict(size=10),
                xanchor="center"
            )
        )

    fig.update_layout(
        title=f"Your Listening Calendar for {year}",
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
        annotations=month_texts,
        coloraxis_colorbar=dict(
            title="Tracks",
            thicknessmode="pixels",
            thickness=20,
            lenmode="pixels",
            len=300
        )
    )

    # Highlight weekends if enabled
    if highlight_weekends:
        weekend_df = calendar_df[calendar_df["is_weekend"]]
        for _, row in weekend_df.iterrows():
            fig.add_shape(
                type="rect",
                x0=row["week_order"] - 0.5,
                y0=row["weekday_order"] - 0.5,
                x1=row["week_order"] + 0.5,
                y1=row["weekday_order"] + 0.5,
                line=dict(width=1, color="rgba(0,0,0,0.2)"),
                fillcolor="rgba(0,0,0,0)"
            )

    return fig, total_tracks, active_days, max_day

def generate_time_of_day_chart(scrobbles, year, colorscale):
    """Generate a chart showing listening activity by time of day and day of week"""

    # Create a DataFrame from scrobbles with time information
    records = []
    for scrobble in scrobbles:
        date = scrobble["date"]
        if date.year == year:
            records.append({
                "date": date,
                "hour": date.hour,
                "weekday": date.strftime("%A"),
                "weekday_num": date.weekday(),  # 0 = Monday, 6 = Sunday
                "artist": scrobble["artist_name"],
                "track": scrobble["track_name"]
            })

    # If no scrobbles for this year, return empty figure
    if not records:
        fig = go.Figure()
        fig.update_layout(
            title=f"No listening data found for {year}",
            xaxis={"visible": False},
            yaxis={"visible": False}
        )
        return fig

    df = pd.DataFrame(records)

    # Ensure the 'date' column is in datetime format
    df["date"] = pd.to_datetime(df["date"])

    # Count scrobbles per hour and weekday
    hour_weekday_counts = df.groupby(["hour", "weekday_num"]).size().reset_index(name="count")

    # Create a pivot table for the heatmap
    pivot_table = hour_weekday_counts.pivot(
        index="hour", 
        columns="weekday_num", 
        values="count"
    ).fillna(0)

    # Set the correct order of days and hours
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Create heatmap
    fig = px.imshow(
        pivot_table,
        labels=dict(x="Day", y="Hour", color="Tracks"),
        x=weekday_names,
        y=list(range(24)),
        aspect="auto",
        color_continuous_scale=colorscale
    )

    # Update layout
    fig.update_layout(
        title=f"Time of Day Listening Pattern for {year}",
        height=450,
        margin=dict(l=40, r=20, t=50, b=40),
        coloraxis_colorbar=dict(
            title="Tracks",
            thicknessmode="pixels",
            thickness=20,
            lenmode="pixels",
            len=300
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(24)),
            ticktext=[f"{hour}:00" for hour in range(24)]
        )
    )

    return fig

def generate_monthly_trend(scrobbles, year, colorscale):
    """Generate a chart showing monthly listening trends"""

    # Create a DataFrame from scrobbles
    records = []
    for scrobble in scrobbles:
        date = scrobble["date"]
        if date.year == year:
            records.append({
                "date": date,
                "month": date.month,
                "month_name": date.strftime("%B"),
                "artist": scrobble["artist_name"],
                "track": scrobble["track_name"]
            })

    # If no scrobbles for this year, return empty figure
    if not records:
        fig = go.Figure()
        fig.update_layout(
            title=f"No listening data found for {year}",
            xaxis={"visible": False},
            yaxis={"visible": False}
        )
        return fig

    df = pd.DataFrame(records)

    # Ensure the 'date' column is in datetime format
    df["date"] = pd.to_datetime(df["date"])

    # Count scrobbles per month
    monthly_counts = df.groupby(["month", "month_name"]).size().reset_index(name="count")
    monthly_counts = monthly_counts.sort_values("month")

    # Calculate the average per day in each month to account for varying month lengths
    days_in_month = {month: pd.Timestamp(year, month, 1).days_in_month for month in range(1, 13)}
    monthly_counts["days"] = monthly_counts["month"].map(days_in_month)
    monthly_counts["avg_per_day"] = monthly_counts["count"] / monthly_counts["days"]

    # Create bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly_counts["month_name"],
        y=monthly_counts["count"],
        name="Total Tracks",
        marker_color=px.colors.sequential.Viridis[0]
    ))

    fig.add_trace(go.Scatter(
        x=monthly_counts["month_name"],
        y=monthly_counts["avg_per_day"],
        name="Daily Average",
        yaxis="y2",
        mode="lines+markers",
        marker=dict(color=px.colors.sequential.Viridis[-1]),
        line=dict(width=3)
    ))

    # Update layout
    fig.update_layout(
        title=f"Monthly Listening Trends for {year}",
        xaxis=dict(
            title="Month",
            tickmode="array",
            tickvals=monthly_counts["month_name"]
        ),
        yaxis=dict(
            title="Total Tracks",
            side="left"
        ),
        yaxis2=dict(
            title="Avg Tracks per Day",
            side="right",
            overlaying="y"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=50, b=40),
        height=350
    )

    return fig

def listening_calendar():
    """Main function for the listening calendar page"""

    st.header("📅 Listening Calendar")
    st.markdown("""
    This visualization shows your music listening patterns throughout the year in a calendar format. 
    Each cell represents a day, with darker colors indicating more tracks played on that day.
    """)

    if "scrobbles" not in st.session_state or not st.session_state.scrobbles:
        st.warning("Please log in and fetch your listening data first.")
        return

    # Get the range of years in the data
    years = sorted(list(set(scrobble["date"].year for scrobble in st.session_state.scrobbles)))

    if not years:
        st.error("No listening data found. Please fetch your data first.")
        return

    # Default to the most recent year
    default_year = max(years)

    # Sidebar controls
    with st.sidebar:
        st.subheader("Calendar Settings")

        selected_year = st.selectbox(
            "Select Year", 
            options=years,
            index=years.index(default_year) if default_year in years else 0
        )

        colorscale = st.selectbox(
            "Color Scheme",
            options=["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Blues", "Greens", "Reds", "Purples"],
            index=0
        )

        highlight_weekends = st.checkbox("Highlight Weekends", value=True)

    # Generate the calendar heatmap
    fig, total_tracks, active_days, max_day = generate_calendar_heatmap(
        st.session_state.scrobbles,
        selected_year,
        colorscale.lower(),
        highlight_weekends
    )

    # Display the calendar
    st.plotly_chart(fig, use_container_width=True)

    # If we have data, show stats
    if total_tracks > 0:
        # Stats in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tracks", f"{total_tracks:,}")
        with col2:
            st.metric("Active Days", f"{active_days} / 365")
        with col3:
            try:
                st.metric(
                    "Most Active Day",
                    f"{max_day['date'].strftime('%b %d')}: {int(max_day['count'])} tracks"
                )
            except:
                st.metric("Most Active Day", "N/A")

    # Time of day analysis
    st.subheader("Time of Day Analysis")
    st.markdown("""
    This heatmap shows what time of day and which days of the week you listen to music most frequently.
    """)

    time_fig = generate_time_of_day_chart(
        st.session_state.scrobbles,
        selected_year,
        colorscale.lower()
    )
    st.plotly_chart(time_fig, use_container_width=True)

    # Monthly trends
    st.subheader("Monthly Listening Trends")
    st.markdown("""
    This chart shows how your listening habits changed throughout the months of the year.
    """)

    monthly_fig = generate_monthly_trend(
        st.session_state.scrobbles,
        selected_year,
        colorscale.lower()
    )
    st.plotly_chart(monthly_fig, use_container_width=True)

    # Patterns and insights
    with st.expander("Patterns & Insights", expanded=False):
        st.markdown("""
        ### How to interpret these visualizations:

        #### Calendar Heatmap
        - **Dark spots** show days with high listening activity
        - **Empty/light spots** show days with little or no listening
        - **Patterns across weeks** might indicate consistent listening habits

        #### Time of Day Analysis
        - See if you listen more during certain hours or days
        - Identify your peak listening hours
        - Notice differences between weekdays and weekends

        #### Monthly Trends
        - Track seasonal variations in your listening habits
        - The line graph shows average daily listening, controlling for the different number of days in each month

        Look for patterns that might correspond to your lifestyle, such as:
        - More listening during commutes
        - Weekend listening spikes
        - Seasonal variations (summer vs. winter)
        - Times of low activity (vacations, busy periods)
        """)

# Page setup
st.set_page_config(
    page_title="Graph.fm - Listening Calendar",
    layout="wide",
    page_icon="📅",
)

redirect_unauthenticated()
st.title("📅 Listening Calendar")
menu()
listening_calendar()
footer()