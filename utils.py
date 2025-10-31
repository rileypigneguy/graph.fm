import streamlit as st
from api import get_user_info


def menu():
  st.sidebar.page_link("main.py", label="Input User", icon=":material/login:")
  if "scrobbles" in st.session_state and st.session_state.scrobbles:
    st.sidebar.page_link("pages/rank_compare.py",
                         label="Rank Comparison",
                         icon=":material/leaderboard:")
    st.sidebar.page_link("pages/genre_tree_map.py",
                         label="Genre Treemap",
                         icon=":material/radio:")
    st.sidebar.page_link("pages/genre_trend.py",
                         label="Genre Timeline",
                         icon=":material/timeline:")
    st.sidebar.page_link("pages/listening_stats.py",
                         label="Listening Stats",
                         icon=":material/music_note:")
    st.sidebar.page_link("pages/first_achievers.py",
                         label="First Achievers Stats",
                         icon=":material/emoji_events:")
    #st.sidebar.page_link("pages/music_discovery.py",
                         #label="Music Discovery",
                         #icon=":material/headphones:")
    #st.sidebar.page_link("pages/similar_artists_network.py",
                       #label="Artist Network",
                       #icon=":material/share:")
    #st.sidebar.page_link("pages/listening_calendar.py",
                       #label="Listening Calendar",
                       #icon=":material/calendar_month:")

    user_pfp = get_user_info(st.session_state.user, "pfp")
    st.sidebar.write("---")
    if user_pfp:
      col1, col2 = st.sidebar.columns([1, 7])
      with col1:
        st.image(user_pfp)
      with col2:
        st.write(st.session_state.user)
    else:
      st.sidebar.write(st.session_state.user)


def redirect_unauthenticated():
  if 'user' not in st.session_state or not st.session_state.user:
    print("No user and on bad page!")
    st.switch_page(page="main.py")


def footer():
  st.write("Made with [last.fm](%s)" % "https://www.last.fm/home")
