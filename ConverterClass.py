from termcolor import colored

class Converter():
    ''' SCORE: constant by which we linearly increment scores when scoring search results '''
    SCORE = 100

    ''' EXP: constant by which we exponentially punish differences in song duration when 
    scoring search results (eg. score -= e^(EXP_COEFFICIENT*(abs(DIFFERENCE_IN_SONG_DURATION))))
    '''
    EXP = 100

    ''' NOT_ADDED_SONGS: dict where (str) keys = playlist names -> (dict) values = {"unfound":[str], "dupes":[str]}
    - NOT_ADDED_SONGS -> {str:{"unfounded":[str], "dupes":[str]})}
        - "unfound" -> (list) list of song YT queries that were not added because they could not be found
        - "dupes" -> (list) list of song YT queries that were not added because they were duplicates
    '''
    NOT_ADDED_SONGS = {}

    ''' NOT_ADDED_ALBUMS: list of album names that were not added because they could not be found'''
    NOT_ADDED_ALBUMS = []
    
    def __init__(self, YTM_CLIENT, SP_CLIENT, KEEP_DUPES) -> None:
        self.ytm_client = YTM_CLIENT
        self.sp_client = SP_CLIENT
        self.keep_dupes = KEEP_DUPES
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
            print(colored("\nThe following songs could not be found and were not added:\n", "green"))
            index = 1
            for playlist in self.NOT_ADDED_SONGS:
                print(f"\n-----PLAYLIST: {playlist}-----")
                for song_query in self.NOT_ADDED_SONGS[playlist]["unfound"]:
                    print(f"{index}. {song_query}")
                    index += 1
            if index == 1:
                print("None. All songs were fuound.")
            if not self.keep_dupes:
                print(colored("\nThe following songs were duplicates and were not added:", "green"))
                index = 1
                for playlist in self.NOT_ADDED_SONGS:
                    print(f"\n-----PLAYLIST: {playlist}-----")
                    for song_query in self.NOT_ADDED_SONGS[playlist]["dupes"]:
                        print(f"{index}. {song_query}")
                        index += 1
                if index == 1:
                    print("None. Source playlist had no duplicates.")
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
            print("\nThe following albums could not be found and were not added:")
            for index, album in enumerate(self.NOT_ADDED_ALBUMS):
                print(f"{index + 1}. {album}")
        return

    def print_unfound_song_error(self, playlist_name: str, query: str) -> None: 
        '''
        Given a playlist name and song query, adds the query to self.NOT_ADDED, and then
        prints that the song was not found.\n
        Parameters:
        - (str) playlist_name: name of source playlist from which song query was derived
        - (str) query: query for the song that was not added (eg. f"{song['name']} by {song['artist']}")\n
        Return:
        - None
        '''
        if playlist_name not in self.NOT_ADDED_SONGS:
            self.NOT_ADDED_SONGS[playlist_name] = {"unfound":[], "dupes":[]}
        self.NOT_ADDED_SONGS[playlist_name]["unfound"].append(query)
        print(colored(f"ERROR: '{query}' not found.", "green"))
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
        song_info["type"] = song["resultType"]
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
