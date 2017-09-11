#!/usr/bin/env python3
#
# Bare bones python template for parsing command-line arguments

import sys
import os.path
import argparse
import biorad1sc_reader

def bio1sc2tiff_process_command_line(argv):
    """
    Return args struct
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    #script_name = argv[0]
    argv = argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(
            description="Convert input 1sc file to TIFF image.")

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument('src_1sc_file', nargs='+',
            help="Source 1sc file."
            )

    # switches/options:
    parser.add_argument(
        '-s', '--scale', action='store_true',
        help='Scale brightness of output image to maximize dynamic range ' \
                'between darkest and lightest pixels in input file.')
    parser.add_argument(
        '-i', '--invert', action='store_true',
        help='Invert brightness scale of image.')
    parser.add_argument(
        '-o', '--output_filename', action='store',
        help='Name of output image. (Defaults to <input_image>.tif)')

    #(settings, args) = parser.parse_args(argv)
    args = parser.parse_args(argv)

    return args

def bio1sc2tiff_main(argv=None):
    args = bio1sc2tiff_process_command_line(argv)

    if args.output_filename and len(args.src_1sc_file)>1:
        print("Sorry, you cannot specify an output filename with more than " \
                "one input files.")
        return 1
 
    for srcfilename in args.src_1sc_file:
        print(srcfilename)
        if args.output_filename:
            outfilename = args.output_filename
        else:
            (rootfile,_)=os.path.splitext(srcfilename)
            outfilename = rootfile+".tif"

        print("    -> "+outfilename)
        # open reader instance and read in file
        bio1sc_reader = biorad1sc_reader.Reader(srcfilename )

        if args.scale:
            bio1sc_reader.save_img_as_tiff_sc(
                    outfilename,
                    invert=args.invert
                    )
        else:
            bio1sc_reader.save_img_as_tiff(
                    outfilename,
                    invert=args.invert
                    )

    return 0

def bio1sc2tiff():
    """
    intended to be called as a command from entry_points in setup.py
    """
    try:
        status = bio1sc2tiff_main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        # exit error code for Ctrl-C
        status = 130

    return status

if __name__ == "__main__":
    status = bio1sc2tiff()

    sys.exit(status)
