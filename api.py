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
  params = {
    'limit': 1000,
    'page': 2
  }

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
    
    params = {
      'limit': 1000,
      'page': page_num
    }
    
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
              if track.get("@attr",{}).get("nowplaying",False):
                continue
                
              album_name = track["album"]["#text"]
              track_name = track["name"]
              mbid = track["mbid"]
              artist_name = track["artist"]["#text"]
              date_str = track["date"]["#text"]
              parsed_date = (datetime.strptime(date_str, "%d %b %Y, %H:%M")).date()
              artist_name = artist_corrections.get(artist_name, artist_name)
              
              if artist_name not in artists:
                top_tag = get_artist_tags(artist_name)
                artists[artist_name] = {
                  "scrobbles": 1,
                  "top_tag": top_tag
                }
              else:
                artists[artist_name]["scrobbles"] += 1

              if parsed_date < min_date:
                min_date = parsed_date
              
              scrobbles.append({
                "track_name":track_name,
                "artist_name":artist_name,
                "album_name":album_name,
                "date":parsed_date,
                "genre": artists[artist_name]["top_tag"]
              })
              page_scrobbles += 1
            
            actual_scrobbles_fetched += page_scrobbles
            success = True
            progress_text.text(f"Fetched {actual_scrobbles_fetched}/{total_scrobbles} scrobbles (Page {page_num}/{required_pages})")
            
          else:
            st.warning(f"No track data in response for page {page_num}")
            break
            
        elif response.status_code == 429:  # Rate limited
          wait_time = 2 ** retry_count  # Exponential backoff
          st.warning(f"Rate limited. Waiting {wait_time} seconds before retrying page {page_num}...")
          time.sleep(wait_time)
          retry_count += 1
          
        else:
          st.warning(f"HTTP {response.status_code} error on page {page_num}. Retrying...")
          retry_count += 1
          time.sleep(1)
          
      except requests.exceptions.RequestException as e:
        st.warning(f"Request failed for page {page_num}: {str(e)}. Retrying...")
        retry_count += 1
        time.sleep(1)
    
    if not success:
      failed_pages.append(page_num)
      st.error(f"Failed to fetch page {page_num} after {max_retries} attempts")
    
    # Small delay to be respectful to the API
    time.sleep(0.1)
    progress_bar.progress(page_num/required_pages)

  # Report on data completeness
  completion_rate = (actual_scrobbles_fetched / total_scrobbles) * 100
  progress_text.text(f"Completed: {actual_scrobbles_fetched}/{total_scrobbles} scrobbles ({completion_rate:.1f}%)")
  
  if failed_pages:
    st.warning(f"Failed to fetch {len(failed_pages)} pages: {failed_pages}. Data may be incomplete.")
  
  if completion_rate < 95:
    st.warning(f"Only {completion_rate:.1f}% of scrobbles were fetched. Consider re-running the data fetch.")

  st.session_state.min_date = min_date
  st.session_state.scrobbles = scrobbles
  st.session_state.artists = artists
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


