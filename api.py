from altair.vegalite.v5.schema.core import Data
import requests
import urllib.parse
from datetime import datetime, date
import os
import math
import streamlit as st

api_key = os.environ["LASTFM_API_KEY"]

artist_corrections = {
    "Charli XCX": "Charli xcx",
    "Travi$ Scott": "Travis Scott",
    "geordie greep": "Geordie Greep",
    "Underscores": "underscores",
    "Nxworries": "NxWorries",
    "Boygenius": "boygenius",
    "Makaveli": "2Pac",
    "DeVon Hendryx": "Devon Hendryx"
}


def get_release_date(mbid):
  params = {'limit': 1000, 'page': 2}

  url = f"https://ws.audioscrobbler.com/2.0/?method=user.getRecentTracks&api_key={api_key}&user={user}&format=json"
  response = requests.get(url, params=params)


def generate_datasets(user):
  import time

  user_info = get_user_info(user)
  total_scrobbles = int(user_info["playcount"])
  required_pages = math.ceil(total_scrobbles / 1000)
  page_num = 0
  progress_bar = st.progress(0)
  progress_text = st.empty()

  artists = {}
  scrobbles = []
  min_date = date.max
  failed_pages = []
  actual_scrobbles_fetched = 0

  while page_num < required_pages:
    page_num += 1

    params = {'limit': 1000, 'page': page_num}

    url = f"https://ws.audioscrobbler.com/2.0/?method=user.getRecentTracks&api_key={api_key}&user={user}&format=json"

    # Retry logic for failed requests
    max_retries = 3
    retry_count = 0
    success = False

    while retry_count < max_retries and not success:
      try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
          data = response.json()

          # Check if we have valid track data
          if "recenttracks" in data and "track" in data["recenttracks"]:
            tracks = data["recenttracks"]["track"]
            page_scrobbles = 0

            for track in tracks:
              if track.get("@attr", {}).get("nowplaying", False):
                continue

              album_name = track["album"]["#text"]
              track_name = track["name"]
              mbid = track["mbid"]
              artist_name = track["artist"]["#text"]
              date_str = track["date"]["#text"]
              parsed_date = (datetime.strptime(date_str,
                                               "%d %b %Y, %H:%M")).date()
              artist_name = artist_corrections.get(artist_name, artist_name)

              if artist_name not in artists:
                top_tag = get_artist_tags(artist_name)
                artists[artist_name] = {"scrobbles": 1, "top_tag": top_tag}
              else:
                artists[artist_name]["scrobbles"] += 1

              genre = artists[artist_name]["top_tag"]
              parent_genre = genre_parent_map.get(genre, "Other")

              if parsed_date < min_date:
                min_date = parsed_date

              scrobbles.append({
                  "track_name": track_name,
                  "artist_name": artist_name,
                  "album_name": album_name,
                  "date": parsed_date,
                  "genre": genre,
                  "parent_genre": parent_genre
              })
              page_scrobbles += 1

            actual_scrobbles_fetched += page_scrobbles
            success = True
            progress_text.text(
                f"Fetched {actual_scrobbles_fetched}/{total_scrobbles} scrobbles (Page {page_num}/{required_pages})"
            )

          else:
            st.warning(f"No track data in response for page {page_num}")
            break

        elif response.status_code == 429:  # Rate limited
          wait_time = 2**retry_count  # Exponential backoff
          st.warning(
              f"Rate limited. Waiting {wait_time} seconds before retrying page {page_num}..."
          )
          time.sleep(wait_time)
          retry_count += 1

        else:
          st.warning(
              f"HTTP {response.status_code} error on page {page_num}. Retrying..."
          )
          retry_count += 1
          time.sleep(1)

      except requests.exceptions.RequestException as e:
        st.warning(
            f"Request failed for page {page_num}: {str(e)}. Retrying...")
        retry_count += 1
        time.sleep(1)

    if not success:
      failed_pages.append(page_num)
      st.error(f"Failed to fetch page {page_num} after {max_retries} attempts")

    # Small delay to be respectful to the API
    time.sleep(0.1)
    progress_bar.progress(page_num / required_pages)

  # Report on data completeness
  completion_rate = (actual_scrobbles_fetched / total_scrobbles) * 100
  progress_text.text(
      f"Completed: {actual_scrobbles_fetched}/{total_scrobbles} scrobbles ({completion_rate:.1f}%)"
  )

  if failed_pages:
    st.warning(
        f"Failed to fetch {len(failed_pages)} pages: {failed_pages}. Data may be incomplete."
    )

  if completion_rate < 95:
    st.warning(
        f"Only {completion_rate:.1f}% of scrobbles were fetched. Consider re-running the data fetch."
    )

  st.session_state.min_date = min_date
  st.session_state.scrobbles = scrobbles
  st.session_state.artists = artists
  return scrobbles, artists


