#!/usr/bin/env python3

"""
Command-line utility to save image data from Bio-Rad *.1sc file to
16-bit TIFF file.
"""

import sys
import os.path
import argparse
import biorad1sc_reader


def get_cmdline_args():
    """
    Return parser for command-line arguments, options
    """
    # initialize the parser object:
    parser = argparse.ArgumentParser(
        description="Convert input 1sc file(s) to TIFF image(s)."
    )

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument("src_1sc_file", nargs="+", help="Source 1sc file.")

    # switches/options:
    parser.add_argument(
        "-s",
        "--scale",
        action="store_true",
        help="Scale brightness of output image to maximize dynamic range "
        "between darkest and lightest pixels in input file.",
    )
    parser.add_argument(
        "-i", "--invert", action="store_true", help="Invert brightness scale of image."
    )
    parser.add_argument(
        "-o",
        "--output_filename",
        action="store",
        help="Name of output image. (Defaults to <input_image>.tif)"
        " in same directory as source file.",
    )

    args = parser.parse_args()

    return args


def main():
    """
    Top-level of program
    """
    args = get_cmdline_args()

    if args.output_filename and len(args.src_1sc_file) > 1:
        print(
            "Sorry, you cannot specify an output filename with more than "
            "one input files."
        )
        return 1

    for srcfilename in args.src_1sc_file:
        print(srcfilename, file=sys.stderr)
        if args.output_filename:
            outfilename = args.output_filename
        else:
            (rootfile, _) = os.path.splitext(srcfilename)
            outfilename = rootfile + ".tif"

        print("    -> " + outfilename, file=sys.stderr)
        # open reader instance and read in file
        bio1sc_reader = biorad1sc_reader.Reader(srcfilename)

        if args.scale:
            bio1sc_reader.save_img_as_tiff_sc(outfilename, invert=args.invert)
        else:
            bio1sc_reader.save_img_as_tiff(outfilename, invert=args.invert)

    return 0


def entry_point():
    """
    intended to be called as a command from entry_points in setup.py
    """
    try:
        status = main()
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        # exit error code for Ctrl-C
        status = 130

    return status


if __name__ == "__main__":
    exit_status = entry_point()
    sys.exit(exit_status)
