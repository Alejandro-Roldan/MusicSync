#!/usr/bin/env python3

import os

from mutagen.flac import FLAC
from mutagen.flac import Picture as FlacPicture
from mutagen.id3 import APIC, ID3

IMG_EXTS = ("jpg", "jpeg", "png")


def change_img(item, img_path):
    """
    Calls the procedure to only change the image metadata.
    Loads the new image and then iterates over each item setting
    the picture.
    """
    if img_path.lower().endswith(IMG_EXTS) and os.path.exists(img_path):
        # Load the item metadata and set the new picture.
        if item.endswith("flac"):
            # Load the new image
            img = gen_flac_picture(img_path)

            meta_audio = FLAC(item)
            apply_img_changes_flac(meta_audio, img)

        elif item.endswith("mp3"):
            # Load the new image
            img = gen_mp3_picture(img_path)

            meta_audio = ID3(item)
            apply_img_changes_mp3(meta_audio, img)


def gen_flac_picture(*args, **kwargs):
    """
    Creates a mutagen.flac.Picture object, sets its mimetype, its
    type and its description. Then loads the selected img and returns
    the Picture object.
    """
    # Set the corresponding mime type
    if img_path.endswith("png"):
        mime_type = "image/png"
    else:
        mime_type = "image/jpg"

    # Open bytes like object for the image
    albumart = open(img_path, "rb").read()

    # create img object for flacs and set its properties
    img = FlacPicture()
    # type 3 is for cover image
    img.type = 3
    # Set the corresponding mime type
    img.mime = mime_type
    # Set description
    img.desc = "front cover"
    img.data = albumart

    return img


def gen_mp3_picture(img_path, *args, **kwargs):
    """
    Creates a mutagen APIC object, sets its mimetype, its
    type and its description. Then loads the selected img and returns
    the Picture object.
    """
    # Set the corresponding mime type
    if img_path.endswith("png"):
        mime_type = "image/png"
    else:
        mime_type = "image/jpg"

    # Open bytes like object for the image
    albumart = open(img_path, "rb").read()

    # Create Image object for mp3s and set its properties
    apic = APIC(
        encoding=3, mime=mime_type, type=3, desc="front cover", data=albumart
    )

    return apic


def apply_img_changes_flac(meta_audio, img=None, *args, **kwargs):
    """Changes the image of a flac audio file"""
    if img:
        meta_audio.clear_pictures()  # clear other images
        meta_audio.add_picture(img)  # set new image
        meta_audio.save()


def apply_img_changes_mp3(meta_audio, apic=None, *args, **kwargs):
    """Changes the image of a mp3 audio file"""
    if apic:
        for tag in meta_audio:
            if "APIC" in tag:
                meta_audio.delall(tag)
                break
        meta_audio["APIC"] = apic

        meta_audio.save()


if __name__ == "__main__":
    import sys

    SONG_PATH = sys.argv[1]
    IMG_PATH = sys.argv[2].replace("\n", "")

    if SONG_PATH and IMG_PATH:
        change_img(SONG_PATH, IMG_PATH)
    else:
        print("No song or no img")