def get_user_info(user, method=None):
  url = f"https://ws.audioscrobbler.com/2.0/?method=user.getinfo&api_key={api_key}&user={user}&format=json"
  response = requests.get(url)
  if response.status_code == 404:
    return {"error": "User not found, please try again"}
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
    return {"error": "Internal Server Error, try again later"}


def compare_ranks(dataset, date_1, date_2, type):
  streams1 = {}
  streams2 = {}
  search_terms = {
      "Artist": {
          "key": "artist_name",
          "addition": "genre"
      },
      "Genre": {
          "key": "genre"
      },
      "Album": {
          "key": "album_name",
          "addition": "artist_name"
      },
      "Track": {
          "key": "track_name",
          "addition": "artist_name"
      }
  }
  search_term = search_terms[type]

  # Track artists per genre (only when type == "Genre")
  genre_artists = {}

  for scrobble in dataset:
    name = scrobble[search_term["key"]]
    additional_term = scrobble[search_term.get("addition")] if search_term.get(
        "addition") else None
    date = scrobble["date"]

    # Track artists per genre only for Genre type (for all scrobbles up to date_2)
    if type == "Genre" and date <= date_2:
      genre = scrobble.get("genre")
      artist = scrobble.get("artist_name")
      if genre and artist:
        if genre not in genre_artists:
          genre_artists[genre] = set()
        genre_artists[genre].add(artist)

    # Combine name and artist into a single key, but account for dashes in names
    if additional_term:
      item_key = f"{name}/!-<:>::::-!/{additional_term}"
    else:
      item_key = name
    if date <= date_1:
      streams1[item_key] = 1 + streams1.get(item_key, 0)
    if date <= date_2:
      streams2[item_key] = 1 + streams2.get(item_key, 0)

  # Convert sets to counts (only when type == "Genre")
  if type == "Genre":
    genre_artist_counts = {
        genre: len(artists)
        for genre, artists in genre_artists.items()
    }

  # Create sorted lists of items by scrobble count for ranking
  ranked_item1 = sorted(streams1.items(), key=lambda x: x[1], reverse=True)
  ranked_item2 = sorted(streams2.items(), key=lambda x: x[1], reverse=True)
  # Create rank dictionaries
  rank_dict1 = {name: idx + 1 for idx, (name, _) in enumerate(ranked_item1)}
  rank_dict2 = {name: idx + 1 for idx, (name, _) in enumerate(ranked_item2)}
  # Create a list of dictionaries for DataFrame
  data = []
  for item in streams2:
    if not item:
      continue
    # Split back to name and artist if applicable, using a different separator
    if '/!-<:>::::-!/' in item:
      name, additional_term = item.split('/!-<:>::::-!/')
    else:
      name, additional_term = item, None
    scrobbles1 = streams1.get(item, 0)
    scrobbles2 = streams2.get(item, 0)
    rank1 = rank_dict1.get(item, len(streams2))
    rank2 = rank_dict2.get(item, len(streams2))
    rank_change = rank1 - rank2
    scrobbles_change = scrobbles2 - scrobbles1
    info = {type: name}
    if additional_term:
      additional_name = "Artist" if search_term.get(
          "addition") == "artist_name" else "Genre"
      info[additional_name] = additional_term
    info.update({
        "Rank (current)": rank2,
        "Rank (old)": rank1,
        "Scrobbles (current)": scrobbles2,
        "Scrobbles (old)": scrobbles1,
        "Rank Change": rank_change,
        "Scrobbles Change": scrobbles_change
    })

    # Add artist count only for Genre type
    if type == "Genre":
      info["Artists in Genre"] = genre_artist_counts.get(name, 0)

    data.append(info)
  # Sort the data list by current rank
  data.sort(key=lambda x: x["Rank (current)"])
  return data


