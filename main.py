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

''' SCORE_COEFFICIENT: constant by which we linearly increment scores when scoring YT search results '''
SCORE_COEFFICIENT = 100

'''
EXP_COEFFICIENT: constant by which we exponentially punish differences in song duration when 
scoring YT search results (eg. score -= e^(EXP_COEFFICIENT*(abs(DIFFERENCE_IN_SONG_DURATION))))
'''
EXP_COEFFICIENT = 0.5

'''
NOT_ADDED: dict where (str) keys = playlist names -> (dict) values = {"unfound":[str], "dupes":[str]}
NOT_ADDED -> {str:{"unfounded":[str], "dupes":[str]})}
"unfound" -> (list) list of song YT queries that were not added because they could not be found
"dupes" -> (list) list of song YT queries that were not added because they were duplicates
'''
NOT_ADDED = {}

''' YTM_CLIENT: unofficial YouTube Music API (ytmusicapi library) client '''
YTM_CLIENT = YTMusic('headers_auth.json')

# TO_DO:
# 1. [DONE] (job = P) convert Spotify playlist to Youtube playlist
# 2. [DONE] (job = L) convert Spotify library (liked songs, all playlists, liked albums) to Youtube
# 3. (?) Add Spotify liked songs to YouTube Music liked songs instead of separate playlist
# 3. convert Youtube playlist to Spotify playlist
# 4. convert Youtube library of playlists to multiple Spotify playlists

def main():
    job = input(colored("\nHello! Welcome to the Spotify-Youtube playlist coverter.\n" 
            + "Type 'L' to convert a library, or type 'P' to convert a playlist.\n", "green"))
    while job.upper() != "L" and job.upper() != "P":
        job = input(colored("Make sure you're entering either 'L' or 'P'.", "green"))

    keep_dupes = input(colored("\nShould we keep duplicates? Type 'Y' for yes, or 'N' for no.\n", "green"))
    while keep_dupes.upper() != "Y" and keep_dupes.upper() != "N":
        keep_dupes = input(colored("Make sure you're entering either 'Y' or 'N'.\n", "green"))

    job = "Playlist" if job.upper() == "P" else "Library"
    keep_dupes = True if keep_dupes.upper() == "Y" else False
    while True:
        if job == "Playlist":
            input_URL = input(colored(f"\nCopy-and-paste the URL for the Spotify playlist.\n", "green"))
            parsed_URL = urllib.parse.urlparse(input_URL)
            if (parsed_URL.netloc == "open.spotify.com"):
                if (parsed_URL.path[:10] == "/playlist/"):
                    sp_playlist_ID = parsed_URL.path[10:]
                    sp_scope = "playlist-read-private"
                    sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
                    convert_SP_to_YT_playlist(YTM_CLIENT, sp_client, sp_playlist_ID, keep_dupes)
                    return get_run_time()
                else:
                    input_URL = input(colored(f"\nMake sure the URL directs to a Spotify playlist.\n", "green"))
            else:
                input_URL = input(colored(f"\nMake sure the URL directs to Spotify.\n", "green"))
        elif job == "Library":
            convert_SP_to_YT_library(YTM_CLIENT, keep_dupes)
            return get_run_time()
    return

def convert_SP_to_YT_library(YTM_CLIENT, keep_dupes: bool) -> None:
    '''
    Converts current user's library (liked songs and all playlists) to YouTube Music playlists.
    In order: Liked songs -> Playlists -> Albums

    :param --- (bool) KEEP_DUPES: add duplicates to new playlist? True : False
    :return: None
    '''
    # Convert Spotify Liked Songs to YouTube Music playlist (and add Liked Albums to a list, to use later)
    sp_scope = "user-library-read"
    sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
    sp_playlist_ID = "LIKED_SONGS"
    liked_albums = get_all_SP_tracks(sp_client, "LIKED_ALBUMS")
    # convert_SP_to_YT_playlist(YTM_CLIENT, sp_client, sp_playlist_ID, keep_dupes)

    # # Convert all Spotify playlists to YouTube Music playlists
    # sp_scope = "playlist-read-private"
    # sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
    # for sp_playlist in sp_client.current_user_playlists()["items"]:
    #     sp_playlist_ID = sp_playlist["id"]
    #     convert_SP_to_YT_playlist(YTM_CLIENT, sp_client, sp_playlist_ID, keep_dupes)
    
    # # Add all Spotify Liked Albums to YouTube Music Liked Albums
    # not_added_albums = add_SP_liked_albums(liked_albums)

    # Print unadded songs from each playlist
    print_not_added(keep_dupes)

    # # Print unadded Spotify albums
    # if not_added_albums:
    #     print("\nThe following albums could not be found and were not added:")
    #     for index, album in enumerate(not_added_albums):
    #         print(f"{index + 1}. {album}")
    return 

