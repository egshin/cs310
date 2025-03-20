import json
import requests
import logging
from configparser import ConfigParser
import os

SPOTIFY_API_URL = 'https://api.spotify.com/v1' 

def lambda_handler(event, context):
    try:
        print("**STARTING**")
        print("**lambda: modify_playlist **")

        # Define the config file location
        config_file = 'spotify-config-lambda.ini'
        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file  # Set AWS credentials file

        # Load the configuration
        configur = ConfigParser()
        configur.read(config_file)
        print(SPOTIFY_API_URL)
        body = event.get('body')

        # Check if 'body' is a string, and if so, parse it as JSON
        if isinstance(body, str):
            try:
                body = json.loads(body)  # Parse the string into a dictionary
                print(f"Parsed body: {json.dumps(body)}")
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {str(e)}")
                return {
                    'statusCode': 400,
                    'body': json.dumps('Invalid JSON format in the body')
                }
        access_token = body.get('access_token')
        print(access_token)
        playlist_title = body.get('playlist_title')
        print(playlist_title)
        track_titles = body.get('track_titles')
        print(track_titles)

        if not access_token or not playlist_title or not track_titles:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing required fields (access_token, playlist_title, track_titles)')
            }

        playlist_id = search_playlist_by_title(access_token, playlist_title, SPOTIFY_API_URL)
        if not playlist_id:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Playlist with title '{playlist_title}' not found.")
            }
        
        track_uris = []
        for track_title in track_titles:
            track_uri = search_track_by_title(access_token, track_title['title'], track_title['artist'], SPOTIFY_API_URL)
            if track_uri:
                track_uris.append(track_uri)
            else:
                logging.error(f"Track not found: {track_title['title']} by {track_title['artist']}")
        
        success = add_tracks_to_playlist(access_token, playlist_id, track_uris)
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps('Tracks added to playlist successfully!')
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps("Error adding tracks to playlist.")
            }

    except Exception as e:
        logging.error(str(e))
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

def search_track_by_title(access_token, title, artist, SPOTIFY_API_URL):
    search_url = f'{SPOTIFY_API_URL}/search'
    query = f"track:{title} artist:{artist}"  # artist and song title
    params = {
        'q': query,
        'type': 'track',
        'limit': 1  # top result
    }

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(search_url, headers=headers, params=params)

    if response.status_code == 200:
        results = response.json()
        tracks = results['tracks']['items']
        if tracks:
            return tracks[0]['uri']
        else:
            logging.error(f"Track '{title}' by '{artist}' not found.")
            return None
    else:
        # Log the response details for debugging
        logging.error(f"Error searching for track '{title}' by artist '{artist}': {response.status_code} - {response.text}")
        return None

def search_playlist_by_title(access_token, playlist_title, SPOTIFY_API_URL):
    url = f'{SPOTIFY_API_URL}/me/playlists'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        playlists = response.json().get('items', [])
        print(playlists)
        for playlist in playlists:
            # Case-sensitive comparison for playlist titles
            if playlist.get('name', '').lower() == playlist_title.lower():
                return playlist.get('id')
        logging.error(f"Playlist '{playlist_title}' not found.")
        return None
    else:
        logging.error(f"Failed to fetch user playlists: {response.status_code} {response.text}")
        return None

def add_tracks_to_playlist(access_token, playlist_id, track_uris):
    url = f'{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks'
    headers = {'Authorization': f'Bearer {access_token}'}
    data = {'uris': track_uris}
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return True
    else:
        logging.error(f"Failed to add tracks: {response.status_code} {response.text}")
        return False