def compare_ranks(dataset, date_1, date_2, type):
  streams1 = {}
  streams2 = {}
  search_terms = {
      "Artist": {"key": "artist_name", "addition": "genre"},
      "Genre": {"key": "genre"},
      "Album": {"key": "album_name", "addition": "artist_name"},
      "Track": {"key": "track_name", "addition": "artist_name"}
  }
  search_term = search_terms[type]

  for scrobble in dataset:
      name = scrobble[search_term["key"]]
      additional_term = scrobble[search_term["addition"]] if search_term.get("addition") else None
      date = scrobble["date"]

      # Combine name and artist into a single key, but account for dashes in names
      if additional_term:
          item_key = f"{name}/!-<:>::::-!/{additional_term}"
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
          additional_name = "Artist" if search_term.get("addition") == "artist_name" else "Genre"
          info[additional_name] = additional_term
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
  "bubblegum bass": "Hyperpop",
  "experimental hip hop": "Experimental Hip-hop"
}
x="""genre_picker = {
    "Kanye West": "Hip-hop",
    "Kendrick Lamar": "Conscious Hip-hop",
    "Mac Miller": "Alternative Hip-hop",
    "JPEGMAFIA": "Experimental Hip-hop",
    "Travis Scott": "Trap",
    "Tyler, the Creator": "Alternative Hip-hop",
    "Frank Ocean": "Alternative R&B",
    "Charli XCX": "Hyperpop",
    "Playboi Carti": "Cloud Rap",
    "SZA": "Alternative R&B",
    "Denzel Curry": "Conscious Hip-hop",
    "Radiohead": "Alternative Rock",
    "A$AP Rocky": "Cloud Rap",
    "MF DOOM": "Boom Bap",
    "JID": "Conscious Hip-hop",
    "Beyoncé": "R&B",
    "The Weeknd": "Alternative R&B",
    "Young Thug": "Trap",
    "Little Simz": "Conscious Hip-hop",
    "BROCKHAMPTON": "Alternative Hip-hop",
    "The Beatles": "Classic Rock",
    "FKA twigs": "Trip-hop",
    "Freddie Gibbs": "Boom Bap",
    "Drake": "Pop Rap",
    "Future": "Trap",
    "Childish Gambino": "Alternative Hip-hop",
    "Smino": "Alternative R&B",
    "Isaiah Rashad": "Conscious Hip-hop",
    "Caroline Polachek": "Art Pop",
    "Taylor Swift": "Pop",
    "King Krule": "Indie Rock",
    "Vince Staples": "Conscious Hip-hop",
    "Noname": "Conscious Hip-hop",
    "Lana Del Rey": "Indie Pop",
    "A Tribe Called Quest": "Boom Bap",
    "Phoebe Bridgers": "Singer-Songwriter",
    "Kid Cudi": "Alternative Hip-hop",
    "Mitski": "Indie Rock",
    "Vampire Weekend": "Indie Rock",
    "Nas": "Boom Bap",
    "JAY-Z": "Boom Bap",
    "Saba": "Conscious Hip-hop",
    "NxWorries": "Soul",
    "OutKast": "Alternative Hip-hop",
    "Juice WRLD": "Emo Rap",
    "Danny Brown": "Experimental Hip-hop",
    "The 1975": "Indie Pop",
    "Steve lacy": "Alternative R&B",
    "J. Cole": "Conscious Hip-hop",
    "D'Angelo": "Neo-Soul",
    "Lil Uzi Vert": "Cloud Rap",
    "Alvvays": "Dream Pop",
    "Björk": "Experimental Pop",
    "Sampha": "Alternative R&B",
    "Ethel Cain": "Dream Pop",
    "Yves Tumor": "Experimental Pop",
    "Joey Bada$$": "Boom Bap",
    "Quadeca": "Alternative",
    "Billie Eilish": "Pop",
    "Billy Woods": "Experimental Hip-hop",
    "Ms. Lauryn Hill": "Neo-Soul",
    "J Dilla": "Instrumental Hip-hop",
    "Magdalena Bay": "Synthpop",
    "yeule": "Electronic",
    "The Notorious B.I.G.": "Boom Bap",
    "Blxst": "R&B",
    "Brent Faiyaz": "Alternative R&B",
    "2Pac": "Boom Bap",
    "Rina Sawayama": "Pop",
    "Pusha T": "Boom Bap",
    "Kelela": "Alternative R&B",
    "underscores": "Hyperpop",
    "Don Toliver": "Trap",
    "ScHoolboy Q": "Conscious Hip-hop",
    "Tame Impala": "Psychedelic Rock",
    "Chance the Rapper": "Conscious Hip-hop",
    "Olivia Rodrigo": "Pop",
    "PinkPantheress": "Electronic",
    "KIDS SEE GHOSTS": "Alternative Hip-hop",
    "Lorde": "Indie Pop",
    "boygenius": "Indie Rock",
    "Common": "Old School Hip-hop",
    "Weyes Blood": "Art Pop",
    "Pop Smoke": "Drill",
    "Lil Yachty": "Cloud Rap",
    "Anderson .Paak": "Soul",
    "Roddy Ricch": "Trap",
    "Grimes": "Experimental Pop",
    "6LACK": "Alternative R&B",
    "Tkay Maidza": "Alternative Hip-hop",
    "Erykah Badu": "Neo-Soul",
    "Bruno Mars": "Pop",
    "Porter Robinson": "Electronic",
    "slowthai": "Grime",
    "Mos Def": "Boom Bap",
    "Bryson Tiller": "R&B",
    "Blu & Exile": "Boom Bap",
    "Solange": "Alternative R&B",
    "Marvin Gaye": "Soul",
    "Metro Boomin": "Trap",
    "Injury Reserve": "Experimental Hip-hop",
    "The Roots": "Alternative Hip-hop",
    "Dijon": "Alternative R&B",
    "KAYTRANADA": "House",
    "Jamie xx": "Electronic",
    "McKinley Dixon": "Jazz Rap",
    "Daniel Caesar": "R&B",
    "The Strokes": "Indie Rock",
    "The Smile": "Art Rock",
    "clipping.": "Experimental Hip-hop",
    "Kacey Musgraves": "Country",
    "Paramore": "Pop Rock",
    "21 Savage": "Trap",
    "Cocteau Twins": "Dream Pop",
    "Mach-Hommy": "Boom Bap",
    "The Internet": "Soul",
    "Danger Mouse": "Alternative Hip-hop",
    "Jazmine Sullivan": "R&B",
    "IDK": "Conscious Hip-hop",
    "Stevie Wonder": "Soul",
    "Partyof2": "Trap",
    "Nirvana": "Grunge",
    "Kenny Beats": "Instrumental Hip-hop",
    "Michael Jackson": "Pop",
    "Blood Orange": "Alternative R&B",
    "Sophie": "Hyperpop",
    "Jeff Buckley": "Singer-Songwriter",
    "Slowdive": "Shoegaze",
    "Baby Keem": "Conscious Hip-hop",
    "Sir": "R&B",
    "Aminé": "Alternative Hip-hop",
    "Japanese Breakfast": "Indie Pop",
    "Fontaines D.C.": "Post-punk",
    "Wu-Tang Clan": "Boom Bap",
    "Logic": "Conscious Hip-hop",
    "Amy Winehouse": "Soul",
    "Soccer Mommy": "Indie Pop",
    "Devon Hendryx": "Experimental Hip-hop",
    "Portishead": "Trip-hop",
    "Mk.gee": "Alternative R&B",
    "Rihanna": "Pop",
    "Navy Blue": "Boom Bap",
    "Chappell Roan": "Pop",
    "Burial": "Dubstep",
    "Have a Nice Life": "Shoegaze",
    "Fugees": "Boom Bap",
    "Teyana Taylor": "R&B",
    "Sabrina Carpenter": "Pop",
    "Massive Attack": "Trip-hop",
    "Daft Punk": "Electronic",
    "Lupe Fiasco": "Conscious Hip-hop",
    "Odunsi (The Engine)": "Afrobeats",
    "Pink Floyd": "Progressive Rock",
    "PARTYNEXTDOOR": "Alternative R&B",
    "Nujabes": "Jazz Rap",
    "Men I Trust": "Dream Pop",
    "$NOT": "Trap",
    "Prince": "Funk",
    "Digable Planets": "Boom Bap",
    "Doechii": "Alternative Hip-hop",
    "Jessica Pratt": "Folk",
    "Kate Bush": "Art Pop",
    "Black Country, New Road": "Post-punk",
    "Fiona Apple": "Singer-Songwriter",
    "my bloody valentine": "Shoegaze",
    "Thundercat": "Funk",
    "Pi'erre Bourne": "Trap",
    "The Pharcyde": "Alternative Hip-hop",
    "Oklou": "Electronic",
    "Trippie Redd": "Emo Rap",
    "Lianne La Havas": "Soul",
    "Jordan Ward": "R&B",
    "Sky Ferreira": "Indie Pop",
    "Terrace Martin": "Jazz Rap",
    "Fleetwood Mac": "Classic Rock",
    "Ski Mask the Slump God": "Trap",
    "Snoop Dogg": "G-Funk",
    "Dreamville": "Conscious Hip-hop",
    "Dua Lipa": "Pop",
    "Beach House": "Dream Pop",
    "Ravyn Lenae": "Alternative R&B",
    "Slow Pulp": "Dream Pop",
    "Killer Mike": "Conscious Hip-hop",
    "Geordie Greep": "Progressive Rock",
    "The Velvet Underground": "Art Rock",
    "BLK ODYSSY": "Soul",
    "Cordae": "Conscious Hip-hop",
    "Missy Elliott": "Hip-hop",
    "tobi lou": "Alternative Hip-hop",
    "XXXTENTACION": "Emo Rap",
    "Sly & The Family Stone": "Funk",
    "DOMi & JD Beck": "Jazz",
    "100 gecs": "Hyperpop",
    "Yeat": "Trap",
    "orion sun": "Alternative R&B",
    "Black Star": "Boom Bap",
    "Dr. Dre": "G-Funk",
    "The War on Drugs": "Indie Rock",
    "A Boogie wit da Hoodie": "Trap",
    "Sade": "Soul",
    "Kali Uchis": "Alternative R&B",
    "beabadoobee": "Indie Pop",
    "Flying Lotus": "Electronic",
    "Joy Division": "Post-punk",
    "Joey Valence & Brae": "Alternative Hip-hop",
    "Simon & Garfunkel": "Folk",
    "Sufjan Stevens": "Indie Folk",
    "JACKBOYS": "Trap",
    "Lil Tecca": "Trap",
    "Nick Drake": "Folk",
    "GoldLink": "Alternative Hip-hop",
    "ANOHNI": "Art Pop",
    "Aaliyah": "R&B",
    "KaytrAminé": "Alternative Hip-hop",
    "Lush": "Shoegaze",
    "Sonder": "Alternative R&B",
    "Cochise": "Trap",
    "Jay Electronica": "Conscious Hip-hop",
    "Jack Harlow": "Pop Rap",
    "Gil Scott-Heron": "Soul",
    "Bas": "Conscious Hip-hop",
    "James Blake": "Electronic",
    "Bon Iver": "Indie Folk",
    "The Alchemist": "Boom Bap",
    "Ghais Guevara": "Experimental Hip-hop",
    "Snoh Aalegra": "R&B",
    "Young Stoner Life": "Trap",
    "De La Soul": "Alternative Hip-hop",
    "Chairlift": "Indie Pop",
    "Mike": "Boom Bap",
    "Coldplay": "Alternative Rock",
    "Kara Jackson": "Singer-Songwriter",
    "Inhaler": "Indie Rock",
    "A$AP Mob": "Cloud Rap",
    "Jack White": "Alternative Rock",
    "Mustard": "Hip-hop Production",
    "Eartheater": "Experimental Pop",
    "Mavi": "Conscious Hip-hop",
    "Gunna": "Trap",
    "KOTA The Friend": "Conscious Hip-hop",
    "Big Thief": "Indie Rock",
    "Masego": "Alternative R&B",
    "Jay Rock": "Conscious Hip-hop",
    "Miguel": "R&B",
    "Westside Gunn": "Boom Bap",
    "Kevin Abstract": "Alternative Hip-hop",
    "Janelle Monáe": "Soul",
    "Ariana Grande": "Pop",
    "Polo G": "Drill",
    "The Kid LAROI": "Emo Rap",
    "LSD and the Search for God": "Shoegaze",
    "SiR": "R&B",
    "Czarface": "Boom Bap",
    "Armand Hammer": "Experimental Hip-hop",
    "Viktor Vaughn": "Boom Bap",
    "Fred again..": "House",
    "070 Shake": "Alternative R&B",
    "Lil Skies": "Cloud Rap",
    "Sideshow": "Boom Bap",
    "Offset": "Trap",
    "Mereba": "Alternative R&B",
    "Mobb Deep": "Boom Bap",
    "ROSALÍA": "Pop",
    "Isaac Hayes": "Soul",
    "Faye Webster": "Indie Folk",
    "Lil Tjay": "Drill",
    "Standing On The Corner": "Experimental Hip-hop",
    "The Game": "Boom Bap",
    "Migos": "Trap",
    "Alicia Keys": "R&B",
    "The wrldfms Tony Williams": "R&B",
    "THE CARTERS": "Hip-hop",
    "Slum Village": "Boom Bap",
    "King Crimson": "Progressive Rock",
    "Paperboy Fabe": "Electronic",
    "Action Bronson": "Boom Bap",
    "Earl Sweatshirt": "Experimental Hip-hop",
    "Emotional Oranges": "Alternative R&B",
    "Thug Life": "Boom Bap",
    "Benny the Butcher": "Boom Bap",
    "Post Malone": "Pop Rap",
    "Victoria Monét": "R&B",
    "Lost Boyz": "Boom Bap",
    "BLAck pARty": "Alternative R&B",
    "DJ Scheme": "Hip-hop Production",
    "Bee Gees": "Disco",
    "Domo Genesis": "Boom Bap",
    "Summer Walker": "R&B",
    "Quavo": "Trap",
    "Free Nationals": "Soul",
    "Lil Durk": "Drill",
    "Khalid": "R&B",
    "JASIAH": "Trap Metal",
    "Vegyn": "Electronic",
    "Eminem": "Hip-hop",
    "BJ The Chicago Kid": "R&B",
    "Emmavie": "Alternative R&B",
    "Ken Car$on": "Trap",
    "Redveil": "Conscious Hip-hop",
    "Gwen Bunn": "Alternative R&B",
    "Westside Boogie": "Conscious Hip-hop",
    "Doja Cat": "Pop Rap",
    "Elton John": "Pop",
    "Ray Charles": "Soul",
    "dvsn": "Alternative R&B",
    "Jay Wile": "R&B",
    "Wunderhorse": "Alternative Rock",
    "Big Red Machine": "Indie Folk",
    "B. Cool-Aid": "Boom Bap",
    "Baby Rose": "Alternative R&B",
    "Amaarae": "Alternative R&B",
    "EARTHGANG": "Conscious Hip-hop",
    "Aretha Franklin": "Soul",
    "Kehlani": "R&B",
    "River Tiber": "Alternative R&B",
    "Lady Gaga": "Pop",
    "Manchester Orchestra": "Indie Rock",
    "Twista": "Hip-hop",
    "Blu": "Boom Bap",
    "H.E.R.": "R&B",
    "Mark Ronson": "Funk",
    "Her's": "Dream Pop",
    "Julia Holter": "Experimental Pop",
    "UMI": "R&B",
    "Rejjie Snow": "Alternative Hip-hop",
    "Electric Light Orchestra": "Classic Rock",
    "OsamaSon": "Trap",
    "Souls of Mischief": "Boom Bap",
    "Dreamer Isioma": "Alternative R&B",
    "Elujay": "Alternative R&B",
    "Estelle": "R&B",
    "Meek Mill": "Hip-hop",
    "DaBaby": "Trap",
    "Tokyo's Revenge": "Trap",
    "Acopia": "Electronic",
    "Clairo": "Indie Pop",
    "Abra": "Alternative R&B",
    "Gorillaz": "Alternative",
    "Diale": "Hip-hop",
    "jev.": "Hip-hop",
    "A. G. Cook": "Hyperpop",
    "Lil Baby": "Trap",
    "The xx": "Indie Pop",
    "Spillage Village": "Conscious Hip-hop",
    "50 Cent": "Hip-hop",
    "Ghetto Sage": "Hip-hop",
    "Only The Family": "Drill",
    "Lil Wayne": "Hip-hop",
    "black midi": "Math Rock",
    "Neutral Milk Hotel": "Indie Folk",
    "Ty Dolla $ign": "R&B",
    "The Cranberries": "Alternative Rock",
    "The Smashing Pumpkins": "Alternative Rock",
    "Zack Bia": "Hip-hop Production",
    "Black Sheep": "Boom Bap",
    "Rimon": "Alternative R&B",
    "jourden": "Alternative Hip-hop",
    "Boldy James": "Boom Bap",
    "MGMT": "Indie Pop",
    "Led Zeppelin": "Classic Rock",
    "OFWGKTA": "Alternative Hip-hop",
    "Nipsey Hussle": "Conscious Hip-hop",
    "Rod Wave": "Trap",
    "Internet Money": "Hip-hop Production",
    "Larry June": "Boom Bap",
    "Shelly": "Indie Pop",
    "RAE KHALIL": "Alternative Hip-hop",
    "DJ Harrison": "Instrumental Hip-hop",
    "Ice Cube": "G-Funk",
    "Pearl Jam": "Grunge",
    "Yebba": "Soul",
    "Mick Jenkins": "Conscious Hip-hop",
    "Pink Sweat$": "R&B",
    "Kaash Paige": "Alternative R&B",
    "Julia Jacklin": "Singer-Songwriter",
    "AZ": "Boom Bap",
    "Slick Rick": "Boom Bap",
    "Varnish La Piscine": "Hip-hop",
    "Talking Heads": "New Wave",
    "Arctic Monkeys": "Indie Rock",
    "Nitty Scott, MC": "Hip-hop",
    "Lizzy McAlpine": "Indie Pop",
    "M.I.A.": "Alternative Hip-hop",
    "Death Grips": "Experimental Hip-hop",
    "Toro y Moi": "Indie Electronic",
    "YNW Melly": "Emo Rap",
    "Deafheaven": "Black Metal",
    "Eric B. & Rakim": "Boom Bap",
    "Labi Siffre": "Soul",
    "Xiu Xiu": "Experimental",
    "Da Brat": "Hip-hop",
    "Calvin Harris": "Electronic",
    "¥$": "Hip-hop",
    "Laufey": "Jazz Pop",
    "Backxwash": "Horrorcore",
    "Whirr": "Shoegaze",
    "Alison's Halo": "Shoegaze",
    "Gang Starr": "Boom Bap",
    "Kate Bollinger": "Indie Pop",
    "Adrianne Lenker": "Singer-Songwriter",
    "ssgkobe": "Hip-hop",
    "GZA": "Old School Hip-hop",
    "RZA": "Old School Hip-hop",
    "DMX": "Old School Hip-hop",
    "Bone Thugs-N-Harmony": "Old School Hip-hop",
    "Salt-N-Pepa": "Old School Hip-hop",
    "Run-D.M.C.": "Old School Hip-hop",
    "Eazy-E": "Old School Hip-hop",
    "Smif-N-Wessun": "Old School Hip-hop",
    "Ol' Dirty Bastard": "Old School Hip-hop",
    "Ghostface Killah": "Old School Hip-hop"
}"""
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
  "XXXTENTACION": "Emo rap",
  "Juice WRLD": "Emo rap",
  "Terrace Martin": "Jazz",
  "Nujabes": "Jazz",
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
    if scrobble["date"] < start_date or scrobble["date"] > end_date :
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

  sorted_artists = sorted(
     filtered_artist_info.items(), 
     key=lambda item: item[1]["scrobbles"], 
     reverse=True
  )

  # Convert to the required format with correct ranking
  ranked_artists = {
    key: {
      "tag_name": value["tag_name"], 
      "scrobbles": value["scrobbles"], 
      "rank": rank + 1, 
    } for rank, (key, value) in enumerate(sorted_artists) 
  }
  
  st.session_state.artists_genre = ranked_artists
  return ranked_artists
  

