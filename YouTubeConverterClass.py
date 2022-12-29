import youtube_dl
from ConverterClass import Converter

class YouTubeMusicConverter(Converter):
    '''
    Convert all YouTube Music playlists and liked albums to Spotify
    '''
    def convert_YT_to_SP_library(self) -> None:
        '''
        Converts current user's YouTube Music library (liked songs, liked albums, all playlists) to 
        Spotify. In order: Playlists -> Albums\n
        Parameters:
        - None
        Return:
        - None
        '''
        # Convert all YouTube Music playlists to Spotify playlists
        # NOTE: YouTube Music liked songs behave as playlists, unlike Spotify liked songs, which
        #   are not playlists, but rather a separate object type.
        # NOTE: We slice the library playlists starting from 1 because the 0th playlist is the 
        #   native liked videos playlist ("Your Likes"), which contains normal YouTube video likes in 
        #   addition to YouTube Music song likes. Since most people probably only intend to convert
        #   their YouTube Music songs rather than their liked videos, I don't think it's valuable to 
        #   convert this playlist.
        yt_playlists_no_liked_vids = self.ytm_client.get_library_playlists(limit=None)[1:]
        for yt_playlist in yt_playlists_no_liked_vids:
            yt_playlist_ID = yt_playlist["playlistId"]
            self.convert_YT_to_SP_playlist(yt_playlist_ID)

        # Convert YouTube Music Liked Albums to Spotify Liked Albums
        self.convert_YT_to_SP_liked_albums()

        # Print unadded songs from each playlist
        self.print_not_added_songs()

        # Print unadded Spotify albums
        self.print_not_added_albums()

        # Download YouTube Music videos that are not song types or official music videos
        self.download_YT_videos()
        return 

    '''
    Convert single YouTube Music playlist to Spotify
    '''
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
        self.print(f"\nYouTube Music playlist detected: '{yt_playlist_name}'")
        yt_tracks = yt_playlist["tracks"]
        sp_playlist = []
        self.print("Copying contents into Spotify playlist...")
        for index, yt_song in enumerate(yt_tracks):
            if yt_song:
                song_info = self.get_YT_song_info(yt_song)
                full_sp_query = f"\"{yt_song['title']}\" by {yt_song['artists'][0]['name']}"
                if (yt_song["videoType"] == "MUSIC_VIDEO_TYPE_ATV" or 
                    yt_song["videoType"] == "MUSIC_VIDEO_TYPE_OMV"):
                    best_match_ID = self.find_best_match_ID(song_info, self.get_multiple_SP_search_results)
                    if best_match_ID:
                        if best_match_ID not in sp_playlist or self.keep_dupes:
                            sp_playlist.append(best_match_ID)
                            self.print(f"Copying song {index + 1}/{len(yt_tracks)}")
                        else:
                            self.print_unadded_song_error(yt_playlist_name, "dupes", full_sp_query, best_match_ID)
                    else:
                        self.print_unadded_song_error(yt_playlist_name, "unfound", full_sp_query)
                else:
                    self.print_unadded_song_error(yt_playlist_name, "downloads", full_sp_query, song_info["id"])
            else:
                self.print_unadded_song_error(yt_playlist_name, "unfound", f"Song #{index + 1}")
        sp_playlist_ID = self.create_SP_playlist(sp_playlist, yt_playlist_name)
        return sp_playlist_ID

    def get_multiple_SP_search_results(self, song_info: dict) -> list[list[dict]]:
        '''
        Given a song name and artist, perform multiple Spotify queries and aggregate 
        the search results of all queries into a single list of search results.\n
        Parameters:
        - (dict) song_info: dict with info about the target YouTube Music song\n
        Return:
        - (list) list of lists of song_info dicts (each inner list is the search result of 
            a query and contains multiple song_info dicts of songs from that search result)
        '''
        query_1 = f"{song_info['title']}"
        query_2 = f"{song_info['title']} {song_info['artist']}"
        query_3 = f"{song_info['title']} by {song_info['artist']}"
        queries_lst = [query_1, query_2, query_3]
        if "(" in song_info["title"] or "(" in song_info["artist"]:
            queries_lst.append(self.remove_parentheses(query_2))
        all_sp_search_res = []
        for query in queries_lst:
            single_search_raw = self.sp_client.search(
                query, type="track", limit=self.LIMIT)["tracks"]["items"]
            single_search_processed = [self.get_SP_song_info(res) for res in single_search_raw if res]
            all_sp_search_res.append(single_search_processed)
        return all_sp_search_res

    def create_SP_playlist(self, sp_playlist: list, yt_playlist_name: str) -> str:
        '''
        Creates a Spotify playlist and handles duplicates based on self.keep_dupes.\n
        Parameters:
        - (list) SP_PLAYLIST: list of Spotify song IDs to add to new Spotify playlist
        - (str) YT_PLAYLIST_NAME: name of Spotify playlist
        Return:
        - (str) playlist ID of newly created Spotify playlist
        '''
        self.print("Finishing up...")
        # CREATE EMPTY SPOTIFY PLAYLIST
        user_ID = self.sp_client.me()["id"]
        sp_playlist_ID = self.sp_client.user_playlist_create(
                        user=user_ID, 
                        name=f"{yt_playlist_name} (copied from YouTube Music)",
                        public=False,
                        collaborative=False,
                        description="Includes duplicates" if self.keep_dupes else "Does not include duplicates")["id"]
        # ADD LIST OF SONGS TO SPOTIFY PLAYLIST (NO DUPLICATES YET)
        if sp_playlist:
            while len(sp_playlist) > 100:
                self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, sp_playlist[:100])
                sp_playlist = sp_playlist[100:]
            self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, sp_playlist)
        # HANDLE DUPLICATES
        for playlist in self.NOT_ADDED_SONGS:
            dupes = [dupe["id"] for dupe in self.NOT_ADDED_SONGS[playlist]["dupes"]]
            if self.keep_dupes and dupes:
                while len(dupes) > 100:
                    self.sp_client.user_playlist_add_tracks(user_ID, sp_playlist_ID, dupes[:100])
                    dupes = dupes[100:]
        self.print("Finished!")
        return sp_playlist_ID

    ''' 
    Convert YouTube Music liked albums to Spotify
    '''
    def convert_YT_to_SP_liked_albums(self) -> None:
        '''
        Given a list of YouTube Music Liked Albums, add all albums to Spotify 
        Liked Albums, and add all unadded albums to self.NOT_ADDED_ALBUMS.\n
        Parameters:
        - None\n
        Return:
        - None\n     
        '''
        liked_albums = self.ytm_client.get_library_albums(limit=None)
        if liked_albums:
            self.print(f"\nAdding YouTube Music saved albums to Spotify library...")
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
                    self.print(f"Added album: {sp_query}")
                else:
                    self.NOT_ADDED_ALBUMS.append(sp_query)
        return

    '''
    Helper functions: Miscellaneous
    '''
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
                self.print(f"\nFinished downloading song {index + 1}: {video_dict['query']}")
            return

        if self.download_videos:
            for playlist in self.NOT_ADDED_SONGS:
                self.YTDL_OPTIONS['outtmpl'] = f"/{playlist}/%(title)s.%(ext)s"
                # self.YTDL_OPTIONS['progress_hooks'] = [print_YT_download_progress]
                yt_downloads = self.NOT_ADDED_SONGS[playlist]["downloads"]
                self.print(f"\n{'_'*5}Downloading {len(yt_downloads)} videos for playlist: {playlist}{'_'*5}...")
                for index, video_dict in enumerate(yt_downloads):
                    try:
                        with youtube_dl.YoutubeDL(self.YTDL_OPTIONS) as ytdl:
                            ytdl.download(["https://www.youtube.com/watch?v=" + video_dict["id"]])
                        self.print(f"\nFinished downloading song {index + 1}: {video_dict['query']}")
                    except:
                        self.print(f"\nFailed to download song {index + 1}: {video_dict['query']}")
        return
