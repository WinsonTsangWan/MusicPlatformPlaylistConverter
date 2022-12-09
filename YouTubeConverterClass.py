import math
import spotipy

from termcolor import colored
from spotipy.oauth2 import SpotifyOAuth

class YouTubeMusicConverterClass():
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

    def __init__(self, YTM_CLIENT) -> None:
        self.ytm_client = YTM_CLIENT
        pass

    def convert_YT_to_SP_playlist(self, sp_client: spotipy.client, yt_playlist_ID: str, keep_dupes: bool) -> str:
        '''
        Converts YouTube Music playlist with given playlist ID to Spotify playlist.

        Parameters:
        - (spotipy.client) sp_client: Spotify API client
        - (bool) keep_dupes: add duplicates to new playlist? True : False
        Return:
        - (str) playlist ID for newly created Spotify playlist
        '''
        yt_playlist = self.ytm_client.get_playlist(yt_playlist_ID, limit=None)
        yt_playlist_songs = yt_playlist["tracks"]
        for song in yt_playlist_songs:
            song_name = song["title"]
            song_artist = song["artists"][0]["name"]
            