def convert_SP_to_YT_playlist(YTM_CLIENT, sp_client: spotipy.client, sp_playlist_ID: str, keep_dupes: bool) -> str:
    '''
    Given a Spotify playlist ID, create a YouTube Music playlist with the same songs
    
    :param --- (YTM_CLIENT) YTM_CLIENT: youtubemusicapi API client
    :param --- (spotipy.client) SP_CLIENT: Spotify API client
    :param --- (str) SP_PLAYLIST_ID: playlist ID of source Spotify playlist
    :param --- (bool) KEEP_DUPES: add duplicate song to new playlist? True : False
    :return: (str) playlist ID for newly created YouTube Music playlist
    '''
    if sp_playlist_ID == "LIKED_SONGS":
        sp_playlist_name = "Liked Songs"
    else:
        sp_playlist_name = sp_client.playlist(playlist_id=sp_playlist_ID)["name"]
    print(colored(f"\nSpotify playlist detected: '{sp_playlist_name}'", "green"))
    sp_tracks = get_all_SP_tracks(sp_client, sp_playlist_ID)
    yt_playlist = {}
    count = 0
    print(colored("Copying contents into Youtube playlist...", "green"))
    for sp_track in sp_tracks:
        song = sp_track["track"]
        try:
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
                if sp_playlist_name not in NOT_ADDED:
                    NOT_ADDED[sp_playlist_name] = {"unfound":[], "dupes":[]}
                NOT_ADDED[sp_playlist_name]["unfound"].append(yt_query)
                print(f"ERROR: '{yt_query}' not found.")
        except:
            print(f"ERROR: Song was {type(song)} type. Not a song object.")
    yt_playlist_ID = create_YT_playlist(yt_playlist, sp_playlist_name, keep_dupes)
    return yt_playlist_ID

def get_all_SP_tracks(sp_client: spotipy.client, sp_playlist_ID: str) -> list[dict]:
    '''
    Given a Spotify API client and playlist ID, return a list of all songs in the playlist.
    Note:
        Spotify playlists are paginated, meaning sp_playlist["items"] only retrieves the
        first 100 items. If there are more than 100 items on the playlist, then we must 
        request the next page using sp_client.next(sp_playlist). Here, we simply do that
        for every page, add all items from each page to a list, and return that list.

    :param --- (spotipy.client) SP_CLIENT: Spotify API client
    :param --- (str) SP_PLAYLIST_ID: playlist ID for a Spotify playlist
                                    "LIKED_SONGS" for liked songs
                                    "LIKED_ALBUMS" for liked albums
    :return: (list[dict]) list of all songs (dicts) on a Spotify playlist
    '''
    if sp_playlist_ID == "LIKED_SONGS":
        sp_playlist = sp_client.current_user_saved_tracks(limit=50)
    elif sp_playlist_ID == "LIKED_ALBUMS":
        sp_playlist = sp_client.current_user_saved_albums(limit=50)
    else:
        sp_playlist = sp_client.playlist_tracks(sp_playlist_ID)
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
    song_info = {}
    song_info["name"] = song["name"].lower()
    song_info["artist"] = song["artists"][0]["name"].lower()
    song_info["album"] = song["album"]["name"].lower()
    song_info["duration_seconds"] = song["duration_ms"]/1000
    return song_info

