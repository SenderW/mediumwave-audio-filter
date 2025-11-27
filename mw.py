#!/usr/bin/env python3
"""
mw.py - Medium wave style audio player

This script is an experimental tool to simulate a rough medium wave radio sound
on top of local audio files.

What it does:

- lets you choose a folder with audio files
- plays each file through ffmpeg with a filter chain that adds
  - mono, band limited audio
  - slight distortion
  - a very quiet low pitched whistle tone
  - intense, hard, staccato high frequency crackle
- on Windows you can skip tracks and quit with keys

This is not an accurate broadcast model. It is a simple, stylised effect.
"""

import os
import sys
import subprocess
import tempfile
import time
import shutil
from tkinter import Tk, filedialog

SUPPORTED_EXTENSIONS = (
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
    ".wma",
    ".opus",
)

STOP_ALL = False  # global switch for "q = quit everything"


def find_ffplay() -> str:
    """Locate ffplay in the same folder as this script or in PATH."""
    exe_name = "ffplay.exe" if os.name == "nt" else "ffplay"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, exe_name)
    if os.path.isfile(local_path):
        return local_path

    ffplay_path = shutil.which(exe_name)
    if ffplay_path is not None:
        return ffplay_path

    print("Error: ffplay not found.")
    print("Install an ffmpeg build that includes ffplay")
    print("and either put ffplay next to mw.py or add it to PATH.")
    sys.exit(1)


def find_ffmpeg() -> str:
    """Locate ffmpeg in the same folder as this script or in PATH."""
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, exe_name)
    if os.path.isfile(local_path):
        return local_path

    ffmpeg_path = shutil.which(exe_name)
    if ffmpeg_path is not None:
        return ffmpeg_path

    print("Error: ffmpeg not found.")
    print("Install an ffmpeg build and either put ffmpeg next to mw.py")
    print("or add it to PATH.")
    sys.exit(1)


def choose_folder() -> str:
    """Open a folder selection dialog and return the chosen path."""
    root = Tk()
    root.withdraw()
    root.update_idletasks()
    folder = filedialog.askdirectory(title="Choose folder with audio files")
    root.destroy()
    return folder


def build_filter_complex_for_music_plus_effects() -> str:
    """
    Build the ffmpeg filter_complex string.

    Graph:

    - [0:a]  main music signal
      - downmix to mono
      - medium wave style bandpass and EQ
      - light bitcrushing for gentle distortion
    - whistle path
      - low pitched sine with slow tremolo and light vibrato
    - crackle path
      - very high band limited noise
      - extreme bitcrushing
      - very fast tremolo for hard staccato pulses
    - amix
      - mix main + whistle + crackle into [out]
    """

    # Main signal: mono, band limited, slightly distorted
    main_chain = (
        "[0:a]"
        "aformat=channel_layouts=mono,"
        "highpass=f=220,"
        "lowpass=f=4500,"
        "equalizer=f=350:t=q:w=1:g=3,"
        "equalizer=f=1000:t=q:w=1:g=1.5,"
        "equalizer=f=2600:t=q:w=2:g=-2,"
        "acrusher=bits=9:mode=log:aa=1,"
        "volume=0dB"
        "[a0];"
    )

    # Very quiet, lower pitched whistle
    whistle = (
        "sine=frequency=1800:sample_rate=44100[wsrc];"
        "[wsrc]"
        "tremolo=f=0.1:d=1,"       # slow fade in and out
        "vibrato=f=0.4:d=0.05,"    # small pitch wobble
        "aformat=channel_layouts=mono,"
        "volume=0.05"
        "[w1];"
    )

    # Intense, hard, staccato high frequency crackle
    crackle = (
        "anoisesrc=color=white:amplitude=1.0:sample_rate=44100[nk];"
        "[nk]"
        "highpass=f=6000,"         # keep only high band
        "lowpass=f=12000,"
        "acrusher=bits=2:mode=log:aa=0.0,"
        "tremolo=f=40.0:d=1,"      # very fast, full depth tremolo -> staccato
        "aformat=channel_layouts=mono,"
        "volume=0.12"
        "[k1];"
    )

    # Mix whistle and crackle to [w]
    effects_mix = "[w1][k1]amix=inputs=2:normalize=0[w];"

    # Mix music and effects to [out]
    mix_chain = "[a0][w]amix=inputs=2:duration=first:normalize=0[out]"

    return main_chain + whistle + crackle + effects_mix + mix_chain


