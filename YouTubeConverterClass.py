import math
import youtube_dl

from os import mkdir, getcwd
from pprint import pprint
from ConverterClass import Converter
from termcolor import colored

class YouTubeMusicConverter(Converter):

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

        # Download YouTube Music videos that are not song types or official music videos
        self.download_YT_videos()

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
        sp_playlist = []
        count = 1
        print(colored("Copying contents into Spotify playlist...", "green"))
        for yt_song in yt_tracks:
            if yt_song:
                song_info = self.get_YT_song_info(yt_song)
                sp_query = f"{song_info['title']} {song_info['artist']}"
                if (yt_song["videoType"] == "MUSIC_VIDEO_TYPE_ATV" or 
                    yt_song["videoType"] == "MUSIC_VIDEO_TYPE_OMV"):
                    best_match_ID = self.do_multiple_queries(song_info)
                    if best_match_ID:
                        if best_match_ID not in sp_playlist:
                            sp_playlist.append(best_match_ID)
                        else:
                            self.print_unadded_song_error(yt_playlist, "dupes", sp_query, best_match_ID)
                    else:
                        self.print_unadded_song_error(yt_playlist_name, "unfound", sp_query)
                else:
                    self.print_unadded_song_error(yt_playlist_name, "downloads", sp_query, song_info["id"])
                print(colored(f"Copying song {count}/{len(yt_tracks)}", "green"))
            else:
                self.print_unadded_song_error(yt_playlist_name, "unfound", f"Song #{count}")
                print(colored(f"(It was {type(yt_song)} type, not a song dict. Couldn't even query.)", "green"))
            count += 1
        sp_playlist_ID = self.create_SP_playlist(yt_playlist_name, sp_playlist)
        return sp_playlist_ID

    def convert_YT_to_SP_liked_albums(self) -> None:
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

    def do_multiple_queries(self, song_info: dict):
        '''
        Given a song name and artist, perform multiple Spotify queries and run find_best_match on 
        both search results, and then choose the better of the two search results.\n
        Parameters:
        - (dict) song_info: dictionary with song name, artist, album and duration of the target song\n
        Return:
        - (str) Spotify song ID of search result with best holistic score (ie. best match to the song in song_info)
        '''
        url_encode_title = '%20'.join(song_info['title'].split())
        url_encode_artist = '%20'.join(song_info['artist'].split())
        query_1 = f"track:{url_encode_title}%20artist:{url_encode_artist}"
        query_2 = f"{song_info['title']}"
        query_3 = f"{song_info['title']} {song_info['artist']}"
        queries_lst = [query_1, query_2, query_3]
        local_best_scores_dict = {}
        for query in queries_lst:
            # print(f"\nQUERY: {query}")
            search_res = self.sp_client.search(query, type="track", limit=50)["tracks"]["items"]
            local_best_match_ID, local_best_score = self.find_best_match_complex(search_res, song_info)
            local_best_scores_dict[local_best_match_ID] = local_best_score
        overall_best_match_ID = max(local_best_scores_dict, key=local_best_scores_dict.get)
        return overall_best_match_ID

    def find_best_match_complex(self, sp_search_res: list, song_info: dict) -> str:
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
        best_match_ID = None
        best_score = float("-inf")
        offset = [self.OFFSET]
        for res in sp_search_res:
            if res:
                res_info = self.get_SP_song_info(res)
                res_score = self.score(song_info, res_info, offset)
                if res_score > best_score:
                    best_score = res_score
                    best_match_ID = res_info["id"]
                # print(f"{res_info['title']} by {res_info['artist']}: {res_score}")
        return best_match_ID, best_score

    def score(self, song_info: dict, res_info: dict, offset: list) -> float:
        major = 0
        close_title = (song_info["title"] in res_info["title"] or 
                        res_info["title"] in song_info["title"])
        close_artist = (song_info["artist"] in res_info["artist"] or 
                        res_info["artist"] in song_info["artist"])
        same_title = song_info["title"] == res_info["title"]
        same_artist = song_info["artist"] == res_info["artist"]
        same_album = res_info["album"] and res_info["album"] == song_info["album"]
        if "top_result" in res_info:
            is_top_result = res_info["top_result"]
            if is_top_result:
                major += 2
        if offset[0] > 0:
            major += offset[0]
            offset[0] -= 1
        if same_title:
            major += 2
        elif close_title:
            major += 1
        if same_artist:
            major += 2
        elif close_artist:
            major += 1
        if same_album:
            major += 2
        if "type" in res_info:
            is_song = res_info["type"] == "song"
            if is_song:
                if major > 2.5:
                    major += 30
                else:
                    major += 1
        major *= 2
        try:
            diff_factor = math.exp(abs(song_info["duration_seconds"]-res_info["duration_seconds"]))
        except OverflowError:
            diff_factor = float("inf")
        score = (self.SCORE * major) - diff_factor
        return score

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
        if sp_playlist:
            while len(sp_playlist) > 100:
                self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, sp_playlist[:100])
                sp_playlist = sp_playlist[100:]
            self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, sp_playlist)

        # HANDLE DUPLICATES
        for playlist in self.NOT_ADDED_SONGS:
            dupes = self.NOT_ADDED_SONGS[playlist]["dupes"]
            if self.keep_dupes and dupes:
                while len(dupes) > 100:
                    self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, dupes[:100])
                    dupes = dupes[100:]

        print(colored("Finished! Spotify playlist has been created.\n" 
                    + "Check your Spotify library to find it.", "green"))
        return sp_playlist_ID

    def download_YT_videos(self) -> None:
        '''
        Given a list of video IDs of YouTube videos, download all videos using youtube_dl.\n
        Parameters:
        - (str) yt_playlist_name: name of the YouTube playlist currently being converted
        - (list) yt_download_IDs: list of YouTube videos in the playlist that were not added
            to the Spotify playlist and must be downloaded\n
        Return:
        - None\n
        NOTE: YouTube Music results can have video types (ie. song["videoType"] values) of 
        MUSIC_VIDEO_TYPE_ATV (ie. song), MUSIC_VIDEO_TYPE_OMV (ie. official music video), or 
        MUSIC_VIDEO_TYPE_UGC (ie. video). If the videoType is the first two, then we know that 
        the result is an official song by an official artist, which we can almost certainly find
        on Spotify. If the videoType is the last one, the result might be a cover or some other 
        song not published on Spotify, in which case we do not want to risk adding the incorrect
        song to the newly created Spotify playlist. Thus, we simply download the YouTube Music
        result instead.
        '''
        def print_YT_download_progress(d):
            '''
            Print "Finished downloading" after every completed YouTube video download.\n
            Parameters:
            - (?) d: download progress object from youtube_dl (not sure of object type)\n
            Return:
            - None
            '''
            if d["status"] == "finished":
                print(colored(f"\nFinished downloading song {count}/{len(yt_download_IDs)}", "green"))
            return
        if self.download_videos:
            for playlist in self.NOT_ADDED_SONGS:
                count = 1
                self.YTDL_OPTIONS['outtmpl'] = f"/{playlist}/%(title)s.%(ext)s"
                self.YTDL_OPTIONS['progress_hooks'] = [print_YT_download_progress]
                yt_download_IDs = self.NOT_ADDED_SONGS[playlist]["downloads"]
                print(colored(f"\nDownloading {len(yt_download_IDs)} videos that are not song type objects...", "green"))
                for video_ID in yt_download_IDs:
                    yt_video_URL = "https://www.youtube.com/watch?v="+video_ID
                    with youtube_dl.YoutubeDL(self.YTDL_OPTIONS) as ytdl:
                        ytdl.download([yt_video_URL])
                    count += 1
        return
