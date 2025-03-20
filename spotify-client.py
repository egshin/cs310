import requests
import logging
import sys
import base64
import webbrowser
from urllib.parse import urlencode
import configparser
from flask import Flask, request
import os
import boto3
import json

lambda_client = boto3.client('lambda')

# Load the Spotify credentials from config.ini
configur = configparser.ConfigParser()
configur.read('spotify-config.ini')

# Spotify API credentials from config.ini
SPOTIFY_CLIENT_ID = configur.get('spotify', 'SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = configur.get('spotify', 'SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = configur.get('spotify', 'SPOTIFY_REDIRECT_URI')

# Spotify OAuth URLs
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
MODIFY_PLAYLIST_URL = configur.get('api_gateway', 'lambda_api_url')

#permissions for what we can do to an app on our account
SPOTIFY_SCOPE = 'user-library-read user-read-private playlist-read-private playlist-modify-public playlist-modify-private'

# Flask app to handle the redirect
app = Flask(__name__)

auth_code = None
token = None
state = os.urandom(32).hex() ## generate a random number

def prompt():
  """
  Prompts the user and returns the command number
  
  Parameters
  ----------
  None
  
  Returns
  -------
  Command number entered by user (0, 1, 2, ...)
  """

  try:
    print()
    print(">> Enter a command:")
    print("   0 => end")
    print("   1 => login")
    print("   2 => create a playlist")
    print("   3 => modify a playlist")

   

    cmd = int(input())
    return cmd

  except Exception as e:
    print("ERROR")
    print("ERROR: invalid input")
    print("ERROR")
    return -1


def get_spotify_auth_url():
    """
    This function generates the Spotify authorization URL to which the user should be redirected.
    The user needs to login and authorize the app to access their data.
    """
    auth_params = {
        'response_type': 'code',
        'client_id': SPOTIFY_CLIENT_ID,
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'scope': SPOTIFY_SCOPE,
        'state': state ## this is used to ensure that authorization is not forged and corresponds to original request sent
    }
    
    auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(auth_params)}"
    return auth_url

# Step 2: Start Flask app to listen for the Spotify redirect
@app.route('/callback')
def callback():
    global auth_code
    auth_code = request.args.get('code')
    state = request.args.get('state')
    if auth_code:
        return f"Authorization successful! You can now close this window."
    else:
        return "Error: No authorization code received."

def get_access_token(authorization_code):
    """
    Exchange the authorization code for an access token from Spotify's API.
    """
    headers = {
        'Authorization': 'Basic ' + base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode('utf-8')
    }

    data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'redirect_uri': SPOTIFY_REDIRECT_URI
    }

    response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
    
    if response.status_code == 200:
        # Successful authentication, retrieve token
        token_data = response.json()
        return token_data['access_token'], token_data['refresh_token'], token_data['expires_in']
    else:
        logging.error(f"Failed to get access token: {response.status_code} {response.text}")
        return None, None, None

def login():
    """
    Starts the login process by generating the auth URL, opening it in the browser,
    and then handling the response to get the authorization code.
    """
    auth_url = get_spotify_auth_url()
    print("Please login to Spotify and authorize access.")
    print(f"Open this URL in your browser: {auth_url}")
    webbrowser.open(auth_url)

   #wait for Flask to receive the authorization code
    print("Waiting for Spotify to redirect...")
    while auth_code is None:
        pass  # wait

    #exchange the authorization code for an access token
    access_token, refresh_token, expires_in = get_access_token(auth_code)

    if access_token:
        print("Login successful!")
        print(f"Token expires in {expires_in} seconds.")
        return access_token, refresh_token
    else:
        print("Failed to log in to Spotify.")
        return None, None
def create_playlist(access_token):

    playlist_name = input("Enter playlist name: ")
    playlist_description = input("Enter playlist description: ")
    is_public = input("Should the playlist be public? (yes/no): ").strip().lower()
    public = True if is_public == "yes" else False
    favorite_artist = input("Who is your favorite artist? ")
    n_songs = input("How many of their songs do you want in your playlist? ")
    n_songs = int(n_songs)


    payload = {
        "access_token": access_token,
        "name": playlist_name,
        "description": playlist_description,
        "public": public,
        "artist_name": favorite_artist,
        "n_songs": n_songs

    }

    
    api = '/create_playlist'
    url = MODIFY_PLAYLIST_URL + api
    try:
        response = requests.post(url, json=payload)
        response_payload = response.json()
        
        if response.status_code == 200:
            print("Playlist Created Successfully!")
        else:
            print(f"Error: {response_payload}")  
        return response_payload
    except Exception as e:
        logging.error(f"Error calling Lambda: {str(e)}")
        return None
def modify_playlist(access_token):
    playlist_title = input("Enter the playlist title you want to modify: ")
    track_uris_input = input("Enter song(s) (with artists, separated by a dash) that you want to add (comma separated): ")
    
    track_titles = []
    for track in track_uris_input.split(','):
        title_artist = track.strip().split(' - ')  # Assuming the format is "Song Title - Artist"
        if len(title_artist) == 2:
            track_titles.append({
                'title': title_artist[0],
                'artist': title_artist[1]
            })
        else:
            print(f"Invalid track format: {track}. Skipping.")
    
    # Prepare payload to send to API Gateway
    payload = {
        "access_token": access_token,
        "playlist_title": playlist_title,
        "track_titles": track_titles
    }
    print(payload)
    # Make the POST request to API Gateway
    api = '/modify_playlist'
    url = MODIFY_PLAYLIST_URL + api
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        # Parse the response body
        response_data = response.json()
        print(response_data)
        
    else:
        print(f"Error with API call: {response.status_code} {response.text}")


    return None

    

# Main Program Loop
if __name__ == "__main__":
    # Start the Flask app to handle the callback
    import threading
    thread = threading.Thread(target=app.run, kwargs={'host': 'localhost', 'port': 8888})
    thread.start()
    try:
        # Start the Flask app to handle the callback
        print("** Welcome to Spotify Authentication App **")
        

        cmd = prompt()
        while cmd != 0:
            if cmd == 1:
            # Login process
                token, refresh_token = login()
                if token:
                    print("Access Token acquired! You can now make API requests to Spotify.")       
                else:
                    print("Authentication failed. Exiting program.")
                    sys.exit(0)
            elif cmd == 2:
                if token:
                    create_playlist(token)  
                else:
                    print("Please log in first to create a playlist.")
            elif cmd == 3:
                if token:
                    modify_playlist(token)  
                else:
                    print("Please log in first to create a playlist.")

            else:
                    print("Invalid option, please try again.")
            cmd = prompt()
    except Exception as e:
        logging.error("**ERROR: An error occurred:")
        logging.error(e)
        sys.exit(0)
