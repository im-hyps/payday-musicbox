# Payday 2 Music Box

A GUI tool that makes custom Payday 2 music mods from any audio file. Requires BeardLib and Project Cell: Beta.

## What It Does

Converts any audio file (MP3, FLAC, WAV, etc) to a clean OGG, generates the necessary mod files, and puts everything in a ready-to-use mod folder.
Supports both single-track menu music and multi-phase heist playlists.

## What You Need

- Payday 2 (obviously)
- SuperBLT mod loader
- BeardLib + Project Cell Beta mods
- Python 3 (with Tkinter)
- FFmpeg

## Installation

### Windows:
- Install Python 3 & Tkinter.
  > Visit https://www.python.org/downloads/ and download the latest Python 3 installer.

  > Tkinter is installed by default.
  
  > *Make sure to check "Add Python to PATH" during installation.*
- Install FFMPEG.
  > Download FFMPEG from https://ffmpeg.org/download.html.
  
  > Extract the zip to C:\ffmpeg. 
  
- Add C:\ffmpeg\bin to your system PATH.
  
  > Right click "This PC".
  
  > Properties > Advanced system settings > Environment Variables.
  
  > Find "Path" in system variables, click Edit, add C:\ffmpeg\bin.
  
  > Click OK and restart any open terminals.

- Run the program file in a new folder.


### Linux (Ubuntu/Debian)
- Run `sudo apt install python3 python3-tk` in terminal.
- Run `chmod +x pd2musicbox.py`
- Run the python file anywhere.

## Notes

- Menu music shows up in the Project Cell: Beta jukebox.
- Converted OGGs are stripped of metadata and album art (PAYDAY 2 doesn't like those).
- Saves your output folder preference so you don't have to pick it every time.
- Mod ID is generated from your mod name.

## Known Issues
- If two mods have names that produce the same ID, the second one won't load. Give them distinct names.
- Drag and drop isn't fully supported on Linux. Just select it automatically, you're still saving a shitload of time using this.
- On windows, for the error logs to open automatically, find and replace `xdg-open` with `os.startfile`.

## License

Do whatever you want, just credit me.
