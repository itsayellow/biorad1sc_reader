#!/usr/bin/env python3

"""
Command-line utility to report all metadata contained in a Bio-Rad *.1sc file
"""

import sys
import pprint
import os.path
import argparse
import biorad1sc_reader


# Verbosity:
#   0: as compact representation of metadata as possible, null references
#       are omitted
#   1: Some more details.
#       No full data structure from biorad1sc_reader
#   2: Every detail about metadata, even the pretty-printed full data structure
#       from biorad1sc_reader


def get_cmdline_args():
    """
    Return args struct
    """
    # initialize the parser object:
    parser = argparse.ArgumentParser(
        description="Print all metadata contained in 1sc file(s)."
    )

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument("src_1sc_file", nargs="+", help="Source 1sc file.")

    # switches/options:
    parser.add_argument(
        "-v",
        "--verbosity",
        action="store",
        default=0,
        type=int,
        help="Verbosity of report, number, 0, 1, or 2 (default 0).",
    )
    parser.add_argument(
        "-o",
        "--output_filename",
        action="store",
        help="Name of output text file. (Defaults to <filename>_meta.txt"
        " in same directory as source file.",
    )

    args = parser.parse_args()

    return args


def print_raw_data(data_raw, tab, label_len, file):
    """
    Print series of bytes compactly, keeping starting tab for
    possible additional lines
    """
    same_line_chars_avail = 80 - len(tab) - label_len
    if len(data_raw) * 5 < same_line_chars_avail:
        data_str = ["0x{0:02x}".format(byte) for byte in data_raw]
        data_str = " ".join(data_str).rstrip()
        print(data_str, file=file)
    else:
        own_line_chars_avail = 80 - len(tab) - 2
        bytes_per_line = own_line_chars_avail // 5
        bytes_per_line = bytes_per_line // 4 * 4
        print("", file=file)
        for i in range(0, len(data_raw), bytes_per_line):
            data_str = [
                "0x{0:02x}".format(byte) for byte in data_raw[i : i + bytes_per_line]
            ]
            data_str = " ".join(data_str).rstrip()
            print(tab + "  " + data_str, file=file)


def recurse_report(coll_item, tablevel, file, verbosity):
    """
    Recurse into the hierarchy of a Collection Item, reporting data.
    """
    tab = " " * 4 * tablevel

    def sort_by_iter_index(reg):
        return 1e3 * reg["key_iter"] + reg["region_idx"]

    for region in sorted(coll_item, key=sort_by_iter_index):
        data_proc = region["data"]["proc"]
        data_interp = region["data"]["interp"]
        dtype_str = "%d" % (region["dtype_num"])
        if region["dtype"] is not None:
            dtype_str += " (%s)" % (region["dtype"])

        if verbosity == 0:
            if data_interp is not None:
                print(tab + "%s: " % (region["label"]), end="", file=file)
                if isinstance(data_interp, dict):
                    print("", file=file)
                    # reference to another data structure, recurse
                    recurse_report(data_interp["data"], tablevel + 1, file, verbosity)
                else:
                    print("%s" % (repr(data_interp)), file=file)
            elif data_interp is None and region["dtype_num"] in [15, 17]:
                # data_interp is None with Reference type, means missing
                #   reference, skip
                pass
            elif data_proc is not None:
                print(tab + "%s: " % (region["label"]), end="", file=file)
                print("%s" % (repr(data_proc)), file=file)
            else:
                print(tab + "%s: " % (region["label"]), end="", file=file)
                print_raw_data(
                    region["data"]["raw"], tab, 2 + len(region["label"]), file=file
                )
        elif verbosity == 1:
            print(tab + "Region: %s" % (region["label"]), file=file)
            print(tab + " Data Type   : %s" % (dtype_str), file=file)
            if data_proc is None and data_interp is None:
                print(tab + " Data (raw)  : ", end="", file=file)
                print_raw_data(
                    region["data"]["raw"], tab, len(" Data (raw) : "), file=file
                )
            if data_proc is not None:
                print(tab + " Data        : " + repr(data_proc), file=file)
            if isinstance(data_interp, dict):
                print(
                    tab
                    + " Data (intrp): (Reference, Field Type "
                    + "%d)" % (data_interp["type"]),
                    file=file,
                )
                # reference to another data structure, recurse
                recurse_report(data_interp["data"], tablevel + 1, file, verbosity)
            elif data_interp is not None:
                print(tab + " Data (intrp): " + repr(data_interp), file=file)
        elif verbosity == 2:
            print(tab + "Region: %s" % (region["label"]), file=file)
            print(tab + " Data Type   : %s" % (dtype_str), file=file)
            print(tab + " Region Index: %d" % (region["region_idx"]), file=file)
            print(tab + " Word Size   : %d" % (region["word_size"]), file=file)
            print(tab + " Num. Words  : %d" % (region["num_words"]), file=file)
            print(tab + " Data (raw)  : ", end="", file=file)
            print_raw_data(region["data"]["raw"], tab, len(" Data raw   : "), file=file)
            if data_proc is not None:
                print(tab + " Data        : " + repr(data_proc), file=file)

            if isinstance(data_interp, dict):
                print(
                    tab
                    + " Data (intrp): (Reference, Field Type "
                    + "%d)" % (data_interp["type"]),
                    file=file,
                )
                # reference to another data structure, recurse
                recurse_report(data_interp["data"], tablevel + 1, file, verbosity)
            elif data_interp is not None:
                print(tab + " Data (intrp): " + repr(data_interp), file=file)


