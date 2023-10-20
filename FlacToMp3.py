#!/bin/python

import os
import sys
import subprocess
import re

sys.path.append(
    "/home/leptope/Programs/Python/ScandirRecursive/ScandirRecursiveV03.00"
)
import scandirrecursive


# POS_CHECKER_RE = re.compile(r".+Music/(.+?\/\d{2})\s-")
# FLAC_PATH = "/home/leptope/Music"
FLAC_PATH = "/home/Saturn/music_test/flac"
# MP3_PATH = "/home/Mars/Music"
MP3_PATH = "/home/Saturn/music_test/mp3"
POS_CHECKER_RE = re.compile(rf"(?>{FLAC_PATH}|{MP3_PATH})/?(.+?\/\d{{2}})\s-")


def jupiter_to_mars_path(path):
    # path = path.replace("/Jupiter/", "/Mars/").replace("/leptope/", "/Mars/")
    path = path.replace(FLAC_PATH, MP3_PATH)

    if path.endswith(".flac"):
        return path.replace(".flac", ".mp3")
    elif path.endswith(".mp3"):
        return path.replace(" [mp3]", "")


def alph_pos_checker(str1, str2):
    """
    if str1 is alphabetically further than str2:
    returns str1
    if str2 is alphabetically further than str1:
    returns str2
    """
    # This method works relying in how I order my music
    list_ = [
        (str1, POS_CHECKER_RE.match(str1)[1]),
        (str2, POS_CHECKER_RE.match(str2)[1]),
    ]
    list_.sort(key=lambda a: a[1])
    return list_[0][0]

    # But i wonder if i could make something simpler
    # list_ = [str1, str2]
    # list_.sort()
    # return list_[0]


def deleter(list_):
    for item in list_:
        # Security check to not delete items that arent in the destination HDD
        if MP3_PATH not in item.path:
            continue


def main():
    """
    If file exists in flac but not in mp3: convert
    If file exists in both: compare mtime and
        if flac is newer: convert
        if mp3 is newer or same: pass
    If file exists in mp3 but not in flac: delete
    """

    flac_files = scandirrecursive.scandir_recursive_sorted(
        FLAC_PATH,
        ext_tuple=("flac", "mp3"),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )
    print("Ended flac_files list creation")

    mp3_files = scandirrecursive.scandir_recursive_sorted(
        MP3_PATH,
        ext_tuple=("mp3"),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )
    print("Ended mp3_files list creation")

    convert_list = []
    delete_list = []
    # loop through mp3 file list and
    for mp3_file in mp3_files:
        for i, flac_file in enumerate(flac_files):
            # Check if file exists in flac list both as flac or mp3
            if mp3_file.path == jupiter_to_mars_path(flac_file.path):
                if mp3_file.stat().st_mtime < flac_file.stat().st_mtime:
                    convert_list.append(flac_file.path)

                # Continue with next mp3 file
                break

            else:
                # Check if alphabetical position has been surpassed to stop looping
                if mp3_file.path == alph_pos_checker(
                    mp3_file.path, flac_file.path
                ):
                    delete_list.append(mp3_file.path)
                    # To prevent removing the next item
                    i -= 1
                    break

                convert_list.append(flac_file.path)

        # Remove from flac list to not reiterate over them
        del flac_files[0 : i + 1]

    # When finished mp3 files loop:
    # add the rest of flac files to the convert list
    convert_list = convert_list + flac_files

    print(convert_list)
    # with open("convert.txt", "w") as f:
    #     f.writelines(line + "\n" for line in convert_list)
    print(delete_list)
    # with open("delete.txt", "w") as f:
    #     f.writelines(line + "\n" for line in delete_list)

    # break into 4 lists for multiproccessing
    # convert_list_chunked = [[convert_list[i]],[convert_list[i+1]],[convert_list[i+2]],[convert_list[i+3]] for i in range(0, len(convert_list), 4)]

    # os.system(f'ffmpeg -hide_banner -i "{filename}" --map 0:a -b:a 320k "{out_file}"')
    # subprocess.run(["ls", "-l"])


if __name__ == "__main__":
    main()
    print("end")
