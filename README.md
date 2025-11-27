# Mediumwave Audio Filter (mw.py)

This is an experimental toy project to simulate the sound of old medium wave radio on top of modern audio files.

It is not accurate broadcast emulation. It is a simple ffmpeg based filter chain that adds:

- mono band limited audio
- slight distortion
- a very quiet low pitched whistle (simulating heterodyne tones)
- intense staccato high frequency crackle (simulating electrical interference)

The script lets you pick a folder with audio files and plays them one by one through `ffplay`.

## Features

- Folder picker for audio files (GUI dialog via Tkinter)
- Supports common formats: `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`, `.aac`, `.wma`, `.opus`
- Uses `ffmpeg` filter_complex to:
  - downmix to mono
  - apply a medium wave style bandpass
  - add bitcrushing for slight distortion
  - add a low pitched whistle tone
  - add very hard, high frequency staccato crackle
- Playback via `ffplay`
- On Windows:
  - `n` skips to the next track
  - `q` quits the whole playback

## Requirements

- Python 3.10 or newer
- `ffmpeg` build that includes `ffplay`
- `tkinter` available in your Python installation (on Windows this is usually included)

No third party Python packages are required. Everything uses the standard library plus the external `ffmpeg` tools.

## Installation

1. Install a recent ffmpeg build that includes `ffmpeg.exe` and `ffplay.exe`.  
   On Windows you can use a static build and unpack it somewhere like:

   ```text
   C:\tools\ffmpeg\bin
