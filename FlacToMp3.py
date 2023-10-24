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


SRC = "/home/leptope/Music"
DEST = "/home/Mars/Music"
DELETE_BEFORE = 0
DELETE_AFTER = 2
NO_DELETE = 1
LOG_LEVEL = ""
CORES = None


def src_to_dest_path(path):
    path = path.replace(SRC, DEST)

    if path.endswith(".flac"):
        return path.replace(".flac", ".mp3")
    elif path.endswith(".mp3"):
        # Specific to how I order my music
        return path.replace(" [mp3]", "")


def compare_lists(src_list, dest_list):
    """
    Compares src_list to dest_list and extracts the needed actions for
    every file.
    * Convert/Copy if file only exists in SRC or SRC is newer than DEST
    * Delete if file only exists in DEST

    Returns:
    * convert_list
    * copy_list
    * delete_list
    """

    convert_list = []
    copy_list = []
    delete_list = []

    # Generate a dict that has the DEST paths as keys and SRC paths as values
    # from the SRC list
    dict1 = {
        src_to_dest_path(src_file.path): src_file.path for src_file in src_list
    }
    # Generate a dict that has the DEST existing paths as keys and EMPTY as
    # values. From DEST list
    dict2 = {dest_file.path: None for dest_file in dest_list}

    # Join both dicts
    # For the keys that exist in both: keep the values from dict1 (SRC paths)
    joint_dict = dict2 | dict1
    # Sort it (could be skipped since progress is kept through numbers)
    joint_dict = dict(
        sorted(joint_dict.items(), key=lambda entry: entry[0].casefold())
    )

    # Process joint_dict
    for file in joint_dict:
        # When value is EMPTY (file only exists in DEST): delete it
        if not joint_dict[file]:
            delete_list.append(file)
        else:
            # Check which is newer
            try:
                # When SRC is newer
                if int(os.stat(file).st_mtime) < int(
                    os.stat(joint_dict[file]).st_mtime
                ):
                    if joint_dict[file].endswith(".mp3"):
                        copy_list.append(joint_dict[file])
                    else:
                        convert_list.append(joint_dict[file])

            # Handle when file only exists in SRC
            except FileNotFoundError:
                if joint_dict[file].endswith(".mp3"):
                    copy_list.append(joint_dict[file])
                else:
                    convert_list.append(joint_dict[file])

    logging.info("Ended convert list and delete list creation")
    logging.info(f"{len(convert_list)} files to convert")
    logging.info(f"{len(copy_list)} files to copy")
    logging.info(f"{len(delete_list)} files to delete")

    return convert_list, copy_list, delete_list


def progress_gen(i, len_):
    """Progress str generator"""
    return f"[{i+1}/{len_}({(i+1)/len_:.0%})] "


def synchronize(convert_list, copy_list, delete_list):
    if delete_list and DELETE == 1:
        logging.info("Start file deletion")
        deleter(delete_list)
        logging.info("Ended file deletion")

    if convert_list:
        logging.info("Start conversion proccess")
        converter(convert_list)
        logging.info("Ended conversion proccess")

    if copy_list:
        logging.info("Start file copy")
        copier(copy_list)
        logging.info("Ended file copy")

    if delete_list and DELETE == 2:
        logging.info("Start file deletion")
        deleter(delete_list)
        logging.info("Ended file deletion")


def deleter(list_):
    list_len = len(list_)
    for i, item in enumerate(list_):
        # Security check to not delete items that arent in the destination
        # directories
        if DEST in item:
            try:
                progress = progress_gen(i, list_len)
                # Remove the file
                logging.info(f"DEL{progress} {item}")
                os.remove(item)
                # Try to remove the empty directories that might been left by
                # the file removal
                os.removedirs(os.path.dirname(item))
            # Handle FileNotFoundError from file removal and OSError from
            # directory not empty
            except (FileNotFoundError, OSError):
                pass


def copier(list_):
    list_len = len(list_)
    for i, item in enumerate(list_):
        out_item = src_to_dest_path(item)

        # Create directory hirearchy if it doesnt exists
        os.makedirs(os.path.dirname(out_item), exist_ok=True)

        try:
            progress = progress_gen(i, list_len)
            # Copy file with metadata included
            shutil.copy2(item, out_item)
            logging.info(f"COP{progress} {item} -> {out_item}")
        except shutil.SameFileError:
            logging.error(
                "Couldn't copy file: SRC and DEST files are the same"
            )
        except PermissionError:
            logging.error("Couldn't copy file: Permission Denied")