def report(file_metadata, out_fh, verbosity):
    """
    Report data contained in file_metadata Collections
    """
    if verbosity == 2:
        # print out full data structure if verbosity == 2
        pp = pprint.PrettyPrinter(indent=4, width=100, stream=out_fh)
        pp.pprint(file_metadata)

    for collection in file_metadata:
        if verbosity == 0:
            print("\n%s" % collection["label"], file=out_fh)
        elif verbosity == 1:
            print("\nCollection: %s" % collection["label"], file=out_fh)
        elif verbosity == 2:
            print("\nCollection: %s" % collection["label"], file=out_fh)

        coll = collection["data"]

        for item in sorted(coll):
            if verbosity == 0:
                print(" " * 4 + "%s" % item["label"], file=out_fh)
            elif verbosity == 1:
                print(" " * 4 + "Item: %s" % item["label"], file=out_fh)
                print(" " * 4 + " Field Type: %s" % item["type"], file=out_fh)
                print(" " * 4 + " Field ID: %s" % item["id"], file=out_fh)
            elif verbosity == 2:
                print(" " * 4 + "Item: %s" % item["label"], file=out_fh)
                print(" " * 4 + " Field Type: %s" % item["type"], file=out_fh)
                print(" " * 4 + " Field ID: %s" % item["id"], file=out_fh)

            coll_item = item["data"]
            recurse_report(coll_item, 2, out_fh, verbosity)

    out_fh.close()


def main():
    """
    Main command top-level function.
    """
    returnval = 0
    args = get_cmdline_args()

    if args.verbosity not in [0, 1, 2]:
        print(
            "Option -v or --verbosity must have an argument of 0, 1, or 2.",
            file=sys.stderr,
        )
        return 1

    if args.output_filename and len(args.src_1sc_file) > 1:
        print(
            "Sorry, you cannot specify an output filename with more than "
            "one input files.",
            file=sys.stderr,
        )
        return 1

    for srcfilename in args.src_1sc_file:
        print(srcfilename, file=sys.stderr)
        if args.output_filename:
            outfilename = args.output_filename
        else:
            (rootfile, _) = os.path.splitext(srcfilename)
            outfilename = rootfile + "_meta.txt"

        try:
            out_fh = open(outfilename, "w")
        except OSError:
            print("ERROR: Can't write to " + outfilename, file=sys.stderr)
            # don't stop because of one file, keep trying to process others
            returnval = 1
            continue

        print("    -> " + outfilename, file=sys.stderr)
        # open reader instance and read in file
        bio1sc_reader = biorad1sc_reader.Reader(srcfilename)

        file_metadata = bio1sc_reader.get_metadata()

        # DEBUG DELETEME
        # file_metadata_compact = bio1sc_reader.get_metadata_compact()
        # pp = pprint.PrettyPrinter(indent=4, width=100, stream=out_fh)
        # pp.pprint(file_metadata_compact)

        report(file_metadata, out_fh, args.verbosity)

    return returnval


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
