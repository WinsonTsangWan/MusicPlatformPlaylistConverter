import time
start_time = time.time()
import spotipy
import urllib

from SpotifyConverterClass import SpotifyConverter
from YouTubeConverterClass import YouTubeMusicConverter

from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
from termcolor import colored
from dotenv import load_dotenv
# YTMusic.setup(filepath="headers_auth.json")

load_dotenv()

''' YTM_CLIENT: unofficial YouTube Music API (ytmusicapi library) client '''
YTM_CLIENT = YTMusic('headers_auth.json')

# TODO:
# 1. (?) Add Spotify liked songs to YouTube Music liked songs instead of separate playlist
# 2. create GUI for easier user input handling
# 3. refactor SpotifyConverterClass and YouTubeConverterClass into subclasses of a parent ConverterClass
# 4. improve find_best_match() function for matching YouTube Music songs with Spotify results

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
            input_URL = input(colored(f"\nCopy-and-paste the URL for the source playlist.\n", "green"))
            parsed_URL = urllib.parse.urlparse(input_URL)
            netloc = parsed_URL.netloc
            path = parsed_URL.path
            query = parsed_URL.query
            if netloc == "open.spotify.com":
                sp_converter = SpotifyConverter(YTM_CLIENT, keep_dupes)
                if path[:10] == "/playlist/":
                    sp_playlist_ID = path[10:]
                    sp_scope = "playlist-read-private"
                    sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
                    sp_converter.convert_SP_to_YT_playlist(sp_client, sp_playlist_ID)
                    sp_converter.print_not_added_songs()
                    return get_run_time()
                else:
                    print(colored(f"\nERROR: Make sure the URL directs to a Spotify playlist.\n", "green"))
            elif netloc == "music.youtube.com":
                yt_converter = YouTubeMusicConverter(YTM_CLIENT, keep_dupes)
                if path == "/playlist":
                    yt_playlist_ID = query[5:]
                    sp_scope = "playlist-modify-private"
                    sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
                    yt_converter.convert_YT_to_SP_playlist(sp_client, yt_playlist_ID)
                    yt_converter.print_not_added_songs()
                    return get_run_time()
                else:
                    print(colored(f"\nERROR: Make sure the URL directs to a YouTube Music playlist.\n", "green"))
            else:
                print(colored(f"\ERROR: Make sure the URL directs to either a Spotify or YouTube Music playlist.\n", "green"))
        elif job == "Library":
            source = input(colored(f"\nType 'S' if the original library is in Spotify or " 
                                    + "type 'Y' if the original library is in YouTube Music.\n", 
                                    "green"))
            if source.upper() == "S":
                sp_converter = SpotifyConverter(YTM_CLIENT, keep_dupes)
                sp_converter.convert_SP_to_YT_library()
                return get_run_time()
            elif source.upper() == "Y":
                yt_converter = YouTubeMusicConverter(YTM_CLIENT, keep_dupes)
                yt_converter.convert_YT_to_SP_library()
                return get_run_time()
            else:
                print(colored("\nMake sure you're entering either 'S' or 'Y'.\n", "green"))

def get_run_time():
    minutes = int((time.time()-start_time)//60)
    seconds = int((time.time()-start_time)%60)
    print(f"\nProgram run time: {minutes} minutes and {seconds} seconds")

if __name__ == '__main__':
    main()
    