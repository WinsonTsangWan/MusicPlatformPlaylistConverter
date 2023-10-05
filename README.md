# Music Platform Playlist Converter

Music Platform Playlist Converter Converter is a console application used to transfer Spotify playlists to YouTube Music and vice versa.

## Usage

### Part 1: Authenticating YouTube Music access
Step #1. Open a new tab \
Step #2. Open developer tools (either Ctrl-Shift-I or F12) \
Step #3. Go to https://music.youtube.com and ensure you are logged in \
Step #4. In the developer tools window, use the search bar to search for "/browse" \
Firefox: \
&nbsp;&nbsp;&nbsp;&nbsp; Step #5. Locate the entry with the file "browse?...", status 200, method POST, domain music.youtube.com \
&nbsp;&nbsp;&nbsp;&nbsp; Step #6. Copy the request headers (right click -> copy -> copy request headers) \
Chrome: \
&nbsp;&nbsp;&nbsp;&nbsp; Step #5. Locate the entry with the name "browse?...", status 200 \
&nbsp;&nbsp;&nbsp;&nbsp; Step #6. Left-click on any matching entry \
&nbsp;&nbsp;&nbsp;&nbsp; Step #7. In the "Headers" tab, scroll to the "Request Headers" section \
&nbsp;&nbsp;&nbsp;&nbsp; Step #8. Copy everything from "accept: \*/*" to the end of the section.

### Part 2: Running the application
Step #1. Double-click the main.exe file \
Step #2. Follow the instructions as they appear on the command-line interface \
Step #3. When prompted with ```Please paste the request headers from Firefox and press 'Enter, Ctrl-Z, Enter' to continue```, paste the content copied in Part 1, press Enter, Ctrl-Z, and Enter again. \
Step #4. Proceed with following the instructions on the command-line interface
