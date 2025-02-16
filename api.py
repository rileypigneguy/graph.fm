from altair.vegalite.v5.schema.core import Data
import requests
from datetime import datetime
import os
import math


api_key = os.environ["LASTFM_API_KEY"]
dataset = None

def get_scrobbles(user, page_num):
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
  
  scrobbles = []
  for track in data["recenttracks"]["track"]:

      
    if track.get("@attr",{}).get("nowplaying",False):
      continue
    album_name = track["album"]["#text"]
    track_name = track["name"]
    artist_name = track["artist"]["#text"]
    date_str = track["date"]["#text"]
    parsed_date = datetime.strptime(date_str, "%d %b %Y, %H:%M")

    scrobbles.append({
      "track_name":track_name,
      "artist_name":artist_name,
      "album_name":album_name,
      "date":parsed_date.date()
    })
    
  return scrobbles


def get_user_info(user):
  url = f"https://ws.audioscrobbler.com/2.0/?method=user.getinfo&api_key={api_key}&user={user}&format=json"
  response = requests.get(url)
  if response.status_code == 404:
    return {"error":"User not found, please try again"}
  if response.status_code == 200:
    data = response.json()
    return data["user"]
  else:
    return {"error":"Internal Server Error, try again later"}

def generate_dataset(user):
  global dataset
  
  user = get_user_info(user)
  total_scrobbles = int(user["playcount"])
  required_pages = math.ceil(total_scrobbles / 1000)
  
  page_num = 1
  scrobbles = []
  
  while page_num <= required_pages:
    addition = get_scrobbles(user, page_num)
    if not addition:
      break
    scrobbles += addition
    page_num += 1

  dataset = scrobbles
  return scrobbles

def compare_ranks(date_1, date_2):
  global dataset
  artist_ranks1 = {}
  artist_ranks2 = {}
    
  for scrobble in dataset:
    artist = scrobble["artist_name"]
    date = scrobble["date"]
    if date <= date_1:
      artist_ranks1[artist] = 1 + artist_ranks1.get(artist, 0)
    if date <= date_2:
      artist_ranks2[artist] = 1 + artist_ranks2.get(artist, 0)

  # Combine artists from both rankings
  all_artists = set(artist_ranks1.keys()).union(artist_ranks2.keys())

  # Create sorted lists of artists by scrobble count for ranking
  ranked_artists1 = sorted(artist_ranks1.items(), key=lambda x: x[1], reverse=True)
  ranked_artists2 = sorted(artist_ranks2.items(), key=lambda x: x[1], reverse=True)

  # Create rank dictionaries
  rank_dict1 = {artist: idx + 1 for idx, (artist, _) in enumerate(ranked_artists1)}
  rank_dict2 = {artist: idx + 1 for idx, (artist, _) in enumerate(ranked_artists2)}

  # Create a list of dictionaries for DataFrame
  data = []
  for artist in all_artists:
      scrobbles1 = artist_ranks1.get(artist, 0)
      scrobbles2 = artist_ranks2.get(artist, 0)
      rank1 = rank_dict1.get(artist, len(all_artists))
      rank2 = rank_dict2.get(artist, len(all_artists))
      rank_change = rank1 - rank2
      scrobbles_change = scrobbles2 - scrobbles1

      data.append({
          "Artist": artist,
          "Rank 1": rank1,
          "Rank 2": rank2,
          "Scrobbles 1": scrobbles1,
          "Scrobbles 2": scrobbles2,
          "Rank_Change": rank_change,
          "Scrobbles_Change": scrobbles_change
      })

  # Sort the data list by Rank1
  data.sort(key=lambda x: x["Rank 1"])

  return data




    


