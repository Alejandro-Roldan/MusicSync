#!/usr/bin/env python3

import logging
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

from scandirrecursive.scandirrecursive import scandir_recursive

from . import imagecover


def diff_dirs(src_iterator, dest_iterator):
    """
    Compares src_iterator to dest_iterator and extracts the needed actions for
    every file.
    * Convert/Copy if file only exists in SRC or SRC is newer than DEST
    * Delete if file only exists in DEST

    Returns:
    * convert_list
    * copy_list
    * delete_list
    """

    def convert_or_copy(item):
        if item.endswith(".mp3"):
            copy_list.append(item)
        else:
            convert_list.append(item)

    convert_list = []
    copy_list = []

    # Have DEST files paths in a set() type
    # (sets have very quick access by value)
    dest_set = {dest_file.path for dest_file in dest_iterator}
    # Loop through SRC files
    for src_file in src_iterator:
        src_dest_path = src_to_dest_path(src_file.path)

        # When SRC file exists in DEST files
        if src_dest_path in dest_set:
            # Remove from DEST set
            dest_set.remove(src_dest_path)

            # And if SRC is newer: convert/copy
            if int(os.stat(src_dest_path).st_mtime) < int(
                os.stat(src_file.path).st_mtime
            ):
                convert_or_copy(src_file.path)

        # When SRC file doesnt exist in DEST: convert/copy
        else:
            convert_or_copy(src_file.path)

    # The files that are left in DEST set are the ones to delete

    # Sort lists not needed, progress is kept through numbers; but it doesnt
    # slow execution at all
    convert_list.sort(key=str.casefold)
    copy_list.sort(key=str.casefold)
    delete_list = sorted(dest_set, key=str.casefold)

    return convert_list, copy_list, delete_list


def src_to_dest_path(path):
    """Converts SRC path str to DEST path str"""
    path = path.replace(SRC, DEST)

    if path.endswith(".flac"):
        return path.replace(".flac", ".mp3")
    elif path.endswith(".mp3"):
        # Specific to how I order my music
        return path.replace(" [mp3]", "")


def progress_gen(i, len_):
    """Progress str generator

    [current_item/total_items(%)]
    """
    return f"[{i+1}/{len_}({(i+1)/len_:.0%})] "


def deleter(list_):
    list_len = len(list_)
    for i, item in enumerate(list_):
        # Security check to not delete items that arent in the destination
        # directories
        if DEST in item:
            try:
                os.remove(item)
                # Try to remove the empty directories that might been left by
                # the file removal
                os.removedirs(os.path.dirname(item))

                # Logging
                progress = progress_gen(i, list_len)
                # Remove the file
                logging.info(f"DEL{progress} {item}")

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
            # Copy file with metadata included
            shutil.copy2(item, out_item)

            # Logging
            progress = progress_gen(i, list_len)
            logging.info(f"COP{progress} {item} -> {out_item}")

        except shutil.SameFileError:
            logging.error(
                "Couldn't copy file: SRC and DEST files are the same"
            )
        except PermissionError:
            logging.error("Couldn't copy file: Permission Denied")


def converter(list_, cores):
    """CPU heavy execution that can be done in multiproccessing"""
    convert_len = len(list_)
    # Multicore execution
    with ProcessPoolExecutor(max_workers=cores) as executor:
        # Returns result status of each item seperate to handle printing and
        # errors
        for i, result in enumerate(executor.map(convert, list_)):
            # Logging
            progress = progress_gen(i, convert_len)
            # Break into vars the func return
            result_code, result_msg = result
            # Handle statuses for logging
            if result_code == 0 or result_code == 127:
                logging.info(f"CON{progress} {result_msg}")
            else:
                logging.error(result_msg)


def convert(item):
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
    # files size ~double if converted whith images

    # Handle execution error
    if result.returncode != 0:
        result_msg = f'Couldn\'t convert "{item}" to "{out_item}"'
        result_code = 1
    else:
        img = _get_img_file(item)
        # Try to add image if theres one
        if img:
            imagecover.change_img(out_item, img.path)
            result_msg = f'{item} -> {out_item} with image "{img.name}"'
            result_code = 0
        else:
            result_msg = (
                f"{item} -> {out_item}\n"
                f'Couldn\'t add image to "{out_item}"'
            )
            # Warning state when image fails
            result_code = 127

    return result_code, result_msg


