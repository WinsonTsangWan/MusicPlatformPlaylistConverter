import math
import spotipy

from pprint import pprint
from ConverterClass import Converter
from termcolor import colored
from spotipy.oauth2 import SpotifyOAuth

class SpotifyConverter(Converter):

    ''' CUTOFF_COEFFICIENT: when scoring search results, if the current song's score is greater than this
    coefficient, then we stop iterating and simply take the current song as the best match'''

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
        sp_playlist_ID = "LIKED_SONGS"
        self.convert_SP_to_YT_playlist(sp_playlist_ID)

        # Convert all Spotify playlists to YouTube Music playlists
        for sp_playlist in self.sp_client.current_user_playlists()["items"]:
            sp_playlist_ID = sp_playlist["id"]
            self.convert_SP_to_YT_playlist(sp_playlist_ID)

        # Convert Spotify Liked Albums to YouTube Music Liked Albums
        self.convert_SP_liked_albums()

        # Print unadded songs from each playlist
        self.print_not_added_songs()

        # Print unadded Spotify albums
        self.print_not_added_albums()
        return 

    def convert_SP_to_YT_playlist(self,  sp_playlist_ID: str) -> str:
        '''
        Given a Spotify playlist ID, create a YouTube Music playlist with the same songs\n
        Parameters:
        - (str) SP_PLAYLIST_ID: playlist ID of source Spotify playlist\n
        Return:
        - (str) playlist ID for newly created YouTube Music playlist
        '''
        if sp_playlist_ID == "LIKED_SONGS":
            sp_playlist_name = "Liked Songs"
        else:
            sp_playlist_name = self.sp_client.playlist(playlist_id=sp_playlist_ID)["name"]
        print(colored(f"\nSpotify playlist detected: '{sp_playlist_name}'", "green"))
        sp_tracks = self.get_all_SP_tracks(sp_playlist_ID)
        yt_playlist = {}
        count = 1
        print(colored("Copying contents into Youtube playlist...", "green"))
        for sp_track in sp_tracks:
            song = sp_track["track"]
            if song:
                song_info = self.get_SP_song_info(song)
                yt_query = f"{song['name']} by {song['artists'][0]['name']}"
                yt_search_res = self.ytm_client.search(query=yt_query)
                best_match_ID = self.find_best_match(yt_search_res, song_info)
                if best_match_ID:
                    if best_match_ID not in yt_playlist:
                        yt_playlist[best_match_ID] = {"yt_query":yt_query, "count":1}
                    else:
                        yt_playlist[best_match_ID]["count"] += 1
                    print(colored(f"Copying song {count}/{len(sp_tracks)}", "green"))
                else:
                    self.print_unfound_song_error(sp_playlist_name, yt_query)
            else:
                self.print_unfound_song_error(sp_playlist_name, f"Song #{count}")
                print(f"(It was {type(song)} type. Not a song dict).")
            count += 1
        yt_playlist_ID = self.create_YT_playlist(yt_playlist, sp_playlist_name)
        return yt_playlist_ID

    def convert_SP_liked_albums(self) -> list:
        '''
        Given a list of Spotify Liked Albums, add all albums to YouTube Music Liked Albums, 
        and returns a list of albums that were not added.\n
        Parameters:
        - None\n
        Return:
        - (list) list of albums that were not added to YouTube Music Liked Albums
                because a good match could not be found\n
        '''
        liked_albums = self.get_all_SP_tracks("LIKED_ALBUMS")
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
                        found[res_browse_ID] += self.SCORE
                    if res["title"] == album_name:
                        found[res_browse_ID] += self.SCORE
                    if res["title"] in album_name or album_name in res["title"]:
                        found[res_browse_ID] += self.SCORE
                    if res["year"] == album_year:
                        found[res_browse_ID] += self.SCORE
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
        Return:
        - (str) video ID of search result with best holistic score (ie. best match to the song in song_info)
        '''
        debug = {}
        best_match_ID = None
        best_score = float("-inf")
        for res in yt_search_res:
            if res["resultType"] == "song" or res["resultType"] == "video":
                res_info = self.get_YT_song_info(res)
                res_score = self.score(song_info, res_info)
                if res_score > best_score:
                    best_score = res_score
                    best_match_ID = res_info["id"]
                self.OFFSET = 2
                print(f"{res_info['title']} by {res_info['artist']}: {res_score}")
                debug[f"{res_info['title']} by {res_info['artist']}"] = res_score
        if best_score < 0:
            pprint(debug)
            return None
        return best_match_ID
    
    def score(self, song_info: dict, res_info: dict) -> int:
        close_title = song_info["title"] in res_info["title"]
        close_artist = song_info["artist"] in res_info["title"]
        same_title = song_info["title"] == res_info["title"]
        same_artist = song_info["artist"] == res_info["artist"]
        same_album = res_info["album"] and res_info["album"] == song_info["album"]
        is_song = res_info["type"] == "song"
        is_top_result = res_info["top_result"]
        major = 0
        if is_top_result:
            major += 2
        if self.OFFSET:
            major += self.OFFSET
            self.OFFSET -= 1
        if same_title:
            major += 1.5
        if same_artist:
            major += 1.5
        if same_album:
            major += 1.5
        if is_song:
            if major > 2.5:
                major += 30
            else:
                major += 0.5
        major *= 2
        try:
            diff_factor = math.exp(abs(song_info["duration_seconds"]-res_info["duration_seconds"]))
        except OverflowError:
            diff_factor = float("inf")
        score = (self.SCORE * major) - diff_factor
        return score

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

    def get_all_SP_tracks(self, sp_playlist_ID: str) -> list[dict]:
        '''
        Given a Spotify API client and playlist ID, return a list of all songs in the playlist.\n
        Parameters:
        - (str) SP_PLAYLIST_ID: 
            - playlist ID for a Spotify playlist
            - "LIKED_SONGS" for liked songs
            - "LIKED_ALBUMS" for liked albums\n
        Return:
        - (list[dict]) list of all songs (dicts) on a Spotify playlist\n
        Note: Spotify playlists are paginated, meaning sp_playlist["items"] only retrieves the
        first 100 items. If there are more than 100 items on the playlist, then we must 
        request the next page using self.sp_client.next(sp_playlist). Here, we simply do that
        for every page, add all items from each page to a list, and return that list.
        '''
        if sp_playlist_ID == "LIKED_SONGS":
            sp_playlist = self.sp_client.current_user_saved_tracks(limit=50)
        elif sp_playlist_ID == "LIKED_ALBUMS":
            sp_playlist = self.sp_client.current_user_saved_albums(limit=50)
        else:
            sp_playlist = self.sp_client.playlist_tracks(sp_playlist_ID)
        sp_tracks = sp_playlist["items"]
        while sp_playlist["next"]:
            sp_playlist = self.sp_client.next(sp_playlist)
            sp_tracks.extend(sp_playlist["items"])
        return sp_tracks