def mix_to_temp_wav(ffmpeg_path: str, music_file: str) -> str:
    """
    Render one input file with the filter chain into a temporary WAV file.

    Returns the path to the temporary file.
    """
    tmp_dir = tempfile.mkdtemp(prefix="mw_mix_")
    tmp_path = os.path.join(tmp_dir, "out.wav")

    filter_complex = build_filter_complex_for_music_plus_effects()

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        music_file,
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        "-ac",
        "1",
        "-ar",
        "44100",
        tmp_path,
    ]

    print("ffmpeg filter_complex:", filter_complex)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error while mixing with ffmpeg: {e}")
        # Clean up temp directory
        try:
            if os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir)
        except OSError:
            pass
        raise

    return tmp_path


def play_wav_with_ffplay(ffplay_path: str, wav_path: str) -> str:
    """
    Play the given WAV file with ffplay.

    On Windows:
      - n  -> skip to next track
      - q  -> quit entire playback

    Returns:
      "done"  -> track finished normally
      "next"  -> user pressed n
      "quit"  -> user pressed q or Ctrl+C
    """
    global STOP_ALL

    cmd = [
        ffplay_path,
        "-nodisp",
        "-autoexit",
        wav_path,
    ]

    # Windows skip and quit handling via msvcrt
    if os.name == "nt":
        try:
            import msvcrt  # type: ignore[attr-defined]
        except ImportError:
            subprocess.run(cmd, check=False)
            return "done"

        proc = subprocess.Popen(cmd)
        print("Keys: n = next track, q = quit")

        try:
            while proc.poll() is None:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b"n", b"N"):
                        proc.terminate()
                        return "next"
                    elif ch in (b"q", b"Q"):
                        proc.terminate()
                        STOP_ALL = True
                        return "quit"
                time.sleep(0.1)
        except KeyboardInterrupt:
            proc.terminate()
            STOP_ALL = True
            return "quit"

        return "done"
    else:
        subprocess.run(cmd, check=False)
        return "done"


def main() -> None:
    """Entry point for the medium wave style player."""
    global STOP_ALL

    print("mw.py - medium wave style player with whistle and high frequency crackle")
    print("---------------------------------------------------------------------")

    ffplay_path = find_ffplay()
    ffmpeg_path = find_ffmpeg()

    folder = choose_folder()
    if not folder:
        print("No folder selected. Exiting.")
        return

    if not os.path.isdir(folder):
        print("Selected path is not a folder.")
        return

    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]
    files.sort()

    if not files:
        print("No supported audio files found in the selected folder.")
        print("Supported extensions:")
        print(", ".join(SUPPORTED_EXTENSIONS))
        return

    print(f"Found audio files in '{folder}':")
    for f in files:
        print("  -", f)

    print("\nStarting playback with medium wave style effect ...\n")
    print("On Windows you can use: n = next track, q = quit, Ctrl+C = stop script.\n")

    for filename in files:
        if STOP_ALL:
            break

        full_path = os.path.join(folder, filename)
        print(f"\nPlaying: {filename}")

        try:
            tmp_wav = mix_to_temp_wav(ffmpeg_path, full_path)
        except Exception:
            print("Skipping this file due to an error while creating the mixed file.")
            continue

        tmp_dir = os.path.dirname(tmp_wav)

        try:
            result = play_wav_with_ffplay(ffplay_path, tmp_wav)
        finally:
            # Clean up the whole temp directory
            try:
                if os.path.isdir(tmp_dir):
                    shutil.rmtree(tmp_dir)
            except OSError:
                pass

        if result == "quit":
            break

    print("\nDone. All files have been processed and played, unless errors occurred.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