translater = {
    "rap": "Hip-hop",
    "hip hop": "Hip-hop",
    "bubblegum bass": "Hyperpop",
    "experimental hip hop": "Experimental Hip-hop"
}

genre_parent_map = {
    "Hip-hop": "Hip-hop",
    "Rnb": "R&B/Soul/Funk",
    "Trap": "Hip-hop",
    "Old School Hip-hop": "Hip-hop",
    "Pop": "Pop",
    "Soul": "R&B/Soul/Funk",
    "Electronic": "Electronic",
    "Experimental Hip-hop": "Hip-hop",
    "Indie": "Rock",
    "Dream pop": "Rock",
    "Indie rock": "Rock",
    "Rock": "Rock",
    "Trip-hop": "Electronic",
    "Classic rock": "Rock",
    "Singer-songwriter": "Folk/Country",
    "Country": "Folk/Country",
    "Folk": "Folk/Country",
    "Shoegaze": "Rock",
    "Hyperpop": "Pop",
    "Slowcore": "Rock",
    "Art pop": "Pop",
    "Post-punk": "Rock",
    "Emo rap": "Hip-hop",
    "Indie pop": "Pop",
    "Beats": "Electronic",
    "Digicore": "Electronic",
    "2-step": "Electronic",
    "Alternative": "Rock",
    "Free jazz": "Jazz",
    "Chillwave": "Electronic",
    "Neo-psychedelia": "Rock",
    "Grime": "Electronic",
    "Jazz": "Jazz",
    "Synthpop": "Pop",
    "Funk": "R&B/Soul/Funk",
    "Dubstep": "Electronic",
    "Jazz rap": "Hip-hop",
    "Psychedelic rock": "Rock",
    "Electro house": "Electronic",
    "Drill": "Hip-hop",
    "Progressive rock": "Rock",
    "Grunge": "Rock",
    "Art rock": "Rock",
    "Female vocalists": "Other",
    "Cloud rap": "Hip-hop",
    "Vaporwave": "Electronic",
    "Experimental": "Other",
    "Nigeria": "Other",
    "NA": "Other",
    "Lo-fi": "Hip-hop",
    "Jungle": "Electronic",
    "Psychedelic": "Rock",
    "Reggae": "Reggae/Dub",
    "Alternative rock": "Rock",
    "Sigilkore": "Other",
    "House": "Electronic",
    "Glitch pop": "Pop",
    "Breakcore": "Electronic",
    "Ambient": "Electronic",
    "Wonky": "Electronic",
    "K-pop": "Pop",
    "Dub": "Reggae/Dub",
    "Usa": "Other",
    "Nu metal": "Rock",
    "Punk rock": "Rock",
    "Stoner rock": "Rock",
    "Disco": "R&B/Soul/Funk",
    "Alternative rnb": "R&B/Soul/Funk",
    "New wave": "Rock",
    "Rage": "Hip-hop",
    "Punk": "Rock",
    "Folktronica": "Folk/Country",
    "Witch house": "Electronic",
    "Math rock": "Rock",
    "Twee": "Pop",
    "Plugg": "Hip-hop",
    "Britpop": "Rock",
    "Emo": "Rock",
    "Hardcore punk": "Rock",
    "Instrumental": "Other",
    "Black metal": "Rock",
    "Dj": "Other",
    "Swedish": "Other",
    "Heavy metal": "Rock",
    "Bossa nova": "Jazz",
    "Horrorcore": "Hip-hop",
    "Idm": "Electronic",
    "Hardcore": "Electronic",
    "Lounge": "Jazz",
    "West coast": "Hip-hop",
    "English": "Other",
    "Techno": "Electronic",
    "Texas": "Other",
    "Pop punk": "Rock",
    "Blues": "R&B/Soul/Funk",
    "J-pop": "Pop",
    "Goat": "Other",
    "Turntablism": "Hip-hop",
    "Instrumental hip-hop": "Hip-hop",
    "Woman beater": "Other",
    "Austria": "Other",
    "Pluggnb": "Hip-hop",
    "Electropop": "Pop",
    "Drum and bass": "Electronic",
    "American": "Other",
    "Blues rock": "Rock",
    "Chiptune": "Electronic",
    "Japanese": "Other",
    "Hard rock": "Rock",
    "Seen live more than once": "Other",
    "Jazz rock": "Rock",
    "Steezemusik": "Other",
    "Opium": "Other",
    "Midwest emo": "Rock",
    "Piano": "Other",
    "Spanish": "Other",
    "Post-hardcore": "Rock",
    "Acid jazz": "Jazz",
    "Oldies": "Other",
    "Memphis": "Hip-hop",
    "Elfaction": "Other",
    "Industrial black metal": "Rock",
    "Garage rock": "Rock",
    "French": "Other",
    "Trance": "Electronic",
    "Rockabilly": "Rock",
    "Lana del rey -ish": "Other",
    "Burgerrecords": "Other",
    "Noise pop": "Pop",
    "Blow up": "Other",
    "Chinese": "Other",
    "Sextrance": "Other",
    "Covers": "Other",
    "Reggaeton": "Pop",
    "Uk": "Other",
    "Chillout": "Electronic",
    "Punk cabaret": "Other",
    "United states": "Other",
    "Synthwave": "Electronic",
    "Hiphop": "Hip-hop",
    "Downtempo": "Electronic",
    "My top songs": "Other",
    "Dance": "Electronic",
    "Acoustic": "Other",
    "Korean": "Other",
    "Digital hardcore": "Electronic",
    "Drone": "Electronic",
    "Soundtrack": "Other",
    "60s": "Other",
    "Australian": "Other",
    "Bedroom pop": "Pop",
    "Undergroundhiphop downlodugs itsbetterthansoundcloud": "Other",
    "Neo soul": "R&B/Soul/Funk",
    "4 stars": "Other",
    "Afrobeats": "R&B/Soul/Funk",
    "Chamber pop": "Pop",
    "Funk_add_to_lidarr_batch_20": "Other",
    "Glam rock": "Rock",
    "Uk bass": "Electronic",
    "Post-rock": "Rock",
    "Progressive metal": "Rock",
    "Chillhop": "Hip-hop",
    "Underground hip-hop": "Hip-hop",
    "Ethereal": "Pop",
    "Jangle pop": "Pop",
    "Deep house": "Electronic",
    "Ensemble": "Other",
    "Rock argentino": "Rock",
    "Pop rock": "Rock",
    "G-funk": "Hip-hop",
    "Ac/dc": "Rock",
    "Glitch hop": "Hip-hop",
    "Neo-soul": "R&B/Soul/Funk",
    "Atlanta": "Other",
    "Afrobeat": "R&B/Soul/Funk",
    "Nwobhm": "Rock",
    "Space rock": "Rock",
    "Grey's anatomy": "Other",
    "Uk rap": "Hip-hop",
    "80s": "Other",
    "Hypnagogic pop": "Pop",
    "Composer": "Other",
    "Mexico": "Other",
    "Southern hip hop": "Hip-hop",
    "Phonk": "Hip-hop",
    "Ethel cain": "Other",
    "Acid": "Electronic",
    "Beatbox": "Hip-hop",
    "Rapcore": "Rock",
    "Minimalism": "Classical/Minimalism",
    "Netherlands": "Other",
    "Crank wave": "Other",
    "Rare sad girl": "Other",
    "Slacker rock": "Rock",
    "Riot grrrl": "Rock",
    "Us": "Other",
    "Germany": "Other",
    "Metalcore": "Rock",
    "Classical": "Classical/Minimalism",
    "Dariacore": "Electronic",
    "Psychobilly": "Rock",
    "Indietronica": "Electronic",
    "Video game music": "Other",
    "Screamo": "Rock",
    "Rock n roll": "Rock",
    "Kenyan": "Other",
    "Electronica": "Electronic",
    "African": "Other",
    "Edm": "Electronic",
    "Jazz hop": "Hip-hop",
    "Dutch": "Other",
    "Male vocalists": "Other",
    "Hardstyle": "Electronic",
    "Female art rap": "Hip-hop",
    "Electro": "Electronic",
    "Funk_add_to_lidarr_batch_23": "Other",
    "Canadian": "Other",
    "J-rock": "Rock"
}

