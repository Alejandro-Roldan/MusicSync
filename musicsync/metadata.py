#!/usr/bin/env python3

from mutagen import MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3


def change_metadata(in_item, out_item) -> bool:
    try:
        in_meta = load_metadata(in_item)
        out_meta = load_metadata(out_item)

        for key, value in in_meta.items():
            out_meta[key] = value

        out_meta.save()
    except MutagenError:
        return False

    return True


def load_metadata(file):
    if file.endswith("flac"):
        meta_audio = FLAC(file)

    elif file.endswith("mp3"):
        meta_audio = MP3(file, ID3=EasyID3)

    return meta_audio


if __name__ == "__main__":
    import sys

    INPUT_PATH = sys.argv[1]
    OUTPUT_PATH = sys.argv[2].replace("\n", "")

    if INPUT_PATH and OUTPUT_PATH:
        change_metadata(INPUT_PATH, OUTPUT_PATH)
    else:
        print("No input or no output")
