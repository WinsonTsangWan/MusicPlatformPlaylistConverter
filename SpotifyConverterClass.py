import math
import spotipy

from ConverterClass import Converter
from termcolor import colored
from spotipy.oauth2 import SpotifyOAuth

class SpotifyConverter(Converter):

    def convert_SP_to_YT_library(self) -> None:
        '''
        Converts current user's Spotify library (liked songs, liked albums, all playlists) to 
        YouTube Music playlists. In order: Liked songs -> Playlists -> Albums\n
        Parameters:
        - None\n
        Return:
        - None
        '''
        # Convert Spotify Liked Songs to YouTube Music playlist
        sp_scope = "user-library-read"
        sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
        sp_playlist_ID = "LIKED_SONGS"
        self.convert_SP_to_YT_playlist(sp_client, sp_playlist_ID)

        # Add Spotify Liked Albums to a list (so we can convert later)
        liked_albums = self.get_all_SP_tracks(sp_client, "LIKED_ALBUMS")

        # Convert all Spotify playlists to YouTube Music playlists
        sp_scope = "playlist-read-private"
        sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=sp_scope))
        for sp_playlist in sp_client.current_user_playlists()["items"]:
            sp_playlist_ID = sp_playlist["id"]
            self.convert_SP_to_YT_playlist(sp_client, sp_playlist_ID)

        # Convert Spotify Liked Albums to YouTube Music Liked Albums
        self.convert_SP_liked_albums(liked_albums)

        # Print unadded songs from each playlist
        self.print_not_added_songs()

        # Print unadded Spotify albums
        self.print_not_added_albums()
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
                except ValueError:
                    if sp_playlist_name not in self.NOT_ADDED_SONGS:
                        self.NOT_ADDED_SONGS[sp_playlist_name] = {"unfound":[], "dupes":[]}
                    self.NOT_ADDED_SONGS[sp_playlist_name]["unfound"].append(yt_query)
                    print(f"ERROR: '{yt_query}' not found.")
            except TypeError:
                if sp_playlist_name not in self.NOT_ADDED_SONGS:
                    self.NOT_ADDED_SONGS[sp_playlist_name] = {"unfound":[], "dupes":[]}
                self.NOT_ADDED_SONGS[sp_playlist_name]["unfound"].append(f"Song #{count}")
                print(f"ERROR: Song #{count} in Spotify playlist '{sp_playlist_name}' could not be found " 
                    + f"(It was {type(song)} type. Not a song dict).")
            count += 1
        yt_playlist_ID = self.create_YT_playlist(yt_playlist, sp_playlist_name)
        return yt_playlist_ID

    def convert_SP_liked_albums(self, liked_albums: list) -> list:
        '''
        Given a list of Spotify Liked Albums, add all albums to YouTube Music Liked Albums, 
        and returns a list of albums that were not added.\n
        Parameters:
        - (list) LIKED_ALBUMS: list of Spotify Liked Albums\n
        Return:
        - (list) list of albums that were not added to YouTube Music Liked Albums
                because a good match could not be found\n
        '''
        if liked_albums:
            print(colored(f"\nAdding Spotify saved albums to YouTube Music library...", "green"))
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
                    self.NOT_ADDED_ALBUMS.append(yt_query)
        return

    def find_best_match(self, yt_search_res: list, song_info: dict) -> str:
        '''
        Given a list of YouTube Music search results and a target song to match, holistically score each 
        search result and then return the result with the highest score (ie. the best match).\n
        Parameters:
        - (list) YT_SEARCH_RES: list of YouTube Music search results
        - (dict) SONG_INFO: dictionary with song name, artist, album and duration\n
        Return
        - (str) video ID of search result with best holistic score (ie. best match to the song in song_info)
        '''
        found = {}
        while yt_search_res:
            res = yt_search_res.pop(0)
            if res["resultType"] == "song" or res["resultType"] == "video":
                res_info = self.get_YT_song_info(res)
                found[res_info["id"]] = 0
                # Prefer Top result over other results
                if res["category"] == "Top result":
                    found[res_info["id"]] += self.SCORE_COEFFICIENT
                # Prefer songs over video results
                if res["resultType"] == "song":
                    found[res_info["id"]] += self.SCORE_COEFFICIENT
                # Prefer results with the exact same name as Spotify song title
                if song_info["name"] == res_info["name"]:
                    found[res_info["id"]] += self.SCORE_COEFFICIENT
                # Slightly prefer results that closely resemble the Spotify song title
                if song_info["name"] in res_info["name"] or res_info["name"] in song_info["name"]:
                    found[res_info["id"]] += self.SCORE_COEFFICIENT/2
                # Prefer results from the same artist as on Spotify
                if song_info["artist"] == res_info["artist"]:
                    found[res_info["id"]] += self.SCORE_COEFFICIENT
                # Slightly prefer results from artists that closely resemble the Spotify artist
                if song_info["artist"] in res_info["artist"] or res_info["artist"] in song_info["artist"]:
                    found[res_info["id"]] += self.SCORE_COEFFICIENT/2
                # Prefer results from the same album as on Spotify
                if res_info["album"] and res_info["album"] == song_info["album"]:
                    found[res_info["id"]] += self.SCORE_COEFFICIENT
                # Exponentially punish differences in song duration
                try:
                    found[res["videoId"]] -= math.exp(self.EXP_COEFFICIENT*abs(song_info["duration_seconds"]-res_info["duration_seconds"]))
                except OverflowError:
                    found[res["videoId"]] = float("-inf")
        best_match_ID = max(found, key=found.get)
        return best_match_ID
    
    def create_YT_playlist(self, yt_playlist: dict, sp_playlist_name: str) -> str:
        '''
        Creates a YouTube playlist and handles duplicates based on self.keep_dupes.\n
        Parameters:
        - (dict) YT_PLAYLIST: 
            - keys: (str) video IDs | values: (dict) {"yt_query":str, "count":int}
                - yt_query = query string that lead to the given video ID
                - count = number of times the given video ID has been added (eg. duplicate songs)
        - (str) SP_PLAYLIST_NAME: name of Spotify playlist\n
        Return:
        - (str) playlist ID of newly created YouTube Music playlist\n
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
                        self.NOT_ADDED_SONGS[sp_playlist_name]["dupes"].append(yt_playlist[video_ID]['yt_query'])
        if self.keep_dupes and dupes:
            self.ytm_client.add_playlist_items(playlistId=yt_playlist_ID, 
            videoIds=dupes, duplicates=True)
        print(colored("Finished! Youtube Music playlist has been created.\n" 
                    + "Check your YouTube Music library to find it.", "green"))
        
        return yt_playlist_ID

    def get_all_SP_tracks(self, sp_client: spotipy.client, sp_playlist_ID: str) -> list[dict]:
        '''
        Given a Spotify API client and playlist ID, return a list of all songs in the playlist.\n
        Parameters:
        - (spotipy.client) SP_CLIENT: Spotify API client
        - (str) SP_PLAYLIST_ID: 
            - playlist ID for a Spotify playlist
            - "LIKED_SONGS" for liked songs
            - "LIKED_ALBUMS" for liked albums\n
        Return:
        - (list[dict]) list of all songs (dicts) on a Spotify playlist\n
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

