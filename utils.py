import streamlit as st


def menu():
  st.sidebar.page_link("main.py", label="Add User",icon=":material/home:")
  if "scrobbles" in st.session_state and st.session_state.scrobbles:
    st.sidebar.page_link("pages/rank_compare.py", label="Rank Comparison",icon=":material/leaderboard:")
    st.sidebar.success(st.session_state.user)

def redirect_unauthenticated():
  if 'user' not in st.session_state or not st.session_state.user:
    print("No user and on bad page!")
    st.switch_page(page="main.py")

