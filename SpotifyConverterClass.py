import math
import spotipy

from termcolor import colored
from spotipy.oauth2 import SpotifyOAuth

class SpotifyConverter():
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

    def __init__(self, YTM_CLIENT, KEEP_DUPES) -> None:
        self.ytm_client = YTM_CLIENT
        self.keep_dupes = KEEP_DUPES
        pass

    def convert_SP_to_YT_library(self) -> None:
        '''
        Converts current user's Spotify library (liked songs, liked albums, all playlists) to 
        YouTube Music playlists. In order: Liked songs -> Playlists -> Albums\n
        Parameters:
        - None
        Return:
        - None
        '''
        # Convert Spotify Liked Songs to YouTube Music playlist (and add Liked Albums to a list, to use later)
        sp_scope = "user-library-read"
        sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
        sp_playlist_ID = "LIKED_SONGS"
        liked_albums = self.get_all_SP_tracks(sp_client, "LIKED_ALBUMS")
        self.convert_SP_to_YT_playlist(sp_client, sp_playlist_ID)

        # Convert all Spotify playlists to YouTube Music playlists
        sp_scope = "playlist-read-private"
        sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
        for sp_playlist in sp_client.current_user_playlists()["items"]:
            sp_playlist_ID = sp_playlist["id"]
            self.convert_SP_to_YT_playlist(sp_client, sp_playlist_ID)
        
        # Add all Spotify Liked Albums to YouTube Music Liked Albums
        not_added_albums = self.add_SP_liked_albums(liked_albums)

        # Print unadded songs from each playlist
        self.print_not_added()

        # Print unadded Spotify albums
        if not_added_albums:
            print("\nThe following albums could not be found and were not added:")
            for index, album in enumerate(not_added_albums):
                print(f"{index + 1}. {album}")
        return 

    def convert_SP_to_YT_playlist(self, sp_client: spotipy.client, sp_playlist_ID: str) -> str:
        '''
        Given a Spotify playlist ID, create a YouTube Music playlist with the same songs\n
        Parameters:
        - (spotipy.client) SP_CLIENT: Spotify API client
        - (str) SP_PLAYLIST_ID: playlist ID of source Spotify playlist\n
        Return:
        - (str) playlist ID for newly created YouTube Music playlist
        '''
        if sp_playlist_ID == "LIKED_SONGS":
            sp_playlist_name = "Liked Songs"
        else:
            sp_playlist_name = sp_client.playlist(playlist_id=sp_playlist_ID)["name"]
        print(colored(f"\nSpotify playlist detected: '{sp_playlist_name}'", "green"))
        sp_tracks = self.get_all_SP_tracks(sp_client, sp_playlist_ID)
        yt_playlist = {}
        count = 1
        print(colored("Copying contents into Youtube playlist...", "green"))
        for sp_track in sp_tracks:
            song = sp_track["track"]
            try:
                song_info = self.get_SP_song_info(song)
                yt_query = f"{song['name']} by {song['artists'][0]['name']}"
                yt_search_res = self.ytm_client.search(query=yt_query)
                try:
                    best_match_ID = self.find_best_match(yt_search_res, song_info)
                    if best_match_ID not in yt_playlist:
                        yt_playlist[best_match_ID] = {"yt_query":yt_query, "count":1}
                    else:
                        yt_playlist[best_match_ID]["count"] += 1
                    print(colored(f"Copying song {count}/{len(sp_tracks)}", "green"))
                except:
                    if sp_playlist_name not in self.NOT_ADDED:
                        self.NOT_ADDED[sp_playlist_name] = {"unfound":[], "dupes":[]}
                    self.NOT_ADDED[sp_playlist_name]["unfound"].append(yt_query)
                    print(f"ERROR: '{yt_query}' not found.")
            except:
                print(f"ERROR: Song #{count} in Spotify playlist '{sp_playlist_name}' could not be found " 
                    + f"(It was {type(song)} type. Not a song dict).")
            count += 1
        yt_playlist_ID = self.create_YT_playlist(yt_playlist, sp_playlist_name)
        return yt_playlist_ID

    def get_all_SP_tracks(self, sp_client: spotipy.client, sp_playlist_ID: str) -> list[dict]:
        '''
        Given a Spotify API client and playlist ID, return a list of all songs in the playlist.

        Parameters:
        - (spotipy.client) SP_CLIENT: Spotify API client
        - (str) SP_PLAYLIST_ID: 
            - playlist ID for a Spotify playlist
            - "LIKED_SONGS" for liked songs
            - "LIKED_ALBUMS" for liked albums
        
        Return:
        - (list[dict]) list of all songs (dicts) on a Spotify playlist
    
        Note: Spotify playlists are paginated, meaning sp_playlist["items"] only retrieves the
        first 100 items. If there are more than 100 items on the playlist, then we must 
        request the next page using sp_client.next(sp_playlist). Here, we simply do that
        for every page, add all items from each page to a list, and return that list.
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

    def get_SP_song_info(self, song: dict) -> dict:
        '''
        Given a Spotify song, summarize important song information into a dictionary

        Parameters:
        - (dict) SONG: Spotify song

        Return:
        - (dict) dictionary with song name, artist, album, and duration
        '''
        song_info = {}
        song_info["name"] = song["name"].lower()
        song_info["artist"] = song["artists"][0]["name"].lower()
        song_info["album"] = song["album"]["name"].lower()
        song_info["duration_seconds"] = song["duration_ms"]/1000
        return song_info

    def find_best_match(self, yt_search_res: list, song_info: dict) -> str:
        '''
        Given a list of YouTube Music search results and a target song to match, holistically score each 
        search result and then return the result with the highest score (ie. the best match).

        Parameters:
        - (list) YT_SEARCH_RES: list of YouTube Music search results
        - (dict) SONG_INFO: dictionary with song name, artist, album and duration

        Return
        - (str) video ID of search result with best holistic score (ie. best match to the song in song_info)
        '''
        found = {}
        while yt_search_res:
            res = yt_search_res.pop(0)
            if res["resultType"] == "song" or res["resultType"] == "video":
                found[res["videoId"]] = 0
                res_title = res["title"].lower()
                res_artist = res["artists"][0]["name"].lower()
                if "album" in res and res["album"] != None:
                    res_album = res["album"]["name"].lower()
                else:
                    res_album = None
                res_duration = res["duration_seconds"]
                # Prefer Top result over other results
                if res["category"] == "Top result":
                    found[res["videoId"]] += self.SCORE_COEFFICIENT
                # Prefer songs over video results
                if res["resultType"] == "song":
                    found[res["videoId"]] += self.SCORE_COEFFICIENT
                # Prefer results with the exact same name as Spotify song title
                if song_info["name"] == res_title:
                    found[res["videoId"]] += self.SCORE_COEFFICIENT
                # Slightly prefer results that closely resemble the Spotify song title
                if song_info["name"] in res_title or res_title in song_info["name"]:
                    found[res["videoId"]] += self.SCORE_COEFFICIENT/2
                # Prefer results from the same artist as on Spotify
                if song_info["artist"] == res_artist:
                    found[res["videoId"]] += self.SCORE_COEFFICIENT
                # Slightly prefer results from artists that closely resemble the Spotify artist
                if song_info["artist"] in res_artist or res_artist in song_info["artist"]:
                    found[res["videoId"]] += self.SCORE_COEFFICIENT/2
                # Prefer results from the same album as on Spotify
                if res_album and res_album == song_info["album"]:
                    found[res["videoId"]] += self.SCORE_COEFFICIENT
                # Exponentially punish differences in song duration
                try:
                    found[res["videoId"]] -= math.exp(self.EXP_COEFFICIENT*abs(song_info["duration_seconds"]-res_duration))
                except OverflowError:
                    found[res["videoId"]] = float("-inf")
        best_match_ID = max(found, key = found.get)
        return best_match_ID

    def create_YT_playlist(self, yt_playlist: dict, sp_playlist_name: str) -> str:
        '''
        Creates a YouTube playlist and handles duplicates based on KEEP_DUPES.

        Parameters:
        - (dict) YT_PLAYLIST: 
            - keys: (str) video IDs | values: (dict) {"yt_query":str, "count":int}
                - yt_query = query string that lead to the given video ID
                - count = number of times the given video ID has been added (eg. duplicate songs)
        - (str) SP_PLAYLIST_NAME: name of Spotify playlist
        - (bool) KEEP_DUPES: add duplicate song to new playlist? True : False

        Return:
        - (str) playlist ID of newly created YouTube Music playlist
        '''
        print(colored("Finishing up...", "green"))
        yt_playlist_ID = self.ytm_client.create_playlist(
            title=f"{sp_playlist_name} (copied from Spotify)",
            description="Includes duplicates" if self.keep_dupes else "Does not include duplicates",
            video_ids=list(yt_playlist.keys()))
        
        dupes = []
        for video_ID in yt_playlist:
            count = yt_playlist[video_ID]["count"]
            if count > 1:
                for _ in range(count-1):
                    dupes.append(video_ID)
                    if not self.keep_dupes:
                        self.NOT_ADDED[sp_playlist_name]["dupes"].append(yt_playlist[video_ID]['yt_query'])
        if self.keep_dupes and dupes:
            self.ytm_client.add_playlist_items(playlistId=yt_playlist_ID, 
            videoIds=dupes, duplicates=True)
        print(colored("Finished! Youtube Music playlist has been created.\n" 
                    + "Check your YouTube Music library to find it.", "green"))
        
        return yt_playlist_ID

    def add_SP_liked_albums(self, liked_albums: list) -> list:
        '''
        Given a list of Spotify Liked Albums, add all albums to YouTube Music Liked Albums, 
        and returns a list of albums that were not added.

        Parameters:
        - (list) LIKED_ALBUMS: list of Spotify Liked Albums

        Return:
        - (list) list of albums that were not added to YouTube Music Liked Albums
                        because a good match could not be found
        '''
        if liked_albums:
            print(colored(f"\nAdding Spotify saved albumds to YouTube Music library...", "green"))
            not_added_albums = []
            for album in liked_albums:
                found = {}
                album_name = album['album']['name']
                album_artist = album['album']['artists'][0]['name']
                album_year = album['album']['release_date'][:3]
                yt_query = f"{album_name} by {album_artist}"
                yt_search_res = self.ytm_client.search(query=yt_query, filter="albums")
                for res in yt_search_res:
                    res_browse_ID = res["browseId"]
                    found[res_browse_ID] = 0
                    if res["artists"][0]["name"] == album_artist:
                        found[res_browse_ID] += self.SCORE_COEFFICIENT
                    if res["title"] == album_name:
                        found[res_browse_ID] += self.SCORE_COEFFICIENT
                    if res["title"] in album_name or album_name in res["title"]:
                        found[res_browse_ID] += self.SCORE_COEFFICIENT
                    if res["year"] == album_year:
                        found[res_browse_ID] += self.SCORE_COEFFICIENT
                if found:
                    res_browse_ID = max(found, key=found.get)
                    res_album = self.ytm_client.get_album(res_browse_ID)
                    res_playlist_ID = res_album["audioPlaylistId"]
                    self.ytm_client.rate_playlist(res_playlist_ID, "LIKE")
                    print(colored(f"Added album: {yt_query}", "green"))
                else:
                    not_added_albums.append(yt_query)
        return not_added_albums

    def print_not_added(self) -> None:
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
            if not self.keep_dupes:
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
