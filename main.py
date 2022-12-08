import time
start_time = time.time()
import spotipy
import urllib
import math

from termcolor import colored
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
# YTMusic.setup(filepath="headers_auth.json")

load_dotenv()

SCORE_COEFFICIENT = 100
EXP_COEFFICIENT = 0.5
YTM_CLIENT = YTMusic('headers_auth.json')

# TO_DO:
# 1. convert Spotify playlist to Youtube playlist
# 2. convert Spotify library of playlists to multiple Youtube playlists
# 3. convert Youtube playlist to Spotify playlist
# 4. convert Youtube library of playlists to multiple Spotify playlists

def main():
    job = input(colored("\nHello! Welcome to the Spotify-Youtube playlist coverter.\n" 
            + "Type 'L' to convert a library, or type 'P' to convert a playlist.\n", "green"))
    while job.upper() != "L" and job.upper() != "P":
        job = input(colored("Make sure you're entering either 'L' or 'P'.", "green"))
    job = "Playlist" if job.upper() == 'P' else "Library"

    keep_dupes = input(colored("\nShould we keep duplicates? Type 'Y' for yes, or 'N' for no.\n", "green"))
    while keep_dupes.upper() != "Y" and keep_dupes.upper() != "N":
        keep_dupes = input(colored("Make sure you're entering either 'Y' or 'N'.\n", "green"))
    keep_dupes = True if keep_dupes.upper() == 'Y' else False

    input_URL = input(colored(f"\nCopy-and-paste the URL for the {job}.\n", "green"))
    while True:
        # Source: Spotify -> Destination: Youtube
        parsed_URL = urllib.parse.urlparse(input_URL)
        if (parsed_URL.netloc == "open.spotify.com"):
            sp_scope = "playlist-read-private"
            sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
            if (parsed_URL.path[:10] == "/playlist/") and job == "Playlist":
                sp_playlist_ID = parsed_URL.path[10:]
                convert_SP_to_YT(YTM_CLIENT, sp_client, sp_playlist_ID, keep_dupes)
                get_run_time()
                return
            elif (parsed_URL.path[:12] == "/collection/") and job == "Library":
                if (parsed_URL.path[12:] == "playlists"):
                    for sp_playlist in sp_client.current_user_playlists()["items"]:
                        sp_playlist_ID = sp_playlist["id"]
                        convert_SP_to_YT(YTM_CLIENT, sp_client, sp_playlist_ID, keep_dupes)
                    liked_songs = sp_client.current_user_saved_tracks()
                    
                    get_run_time()
                    return
                else:
                    input_URL = input(colored("Sorry, only library of playlists supported.", "green"))
            else:
                input_URL = input(colored(f"Make sure the Spotify URL directs to Spotify {job}", "green"))
        # Source: Youtube -> Destination: Spotify
        elif (parsed_URL.netloc == "www.youtube.com"):
            if (parsed_URL.path == "/playlist"):
                convert_YT_to_SP(YTM_CLIENT, parsed_URL)
                return
            else:
                input_URL = input(colored("Make sure the Youtube URL directs to Youtube playlist.", "green"))
        else:
            input_URL = input(colored("Make sure the URL is either Spotify or YouTube.", "green"))
    return

def convert_SP_to_YT(YTM_CLIENT, sp_client: spotipy.client, sp_playlist_ID: str, keep_dupes: bool) -> str:
    '''
    Given a Spotify playlist ID, create a YouTube Music playlist with the same songs
    
    :param --- (YTM_CLIENT) YTM_CLIENT: youtubemusicapi API client
    :param --- (spotipy.client) SP_CLIENT: Spotify API client
    :param --- (str) SP_PLAYLIST_ID: playlist ID for source Spotify playlist
    :param --- (bool) KEEP_DUPES: add duplicate song to new playlist? True : False
    :return: (str) playlist ID for newly created YouTube Music playlist
    '''
    sp_playlist_name = sp_client.user_playlist(user=None, playlist_id=sp_playlist_ID)["name"]
    print(colored(f"\nSpotify playlist detected: '{sp_playlist_name}'", "green"))
    sp_playlist = sp_client.playlist_tracks(sp_playlist_ID)
    sp_tracks = get_all_SP_tracks(sp_client, sp_playlist)
    yt_playlist = {}
    count = 0
    not_added = []
    print(colored("Copying contents into Youtube playlist...", "green"))
    for sp_track in sp_tracks:
        try:
            song = sp_track["track"]
            song_info = get_SP_song_info(song)
            yt_query = f"{song['name']} by {song['artists'][0]['name']}"
            yt_search_res = YTM_CLIENT.search(query=yt_query)
            try:
                best_match_ID = find_best_match(yt_search_res, song_info)
                if best_match_ID not in yt_playlist:
                    yt_playlist[best_match_ID] = {"yt_query":yt_query, "count":1}
                else:
                    yt_playlist[best_match_ID]["count"] += 1
                count += 1
                print(colored(f"Copying song {count}/{len(sp_tracks)}", "green"))
            except:
                not_added.append(yt_query)
                print(f"ERROR: '{yt_query}' not found.")
        except:
            print("ERROR: Song was NoneType. I don't know how to solve this.")
    yt_playlist_ID = create_YT_playlist(yt_playlist, sp_playlist_name, keep_dupes)
    if not_added:
        print("The following songs could not be found and were not added:")
        for index, query in enumerate(not_added):
            print(f"{index+1}. {query}")
    return yt_playlist_ID

