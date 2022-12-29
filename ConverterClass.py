import math

from termcolor import colored

class Converter():
    ''' SP_SOURCE: string constant for the word "Spotify" '''
    SP_SOURCE = "Spotify"

    ''' YT_SOURCE: string constant for the word "YouTube Music" '''
    YT_SOURCE = "YouTube Music"

    ''' LIMIT: number of results to return in a Spotify search query '''
    LIMIT = 10

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
            (str) "unfounded": [(dict) {(str) query: (str) ID}], 
            (str) "dupes": [(dict) {(str) query: (str) ID}], 
            (str) "downloads": [(dict) {(str) query: (str) ID}]
        }
        - "unfound" -> (list) list of dicts (keys = queries : values = None) 
            that were not added because they could not be found
        - "dupes" -> (list) list of dicts (keys = queries : values = destination IDs) 
            that were not added because they were duplicates
        - "downloads" -> (list) list of dicts (keys = queries : values = source (YT) IDs) 
            that were not added because they were not song type objects
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

    '''
    Helper functions: Get song info
    '''
    def get_SP_song_info(self, song: dict) -> dict:
        '''
        Given a Spotify song, summarize important song information into a dictionary\n
        Parameters:
        - (dict) SONG: Spotify song\n
        Return:
        - (dict) dictionary with song name, artist, id, album, and duration
        '''
        song_info = {}
        song_info["title"] = song["name"]
        song_info["artist"] = song["artists"][0]["name"]
        song_info["id"] = song["id"]
        song_info["album"] = song["album"]["name"]
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
        song_info["title"] = song["title"]
        song_info["artist"] = song["artists"][0]["name"]
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
            song_info["top_result"] = (song["category"] == "Top result")
        return song_info

    '''
    Helper functions: Song matching
    '''
    def find_best_match_ID(self, song_info: dict, multi_search_func) -> str:
        '''
        Given a list of search results and a target song to match, holistically score each 
        search result and then return the result with the highest score (ie. the best match).\n
        Parameters:
        - (dict) SONG_INFO: dictionary with song name, artist, album and duration\n
        - (function) MULTI_SEARCH_FUNC: function to get all search results for the song in song_info
            - NOTE: MULTI_SEARCH_FUNC is our own defined function to perform searches using multiple
                search queries (eg. self.get_multiple_YT_search_results or 
                self.get_multiple_SP_search_results). It is NOT the native search function built-in to 
                the API clients (eg. sp_client.search and ytm_client.search). Rather, these native 
                search functions are called inside MULTI_SEARCH_FUNC.
        Return:
        - (str) ID of search result with best holistic score (ie. best match to the song in song_info)
        '''
        best_match_ID = None
        best_score = 0
        list_all_search_res = multi_search_func(song_info)
        # print("\n")
        for search_res in list_all_search_res:
            offset = self.OFFSET
            for res_info in search_res:
                params = self.check_parameters(song_info, res_info)
                res_score = self.score(params, offset)
                offset -= 1
                if res_score > best_score:
                    best_score = res_score
                    best_match_ID = res_info["id"]
                # if res_score > float("-inf"):
                    # self.print(f"{res_info['title']} by {res_info['artist']}: {res_score}")
        return best_match_ID    

    def score(self, params: dict, offset: int) -> float:
        '''
        Given two song dicts (representing the original song and one search result), 
        assign the result song a holistic quantitative score reflecting how much it 
        matches the original song.\n
        Parameters:
        - (dict) song_info: dict with info of the original song
        - (dict) res_info: dict with info of the search result song
        - (int) offset: index in the search result list at which this current result appeared\n
        Return:
        - (float) score for the current result song based on how much it matches the 
            original song (higher score = better match, lower score = worse match)
        '''
        major = 0
        # Parameters
        if params["is_top_result"]:
            major += 2
        if offset > 0:
            major += offset
        if params["same_title"]:
            major += 2
        elif params["close_title"] or params["same_title_lower"]:
            major += 1
        elif params["close_title_lower"]:
            major += 0
        if params["same_artist"]:
            major += 2
        elif params["close_artist"] or params["same_artist_lower"]:
            major += 1
        elif params["close_artist_lower"]:
            major += 0
        if params["same_album"]:
            major += 2
        # Ignore results with major <= 1 (to be conservative with matches)
        if major <= 1:
            return float("-inf")
        # print(major)
        # Prefer song types over non-song types
        if params["is_song"]:
            if major >= 3:
                major += 30
            else:
                major += 1
        major *= 2
        score = (self.SCORE * major) - params["diff_factor"]
        return score

    def check_parameters(self, song_info: dict, res_info: dict) -> dict:
        '''
        Given two song_info dicts, return a new dict containing info about
        how closely certain items in the two input dicts match.\n
        Parameters:
        - (dict) song_info: dict with info of the original song
        - (dict) res_info: dict with info of the search result song\n
        Return:
        - (dict) dict of bools indicating which items in the input dicts do or don't match
        '''
        params = {}
        params["same_title"] = (song_info["title"] == res_info["title"])
        params["same_artist"] = (song_info["artist"] == res_info["artist"])
        params["same_title_lower"] = (song_info["title"].lower() == res_info["title"].lower())
        params["same_artist_lower"] = (song_info["artist"].lower() == res_info["artist"].lower())
        params["same_album"] = (res_info["album"] and song_info["album"] and 
                        res_info["album"] == song_info["album"])
        params["close_title"] = (song_info["title"] in res_info["title"] or 
                        res_info["title"] in song_info["title"])
        params["close_artist"] = (song_info["artist"] in res_info["artist"] or 
                        res_info["artist"] in song_info["artist"])
        params["close_title_lower"] = (song_info["title"].lower() in res_info["title"].lower() or 
                            res_info["title"].lower() in song_info["title"].lower())
        params["close_artist_lower"] = (song_info["artist"].lower() in res_info["artist"].lower() or 
                            res_info["artist"].lower() in song_info["artist"].lower())
        params["is_song"] = ("type" in res_info and
                    res_info["type"] == "song")
        params["is_top_result"] = ("top_result" in res_info and 
                        res_info["top_result"])
        try:
            params["diff_factor"] = math.exp(abs(song_info["duration_seconds"]-res_info["duration_seconds"]))
        except OverflowError:
            params["diff_factor"] = float("inf")
        return params

    '''
    Helper functions: Printing
    '''
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
                    self.print(f"\n{'_'*5}PLAYLIST: {playlist}{'_'*5}")
                    if print_unfound:
                        self.print("\nThe following songs could not be found and were not added:")
                        for index, song_query in enumerate(unfound):
                            self.print(f"   {index + 1}. {song_query['query']}")
                    if print_dupes:
                        self.print("\nThe following songs were duplicates and were not added:")
                        for index, song_query in enumerate(dupes):
                            self.print(f"   {index + 1}. {song_query['query']}")
                    if print_downloads:
                        self.print("\nThe following songs were not song type objects and were not added nor downloaded:")
                        for index, song_query in enumerate(downloads):
                            self.print(f"   {index + 1}. {song_query['query']}")
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
        query_ID_pair = {"query":query, "id":ID}
        self.NOT_ADDED_SONGS[playlist_name][reason].append(query_ID_pair)
        if reason == "unfound":
            self.print(f"ERROR: {query} not found.")
        elif reason == "dupes":
            self.print(f"{query} not added because it was a duplicate.")
        elif reason == "downloads":
            self.print(f"{query} not added because it was a video type object, not a song type object.")
        return

    def print(self, message: str) -> None:
        '''
        Short helper function to print a colored string without the clutter.\n
        Parameters:
        - (str) message: string to be printed\n
        Return:
        - None
        '''
        print(colored(message, "green"))
        return
    
    '''
    Helper functions: Miscellaneous
    '''
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

    def remove_parentheses(self, song_title: str) -> str:
        '''
        Short helper function to remove parenthetical segments from song titles.
        (eg. )\n
        Parameters:
        - (str) song_title: Song titles from which to remove parenthetical segments\n
        Return:
        - (str) song_title with parenthetical segments removed
        '''
        result = ""
        stop = 0
        for char in song_title:
            if char == "(":
                stop += 1
            elif stop == 0:
                result += char
            elif char == ")":
                stop -= 1
        return result
