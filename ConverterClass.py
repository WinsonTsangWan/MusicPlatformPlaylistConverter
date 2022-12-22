from termcolor import colored

class Converter():
    ''' SCORE: constant by which we linearly increment scores when scoring search results '''
    SCORE = 100

    ''' EXP: constant by which we exponentially punish differences in song duration when 
    scoring search results (eg. score -= e^(EXP_COEFFICIENT*(abs(DIFFERENCE_IN_SONG_DURATION))))
    '''
    EXP = 600

    ''' OFFSET: the number of search results to which we award additional points (in order to prefer
        earlier results over later results)'''
    OFFSET = 2

    ''' NOT_ADDED_SONGS: dict of playlists and their songs that were not added for the given reasons
    - (dict) NOT_ADDED_SONGS = {
        (str) playlist_name: (dict) {
            (str) "unfounded": [(str) query strings], 
            (str) "dupes": [(str) query strings], 
            (str) "downloads": [(str) video IDs]
        }
        - "unfound" -> (list) list of song YT queries that were not added because they could not be found
        - "dupes" -> (list) list of song YT queries that were not added because they were duplicates
        - "downloads" -> (list) list of YT video IDs that were not added because they were not song type objects
    '''
    NOT_ADDED_SONGS = {}

    ''' NOT_ADDED_ALBUMS: list of album names that were not added because they could not be found'''
    NOT_ADDED_ALBUMS = []

    ''' YTDL_OPTIONS: dict of options for youtube_dl download'''
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    def __init__(self, YTM_CLIENT, SP_CLIENT, KEEP_DUPES, DOWNLOADS=False) -> None:
        self.ytm_client = YTM_CLIENT
        self.sp_client = SP_CLIENT
        self.keep_dupes = KEEP_DUPES
        self.download_videos = DOWNLOADS
        pass

    def print_not_added_songs(self) -> None:
        '''
        Prints all songs queries that were not added, either because they could not 
        be found or because they are duplicates, using class variable NOT_ADDED_SONGS.\n
        Parameters:
        - None\n
        Return:
        - None
        '''
        if self.NOT_ADDED_SONGS:
            for playlist in self.NOT_ADDED_SONGS:
                unfound = self.NOT_ADDED_SONGS[playlist]["unfound"]
                dupes = self.NOT_ADDED_SONGS[playlist]["dupes"]
                downloads = self.NOT_ADDED_SONGS[playlist]["downloads"]
                print_unfound = unfound
                print_dupes = dupes and not self.keep_dupes
                print_downloads = downloads and not self.download_videos
                if print_unfound or print_dupes or print_downloads:
                    self.print("\n_______________PLAYLIST: {playlist}_______________")
                    if print_unfound:
                        self.print("\nThe following songs could not be found and were not added:")
                        for index, song_query in enumerate(unfound):
                            self.print(f"{index + 1}. {song_query}")
                    if print_dupes:
                        self.print("\nThe following songs were duplicates and were not added:")
                        for index, song_query in enumerate(dupes):
                            self.print(f"{index + 1}. {song_query}")
                    if print_downloads:
                        self.print("\nThe following songs were not song type objects and were not added nor downloaded:")
                        for index, song_query in enumerate(downloads):
                            self.print(f"{index + 1}. {song_query}")
        return

    def print_not_added_albums(self) -> None:
        '''
        Prints all album queries that were not added because they could not be found.\n
        Parameters:
        - None\n
        Return:
        - None
        '''
        if self.NOT_ADDED_ALBUMS:
            self.print("\nThe following albums could not be found and were not added:")
            for index, album in enumerate(self.NOT_ADDED_ALBUMS):
                self.print(f"{index + 1}. {album}")
        return

    def print_unadded_song_error(self, playlist_name: str, reason: str, query: str, ID: str = None) -> None: 
        '''
        Given a playlist name and song query, adds the query to self.NOT_ADDED, and then
        prints that the song was not found.\n
        Parameters:
        - (str) playlist_name: name of source playlist from which song query was derived
        - (str) query: query string for the song that was not added (eg. f"{song_info['title']} by {song_info['artist']}")
        - (str) ID: song/video ID for the song that was not added (only available for "dupes" and "downloaded", not for "unfound)
        - (str) reason: reason for the song not being added (ie. which NOT_ADDED_SONGS bucket to put the song)
            - "unfound": if the song could not be found with the query
            - "dupes": if the song is a duplicate (we handle duplicates when creating the playlist)
            - "downloads": if the song is a YouTube Music video that is neither a song type nor an official music
                video type, and thus must be either downloaded or discarded
        Return:
        - None
        '''
        if playlist_name not in self.NOT_ADDED_SONGS:
            self.NOT_ADDED_SONGS[playlist_name] = {"unfound":[], "dupes":[], "downloads":[]}
        if reason == "unfound":
            self.NOT_ADDED_SONGS[playlist_name]["unfound"].append(query)
            self.print(f"ERROR: \"{query}\" not found.")
        elif reason == "dupes":
            if ID:
                self.NOT_ADDED_SONGS[playlist_name]["unfound"].append(ID)
                self.print(f"\"{query}\" not added because it was a duplicate.")
            else:
                self.print(f"ERROR: No ID provided for duplicate query: \"{query}\"")
        elif reason == "downloads":
            if ID:
                self.NOT_ADDED_SONGS[playlist_name]["downloads"].append(ID)
                self.print(f"\"{query}\" not added because it was a video type object, not a song type object.")
            else:
                self.print(f"ERROR: No ID provided for download query: \"{query}\"")
        return

    def get_SP_song_info(self, song: dict) -> dict:
        '''
        Given a Spotify song, summarize important song information into a dictionary\n
        Parameters:
        - (dict) SONG: Spotify song\n
        Return:
        - (dict) dictionary with song name, artist, id, album, and duration
        '''
        song_info = {}
        song_info["title"] = song["name"].lower()
        song_info["artist"] = song["artists"][0]["name"].lower()
        song_info["id"] = song["id"]
        song_info["album"] = song["album"]["name"].lower()
        song_info["duration_seconds"] = song["duration_ms"]/1000
        return song_info

    def get_YT_song_info(self, song: dict) -> dict: 
        '''
        Given a YouTube Music song, summarize important song information into a dictionary\n
        Parameters:
        - (dict) song: YouTube Music song dictionary\n
        Return:
        - (dict) dictionary with song name, artist, id, album, and duration
        '''
        song_info = {}
        song_info["title"] = song["title"].lower()
        song_info["artist"] = song["artists"][0]["name"].lower()
        song_info["id"] = song["videoId"]
        if "album" in song and song["album"] != None:
            song_info["album"] = song["album"]["name"]
        else:
            song_info["album"] = None
        song_duration_raw = song["duration"]
        song_info["duration_seconds"] = self.get_sec_from_raw_duration(song_duration_raw)
        if "resultType" in song:
            song_info["type"] = song["resultType"]
        if "category" in song:
            song_info["top_result"] = song["category"] == "Top result"
        return song_info
    
    def get_sec_from_raw_duration(self, song_duration_raw: str) -> int:
        '''
        Converts a time string in "hour:minute:second" format to total seconds.\n
        Parameters:
        - (str) song_duration_raw: a string representing a time duration in "hour:minute:second" format\n
        Return:
        - (int) song_duration_raw in seconds
        '''
        tokens = song_duration_raw.split(":")
        tokens = [int(i) for i in tokens]
        song_duration_sec = 0
        for index in range(len(tokens)):
            song_duration_sec += tokens[index] * (60**(len(tokens) - index - 1))
        return song_duration_sec
    
    def print(self, message: str) -> None:
        print(colored(message, "green"))
        return
