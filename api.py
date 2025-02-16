from altair.vegalite.v5.schema.core import Data
import requests
import urllib.parse
from datetime import datetime
import os
import math
import streamlit as st


api_key = os.environ["LASTFM_API_KEY"]
dataset = None

artist_corrections = {
  "Charli XCX": "Charli xcx",
  "Travi$ Scott": "Travis Scott",
  "geordie greep": "Geordie Greep",
  "Underscores": "underscores"
}

def get_scrobbles(user, page_num, artists=None):
  method = "user.getRecentTracks"
  
  params = {
    'limit': 1000,
    'page': page_num
  }

  url = f"https://ws.audioscrobbler.com/2.0/?method={method}&api_key={api_key}&user={user}&format=json"
  response = requests.get(url, params=params)
  if response.status_code != 200:
    return None
  data = response.json()

  if not artists:
    artists = {}
  scrobbles = []
  for track in data["recenttracks"]["track"]:

      
    if track.get("@attr",{}).get("nowplaying",False):
      continue
    album_name = track["album"]["#text"]
    track_name = track["name"]
    artist_name = track["artist"]["#text"]
    date_str = track["date"]["#text"]
    parsed_date = datetime.strptime(date_str, "%d %b %Y, %H:%M")
    artist_name = artist_corrections.get(artist_name, artist_name)
    
    artists[artist_name] = artists.get(artist_name, 0) + 1
    
    scrobbles.append({
      "track_name":track_name,
      "artist_name":artist_name,
      "album_name":album_name,
      "date":parsed_date.date()
    })


  return scrobbles, artists

def get_user_info(user,method=None):
  url = f"https://ws.audioscrobbler.com/2.0/?method=user.getinfo&api_key={api_key}&user={user}&format=json"
  response = requests.get(url)
  if response.status_code == 404:
    return {"error":"User not found, please try again"}
  if response.status_code == 200:
    data = response.json()
    if not method:
      return data["user"]
    if method == 'pfp':
      try:
        for icon in data["user"]["image"]:
          if icon["size"] == "small":
            return icon["#text"]
      except Exception:
          return None
  else:
    return {"error":"Internal Server Error, try again later"}

def generate_dataset(user):
  global dataset
  
  user_info = get_user_info(user)
  total_scrobbles = int(user_info["playcount"])
  required_pages = math.ceil(total_scrobbles / 1000)
  #required_pages = 2
  
  progress_bar = st.progress(0)  # Initialize progress bar
  page_num = 1
  scrobbles = []
  artists = None
  
  while page_num <= required_pages:
    addition = get_scrobbles(user, page_num, artists)
    if not addition:
      break
    else:
      new_scrobbles, artists = addition
      scrobbles += new_scrobbles
      progress_bar.progress(page_num/required_pages)  # Update progress
      page_num += 1

  dataset = scrobbles
  
  sorted_items = sorted(artists.items(), key=lambda item: item[1], reverse=True)

  # Convert to the required format with correct ranking
  ranked_artists = {key: {"scrobbles": value, "rank": rank + 1} for rank, (key, value) in enumerate(sorted_items)}
  st.session_state.artists = ranked_artists
  return scrobbles

def compare_ranks(dataset, date_1, date_2, type):
  streams1 = {}
  streams2 = {}
  search_terms = {
      "Artist": {"key": "artist_name", "artist": None},
      "Album": {"key": "album_name", "artist": "artist_name"},
      "Track": {"key": "track_name", "artist": "artist_name"}
  }
  search_term = search_terms[type]

  for scrobble in dataset:
      name = scrobble[search_term["key"]]
      artist = scrobble[search_term["artist"]] if search_term["artist"] else None
      date = scrobble["date"]

      # Combine name and artist into a single key, but account for dashes in names
      if artist:
          item_key = f"{name}:::{artist}"
      else:
          item_key = name
      if date <= date_1:
          streams1[item_key] = 1 + streams1.get(item_key, 0)
      if date <= date_2:
          streams2[item_key] = 1 + streams2.get(item_key, 0)
        
  # Create sorted lists of items by scrobble count for ranking
  ranked_item1 = sorted(streams1.items(), key=lambda x: x[1], reverse=True)
  ranked_item2 = sorted(streams2.items(), key=lambda x: x[1], reverse=True)
  # Create rank dictionaries
  rank_dict1 = {name: idx + 1 for idx, (name, _) in enumerate(ranked_item1)}
  rank_dict2 = {name: idx + 1 for idx, (name, _) in enumerate(ranked_item2)}
  # Create a list of dictionaries for DataFrame
  data = []
  for item in streams2:
      # Split back to name and artist if applicable, using a different separator
      if ':::' in item:
          name, artist = item.split(':::')
      else:
          name, artist = item, None
      scrobbles1 = streams1.get(item, 0)
      scrobbles2 = streams2.get(item, 0)
      rank1 = rank_dict1.get(item, len(streams2))
      rank2 = rank_dict2.get(item, len(streams2))
      rank_change = rank1 - rank2
      scrobbles_change = scrobbles2 - scrobbles1
      info = {type: name}
      if type != "Artist" and artist:
          info["Artist"] = artist
      info.update({
          "Rank (current)": rank2,
          "Rank (old)": rank1,
          "Scrobbles (current)": scrobbles2,
          "Scrobbles (old)": scrobbles1,
          "Rank Change": rank_change,
          "Scrobbles Change": scrobbles_change
      })
      data.append(info)
  # Sort the data list by current rank
  data.sort(key=lambda x: x["Rank (current)"])

  return data


