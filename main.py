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

''' SP_CLIENT: Spotify API client with scopes SP_SCOPE'''
SP_SCOPE = "playlist-read-private playlist-modify-private user-library-read user-library-modify"
SP_CLIENT = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SP_SCOPE))

# TODO:
# 1. (?) Add Spotify liked songs to YouTube Music liked songs instead of separate playlist
# 2. create GUI for easier user input handling
# 3. [MOSTLY DONE] improve find_best_match() algorithm for matching search results with query:
#    - Note: Sometimes, we choose incorrect YouTube song results over the correct music video 
#            result if the music video duration is very different from the song audio duration 
#            (as seen on Spotify). In these cases, how do we choose the long music video result 
#            over the incorrect results?
#    - Solution: add all results with major > some threshold to a list and discard the rest, then
#                exponentially punish differences in song duration among these, rather then 
#                exponentially punish differences in song duration on all results (this should 
#                favor long music videos over results with similar duration but are completely incorrect)
#    - Solution: for video results, search only the video title
# 4. [DONE] if YouTube query cannot be found on Spotify, offer to download YouTube video instead

def main():
    job = input(colored("\nHello! Welcome to the Spotify-Youtube playlist coverter.\n" 
            + "Type 'L' to convert a library, or type 'P' to convert a playlist.\n", "green"))
    while job.upper() != "L" and job.upper() != "P":
        job = input(colored("\nMake sure you're entering either 'L' or 'P'.\n", "green"))

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
                sp_converter = SpotifyConverter(YTM_CLIENT, SP_CLIENT, keep_dupes)
                if path[:10] == "/playlist/":
                    sp_playlist_ID = path[10:]
                    sp_converter.convert_SP_to_YT_playlist(sp_playlist_ID)
                    sp_converter.print_not_added_songs()
                    return get_run_time()
                else:
                    print(colored(f"\nERROR: Make sure the URL directs to a Spotify playlist.\n", "green"))
            elif netloc == "music.youtube.com":
                if path == "/playlist":
                    download = input(colored(f"\nShould we download the mp3 for YouTube Music videos and songs " 
                            + "that we can't find on Spotify? Type 'Y' for yes, or 'N' for no.\n", "green"))
                    while download.upper() != 'Y' and download.upper() != 'N':
                        download = input(colored("\nMake sure you're entering either 'Y' or 'N'.\n", "green"))
                    download = True if download.upper() == 'Y' else False
                    yt_converter = YouTubeMusicConverter(YTM_CLIENT, SP_CLIENT, keep_dupes, download)
                    yt_playlist_ID = query[5:]
                    yt_converter.convert_YT_to_SP_playlist(yt_playlist_ID)
                    yt_converter.download_YT_videos()
                    yt_converter.print_not_added_songs()
                    return get_run_time()
                else:
                    print(colored(f"\nERROR: Make sure the URL directs to a YouTube Music playlist.\n", "green"))
            else:
                print(colored(f"\nERROR: Make sure the URL directs to either a Spotify or YouTube Music playlist.\n", "green"))
        elif job == "Library":
            source = input(colored(f"\nType 'S' if the original library is in Spotify or " 
                                    + "type 'Y' if the original library is in YouTube Music.\n", 
                                    "green"))
            if source.upper() == "S":
                sp_converter = SpotifyConverter(YTM_CLIENT, SP_CLIENT, keep_dupes)
                sp_converter.convert_SP_to_YT_library()
                return get_run_time()
            elif source.upper() == "Y":
                download = input(colored(f"\nShould we download the mp3 for YouTube Music videos and songs " 
                        + "that we can't find on Spotify? Type 'Y' for yes, or 'N' for no.\n", "green"))
                while download.upper() != 'Y' and download.upper() != 'N':
                    download = input(colored("\nMake sure you're entering either 'Y' or 'N'.\n", "green"))
                download = True if download.upper() == 'Y' else False
                yt_converter = YouTubeMusicConverter(YTM_CLIENT, SP_CLIENT, keep_dupes, download)
                yt_converter.convert_YT_to_SP_library()
                return get_run_time()
            else:
                print(colored("\nMake sure you're entering either 'S' or 'Y'.\n", "green"))

def get_run_time() -> None:
    minutes = int((time.time()-start_time)//60)
    seconds = int((time.time()-start_time)%60)
    print(f"\nProgram run time: {minutes} minutes and {seconds} seconds")
    return

if __name__ == '__main__':
    main()
    