#genre_picker = {}
genre_picker = {
    "Quadeca": "Alternative",
    "Ghetto Sage": "Hip-hop",
    "ssgkobe": "Hip-hop",
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
    "GZA": "Old School Hip-hop",
    "RZA": "Old School Hip-hop",
    "DMX": "Old School Hip-hop",
    "Bone Thugs-N-Harmony": "Old School Hip-hop",
    "A Tribe Called Quest": "Old School Hip-hop",
    "Salt-N-Pepa": "Old School Hip-hop",
    "Digable Planets": "Old School Hip-hop",
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
    "JAY-Z": "Old School Hip-hop",
    "Ice Cube": "Old School Hip-hop",
    "Eric B. & Rakim": "Old School Hip-hop",
    "Eazy-E": "Old School Hip-hop",
    "Smif-N-Wessun": "Old School Hip-hop",
    "Gang Starr": "Old School Hip-hop",
    "Souls of Mischief": "Old School Hip-hop",
    "AZ": "Old School Hip-hop",
    "Lost Boyz": "Old School Hip-hop",
    "Da Brat": "Old School Hip-hop",
    "Ol' Dirty Bastard": "Old School Hip-hop",
    "Ghostface Killah": "Old School Hip-hop",
    "Missy Elliott": "Old School Hip-hop",
    "J Dilla": "Beats",
    "JPEGMAFIA": "Experimental Hip-hop",
    "Death Grips": "Experimental Hip-hop",
    "Danny Brown": "Experimental Hip-hop",
    "Deathgrips": "Experimental Hip-hop",
    "clipping.": "Experimental Hip-hop",
    "$NOT": "Trap",
    "Cochise": "Trap",
    "Young Stoner Life": "Trap",
    "Gunna": "Trap",
    "Quavo": "Trap",
    "Travis Scott": "Trap",
    "Future": "Trap",
    "Young Thug": "Trap",
    "XXXTENTACION": "Emo rap",
    "Juice WRLD": "Emo rap",
    "Terrace Martin": "Jazz",
    "Nujabes": "Jazz",
    "Blu": "Jazz rap",
    "Blu & Exile": "Jazz rap"
}