translater = {
  "rap": "Hip-hop",
  "hip hop": "Hip-hop",
  "indie": "Alternative",
  "bubblegum bass": "Hyperpop"
}

genre_picker = {
  "Common": "Old School Hip-hop",
  "Wu-Tang Clan": "Old School Hip-hop",
  "Mos Def": "Old School Hip-hop",
  "2Pac": "Old School Hip-hop",
  "Dr. Dre": "Old School Hip-hop",
  "MF DOOM": "Old School Hip-hop",
  "Nas": "Old School Hip-hop",
  "OutKast": "Old School Hip-hop",
  "The Roots": "Old School Hip-hop",
  "The Pharcyde": "Old School Hip-hop",
  "A Tribe Called Quest": "Old School Hip-hop",
  "Makaveli": "Old School Hip-hop",
  "Black Star": "Old School Hip-hop",
  "Snoop Dogg": "Old School Hip-hop",
  "Fugees": "Old School Hip-hop",
  "De La Soul": "Old School Hip-hop",
  "Slum Village": "Old School Hip-hop",
  "Eminem": "Old School Hip-hop",
  "Black Sheep": "Old School Hip-hop",
  "Mobb Deep": "Old School Hip-hop",
  "The Notorious B.I.G.": "Old School Hip-hop",
  "Run-D.M.C.": "Old School Hip-hop",
  "JAY-Z.": "Old School Hip-hop",
  "Ice Cube": "Old School Hip-hop", 
  "Eric B. & Rakim": "Old School Hip-hop",
  "Eazy-E": "Old School Hip-hop",
  "Smif-N-Wessun": "Old School Hip-hop",
  "Lost Boyz": "Old School Hip-hop",
  "Danny Brown": "Old School Hip-hop",
  "J Dilla": "Beats",
  "JPEGMAFIA": "Experimental hip hop",
  "Danny Brown": "Experimental hip hop",
  "Deathgrips": "Experimental hip hop",
  "clipping.": "Experimental hip hop",
  "Missy Elliot.": "Experimental hip hop",
  "$NOT": "Trap",
  "Cochise": "Trap",
  "Terrace Martin": "Jazz"
}

def get_artist_tags(rank_limit):
  disqualifying_genres = ["seen live"]
  
  artists = st.session_state.artists
  
  aritst_tags = {}
  tag_relevance = {}
  for artist_name, artist_info in artists.items():
    rank = artist_info["rank"]
    if rank > rank_limit:
      continue

    weight = artist_info["scrobbles"]
      
    # URL-encode the artist name
    encoded_artist = urllib.parse.quote_plus(artist_name)
    url = f"https://ws.audioscrobbler.com/2.0/?method=artist.getTopTags&artist={encoded_artist}&api_key={api_key}&format=json"
    
    response = requests.get(url)
    data = response.json()
  
    if response.status_code != 200:
      continue
    else:
      for tag_info in data["toptags"]["tag"]:
        
        tag_name = tag_info["name"]
        if tag_name in disqualifying_genres:
          continue
        
        tag_name = (translater.get(tag_name,tag_name)).capitalize()
        count = tag_info["count"]
        
        
        if count >= 10:
          tag_relevance[tag_name] = {
            "count": count + (tag_relevance.get(tag_name,{})).get("count",0),
            "weight": weight + (tag_relevance.get(tag_name,{})).get("weight",0)
          }
        if not aritst_tags.get(artist_name):
          tag_name = genre_picker.get(artist_name) or tag_name
          aritst_tags[artist_name] = {"tag_name": tag_name,"weight": weight, "rank": rank}
            
  return aritst_tags, tag_relevance
  



