import streamlit as st
from api import get_user_info


def menu():
  st.sidebar.page_link("main.py", label="Add User",icon=":material/home:")
  if "scrobbles" in st.session_state and st.session_state.scrobbles:
    st.sidebar.page_link("pages/rank_compare.py", label="Rank Comparison",icon=":material/leaderboard:")
    user_pfp = get_user_info(st.session_state.user,"pfp")
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

