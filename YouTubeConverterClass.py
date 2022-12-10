import math
import spotipy

from termcolor import colored
from spotipy.oauth2 import SpotifyOAuth

class YouTubeMusicConverter():
    ''' SCORE_COEFFICIENT: constant by which we linearly increment scores when scoring YT search results '''
    SCORE_COEFFICIENT = 100

    ''' EXP_COEFFICIENT: constant by which we exponentially punish differences in song duration when 
    scoring YT search results (eg. score -= e^(EXP_COEFFICIENT*(abs(DIFFERENCE_IN_SONG_DURATION))))
    '''
    EXP_COEFFICIENT = 0.5

    ''' NOT_ADDED: dict where (str) keys = playlist names -> (dict) values = {"unfound":[str], "dupes":[str]}
    - NOT_ADDED -> {str:{"unfounded":[str], "dupes":[str]})}
        - "unfound" -> (list) list of song YT queries that were not added because they could not be found
        - "dupes" -> (list) list of song YT queries that were not added because they were duplicates
    '''
    NOT_ADDED = {}

    def __init__(self, YTM_CLIENT) -> None:
        self.ytm_client = YTM_CLIENT
        pass

    def convert_YT_to_SP_playlist(self, sp_client: spotipy.client, yt_playlist_ID: str, keep_dupes: bool) -> str:
        '''
        Converts YouTube Music playlist with given playlist ID to Spotify playlist.

        Parameters:
        - (spotipy.client) sp_client: Spotify API client
        - (bool) keep_dupes: add duplicates to new playlist? True : False

        Return:
        - (str) playlist ID for newly created Spotify playlist
        '''
        if yt_playlist_ID == "LIKED_SONGS":
            yt_playlist_name = "Liked Songs"
        else:
            yt_playlist_name = self.ytm_client.get_playlist(yt_playlist_ID)["title"]
        print(colored(f"\nYouTube Music playlist detected: '{yt_playlist_name}'", "green"))
        yt_playlist = self.ytm_client.get_playlist(yt_playlist_ID, limit=None)
        yt_tracks = yt_playlist["tracks"]
        sp_playlist = {}
        count = 1
        print(colored("Copying contents into Youtube playlist...", "green"))
        for yt_song in yt_tracks:
            try:
                song_info = self.get_YT_song_info(yt_song)
                sp_query = f"{song_info['name']} {song_info['artist']}"
                sp_search_res = sp_client.search(sp_query, type="track", limit=50)["tracks"]["items"]
                best_match_ID = self.find_best_match(sp_search_res, song_info)
                try:
                    if best_match_ID not in sp_playlist:
                        sp_playlist[best_match_ID] = 1
                    else:
                        sp_playlist[best_match_ID] += 1
                    print(colored(f"Copying song {count}/{len(yt_tracks)}", "green"))
                except:
                    if yt_playlist_name not in self.NOT_ADDED:
                        self.NOT_ADDED[yt_playlist_name] = {"unfound":[], "dupes":[]}
                    self.NOT_ADDED[yt_playlist_name]["unfound"].append(sp_query)
                    print(f"ERROR: '{sp_query}' not found.")
            except:
                print(f"ERROR: Song #{count} in Spotify playlist '{yt_playlist_name}' could not be found " 
                    + f"(It was {type(yt_song)} type. Not a song dict).")
            count += 1
        user_ID = sp_client.me()["id"]
        sp_playlist_ID = sp_client.user_playlist_create(
                        user=user_ID, 
                        name=f"{yt_playlist_name} (copied from YouTube Music)",
                        public=False,
                        collaborative=False,
                        description="Includes duplicates" if keep_dupes else "Does not include duplicates")["id"]
        sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, list(sp_playlist.keys()))

        print(colored("Finishing up...", "green"))
        # dupes = []
        # for video_ID in yt_playlist:
        #     count = yt_playlist[video_ID]["count"]
        #     if count > 1:
        #         for _ in range(count-1):
        #             dupes.append(video_ID)
        #             if not keep_dupes:
        #                 self.NOT_ADDED[yt_playlist_name]["dupes"].append(sp_playlist[video_ID]['sp_query'])
        # if keep_dupes and dupes:
        #     self.ytm_client.add_playlist_items(playlistId=yt_playlist_ID, 
        #     videoIds=dupes, duplicates=True)
        print(colored("Finished! Youtube Music playlist has been created.\n" 
                    + "Check your YouTube Music library to find it.", "green"))
        return sp_playlist_ID

    def find_best_match(self, sp_search_res: list, song_info: dict):
        '''
        Given a list of Spotify search results and a target song to match, holistically score each 
        search result and then return the result with the highest score (ie. the best match).

        Parameters:
        - (list) sp_search_res: list of Spotify search results
        - (dict) song_info: dictionary with song name, artist, album and duration

        Return
        - (str) video ID of search result with best holistic score (ie. best match to the song in song_info)
        '''
        found = {}
        while sp_search_res:
            res = sp_search_res.pop(0)
            found[res["id"]] = 0
            res_title = res["name"].lower()
            res_artist = res["artists"][0]["name"].lower()
            res_album = res["album"]["name"].lower()
            res_duration = res["duration_ms"]/1000
            # Prefer results with the exact same name as Spotify song title
            if song_info["name"] == res_title and song_info["artist"] == res_artist:
                found[res["id"]] += float('inf')
                break
            # Prefer results from the same album as on Spotify
            if res_album and res_album == song_info["album"]:
                found[res["id"]] += self.SCORE_COEFFICIENT
            # Exponentially punish differences in song duration
            try:
                found[res["id"]] -= math.exp(self.EXP_COEFFICIENT*abs(song_info["duration_seconds"]-res_duration))
            except OverflowError:
                found[res["id"]] = float("-inf")
        best_match_ID = max(found, key = found.get)
        return best_match_ID

    def get_YT_song_info(self, song: dict) -> dict:
        '''
        Given a YouTube Music song, summarize important song information into a dictionary

        Parameters:
        - (dict) song: YouTube Music song dictionary

        Return:
        - (dict) dictionary with song name, artist, album, and duration
        '''
        song_info = {}
        song_info["name"] = song["title"].lower()
        song_info["artist"] = song["artists"][0]["name"].lower()
        if song["album"] != None:
            song_info["album"] = song["album"]["name"]
        else:
            song_info["album"] = None
        song_duration_raw = song["duration"]
        song_info["duration_seconds"] = self.get_sec_from_raw_duration(song_duration_raw)
        return song_info

    def get_sec_from_raw_duration(self, song_duration_raw: str) -> int:
        '''
        Converts a time string in "hour:minute:second" format to total seconds.

        Parameters:
        - (str) song_duration_raw: a string representing a time duration in "hour:minute:second" format

        Return:
        - (int) song_duration_raw in seconds
        '''
        tokens = song_duration_raw.split(":")
        tokens = [int(i) for i in tokens]
        song_duration_sec = sum([i*(60**(len(tokens)-tokens.index(i)-1)) for i in tokens])
        return song_duration_sec

    def print_not_added(self, keep_dupes: bool) -> None:
        '''
        Prints all songs queries that were not added, either because they could not 
        be found or because they are duplicates, using global variable NOT_ADDED.

        Parameters:
        - (bool) keep_dupes: add duplicates to new playlist? True : False
        Return:
        - None
        '''
        if self.NOT_ADDED:
            print(colored("\nThe following songs could not be found and were not added:\n", "green"))
            index = 1
            for playlist in self.NOT_ADDED:
                print(f"-----PLAYLIST: {playlist}-----")
                for song_query in self.NOT_ADDED[playlist]["unfound"]:
                    print(f"{index}. {song_query}")
                    index += 1
            if index == 1:
                print("None. All songs were fuound.")
            if not keep_dupes:
                print(colored("\nThe following songs were duplicates and were not added:\n", "green"))
                index = 1
                for playlist in self.NOT_ADDED:
                    print(f"-----PLAYLIST: {playlist}-----")
                    for song_query in self.NOT_ADDED[playlist]["dupes"]:
                        print(f"{index}. {song_query}")
                        index += 1
                if index == 1:
                    print("None. Source playlist had no duplicates.")
        return