def _get_img_file(flac_path):
    """Find image in item directory"""

    search_path = os.path.dirname(flac_path)
    # Or in the upper directory when... (specific to how I order my music)
    if "/Disc " in search_path:
        search_path = os.path.dirname(search_path)

    img_files = list(
        scandir_recursive(
            search_path,
            ext_tuple=imagecover.IMG_EXTS,
            folders=False,
            files=True,
            hidden=False,
            depth=-1,
            max_find_items=1,
        )
    )
    return img_files[0] if img_files else None


def synchronize(
    src_path,
    dest_path,
    delete_state=2,
    cores=None,
    auto_yes=False,
    verbose_level=logging.INFO,
):
    """
    If file exists in flac but not in mp3: convert
    If file exists in both: compare last_modified_time and
        if flac is newer: convert
        if mp3 is newer or same: pass
    If file exists in mp3 but not in flac: delete
    """
    global SRC, DEST
    SRC = src_path
    DEST = dest_path

    logging.basicConfig(
        format="[%(asctime)s][%(levelname)s] - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        level=verbose_level,
    )

    src_files = scandir_recursive(
        src_path,
        ext_tuple=("flac", "mp3"),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )

    dest_files = scandir_recursive(
        dest_path,
        ext_tuple=("mp3",),
        folders=False,
        files=True,
        hidden=False,
        depth=-1,
    )

    logging.info(
        f'Starting SRC ("{src_path}") and DEST ("{dest_path}") diff creation'
    )
    convert_list, copy_list, delete_list = diff_dirs(src_files, dest_files)
    # Logging diff results
    logging.info(f"Ended directories diff creation")
    logging.info(f"{len(convert_list)} files to convert")
    logging.info(f"{len(copy_list)} files to copy")
    logging.info(f"{len(delete_list)} files to delete")
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

    # Exit when nothing to do
    if not convert_list and not copy_list and not delete_list:
        sys.exit()

    # Procced execution check
    answer = "y" if auto_yes else "n"
    # Repeat if invalid answers
    while answer != "y":
        answer = input("Procced? [Y/n]: ").lower()
        # empty answer = yes
        answer = "y" if answer == "" else answer
        if answer == "n":
            # Abort and exit
            logging.info("Aborting synchronization")
            sys.exit()
        elif answer != "y":
            print("Not a valid answer. Try again")

    # Delete-before
    if delete_list and delete_state == 1:
        logging.info("Start file deletion")
        deleter(delete_list)
        logging.info("Ended file deletion")

    if convert_list:
        logging.info("Start conversion proccess")
        converter(convert_list, cores)
        logging.info("Ended conversion proccess")

    if copy_list:
        logging.info("Start file copy")
        copier(copy_list)
        logging.info("Ended file copy")

    # Delete-after
    if delete_list and delete_state == 2:
        logging.info("Start file deletion")
        deleter(delete_list)
        logging.info("Ended file deletion")


def _cli_run():
    import argparse

    # Call the argument parse object
    parser = argparse.ArgumentParser()
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
        "-y",
        "--auto-yes",
        help=(
            "Don't ask for confirmation before procceding with synchronization"
        ),
        action="store_true",
    )
    parser.add_argument(
        "--no-delete",
        help="Don't delete files",
        action="store_true",
    )
    parser.add_argument(
        "--delete-before",
        help="Delete files before Copy/Convert",
        action="store_true",
    )
    parser.add_argument("SRC", type=str)
    parser.add_argument("DEST", type=str)

    args = parser.parse_args()

    delete_before = 1 if args.delete_before else 2
    no_delete = 0 if args.no_delete else 1
    # DELETE state will be 0 when no delete, 1 when before and 2 after
    delete_state = no_delete * delete_before

    verbose_level = getattr(logging, args.verbose_level.upper(), None)
    if not isinstance(verbose_level, int):
        raise ValueError("Invalid verbose level: %s" % loglevel)

    synchronize(
        args.SRC,
        args.DEST,
        delete_state=delete_state,
        cores=args.cores,
        auto_yes=args.auto_yes,
        verbose_level=verbose_level,
    )


if __name__ == "__main__":
    _cli_run()