def find_best_match(yt_search_res: list, song_info: dict) -> str:
    '''
    Given a list of search results and a target song to match, holistically score each 
    search result and then return the result with the highest score (ie. the best match).
    Note:
        We use two lists per yt_search_res (found_matches and found_scores) because each
        res is a dict, which is unhashable (and thus cannot be used as keys in another dict)

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
            if "album" in res and res["album"] != None:
                res_album = res["album"]["name"].lower()
            else:
                res_album = None
            res_duration = res["duration_seconds"]
            # Prefer Top result over other results
            if res["category"] == "Top result":
                found_scores[-1] += SCORE_COEFFICIENT
            # Prefer songs over video results
            if res["resultType"] == "song":
                found_scores[-1] += SCORE_COEFFICIENT
            # Prefer results with the exact same name as Spotify song title
            if song_info["name"] == res_title:
                found_scores[-1] += SCORE_COEFFICIENT
            # Slightly prefer results that closely resemble the Spotify song title
            if song_info["name"] in res_title or res_title in song_info["name"]:
                found_scores[-1] += SCORE_COEFFICIENT/2
            # Prefer results from the same artist as on Spotify
            if song_info["artist"] == res_artist:
                found_scores[-1] += SCORE_COEFFICIENT
            # Slightly prefer results from artists that closely resemble the Spotify artist
            if song_info["artist"] in res_artist or res_artist in song_info["artist"]:
                found_scores[-1] += SCORE_COEFFICIENT/2
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
    for video_ID in yt_playlist:
        count = yt_playlist[video_ID]["count"]
        if count > 1:
            for _ in range(count-1):
                dupes.append(video_ID)
                if not keep_dupes:
                    NOT_ADDED[sp_playlist_name]["dupes"].append(yt_playlist[video_ID]['yt_query'])
    if keep_dupes and dupes:
        YTM_CLIENT.add_playlist_items(playlistId=yt_playlist_ID, 
        videoIds=dupes, duplicates=True)
    print(colored("Finished! Youtube Music playlist has been created.\n" 
                + "Check your YouTube Music library to find it.", "green"))
    
    return yt_playlist_ID

def add_SP_liked_albums(liked_albums: list) -> list:
    '''
    Given a list of Spotify Liked Albums, add all albums to YouTube Music Liked Albums.

    :param --- (list) LIKED_ALBUMS: list of Spotify Liked Albums
    :return: (list) list of albums that were not added to YouTube Music Liked Albums
                    because a good match could not be found
    '''
    not_added_albums = []
    for album in liked_albums:
        found = {}
        album_name = album['album']['name']
        album_artist = album['album']['artists'][0]['name']
        album_year = album['album']['release_date'][:3]
        yt_query = f"{album_name} by {album_artist}"
        yt_search_res = YTM_CLIENT.search(query=yt_query, filter="albums")
        for res in yt_search_res:
            print(res, "\n")
            res_ID = res["browseId"]
            found[res_ID] = 0
            if res["artists"][0]["name"] == album_artist:
                found[res_ID] += SCORE_COEFFICIENT
            if res["title"] == album_name:
                found[res_ID] += SCORE_COEFFICIENT
            if res["title"] in album_name or album_name in res["title"]:
                found[res_ID] += SCORE_COEFFICIENT
            if res["year"] == album_year:
                found[res_ID] += SCORE_COEFFICIENT
        if found:
            res_ID = max(found, key=found.get)
            print("RES_ID: ", res_ID)
            res_playlist = YTM_CLIENT.get_playlist(res_ID) 
            YTM_CLIENT.rate_playlist(res_playlist, "LIKE")
            print(f"{yt_query} added to liked albums.")
        else:
            not_added_albums.append(yt_query)
    return not_added_albums

def print_not_added(keep_dupes: bool) -> None:
    '''
    Prints all songs queries that were not added, either because they could not 
    be found or because they are duplicates, using global variable NOT_ADDED.

    :param --- (bool) keep_dupes: add duplicates to new playlist? True : False
    :return: None
    '''
    if NOT_ADDED:
        print("\nThe following songs could not be found and were not added:")
        index = 1
        for playlist in NOT_ADDED:
            print(f"-----PLAYLIST: {playlist}-----")
            for song_query in playlist:
                print(f"{index}. {song_query}")
                index += 1
        if index == 1:
            print("None. All songs were fuound.")
        if not keep_dupes:
            print("\nThe following songs were duplicates and were not added:")
            index = 1
            for playlist in NOT_ADDED:
                print(f"-----PLAYLIST: {playlist}-----")
                for song_query in playlist:
                    print(f"{index}. {song_query}")
                    index += 1
            if index == 1:
                print("None. Source playlist had no duplicates.")
    return

def get_run_time():
    minutes = int((time.time()-start_time)//60)
    seconds = int((time.time()-start_time)%60)
    print(f"Program run time: {minutes} minutes and {seconds} seconds")

if __name__ == '__main__':
    main()
    