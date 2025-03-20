import os
import json
import requests
import logging
from configparser import ConfigParser

def lambda_handler(event, context):
    try:
        print("**STARTING**")
        print("**lambda: proj04_auth**")

        # Define the config file location
        config_file = 'spotify-config-lambda.ini'
        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file  # Set AWS credentials file

        # Load the configuration
        configur = ConfigParser()
        configur.read(config_file)

        # Retrieve Spotify credentials
        spotify_client_id = configur.get('spotify', 'client_id')
        spotify_client_secret = configur.get('spotify', 'client_secret')

        SPOTIFY_API_URL = configur.get('spotify', 'SPOTIFY_API_URL')   
        
          # Get access token from the event
        access_token = event.get('access_token')
        playlist_name = event.get('name') 
        playlist_description = event.get('description') 
        playlist_public = event.get('public')  
        artist_name = event.get('artist_name')
        n_songs = event.get('n_songs')

    
        if not access_token:
            return {
                'statusCode': 400,
                'body': json.dumps('Access token is missing')
            }

       

        # Spotify API endpoint to create a playlist
        spotify_api_url = f'{SPOTIFY_API_URL}/users/{{user_id}}/playlists' 
        print(spotify_api_url)       
        # Get user profile to retrieve user_id
        user_profile_url = f'{SPOTIFY_API_URL}/me'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # Get user details
        user_profile_response = requests.get(user_profile_url, headers=headers)

        if user_profile_response.status_code != 200:
            return {
                'statusCode': 400,
                'body': json.dumps('Failed to get user profile')
            }

        user_data = user_profile_response.json()
        user_id = user_data['id']
        
        # Create a new playlist
        playlist_data = {
            'name': playlist_name,
            'description': playlist_description,
            'public': playlist_public
        }

        # Create playlist for the user
        create_playlist_url = spotify_api_url.format(user_id=user_id)
        create_playlist_response = requests.post(create_playlist_url, headers=headers, json=playlist_data)
        
        if create_playlist_response.status_code != 201:
            return {
                'statusCode': 400,
                'body': json.dumps(f'Failed to create playlist: {create_playlist_response.json()}')
            }

        playlist_info = create_playlist_response.json()
        playlist_id = playlist_info['id']  

        artist_id = search_artist(access_token, artist_name, SPOTIFY_API_URL)
        if artist_id:
            track_uris = get_artist_top_tracks(access_token, artist_id, SPOTIFY_API_URL,  n_songs)
            if track_uris:
                add_tracks_to_playlist(access_token, playlist_id, track_uris, SPOTIFY_API_URL)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Playlist created successfully!',
                'playlist': playlist_info
            })
        }

        # Debugging info, will not be reached because of the return above
        print(f"Spotify Client ID: {spotify_client_id[:4]}... (hidden)")

    except Exception as err:
        print("**ERROR**")
        print(str(err))

        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(err)}")
        }

def search_artist(access_token, artist_name, SPOTIFY_API_URL):
    """
    Searches for an artist by name and returns the artist's ID.
    """
    url = f'{SPOTIFY_API_URL}/search?q={artist_name}&type=artist&limit=1'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        artists = response.json()['artists']['items']
        if artists:
            return artists[0]['id']
        else:
            logging.error(f"Artist '{artist_name}' not found.")
            return None
    else:
        logging.error(f"Error searching for artist: {response.status_code} - {response.text}")
        return None
def get_artist_top_tracks(access_token, artist_id, SPOTIFY_API_URL, limit=10):
    """
    Fetches the top tracks of an artist from Spotify.
    """
    url = f'{SPOTIFY_API_URL}/artists/{artist_id}/top-tracks?market=US'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        top_tracks = response.json()['tracks']
        track_uris = [track['uri'] for track in top_tracks[:limit]]
        return track_uris
    else:
        logging.error(f"Failed to fetch top tracks: {response.status_code} {response.text}")
        return None
def add_tracks_to_playlist(access_token, playlist_id, track_uris, SPOTIFY_API_URL ):
    """
    Adds tracks to an existing playlist.
    """
    url = f'{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    data = {
        'uris': track_uris
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        print("Tracks added to the playlist successfully!")
    else:
        logging.error(f"Failed to add tracks to playlist: {response.status_code} {response.text}")
