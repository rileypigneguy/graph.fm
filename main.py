import streamlit as st
from api import get_user_info, generate_dataset, compare_ranks, get_scrobbles

st.title("Graph.fm")
st.write("Visualize your last.fm stats and rank changes!")

# Initialize session state for user
if 'user' not in st.session_state:
    st.session_state.user = ''
    st.session_state.submitted = False

user = st.text_input('Enter your Last.fm username:', value=st.session_state.user)
submit = st.button('Submit')

if submit or st.session_state.submitted:
    st.session_state.submitted = True
    st.session_state.user = user
    user_info = get_user_info(user)

    if user_info.get("error"):
      st.write(user_info["error"])
    else:
      st.write(f"Fetching data for {user}...")
      dataset = generate_dataset(user)
      if not dataset:
        st.write("Error fetching data, please try again later")
      else:
        date1 = st.date_input('Enter period 1, ending date:')
        date2 = st.date_input('Enter period 2, ending date:')
        compare = st.button('Compare!')
  
        if compare:
            #generate_dataset(user)
            data = compare_ranks(date1, date2)
            st.dataframe(data)



  