import streamlit as st
from api import get_user_info, generate_dataset
from utils import menu

# Initialize session state for user

def get_username():
  if 'username_form_submitted' not in st.session_state:
    st.session_state.username_form_submitted = False
    
  with st.form("username_form"):
    user = st.text_input('Enter your Last.fm username:')
    
    submit = st.form_submit_button('Submit')
    if submit:
      st.session_state.user = user
      st.session_state.username_form_submitted = True
      st.session_state.scrobbles = False
      st.session_state.results = False
      st.rerun()


def main():
  get_username()
  
  if ('user' in st.session_state) and (st.session_state.user):
    user = st.session_state.user

    if (('username_form_submitted' in st.session_state) and
      (st.session_state.username_form_submitted)):
    
      user_info = get_user_info(user)
  
      if user_info.get("error"):
        st.write(user_info["error"])
        st.session_state.user = None
        st.rerun()
      else:
        st.write(f"Fetching data for {user}...")
        scrobbles = generate_dataset(user)
        if not scrobbles:
          st.write("Error fetching data, please try again later")
        else:
          st.session_state.scrobbles = scrobbles
          st.session_state.username_form_submitted = False
          st.rerun()
    else:
      st.write(f"Data fetched for {user} start analyzing by choosing a page in the sidebar...")

    


st.set_page_config(
    page_title="Graph.fm",
    #layout="wide",  # This makes the page wider than default
    page_icon="📊",
    initial_sidebar_state="expanded"
)

menu()
st.title("Graph.fm")
st.write("Visualize your last.fm stats and rank changes!")
main()