disqualifying_genres = ["seen live"]


def get_artist_tags(artist_name):
  import time

  if genre_picker.get(artist_name):
    return genre_picker[artist_name]

  # URL-encode the artist name
  encoded_artist = urllib.parse.quote_plus(artist_name)
  url = f"https://ws.audioscrobbler.com/2.0/?method=artist.getTopTags&artist={encoded_artist}&api_key={api_key}&format=json"

  max_retries = 2
  retry_count = 0

  while retry_count < max_retries:
    try:
      response = requests.get(url, timeout=5)

      if response.status_code == 200:
        data = response.json()
        if "toptags" in data and "tag" in data["toptags"]:
          for tag_info in data["toptags"]["tag"]:
            tag_name = tag_info["name"]
            if tag_name in disqualifying_genres:
              continue
            tag_name = translater.get(tag_name, tag_name.capitalize())
            return tag_name
        return "NA"

      elif response.status_code == 429:  # Rate limited
        time.sleep(0.5)
        retry_count += 1
      else:
        return "NA"

    except requests.exceptions.RequestException:
      retry_count += 1
      time.sleep(0.2)

  return "NA"


def genre_dict(start_date, end_date):
  scrobbles = st.session_state.scrobbles

  filtered_artist_info = {}

  for scrobble in scrobbles:
    if scrobble["date"] < start_date or scrobble["date"] > end_date:
      continue

    artist_name = scrobble["artist_name"]
    top_tag = scrobble["genre"]

    if artist_name not in filtered_artist_info:
      filtered_artist_info[artist_name] = {
          "tag_name": top_tag,
          "scrobbles": 1,
      }
    else:
      filtered_artist_info[artist_name]["scrobbles"] += 1

  sorted_artists = sorted(filtered_artist_info.items(),
                          key=lambda item: item[1]["scrobbles"],
                          reverse=True)

  # Convert to the required format with correct ranking
  ranked_artists = {
      key: {
          "tag_name": value["tag_name"],
          "scrobbles": value["scrobbles"],
          "rank": rank + 1,
      }
      for rank, (key, value) in enumerate(sorted_artists)
  }

  st.session_state.artists_genre = ranked_artists
  return ranked_artists
