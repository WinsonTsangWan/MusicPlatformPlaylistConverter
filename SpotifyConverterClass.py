from ConverterClass import Converter

class SpotifyConverter(Converter):

    '''
    Convert all Spotify playlists, liked songs, and liked albums to YouTube Music
    '''
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
        self.convert_SP_to_YT_liked_albums()

        # Print unadded songs from each playlist
        self.print_not_added_songs()

        # Print unadded Spotify albums
        self.print_not_added_albums()
        return 

    '''
    Convert single Spotify playlist or liked songs to YouTube Music
    '''
    def convert_SP_to_YT_playlist(self, sp_playlist_ID: str) -> str:
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
        self.print(f"\nSpotify playlist detected: '{sp_playlist_name}'")
        sp_tracks = self.get_all_SP_tracks(sp_playlist_ID)
        yt_playlist = []
        self.print("Copying contents into Youtube playlist...")
        for index, sp_track in enumerate(sp_tracks):
            song = sp_track["track"]
            if song:
                song_info = self.get_SP_song_info(song)
                full_yt_query = f"\"{song['name']}\" by {song['artists'][0]['name']}"
                best_match_ID = self.find_best_match_ID(song_info, self.get_multiple_YT_search_results)
                if best_match_ID:
                    if best_match_ID not in yt_playlist:
                        yt_playlist.append(best_match_ID)
                        self.print(f"Copying song {index + 1}/{len(sp_tracks)}")
                    else:
                        self.print_unadded_song_error(sp_playlist_name, "dupes", full_yt_query, best_match_ID)
                        if self.keep_dupes:
                            self.print(f"Copying song {index + 1}/{len(sp_tracks)}")
                else:
                    self.print_unadded_song_error(sp_playlist_name, "unfound", full_yt_query)
            else:
                self.print_unadded_song_error(sp_playlist_name, "unfound", f"Song #{index + 1}")
        yt_playlist_ID = self.create_YT_playlist(yt_playlist, sp_playlist_name)
        return yt_playlist_ID
    
    def get_multiple_YT_search_results(self, song_info: dict) -> list[list[dict]]:
        '''
        Given a song name and artist, perform multiple YouTube Music queries. Next, filter all 
        search results to keep only videoTypes of "song" and "video". Then, get the song info of all
        remaining search results and aggregate them into a single list of search result song info dicts.\n
        Parameters:
        - (dict) song_info: dictionary with info about the target Spotify song\n
        Return:
        - (list) list of lists of song_info dicts (each inner list is the search result of 
            a query and contains multiple song_info dicts of songs from that search result) 
        '''
        query_1 = f"{song_info['title']} {song_info['artist']}"
        query_2 = f"{song_info['title']} by {song_info['artist']}"
        queries_lst = [query_1, query_2]
        all_yt_search_res = []
        for query in queries_lst:
            single_search_raw = self.ytm_client.search(query=query, limit=self.LIMIT)
            single_search_processed = [self.get_YT_song_info(res) for res in single_search_raw
                if (res and (res["resultType"] == "video" or res["resultType"] == "song"))]
            all_yt_search_res.append(single_search_processed)
        return all_yt_search_res

    def create_YT_playlist(self, yt_playlist: list, sp_playlist_name: str) -> str:
        '''
        Creates a YouTube playlist and handles duplicates based on self.keep_dupes.\n
        Parameters:
        - (list) YT_PLAYLIST: list of YouTube Music song/video IDs to add to new YouTube Music playlist
        - (str) SP_PLAYLIST_NAME: name of Spotify playlist\n
        Return:
        - (str) playlist ID of newly created YouTube Music playlist\n
        '''
        self.print("Finishing up...")
        # CREATE YOUTUBE MUSIC PLAYLIST WITH LIST OF SONGS (NO DUPLICATES YET)
        yt_playlist_ID = self.ytm_client.create_playlist(
            title=f"{sp_playlist_name} (copied from Spotify)",
            description="Includes duplicates" if self.keep_dupes else "Does not include duplicates",
            video_ids=yt_playlist)
        # HANDLE DUPLICATES
        if sp_playlist_name in self.NOT_ADDED_SONGS:
            dupes = [dupe["id"] for dupe in self.NOT_ADDED_SONGS[sp_playlist_name]["dupes"]]
            if self.keep_dupes and dupes:
                self.ytm_client.add_playlist_items(playlistId=yt_playlist_ID, videoIds=dupes, duplicates=True)
            self.print("Finished!")
        return yt_playlist_ID

    '''
    Convert Spotify liked albums to YouTube Music
    '''
    def convert_SP_to_YT_liked_albums(self) -> None:
        '''
        Given a list of Spotify Liked Albums, add all albums to YouTube Music 
        Liked Albums, and add all unadded albums to self.NOT_ADDED_ALBUMS.\n
        Parameters:
        - None\n
        Return:
        - None\n
        '''
        liked_albums = self.get_all_SP_tracks("LIKED_ALBUMS")
        if liked_albums:
            self.print(f"\nAdding Spotify saved albums to YouTube Music library...")
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
                    self.print(f"Added album: {yt_query}")
                else:
                    self.NOT_ADDED_ALBUMS.append(yt_query)
        return

    '''
    Helper functions: Utils
    '''
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
        NOTE: Spotify playlists are paginated, meaning sp_playlist["items"] only retrieves the
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
