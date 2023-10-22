#!/bin/python

import os
import sys
import shutil
import subprocess
import re
from concurrent.futures import ProcessPoolExecutor
import logging

import ImageCover


sys.path.append(
    "/home/leptope/Programs/Python/ScandirRecursive/ScandirRecursiveV03.00"
)
import scandirrecursive


# FLAC_PATH = "/home/leptope/Music"
FLAC_PATH = "/home/Saturn/music_test/flac"
# MP3_PATH = "/home/Mars/Music"
MP3_PATH = "/home/Saturn/music_test/mp3"
POS_CHECKER_RE = re.compile(rf"(?>{FLAC_PATH}|{MP3_PATH})/?(.+?/\d{{2}})\s-")
DISC_CHECKER_RE = re.compile(rf"({FLAC_PATH}.+/)(?>Disc\s\d+.*)")


def jupiter_to_mars_path(path):
    path = path.replace(FLAC_PATH, MP3_PATH)

    if path.endswith(".flac"):
        return path.replace(".flac", ".mp3")
    elif path.endswith(".mp3"):
        # Specific to how I order my music
        return path.replace(" [mp3]", "")


def compare_lists(list1, list2):
    # This potentially can be done in multiproccess if the looping through
    # flac files didnt remove files and access was done as a binary tree
    convert_list = []
    delete_list = []
    # In case some of the lists has no items
    i = -1
    j = -1
    # Loop through mp3 file list and
    for i, file2 in enumerate(list2):
        for j, file1 in enumerate(list1):
            # Check if file exists in flac list both as flac or mp3
            if file2.path == jupiter_to_mars_path(file1.path):
                if file2.stat().st_mtime < file1.stat().st_mtime:
                    convert_list.append(file1.path)

                # Continue with next mp3 file
                break

            else:
                # Check if alphabetical position has been surpassed to stop looping
                if file2.path == alph_pos_checker(file2.path, file1.path):
                    delete_list.append(file2.path)
                    # To prevent removing the next item
                    j -= 1
                    break

                convert_list.append(file1.path)

        # Remove from flac list to not reiterate over them
        del list1[0 : j + 1]
        # When flac files run out before mp3 files means we would have to
        # delete the remaining of mp3 files
        if len(list1) == 0:
            break
    # Remove mp3 files from list because if there are were to still be any
    # file it should be removed to
    del list2[0 : i + 1]

    # When finished mp3 files loop:
    # add the rest of flac files to the convert list
    convert_list = convert_list + [file1.path for file1 in list1]
    # add the rest of mp3 files to the remove list
    delete_list = delete_list + [file2.path for file2 in list2]
    logging.info("Ended convert list and delete list creation")

    return convert_list, delete_list


def alph_pos_checker(str1, str2):
    """
    if str1 is alphabetically further than str2:
    returns str1
    if str2 is alphabetically further than str1:
    returns str2
    """
    # Specific to how I order my music
    try:
        list_ = [
            (str1, POS_CHECKER_RE.match(str1)[1]),
            (str2, POS_CHECKER_RE.match(str2)[1]),
        ]
        list_.sort(key=lambda a: a[1])

        return list_[0][0]
    # The strs dont match with the specific way I order music
    except TypeError:
        return str2

    # Previous method works relying in how I order my music
    # But i wonder if i could make something simpler
    # list_ = [str1, str2]
    # list_.sort()
    # return list_[0]


def synchronize(convert_list, delete_list):
    total_len = len(convert_list)
    if total_len:
        logging.info("Start conversion proccess")
        with ProcessPoolExecutor() as executor:
            for i, result in enumerate(
                executor.map(_synchronize, convert_list)
            ):
                progress = f"[{i+1}/{total_len}({(i+1)/total_len:.0%})] "
                result_code, result_msg = result
                if result_code == 0:
                    logging.info(progress + result_msg)
                elif result_code == 127:
                    logging.warning(progress + result_msg)
                else:
                    logging.error(result_msg)
        logging.info("Ended conversion proccess")
    else:
        logging.info(f"No files to convert")

    if len(delete_list):
        logging.info("Start file deletion")
        deleter(delete_list)
        logging.info("Ended file deletion")
    else:
        logging.info(f"No files to Delete")


def deleter(list_):
    for item in list_:
        # Security check to not delete items that arent in the destination
        # directories
        if MP3_PATH in item:
            try:
                # Remove the file
                logging.info(f'Deleting "{item}"')
                os.remove(item)
                # Try to remove the empty directories that might been left by
                # the file removal
                os.removedirs(os.path.dirname(item))
            # Handle FileNotFoundError from file removal and OSError from
            # directory not empty
            except (FileNotFoundError, OSError):
                pass


def _synchronize(item):
    result_msg = "[ERROR] No return status defined"
    result_code = 5

    out_item = jupiter_to_mars_path(item)

    # Create directory hirearchy if it doesnt exists
    os.makedirs(os.path.dirname(out_item), exist_ok=True)

    if not item.endswith("mp3"):
        result_code, result_msg = convert(item, out_item)
    else:
        shutil.copy2(item, out_item)
        result_msg = f'Copied "{item}" to "{out_item}"'
        result_code = 0

    return result_code, result_msg


def convert(item, out_item):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            item,
            "-map",
            "0:a",
            "-b:a",
            "320k",
            out_item,
        ],
        # stdout=subprocess.DEVNULL,
        # stderr=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        # capture_output=True,
        text=True,
    )
    # print(result.stderr)
    if result.returncode != 0:
        result_msg = f'[ERROR] Couldn\'t convert "{item}" to "{out_item}"'
        result_code = 1
    else:
        img = get_img_file(item)
        if img:
            ImageCover.change_img(out_item, img.path)
            result_msg = (
                f'Converted "{item}" to "{out_item}" with image "{img.name}"'
            )
            result_code = 0
        else:
            result_msg = (
                f'Converted "{item}" to "{out_item}" with\n'
                f'[WARNING] Couldn\'t add "{img.name}" to "{out_item}"'
            )
            result_code = 127

    return result_code, result_msg


def get_img_file(flac_path):
    search_path = os.path.dirname(flac_path)
    # Specific to how I order my music
    if "/Disc " in search_path:
        # search_path = DISC_CHECKER_RE.match(search_path)[1]
        search_path = os.path.dirname(search_path)

    img_files = scandirrecursive.scandir_recursive_sorted(
        search_path,
        ext_tuple=ImageCover.IMG_EXTS,
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
        max_find_items=1,
    )
    # print(img_files)
    return img_files[0] if img_files else None


def main(info_level=logging.INFO):
    """
    If file exists in flac but not in mp3: convert
    If file exists in both: compare mtime and
        if flac is newer: convert
        if mp3 is newer or same: pass
    If file exists in mp3 but not in flac: delete
    """
    logging.basicConfig(
        format="[%(asctime)s][%(levelname)s] - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        level=info_level,
    )

    flac_files = scandirrecursive.scandir_recursive_sorted(
        FLAC_PATH,
        ext_tuple=("flac", "mp3"),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )
    logging.info("Ended flac_files list creation")

    mp3_files = scandirrecursive.scandir_recursive_sorted(
        MP3_PATH,
        ext_tuple=("mp3",),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )
    logging.info("Ended mp3_files list creation")

    convert_list, delete_list = compare_lists(flac_files, mp3_files)
    logging.debug(f"Convert List:\n{convert_list}")
    logging.debug(f"Delete List:\n{delete_list}")

    synchronize(convert_list, delete_list)


if __name__ == "__main__":
    main()
    print("end")
