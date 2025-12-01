import streamlit as st
from api import get_user_info


def menu():
    st.sidebar.page_link("main.py", label="Input User", icon=":material/login:")

    if st.session_state.get("scrobbles"):
        analysis_pages = [
            ("pages/rank_compare.py", "Rank Comparison", ":material/leaderboard:"),
            ("pages/genre_tree_map.py", "Genre Treemap", ":material/radio:"),
            ("pages/genre_trend.py", "Genre Timeline", ":material/timeline:"),
            ("pages/listening_stats.py", "Listening Stats", ":material/music_note:"),
            ("pages/first_achievers.py", "First Achievers Stats", ":material/emoji_events:"),
            ("pages/uniqued.py", "Uniqued", ":material/stars:"),
        ]

        for script_path, label, icon in analysis_pages:
            st.sidebar.page_link(script_path, label=label, icon=icon)

    if st.session_state.get("user"):
        username = st.session_state.user
        user_pfp = get_user_info(username, "pfp")

        st.sidebar.write("---")

        if user_pfp:
            col1, col2 = st.sidebar.columns([1, 7])
            with col1:
                st.image(user_pfp, width=40)
            with col2:
                st.markdown(f"<div style='padding-top: 5px;'><b>{username}</b></div>",unsafe_allow_html=True)
        else:
            st.sidebar.write(username)


def redirect_unauthenticated():
  if 'user' not in st.session_state or not st.session_state.user:
    print("No user and on bad page!")
    st.switch_page(page="main.py")


def footer():
  st.write("Made with [last.fm](%s)" % "https://www.last.fm/home")