def get_all_SP_tracks(sp_client: spotipy.client, sp_playlist: dict) -> list:
    '''
    Spotify playlists are paginated, meaning sp_playlist["items"] only retrieves the
    first 100 items. If there are more than 100 items on the playlist, then we must 
    request the next page using sp_client.next(sp_playlist). Here, we simply do that
    for every page, add all items from each page to a list, and return that list.

    :param --- (spotipy.client) SP_CLIENT: Spotify API client
    :param --- (dict) SP_PLAYLIST: Spotify playlist object
    :return: list of all songs on a Spotify playlist
    '''
    sp_tracks = sp_playlist["items"]
    while sp_playlist["next"]:
        sp_playlist = sp_client.next(sp_playlist)
        sp_tracks.extend(sp_playlist["items"])
    return sp_tracks

def get_SP_song_info(song: dict) -> dict:
    '''
    Given a spotify song, summarize important song information into a dictionary

    :param --- (dict) SONG: Spotify song
    :return: (dict) dictionary with song name, artist, album, and duration
    '''
    try:
        song_info = {}
        song_info["name"] = song["name"].lower()
        song_info["artist"] = song["artists"][0]["name"].lower()
        song_info["album"] = song["album"]["name"].lower()
        song_info["duration_seconds"] = song["duration_ms"]/1000
        return song_info
    except:
        print(song)
        print("song == None", song == None)
        return None

def find_best_match(yt_search_res: list, song_info: dict) -> str:
    '''
    Given a list of search results and a target song to match, holistically score each 
    search result and then return the result with the highest score (ie. the best match).

    :param --- (list) YT_SEARCH_RES: list of YouTube Music search results
    :param --- (dict) SONG_INFO: dictionary with song name, artist, album and duration
    :return: (str) video ID of search result with best holistic score
                indicating best match to the song described by song_info
    '''
    found_matches = []
    found_scores = []
    while yt_search_res:
        res = yt_search_res.pop(0)
        if res["resultType"] == "song" or res["resultType"] == "video":
            found_matches.append(res)
            found_scores.append(0)
            res_title = res["title"].lower()
            res_artist = res["artists"][0]["name"].lower()
            res_album = res["album"]["name"].lower() if "album" in res and res["album"] != None else None
            res_duration = res["duration_seconds"]
            # Prefer Top result over other results
            if res["category"] == "Top result":
                found_scores[-1] += SCORE_COEFFICIENT
            # Prefer songs over video results
            if res["resultType"] == "song":
                found_scores[-1] += SCORE_COEFFICIENT
            # Prefer results that closely resemble the Spotify song title
            if song_info["name"] == res_title:
                found_scores[-1] += SCORE_COEFFICIENT
            # Prefer results from the same artist as on Spotify
            if song_info["artist"] in res_artist or res_artist in song_info["artist"]:
                found_scores[-1] += SCORE_COEFFICIENT
            # Prefer results from the same album as on Spotify
            if res_album and res_album == song_info["album"]:
                found_scores[-1] += SCORE_COEFFICIENT
            # Exponentially punish differences in song duration
            try:
                found_scores[-1] -= math.exp(EXP_COEFFICIENT*abs(song_info["duration_seconds"]-res_duration))
            except OverflowError:
                found_scores[-1] = float("-inf")
    best_match = found_matches[found_scores.index(max(found_scores))]
    best_match_ID = best_match["videoId"]
    return best_match_ID

def create_YT_playlist(yt_playlist: dict, sp_playlist_name: str, keep_dupes: bool) -> str:
    '''
    Creates a YouTube playlist and handles duplicates based on KEEP_DUPES.

    :param --- (dict) YT_PLAYLIST: 
        keys: (str) video IDs | values: (dict) {"yt_query":str, "count":int}
            yt_query = query string that lead to the given video ID
            count = number of times the given video ID has been added (eg. duplicate songs)
    :param --- (str) SP_PLAYLIST_NAME: name of Spotify playlist
    :param --- (bool) KEEP_DUPES: add duplicate song to new playlist? True : False
    :return: (str) playlist ID of newly created YouTube Music playlist
    '''
    print(colored("Finishing up...", "green"))
    yt_playlist_ID = YTM_CLIENT.create_playlist(
        title=f"{sp_playlist_name} (copied from Spotify)",
        description="Includes duplicates" if keep_dupes else "Does not include duplicates",
        video_ids=list(yt_playlist.keys()))
    dupes = []
    if not keep_dupes:
        print(colored("The following songs are duplicates and were not added:", "green"))
    for video_ID in yt_playlist:
        count = yt_playlist[video_ID]["count"]
        if count > 1:
            for _ in range(count-1):
                dupes.append(video_ID)
                if not keep_dupes:
                    print(f"{len(dupes)}. {yt_playlist[video_ID]['yt_query']}")
    if keep_dupes and dupes:
        YTM_CLIENT.add_playlist_items(playlistId=yt_playlist_ID, videoIds=dupes, duplicates=True)
    print(colored("Finished! Youtube Music playlist has been created.\n" 
                + "Check your YouTube Music library to find it.", "green"))
    return yt_playlist_ID

def get_run_time():
    minutes = int((time.time()-start_time)//60)
    seconds = int((time.time()-start_time)%60)
    print(f"Program run time: {minutes} minutes and {seconds} seconds")

if __name__ == '__main__':
    main()
    