import PyQt5.QtWidgets as qt_widgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

import logging
import urllib
import spotipy
from SpotifyConverterClass import SpotifyConverter
from YouTubeConverterClass import YouTubeMusicConverter
from ytmusicapi import YTMusic
from dotenv import load_dotenv
load_dotenv()

class ConverterGUI():
    def __init__(self) -> None:
        self.ytm_client = None
        self.sp_client = None

        self.app = qt_widgets.QApplication([])
        self.window = qt_widgets.QWidget()
        self.window_layout = qt_widgets.QVBoxLayout()

        self.ytmusic_auth_textbox = qt_widgets.QLineEdit("")

        self.platforms = ["Spotify", "YouTube Music"]
        self.src_buttons = {platform: qt_widgets.QRadioButton(platform) for platform in self.platforms}
        self.dest_buttons = {platform: qt_widgets.QRadioButton(platform) for platform in self.platforms}
        
        self.jobs = ["Playlist", "Library", "Liked Songs", "Liked Albums"]
        self.jobs_buttons = {job: qt_widgets.QRadioButton(job) for job in self.jobs}
        self.playlist_URL_textbox = qt_widgets.QLineEdit("")
        self.playlist_URL_group_box = qt_widgets.QGroupBox("Paste the playlist URL")

        self.options = ["Keep duplicates", "Download YouTube videos and songs that cannot be found"]
        self.options_buttons = {option: qt_widgets.QCheckBox(option) for option in self.options}
        self.keep_dupes_button = self.options_buttons["Keep duplicates"]
        self.downloads_button = self.options_buttons["Download YouTube videos and songs that cannot be found"]

        self.convert_button = qt_widgets.QPushButton("\nCONVERT\n")

        self.create_window()
        self.create_ytmusic_auth_group()
        self.create_src_dest_group()
        self.create_job_group()
        self.create_options_group()
        self.create_convert_button()
        self.app.exec()
        pass

    def create_ytmusic_auth_group(self):
        ytmusic_auth_group_layout = qt_widgets.QVBoxLayout()
        ytmusic_auth_group_box = qt_widgets.QGroupBox("Paste YouTube Music authentication request headers")
        ytmusic_auth_group_box.setLayout(ytmusic_auth_group_layout)
        ytmusic_auth_group_layout.addWidget(self.ytmusic_auth_textbox, alignment=Qt.AlignTop)
        self.window_layout.addWidget(ytmusic_auth_group_box)
        return self.ytmusic_auth_textbox

    def create_src_dest_group(self):
        # Create outer group
        src_dest_group_layout = qt_widgets.QVBoxLayout()
        src_dest_group_box = qt_widgets.QGroupBox("Step 1. Select conversion source and destination")
        src_dest_group_box.setLayout(src_dest_group_layout)
        self.window_layout.addWidget(src_dest_group_box)
        # Create source buttons group
        src_group_layout = qt_widgets.QVBoxLayout()
        src_group_box = qt_widgets.QGroupBox("Source")
        src_group_box.setLayout(src_group_layout)
        src_dest_group_layout.addWidget(src_group_box, alignment=Qt.AlignTop)
        # Create destination buttons group
        dest_group_layout = qt_widgets.QVBoxLayout()
        dest_group_box = qt_widgets.QGroupBox("Destination")
        dest_group_box.setLayout(dest_group_layout)
        src_dest_group_layout.addWidget(dest_group_box, alignment=Qt.AlignTop)
        # Add source and destination buttons to respective groups
        for platform in self.platforms:
            self.src_buttons[platform].clicked.connect(self.update_hidden_buttons)
            src_group_layout.addWidget(self.src_buttons[platform])
            dest_group_layout.addWidget(self.dest_buttons[platform])
        return

    def create_job_group(self):
        job_group_layout = qt_widgets.QVBoxLayout()
        job_group_box = qt_widgets.QGroupBox("Step 2. Select what you want to convert")
        job_group_box.setLayout(job_group_layout)
        self.window_layout.addWidget(job_group_box)
        for job in self.jobs_buttons:
            job_button = self.jobs_buttons[job]
            job_button.clicked.connect(self.update_hidden_buttons)
            job_group_layout.addWidget(job_button, alignment=Qt.AlignTop)
        playlist_URL_group_layout = qt_widgets.QVBoxLayout()
        self.playlist_URL_group_box.hide()
        self.playlist_URL_group_box.setLayout(playlist_URL_group_layout)
        playlist_URL_group_layout.addWidget(self.playlist_URL_textbox, alignment=Qt.AlignTop)
        job_group_layout.addWidget(self.playlist_URL_group_box)
        return

    def create_options_group(self):
        options_group_layout = qt_widgets.QVBoxLayout()
        options_group_box = qt_widgets.QGroupBox("Step 3. Additional options")
        options_group_box.setLayout(options_group_layout)
        self.window_layout.addWidget(options_group_box)
        for option in self.options:
            option_button = self.options_buttons[option]
            option_button.clicked.connect(self.update_hidden_buttons)
            options_group_layout.addWidget(option_button, alignment=Qt.AlignTop)
        self.downloads_button.hide()
        return

    def create_convert_button(self):
        self.window_layout.addWidget(self.convert_button, alignment=Qt.AlignBottom)
        self.convert_button.clicked.connect(self.get_arguments)
        return

    '''
    Create GUI Window
    '''
    def create_window(self):
        self.window.setLayout(self.window_layout)
        self.set_dark_theme()
        self.set_window_title()
        self.set_window_dimensions()
        self.window.show()
        return

    def set_dark_theme(self) -> None:
        self.app.setStyle("Fusion")
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.app.setPalette(dark_palette)
        return

    def set_window_title(self):
        window_title = "Spotify-YouTubeMusic Converter"
        self.window.setWindowTitle(window_title)
        return

    def set_window_dimensions(self):
        screen = self.app.primaryScreen()
        start_x= screen.size().width() // 3
        start_y = screen.size().height() // 4
        width = 500
        height = 500
        self.window.setGeometry(start_x, start_y, width, height)
        return

    '''
    Helper functions: Utils
    '''
    def update_hidden_buttons(self):
        # Hide opposite destination of currently selected source
        for platform in self.platforms:
            if self.src_buttons[platform].isChecked():
                self.dest_buttons[platform].hide()
                # Hide downloads button if source != YouTube Music
                if platform == "YouTube Music":
                    self.downloads_button.show()
                else:
                    self.downloads_button.hide()
            else:
                self.dest_buttons[platform].show()
        # Hide playlist URL box if job != playlist
        if self.jobs_buttons["Playlist"].isChecked():
            self.playlist_URL_group_box.show()
        else:
            self.playlist_URL_group_box.hide()
        return

    def get_arguments(self):
        args= {}
        args["ytm_auth"] = self.ytmusic_auth_textbox.text()
        args["source"] = [src for src in self.src_buttons if self.src_buttons[src].isChecked()][0]
        args["dest"] = [dest for dest in self.dest_buttons if self.dest_buttons[dest].isChecked()][0]
        args["job"] = [job for job in self.jobs_buttons if self.jobs_buttons[job].isChecked()][0]
        args["playlist_url"] = self.playlist_URL_textbox.text()
        args["keep_dupes"] = self.keep_dupes_button.isChecked()
        args["downloads"] = self.downloads_button.isChecked()
        self.GUI_convert(args)
        return
    
    def GUI_convert(self, args):
        logging.basicConfig(
            filename="log.log", 
            level=logging.INFO,
            format=u"%(message)s",
            filemode="w",
            encoding="utf-8"
        )

        # try:
        #     self.sp_client = self.do_spotify_auth()
        # except:
        #     self.error_message("Failed Spotify authentication")
        #     return
        # try:
        #     self.ytm_client = self.do_youtube_auth(args["ytm_auth"])
        # except:
        #     self.error_message("Invalid YouTube Music authentication")
        #     return

        self.ytm_client = YTMusic('headers_auth.json')

        SP_SCOPE = "playlist-read-private playlist-modify-private user-library-read user-library-modify"
        SP_TOKEN = spotipy.util.prompt_for_user_token(scope=SP_SCOPE)
        self.sp_client = spotipy.Spotify(auth=SP_TOKEN)

        if args["job"] == "Playlist":
            parsed_URL = self.get_playlist_URL(args["playlist_URL"])
            if parsed_URL:
                netloc = parsed_URL.netloc
                path = parsed_URL.path
                query = parsed_URL.query
                if args["source"] == "Spotify":
                    if netloc == "open.spotify.com" and path[:10] == "/playlist/":
                        sp_playlist_ID = path[10:]
                        self.do_playlist_spotify(sp_playlist_ID, args["keep_dupes"])
                    else:
                        self.error_message("Make sure the URL leads to a Spotify playlist")
                elif args["source"] == "YouTube Music":
                    if netloc == "music.youtube.com" and path == "/playlist":
                        yt_playlist_ID = query[5:]
                        self.do_playlist_youtube(yt_playlist_ID, args["keep_dupes"], args["downloads"])
                    else:
                        self.error_message("Make sure the URL leads to a YouTube Music playlist")
        elif args["job"] == "Library":
            if args["source"] == "Spotify":
                self.do_library_spotify(args["keep_dupes"])
            elif args["source"] == "YouTube Music":
                self.do_library_youtube(args["keep_dupes"], args["downloads"])
        return

    def get_playlist_URL(self, input_URL):
        try:
            parsed_URL = urllib.parse.urlparse(input_URL)
        except:
            self.error_message("Invalid playlist URL")
            return
        if parsed_URL.netloc != "open.spotify.com" and parsed_URL.netloc != "music.youtube.com":
            self.error_message("Invalid playlist URL")
            return
        return parsed_URL

    def do_spotify_auth(self):
        SP_SCOPE = "playlist-read-private playlist-modify-private user-library-read user-library-modify"
        SP_TOKEN = spotipy.util.prompt_for_user_token(scope=SP_SCOPE)
        SP_CLIENT = spotipy.Spotify(auth=SP_TOKEN)
        return SP_CLIENT

    def do_youtube_auth(self, ytm_auth):
        YTMusic.setup(ytm_auth)
        YTM_CLIENT = YTMusic('headers_auth.json')
        return YTM_CLIENT

    def error_message(self, message):
        error_message = qt_widgets.QMessageBox()
        error_message.setText(f"ERROR: {message}")
        error_message.exec()
        return

    def do_playlist_spotify(self, sp_playlist_ID: str, keep_dupes: bool) -> None:
        self.error_message("SUCCESS DO PLAYLIST SPOTIFY")
        # sp_converter = SpotifyConverter(self.ytm_client, self.sp_client, keep_dupes)
        # sp_converter.convert_SP_to_YT_playlist(sp_playlist_ID)
        # sp_converter.print_not_added_songs()
        return

    def do_playlist_youtube(self, yt_playlist_ID: str, keep_dupes: bool, downloads: bool) -> None:
        self.error_message("SUCCESS DO PLAYLIST YOUTUBE")
        # yt_converter = YouTubeMusicConverter(self.ytm_client, self.sp_client, keep_dupes, downloads)
        # yt_converter.convert_YT_to_SP_playlist(yt_playlist_ID)
        # yt_converter.print_not_added_songs()
        # yt_converter.download_YT_videos()
        return
    
    def do_library_spotify(self, keep_dupes: bool) -> None:
        self.error_message("SUCCESS DO LIBRARY SPOTIFY")
        # sp_converter = SpotifyConverter(self.ytm_client, self.sp_client, keep_dupes)
        # sp_converter.convert_SP_to_YT_library()
        return

    def do_library_youtube(self, keep_dupes: bool, downloads: bool) -> None:
        self.error_message("SUCCESS DO LIBRARY YOUTUBE")
        # yt_converter = YouTubeMusicConverter(self.ytm_client, self.sp_client, keep_dupes, downloads)
        # yt_converter.convert_YT_to_SP_library()
        return

converter_GUI = ConverterGUI()
