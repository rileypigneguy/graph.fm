import requests
import os

api_key = os.environ["LASTFM_API_KEY"]
user = "Beef_Casserole"
method = "user.gettopartists"


x = "https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&api_key=2c223bda2fe846bd5c24f9a5d2da834e&user=Beef_Casserole&format=json&to=Sat%20Feb%2015%202025&from=1738753393&limit=1000&page=2"
params = {
  'limit':2
}


url = f"https://ws.audioscrobbler.com/2.0/?method={method}&api_key={api_key}&user={user}&format=json"

response = requests.get(url,params=params)
data = response.json()
print("attempting!")

for artist in data["artists"]["artist"]:
  print(artist["name"])

