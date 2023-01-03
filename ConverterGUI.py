import PyQt5.QtWidgets as qt_widgets

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor


class ConverterGUI():
    def __init__(self) -> None:
        self.app = qt_widgets.QApplication([])
        self.window = qt_widgets.QWidget()
        self.window_layout = qt_widgets.QVBoxLayout()
        self.set_dark_theme()
        self.set_window_title()
        self.set_window_dimensions()

        self.platforms = ["Spotify", "YouTube Music", "Apple Music"]
        self.src_dest_buttons = {
            platform: {
                "Source": qt_widgets.QRadioButton(platform),
                "Destination": qt_widgets.QRadioButton(platform)
            }
            for platform in self.platforms
        }
        
        ''' 
        Params:
        - job (src and dest)
        - keep_dupes
        - download
        - playlist URL
        '''
        self.src_dest_group_layout = qt_widgets.QVBoxLayout()
        self.src_dest_group_box = qt_widgets.QGroupBox("Select conversion source")
        self.src_dest_group_box.setLayout(self.src_dest_group_layout)
        self.window_layout.addWidget(self.src_dest_group_box)

        self.src_group_layout = qt_widgets.QVBoxLayout()
        self.src_group_box = qt_widgets.QGroupBox("Source")
        self.src_group_box.setLayout(self.src_group_layout)
        self.src_dest_group_layout.addWidget(self.src_group_box, alignment=Qt.AlignTop)

        self.dest_group_layout = qt_widgets.QVBoxLayout()
        self.dest_group_box = qt_widgets.QGroupBox("Destination")
        self.dest_group_box.setLayout(self.dest_group_layout)

        self.src_dest_group_layout.addWidget(self.dest_group_box, alignment=Qt.AlignTop)

        self.utils_group_layout = qt_widgets.QVBoxLayout()
        self.utils_group_box = qt_widgets.QGroupBox("Options")
        self.utils_group_box.setLayout(self.utils_group_layout)
        self.window_layout.addWidget(self.utils_group_box)

        self.keep_dupes_button = qt_widgets.QCheckBox("Should we keep duplicates?")
        self.utils_group_layout.addWidget(self.keep_dupes_button, alignment=Qt.AlignTop)

        self.downloads_button = qt_widgets.QCheckBox("Should we download YouTube Music videos that cannot be found?")
        self.utils_group_layout.addWidget(self.downloads_button, alignment=Qt.AlignTop)

        self.window_layout.addStretch()

        self.convert_button = qt_widgets.QPushButton("CONVERT")
        self.window_layout.addWidget(self.convert_button)

        self.set_src_dest_buttons()

        self.window.setLayout(self.window_layout)
        self.window.show()
        self.app.exec()
        pass

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
        start_x= screen.size().width() // 4
        start_y = screen.size().height() // 3
        width = 700
        height = 500
        self.window.setGeometry(start_x, start_y, width, height)
        return

    def set_src_dest_buttons(self):
        for platform in self.src_dest_buttons:
            src_button = self.src_dest_buttons[platform]["Source"]
            dest_button = self.src_dest_buttons[platform]["Destination"]
            src_button.clicked.connect(self.update_buttons)
            self.src_group_layout.addWidget(src_button)
            self.dest_group_layout.addWidget(dest_button)
        return

    def update_buttons(self):
        for platform in self.src_dest_buttons:
            self.src_dest_buttons[platform]["Source"].show()
            self.src_dest_buttons[platform]["Destination"].show()
        for platform in self.src_dest_buttons:
            if self.src_dest_buttons[platform]["Source"].isChecked():
                self.src_dest_buttons[platform]["Destination"].hide()
                if self.src_dest_buttons[platform]["Source"].text() == "YouTube Music":
                    self.downloads_button.show()
                else:
                    self.downloads_button.hide()
        return

converter_GUI = ConverterGUI() 