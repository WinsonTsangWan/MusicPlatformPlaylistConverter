import time
start_time = time.time()
import spotipy
import urllib
import tkinter as tk
import SpotifyConverterClass
import YouTubeConverterClass

from termcolor import colored
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
# YTMusic.setup(filepath="headers_auth.json")

load_dotenv()

''' YTM_CLIENT: unofficial YouTube Music API (ytmusicapi library) client '''
YTM_CLIENT = YTMusic('headers_auth.json')

# TODO:
# 1. [DONE] convert Spotify playlist to Youtube playlist
# 2. [DONE] convert Spotify library (liked songs, all playlists, liked albums) to Youtube
# 3. (?) Add Spotify liked songs to YouTube Music liked songs instead of separate playlist
# 4. create GUI for easier input handling 
# 5. convert Youtube playlist to Spotify playlist
# 6. convert Youtube library of playlists to multiple Spotify playlists

def main():
    job = input(colored("\nHello! Welcome to the Spotify-Youtube playlist coverter.\n" 
            + "Type 'L' to convert a library, or type 'P' to convert a playlist.\n", "green"))
    while job.upper() != "L" and job.upper() != "P":
        job = input(colored("\nMake sure you're entering either 'L' or 'P'.", "green"))

    keep_dupes = input(colored("\nShould we keep duplicates? Type 'Y' for yes, or 'N' for no.\n", "green"))
    while keep_dupes.upper() != "Y" and keep_dupes.upper() != "N":
        keep_dupes = input(colored("\nMake sure you're entering either 'Y' or 'N'.\n", "green"))

    job = "Playlist" if job.upper() == "P" else "Library"
    keep_dupes = True if keep_dupes.upper() == "Y" else False
    while True:
        if job == "Playlist":
            input_URL = input(colored(f"\nCopy-and-paste the URL for the Spotify playlist.\n", "green"))
            parsed_URL = urllib.parse.urlparse(input_URL)
            netloc = parsed_URL.netloc
            path = parsed_URL.path
            query = parsed_URL.query
            if netloc == "open.spotify.com":
                sp_converter = SpotifyConverterClass.SpotifyConverter(YTM_CLIENT)
                if path[:10] == "/playlist/":
                    sp_playlist_ID = path[10:]
                    sp_scope = "playlist-read-private"
                    sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
                    sp_converter.convert_SP_to_YT_playlist(YTM_CLIENT, sp_client, sp_playlist_ID, keep_dupes)
                    return get_run_time()
                else:
                    input_URL = input(colored(f"\nMake sure the URL directs to a Spotify playlist.\n", "green"))1
            elif netloc == "music.youtube.com":
                if path == "/playlist":
                    # TODO: Convert single YouTube Music playlist to Spotify playlist
                    pass
                else:
                    input_URL = input(colored(f"\nMake sure the URL directs to a YouTube Music playlist.\n", "green"))
            else:
                input_URL = input(colored(f"\nMake sure the URL directs to either a Spotify or YouTube Music playlist.\n", "green"))
        elif job == "Library":
            source = input(colored(f"\nType 'S' if the original library is in Spotify or type 'Y' if the original library is in YouTube Music.\n", "green"))
            if source.upper() == "S":
                sp_converter = SpotifyConverterClass.SpotifyConverter(YTM_CLIENT)
                sp_converter.convert_SP_to_YT_library(YTM_CLIENT, keep_dupes)
                return get_run_time()
            else:
                # TODO: Convert YouTube Music library (liked songs, liked albums, all playlists) to Spotify library
                pass

def get_run_time():
    minutes = int((time.time()-start_time)//60)
    seconds = int((time.time()-start_time)%60)
    print(f"Program run time: {minutes} minutes and {seconds} seconds")

if __name__ == '__main__':
    main()
    