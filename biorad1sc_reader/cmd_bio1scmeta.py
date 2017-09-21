#!/usr/bin/env python3

"""
Command-line utility to report all metadata contained in a Bio-Rad *.1sc file
"""

import sys
import os.path
import argparse
import biorad1sc_reader


def process_command_line(argv):
    """
    Return args struct
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    #script_name = argv[0]
    argv = argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(
            description="Print all metadata contained in 1sc file(s)."
            )

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument('src_1sc_file', nargs='+',
            help="Source 1sc file."
            )

    # switches/options:
    parser.add_argument(
        '-o', '--output_filename', action='store',
        help='Name of output text file. (Defaults to stdout')

    #(settings, args) = parser.parse_args(argv)
    args = parser.parse_args(argv)

    return args


def print_raw_data(data_raw, tab, file):
    print(tab + " data_raw: " + repr(data_raw), file=file)


def recurse_report(coll_item, tablevel, file):
    tab = " "*4*tablevel
    for region in coll_item:
        print(tab + "Region: %s (%s)"%(region, coll_item[region]['type']),
                file=file)
        data_raw = coll_item[region]['raw']
        data_proc = coll_item[region]['proc']
        data_interp = coll_item[region]['interp']
        print(tab + " type_num: " + repr(coll_item[region]['type_num']),
                file=file)
        if data_proc is not None:
            print(tab + " data_proc: " + repr(data_proc), file=file)
        if type(data_interp) is dict:
            recurse_report(data_interp, tablevel+1, file)
        elif data_interp is not None:
            print(tab + " data_interp: " + repr(data_interp), file=file)
        else:
            pass
        if data_proc is None and data_interp is None:
            print_raw_data(data_raw, tab, file=file)


def main(argv=None):
    args = process_command_line(argv)

    if args.output_filename and len(args.src_1sc_file)>1:
        print("Sorry, you cannot specify an output filename with more than " \
                "one input files.")
        return 1
 
    for srcfilename in args.src_1sc_file:
        print(srcfilename, file=sys.stderr)
        if args.output_filename:
            try:
                outfilename = args.output_filename
                out_fh = open(outfilename, 'w')
            except:
                print("Can't write to " + outfilename, file=sys.stderr)
                return 1
        else:
            outfilename = "stdout"
            out_fh = sys.stdout

        print("    -> "+outfilename, file=sys.stderr)
        # open reader instance and read in file
        bio1sc_reader = biorad1sc_reader.Reader(srcfilename)

        file_metadata = bio1sc_reader.get_metadata()
        for collection in file_metadata:
            print("\nCollection: %s"%collection, file=out_fh)
            coll = file_metadata[collection]
            for item in coll:
                print(" "*4 + "Item: %s"%item, file=out_fh)
                coll_item = coll[item]
                recurse_report(coll_item, 2, out_fh)

        out_fh.close()

    return 0


def entry_point():
    """
    intended to be called as a command from entry_points in setup.py
    """
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        # exit error code for Ctrl-C
        status = 130

    return status


if __name__ == "__main__":
    status = entry_point()
    sys.exit(status)
