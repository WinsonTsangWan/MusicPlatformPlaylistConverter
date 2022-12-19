import math
import spotipy

from pprint import pprint
from ConverterClass import Converter
from termcolor import colored
from spotipy.oauth2 import SpotifyOAuth

class YouTubeMusicConverter(Converter):

    ''' CUTOFF_COEFFICIENT: when scoring search results, if the current song's score is greater than this
    coefficient, then we stop iterating and simply take the current song as the best match'''
    CUTOFF_COEFFICIENT = -3

    def convert_YT_to_SP_library(self) -> None:
        '''
        Converts current user's YouTube Music library (liked songs, liked albums, all playlists) to 
        Spotify. In order: Liked songs -> Playlists -> Albums\n
        Parameters:
        - None
        Return:
        - None
        '''
        # Convert YouTube Music Liked Videos and all playlists to YouTube Music playlist
        for yt_playlist in self.ytm_client.get_library_playlists(limit=None):
            yt_playlist_ID = yt_playlist["playlistId"]
            self.convert_YT_to_SP_playlist(yt_playlist_ID)

        # Convert YouTube Music Liked Albums to Spotify Liked Albums
        self.convert_YT_liked_albums()

        # Print unadded songs from each playlist
        self.print_not_added_songs()

        # Print unadded Spotify albums
        self.print_not_added_albums()
        return 

    def convert_YT_to_SP_playlist(self, yt_playlist_ID: str) -> str:
        '''
        Converts YouTube Music playlist with given playlist ID to Spotify playlist.\n
        Parameters:
        - (str) yt_playlist_ID: playlist ID for source YouTube Music playlist\n
        Return:
        - (str) playlist ID for newly created Spotify playlist
        '''
        if yt_playlist_ID == "LIKED_SONGS":
            yt_playlist_name = "Liked Songs"
            yt_playlist = self.ytm_client.get_library_songs(limit=None)
        elif yt_playlist_ID == "LIKED_VIDS":
            yt_playlist_name = "Liked Videos"
            yt_playlist = self.ytm_client.get_liked_songs(limit=None)
        else:
            yt_playlist_name = self.ytm_client.get_playlist(yt_playlist_ID)["title"]
            yt_playlist = self.ytm_client.get_playlist(yt_playlist_ID, limit=None)
        print(colored(f"\nYouTube Music playlist detected: '{yt_playlist_name}'", "green"))
        yt_tracks = yt_playlist["tracks"]
        sp_playlist = {}
        count = 1
        print(colored("Copying contents into Spotify playlist...", "green"))
        for yt_song in yt_tracks:
            if yt_song:
                song_info = self.get_YT_song_info(yt_song)
                full_sp_query = f"{song_info['title']} by {song_info['artist']}"
                best_match_ID = self.do_two_queries(song_info)
                if best_match_ID:
                    if best_match_ID not in sp_playlist:
                        sp_playlist[best_match_ID] = {"full_sp_query": full_sp_query, "count":1}
                    else:
                        sp_playlist[best_match_ID]["count"] += 1
                    print(colored(f"Copying song {count}/{len(yt_tracks)}", "green"))
                else:
                    self.print_unfound_song_error(yt_playlist_name, full_sp_query)
            else:
                self.print_unfound_song_error(yt_playlist_name, f"Song #{count}")
                print(f"(It was {type(yt_song)} type. Not a song dict).")
            count += 1
        sp_playlist_ID = self.create_SP_playlist(yt_playlist_name, sp_playlist)
        return sp_playlist_ID

    def convert_YT_liked_albums(self) -> None:
        '''
        Given a list of YouTube Music Liked Albums, add all albums to Spotify Liked Albums, 
        and returns a list of albums that were not added.\n
        Parameters:
        - None\n
        Return:
        - (list) list of albums that were not added to Spotify Liked Albums
                because a good match could not be found\n     
        '''
        liked_albums = self.ytm_client.get_library_albums(limit=None)
        if liked_albums:
            print(colored(f"\nAdding YouTube Music saved albums to Spotify library...", "green"))
            for album in liked_albums:
                found = {}
                album_name = album["title"]
                album_artist = album["artists"][0]["name"]
                album_year = album["year"]
                sp_query = f"{album_name} by {album_artist}"
                sp_search_res = self.sp_client.search(sp_query, type="album")["albums"]["items"]
                for res in sp_search_res:
                    res_ID = res["id"]
                    found[res_ID] = 0
                    if res['artists'][0]['name'] == album_artist:
                        found[res_ID] += self.SCORE
                    if res['name'] == album_name:
                        found[res_ID] += self.SCORE
                    if res['name'] in album_name or album_name in res['name']:
                        found[res_ID] += self.SCORE
                    if res['release_date'][:3] == album_year:
                        found[res_ID] += self.SCORE
                if found:
                    self.sp_client.current_user_saved_albums_add([max(found, key=found.get)])
                    print(colored(f"Added album: {sp_query}", "green"))
                else:
                    self.NOT_ADDED_ALBUMS.append(sp_query)
        return

    def do_two_queries(self, song_info: dict):
        '''
        Given a song name and artist, perform two Spotify queries - one with just the song name and one
        with both the song name and the artist - and run find_best_match on both search results, and 
        then choose the better of the two search results.\n
        Parameters:
        - (dict) song_info: dictionary with song name, artist, album and duration of the target song\n
        Return:
        - (str) Spotify song ID of search result with best holistic score (ie. best match to the song in song_info)
        '''
        query_1 = song_info["title"]
        query_2 = song_info["title"] + " " + song_info["artist"]
        search_res_1 = self.sp_client.search(query_1, type="track", limit=50)["tracks"]["items"]
        search_res_2 = self.sp_client.search(query_2, type="track", limit=50)["tracks"]["items"]
        best_match_1, score_1 = self.find_best_match(search_res_1, song_info)
        best_match_2, score_2 = self.find_best_match(search_res_2, song_info)
        if score_1 >= score_2:
            return best_match_1
        return best_match_2

    def find_best_match(self, sp_search_res: list, song_info: dict) -> str:
        '''
        Given a list of Spotify search results and a target song to match, holistically score each 
        search result and then return the result with the highest score (ie. the best match).\n
        Parameters:
        - (list) sp_search_res: list of Spotify search results
        - (dict) song_info: dictionary with song name, artist, album and duration of the target song\n
        Return
        - (str) Spotify song ID of first search result that has a score > self.CUTOFF_COEFFICIENT, or 
            None if there is none
        - (int) score of the search result being returned, or float("-inf") if no song ID is being returned
        '''
        while sp_search_res:
            res = sp_search_res.pop(0)
            res_info = self.get_SP_song_info(res)
            # Automatically take results with same title and same artist
            if (song_info["title"] == res_info["title"] and 
                song_info["artist"] == res_info["artist"]):
                return res_info["id"]
            score = 0
            # Prefer results with the exact same artist as Spotify target song
            if (song_info["artist"] == res_info["artist"] or 
                (res_info["album"] and res_info["album"] == song_info["album"])):
                score += self.SCORE
            # Exponentially punish differences in song duration
            try:
                score += 1 / math.exp(self.EXP*abs(song_info["duration_seconds"]-res_info["duration_seconds"]))
            except OverflowError:
                score = float("-inf")
            # Greedily take current score if it is better than self.CUTOFF_COEFFICIENT
            if score > self.CUTOFF_COEFFICIENT:
                return res_info["id"], score
        return None, float("-inf")

    def create_SP_playlist(self, yt_playlist_name: str, sp_playlist: dict) -> str:    
        '''
        Creates a Spotify playlist and handles duplicates based on self.keep_dupes.\n
        Parameters:
        - (str) YT_PLAYLIST_NAME: name of Spotify playlist
        - (dict) SP_PLAYLIST: 
            - keys: (str) song IDs | values: (dict) {"full_sp_query":str, "count":int}
                - full_sp_query = f"{song['name']} by {song['artist']}"
                - count = number of times the given song ID has been added (eg. duplicate songs)\n
        Return:
        - (str) playlist ID of newly created Spotify playlist
        '''
        print(colored("Finishing up...", "green"))

        # CREATE SPOTIFY PLAYLIST
        user_ID = self.sp_client.me()["id"]
        sp_playlist_ID = self.sp_client.user_playlist_create(
                        user=user_ID, 
                        name=f"{yt_playlist_name} (copied from YouTube Music)",
                        public=False,
                        collaborative=False,
                        description="Includes duplicates" if self.keep_dupes else "Does not include duplicates")["id"]

        # ADD LIST OF SONGS TO SPOTIFY PLAYLIST
        add_songs = list(sp_playlist.keys())
        while len(add_songs) > 100:
            self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, add_songs[:100])
            add_songs = add_songs[100:]
        self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, add_songs)

        # HANDLE DUPLICATES
        dupes = []
        for song_ID in sp_playlist:
            count = sp_playlist[song_ID]["count"]
            if count > 1:
                for _ in range(count-1):
                    dupes.append(song_ID)
                    if not self.keep_dupes:
                        self.NOT_ADDED_SONGS[yt_playlist_name]["dupes"].append(sp_playlist[song_ID]['sp_query'])
        if self.keep_dupes and dupes:
            while len(add_songs) > 100:
                self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, dupes[:100])
                dupes = dupes[100:]
            self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, dupes)

        print(colored("Finished! Spotify playlist has been created.\n" 
                    + "Check your Spotify library to find it.", "green"))
        return sp_playlist_ID
