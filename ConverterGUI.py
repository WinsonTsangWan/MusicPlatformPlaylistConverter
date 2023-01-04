import PyQt5.QtWidgets as qt_widgets

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor


class ConverterGUI():
    def __init__(self) -> None:
        self.app = qt_widgets.QApplication([])
        self.window = qt_widgets.QWidget()
        self.window_layout = qt_widgets.QVBoxLayout()
        self.create_window()

        self.ytmusic_auth_textbox = qt_widgets.QLineEdit("")

        self.platforms = ["Spotify", "YouTube Music", "Apple Music"]
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
        self.downloads_button.hide()

        self.convert_button = qt_widgets.QPushButton("\nCONVERT\n")

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
        return

converter_GUI = ConverterGUI()