def converter(list_):
    convert_len = len(list_)
    with ProcessPoolExecutor(max_workers=CORES) as executor:
        for i, result in enumerate(executor.map(_convert, list_)):
            progress = progress_gen(i, convert_len)
            # Break into vars the func return
            result_code, result_msg = result
            if result_code == 0 or result_code == 127:
                logging.info(f"CON{progress} {result_msg}")
            else:
                logging.error(result_msg)


def _convert(item):
    result_msg = "No return status defined"
    result_code = 5

    out_item = src_to_dest_path(item)

    # Create directory hirearchy if it doesnt exists
    os.makedirs(os.path.dirname(out_item), exist_ok=True)

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
        stderr=subprocess.PIPE,
        text=True,
    )
    # Convert without image because of ffmpeg bug that sometimes makes the
    # files occupy ~double if converted whit images

    # Handle execution error
    if result.returncode != 0:
        result_msg = f'Couldn\'t convert "{item}" to "{out_item}"'
        result_code = 1
    else:
        img = get_img_file(item)
        # Try to add image if theres one
        if img:
            ImageCover.change_img(out_item, img.path)
            result_msg = f'{item} -> {out_item} with image "{img.name}"'
            result_code = 0
        else:
            result_msg = (
                f"{item} -> {out_item}\n"
                f'Couldn\'t add "{img.name}" to "{out_item}"'
            )
            # Warning state when image fails
            result_code = 127

    return result_code, result_msg


def get_img_file(flac_path):
    search_path = os.path.dirname(flac_path)
    # Specific to how I order my music
    if "/Disc " in search_path:
        search_path = os.path.dirname(search_path)

    img_files = scandirrecursive.scandir_recursive(
        search_path,
        ext_tuple=ImageCover.IMG_EXTS,
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
        max_find_items=1,
    )
    return img_files[0] if img_files else None


def main(verbose_level=logging.INFO):
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
        level=verbose_level,
    )

    flac_files = scandirrecursive.scandir_recursive(
        SRC,
        ext_tuple=("flac", "mp3"),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )
    logging.info("Ended flac_files list creation")

    mp3_files = scandirrecursive.scandir_recursive(
        DEST,
        ext_tuple=("mp3",),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )
    logging.info("Ended mp3_files list creation")

    convert_list, copy_list, delete_list = compare_lists(flac_files, mp3_files)
    logging.debug(f"Convert List:\n{convert_list}")
    logging.debug(f"Copy List:\n{copy_list}")
    logging.debug(f"Delete List:\n{delete_list}")
    if verbose_level <= 10:
        with open("convert_list.log", "w") as f:
            f.write("\n".join(convert_list))
        with open("copy_list.log", "w") as f:
            f.write("\n".join(copy_list))
        with open("delete_list.log", "w") as f:
            f.write("\n".join(delete_list))

    if not DRY:
        synchronize(convert_list, copy_list, delete_list)


if __name__ == "__main__":
    import argparse

    # Call the argument parse object
    parser = argparse.ArgumentParser()
    parser.add_argument("SRC", type=str)
    parser.add_argument("DEST", type=str)
    parser.add_argument(
        "--no-delete",
        help="Don't delete files",
        action="store_true",
    )
    parser.add_argument(
        "--delete-after",
        help="Delete files after Copy/Convert",
        action="store_true",
    )
    parser.add_argument(
        "--delete-before",
        help="Delete files before Copy/Convert",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--cores",
        help="Number of cores to use. Default: max available",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose-level",
        help="Possible levels are:\nDEBUG, INFO, WARNING, ERROR, CRITICAL",
        type=str,
        default="INFO",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        help="Perform a trial run with no changes made",
        action="store_true",
    )

    args = parser.parse_args()

    SRC = args.SRC
    DEST = args.DEST

    DELETE_BEFORE = 1 if args.delete_before else 0
    DELETE_AFTER = 2 if args.delete_after else 0
    NO_DELETE = 0 if args.no_delete else 1
    # DELETE state will be 0 when no delete, 1 when delete before and 2 after
    DELETE = NO_DELETE * (DELETE_BEFORE + DELETE_AFTER)

    DRY = args.dry_run
    CORES = args.cores

    verbose_level = getattr(logging, args.verbose_level.upper(), None)
    if not isinstance(verbose_level, int):
        raise ValueError("Invalid verbose level: %s" % loglevel)

    main(verbose_level)
    print("end")
