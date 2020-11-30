#!/usr/bin/env python3

# testbed to read, parse, report *.1sc files

import os.path
import sys
import argparse
import struct
from terminaltables import AsciiTable
import biorad1sc_reader
from biorad1sc_reader.constants import BLOCK_PTR_TYPES, REGION_DATA_TYPES


# TODO: add assertions, so we can automatically check if our understanding
#       of file structure is correct


MAX_LINE_LEN = 80


def print_raw_data(data_raw, tab, label_len, hex=True, file=sys.stdout):
    line_chars_avail = MAX_LINE_LEN - len(tab) - label_len
    bytes_per_line = line_chars_avail // 5
    bytes_per_line = bytes_per_line // 4 * 4
    bytes_per_line = max(bytes_per_line, 4)
    for i in range(0, len(data_raw), bytes_per_line):
        if hex:
            data_str = [
                "0x{0:02x}".format(byte) for byte in data_raw[i : i + bytes_per_line]
            ]
        else:
            data_str = [
                " {0:3d}".format(byte) for byte in data_raw[i : i + bytes_per_line]
            ]
        data_str = " ".join(data_str).rstrip()
        if i != 0:
            # unless first line print spaces to tab in
            print(tab + " " * label_len, end="", file=file)
        print(data_str, file=file)


def print_list(byte_list, bits=8, address=None, var_tab=False, file=sys.stdout):
    """
    TODO: is this doing proper little-endian?
    """
    hex_digits = int(0.25 * bits)
    # add 3 chars for "0x" and ","
    # number of items in a line
    items = 72 // (hex_digits + 3)
    # round items down to multiple of 4
    items = items // 4 * 4
    pr_str = "{:%dd}," % (hex_digits + 2)
    pr_str_hex = "0x{:0%dx}," % (hex_digits)

    byte_groups = range(0, len(byte_list), items)
    byte_groups = [[x, min([x + items, len(byte_list)])] for x in byte_groups]

    if address is None:
        print("\t[", end="", file=file)
        first_loop = True
        for (i, byte_group) in enumerate(byte_groups):
            if first_loop:
                first_loop = False
            else:
                print("\t ", end="", file=file)

            # print decimal words
            for byte in byte_list[byte_group[0] : byte_group[1]]:
                print(pr_str.format(byte), end="", file=file)
            # print spacer
            print(file=file)
            print("         ", end="", file=file)
            # print hex words
            for byte in byte_list[byte_group[0] : byte_group[1]]:
                print(pr_str_hex.format(byte), end="", file=file)

            if i < len(byte_groups) - 1:
                print(file=file)
        print("]", file=file)
    else:
        first_loop = True
        for (i, byte_group) in enumerate(byte_groups):
            # print address start
            if len(byte_groups) > 1:
                if var_tab is False:
                    print(
                        "    %6d: " % (address + i * items * bits / 8),
                        end="",
                        file=file,
                    )
                else:
                    print(
                        "%s%4d: " % (var_tab, address + i * items * bits / 8),
                        end="",
                        file=file,
                    )
            else:
                if var_tab is False:
                    print("            ", end="", file=file)
                else:
                    print("%s      " % (var_tab), end="", file=file)
            # print decimal words
            for byte in byte_list[byte_group[0] : byte_group[1]]:
                print(pr_str.format(byte), end="", file=file)
            print(file=file)

            # print spacer
            if var_tab is False:
                print("            ", end="", file=file)
            else:
                print("%s      " % (var_tab), end="", file=file)
            # print hex words
            for byte in byte_list[byte_group[0] : byte_group[1]]:
                print(pr_str_hex.format(byte), end="", file=file)
            print(file=file)


def print_list_simple(wordlist, bits=8, hexfmt=False):
    outstr = ""
    # print list of words
    first_time = True
    for myword in wordlist:
        if not first_time:
            outstr = outstr + " "
        else:
            first_time = False

        if bits == 8:
            if hexfmt:
                outstr = outstr + "0x{:02x}".format(myword)
            else:
                outstr = outstr + "%4d" % myword
        if bits == 16:
            if hexfmt:
                outstr = outstr + "0x{:04x}".format(myword)
            else:
                outstr = outstr + "%6d" % myword
        if bits == 32:
            if hexfmt:
                outstr = outstr + "0x{:08x}".format(myword)
            else:
                outstr = outstr + "%10d" % myword

    return outstr


def str_safe_bytes(byte_stream):
    table_from = bytes(range(256))
    table_to = b"\x20" + b"\xff" * 31 + bytes(range(32, 127)) + b"\xff" * 129
    trans_table = byte_stream.maketrans(table_from, table_to)
    safe_byte_stream = byte_stream.translate(trans_table)
    return safe_byte_stream


def unpack_string(byte_stream):
    out_string = byte_stream.decode("utf-8", "replace")
    return out_string


def unpack_uint8(byte_stream):
    num_uint8 = len(byte_stream)
    out_uint8s = struct.unpack("B" * num_uint8, byte_stream)
    return out_uint8s


def unpack_uint16(byte_stream, endian="<"):
    num_uint16 = len(byte_stream) // 2
    out_uint16s = struct.unpack(endian + "H" * num_uint16, byte_stream)
    return out_uint16s


def unpack_uint32(byte_stream, endian="<"):
    num_uint32 = len(byte_stream) // 4
    out_uint32s = struct.unpack(endian + "I" * num_uint32, byte_stream)
    return out_uint32s


def unpack_uint64(byte_stream, endian="<"):
    num_uint64 = len(byte_stream) // 8
    out_uint64s = struct.unpack(endian + "Q" * num_uint64, byte_stream)
    return out_uint64s


def debug_generic(
    byte_stream,
    byte_start,
    note_str,
    format_str,
    var_tab=False,
    quiet=False,
    file=sys.stdout,
):
    bytes_per = struct.calcsize(format_str)
    num_shorts = len(byte_stream) // (bytes_per)
    out_shorts = struct.unpack("<" + format_str * num_shorts, byte_stream)
    byte_idx = byte_start + len(byte_stream)
    if not quiet:
        if var_tab is not False:
            print(
                "%s%d-%d: %s" % (var_tab, byte_start, byte_idx - 1, note_str), file=file
            )
        else:
            print("%6d-%6d: %s" % (byte_start, byte_idx - 1, note_str), file=file)
        print_list(
            out_shorts,
            bits=bytes_per * 8,
            address=byte_start,
            var_tab=var_tab,
            file=file,
        )
    return (out_shorts, byte_idx)


def debug_int32s(byte_stream, byte_start, note_str, quiet=False, file=sys.stdout):
    (out_ints, byte_idx) = debug_generic(
        byte_stream, byte_start, note_str, "i", quiet=quiet, file=file
    )
    return (out_ints, byte_idx)


def debug_uint32s(byte_stream, byte_start, note_str, quiet=False, file=sys.stdout):
    (out_uints, byte_idx) = debug_generic(
        byte_stream, byte_start, note_str, "I", quiet=quiet, file=file
    )
    return (out_uints, byte_idx)


def debug_uint16s(
    byte_stream, byte_start, note_str, var_tab=False, quiet=False, file=sys.stdout
):
    (out_shorts, byte_idx) = debug_generic(
        byte_stream, byte_start, note_str, "H", var_tab=var_tab, quiet=quiet, file=file
    )
    return (out_shorts, byte_idx)


def debug_bytes(byte_stream, byte_start, note_str, quiet=False, file=sys.stdout):
    (out_bytes, byte_idx) = debug_generic(
        byte_stream, byte_start, note_str, "B", quiet=quiet, file=file
    )
    return (out_bytes, byte_idx)


def debug_string(
    byte_stream, byte_start, note_str, multiline=False, quiet=False, file=sys.stdout
):
    chars_in_line = 30
    out_string = byte_stream.decode("utf-8", "replace")
    byte_idx = byte_start + len(byte_stream)
    if not quiet:
        print("%6d-%6d: %s" % (byte_start, byte_idx - 1, note_str), file=file)
        if multiline:
            for i in range(1 + len(byte_stream) // chars_in_line):
                byte_substream = byte_stream[
                    i * chars_in_line : (i + 1) * chars_in_line
                ]
                byte_substring = str_safe_bytes(byte_substream)
                out_substring = byte_substring.decode("utf-8", "replace")
                print("    %5d: " % (byte_start + i * chars_in_line), end="", file=file)
                for char in out_substring:
                    print(" %s" % (char), end="", file=file)
                print(file=file)
                print("           " + byte_substream.hex(), file=file)
        else:
            if len(out_string) > 0 and out_string[-1] == "\x00":
                print("\t" + out_string[:-1], file=file)
            else:
                print("\t" + out_string, file=file)
    return (out_string, byte_idx)


def is_valid_string(byte_stream):
    try:
        byte_stream.decode("utf-8", "strict")
    except:
        return False
    return True


def print_field_header(in_bytes, byte_idx, file=sys.stdout, quiet=False):
    # read header
    header_uint16s = unpack_uint16(in_bytes[byte_idx : byte_idx + 8], endian="<")
    header_uint32s = unpack_uint32(in_bytes[byte_idx : byte_idx + 8], endian="<")

    field_type = header_uint16s[0]
    field_len = header_uint16s[1]
    field_id = header_uint32s[1]

    # field_len of 1 means field_len=20
    if field_len == 1:
        field_len = 20
    elif field_len == 2:
        raise Exception("Found Field Length = 2")

    # print header (unless quiet)
    if not quiet:
        print("-" * 79, file=file)
        print("byte_idx = " + repr(byte_idx), file=file)
        print("Field Header:", file=file)
        print(file=file)
        print("Field Type  %4d" % field_type, file=file)
        print("Field ID    0x{0:08x} ({0:d})".format(field_id), file=file)
        print("Field Len   %4d" % field_len, file=file)
        print("Field Payload Len   %4d" % (field_len - 8), file=file)
        print(file=file)

    return (field_type, field_len, field_id, header_uint16s, header_uint32s)


def read_field(
    in_bytes,
    byte_idx,
    field_ids=None,
    file=sys.stdout,
    quiet=False,
    report_strings=True,
):
    if field_ids is None:
        field_ids = {}
    field_info = {}
    field_info_payload = {}
    field_start = byte_idx

    # quiet=True if Field Type is String and we're not reporting them
    field_type_pre = unpack_uint16(in_bytes[byte_idx : byte_idx + 2], endian="<")[0]
    if field_type_pre == 16 and report_strings == False:
        quiet = True

    # read header
    (field_type, field_len, field_id, _, _) = print_field_header(
        in_bytes, byte_idx, file=file, quiet=quiet
    )

    # get payload bytes
    field_payload = in_bytes[byte_idx + 8 : byte_idx + field_len]

    # check for references
    bytes_0mod4 = field_payload[0 : len(field_payload) // 4 * 4]
    bytes_2mod4 = field_payload[2 : 2 + (len(field_payload) - 2) // 4 * 4]
    out_uint32s1 = unpack_uint32(bytes_0mod4, endian="<")
    out_uint32s2 = unpack_uint32(bytes_2mod4, endian="<")
    references = [x for x in out_uint32s1 + out_uint32s2 if x in field_ids]
    if references and not quiet:
        print("Links to: ", end="", file=file)
        for ref in references:
            print("%d (type %d)," % (ref, field_ids[ref]["type"]), end="", file=file)
        print("\n", file=file)

    # compute payloads, report if not quiet
    if field_type == 100:
        field_info_payload = process_payload_type100(
            field_payload, field_ids=field_ids, file=file, quiet=quiet
        )
    elif field_type == 101:
        field_info_payload = process_payload_type101(
            field_payload, field_ids=field_ids, file=file, quiet=quiet
        )
    elif field_type == 102:
        field_info_payload = process_payload_type102(
            field_payload, field_ids=field_ids, file=file, quiet=quiet
        )

    # report the following payloads if not quiet
    if not quiet and field_type not in [100, 101, 102]:
        print("Field Payload:", file=file)

        if field_type == 0:
            process_payload_type0(in_bytes, file=file)
        elif field_type == 16:
            process_payload_type16(field_payload, file=file)
        elif field_type in [100, 101, 102]:
            # we've already taken care of these fields in previous if field_type
            pass
        elif field_type in BLOCK_PTR_TYPES:
            process_payload_blockptr(field_payload, field_type=field_type, file=file)
        elif field_type == 131:
            process_payload_type131(field_payload, field_ids=field_ids, file=file)
        else:
            process_payload_generic_refs_data(
                field_payload, field_ids=field_ids, file=file
            )

    field_info["type"] = field_type
    field_info["start"] = field_start
    field_info["len"] = field_len
    field_info["id"] = field_id
    field_info["payload"] = field_payload
    field_info["references"] = references

    field_info.update(field_info_payload)

    return (byte_idx + field_len, field_info)


def process_payload_generic(field_payload, file=sys.stdout, quiet=False):
    # string also shows bytes in hex
    debug_string(field_payload, 0, "", multiline=True, file=file, quiet=quiet)
    if len(field_payload) % 2 == 0:
        debug_uint16s(field_payload, 0, "ushorts", file=file, quiet=quiet)
    if len(field_payload) % 4 == 0:
        (out_uints, _) = debug_uint32s(
            field_payload, 0, "uints", file=file, quiet=quiet
        )
        if any([x > 0x7FFFFFFF for x in out_uints]):
            # only print signed integers if one is different than uint
            debug_int32s(field_payload, 0, "ints", file=file, quiet=quiet)


def process_payload_type0(in_bytes, file=sys.stdout, quiet=False):
    # Simple.  End Of Data Block field has no payload
    print(file=file)
    print("** End Of Data Block Field **", file=file)
    print(file=file)


def process_payload_type16(field_payload, file=sys.stdout):
    field_end = len(field_payload) + 8 - 1
    out_string = unpack_string(field_payload)

    byte_table_data = [
        ["Field\nBytes", "Type", "Description", "Value(s)"],
        ["8-%d" % field_end, "ASCII", "Null-terminated\n  string", out_string[:-1]],
    ]

    print(AsciiTable(byte_table_data).table, file=file)

    if not is_valid_string(field_payload):
        # some byte does not resolve to valid utf-8 character
        print("Invalid character in string!  Error.", file=file)
        debug_bytes(field_payload, 0, "bytes", file=file)


def process_payload_blockptr(field_payload, field_type, file=sys.stdout):

    assert (
        len(field_payload) == 12
    ), "Field Type <Block Pointer>: payload size should be 12 bytes"

    # payload is 12 bytes long
    uint8s = unpack_uint8(field_payload)
    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    block_num = BLOCK_PTR_TYPES[field_type]

    print("\nField Type %d - Data Block %02d" % (field_type, block_num), file=file)

    byte_table_data = [
        ["Field\nBytes", "Type", "Description", "Value(s)"],
        [
            "8-11",
            "uint32",
            "Data Block start\n  Byte offset from file start",
            "%d" % (uint32s[0]),
        ],
        [
            "12-15",
            "uint32",
            "Data Block length\n  Length in bytes",
            "%d" % (uint32s[1]),
        ],
        ["16-19", "uint16", "Unknown", print_list_simple(uint16s[-2:], bits=16)],
    ]

    print(AsciiTable(byte_table_data).table, file=file)


def summarize_ref(field_id, field_ids):
    if field_ids.get(field_id, False):
        ref_type = field_ids[field_id]["type"]
        if ref_type == 16:
            payload_str = field_ids[field_id]["payload"][:-1].decode("utf-8", "ignore")
            ref_string = "'" + payload_str + "'"
        else:
            ref_string = "Field Type %d" % ref_type
    else:
        ref_string = "??"

    return ref_string


def process_payload_type100(
    field_payload, field_ids=None, file=sys.stdout, quiet=False
):
    if field_ids is None:
        field_ids = {}
    field_info_payload = {}
    field_payload_regions = {}

    assert (
        len(field_payload) % 36 == 0
    ), "Field Type 100: payload size should be multiple of 36 bytes"

    # every 36 bytes is a new Data Item
    # each uint at bytes 12-15 + 36*N is a reference to Field Type 16
    ditem_len = 36

    num_data_items = len(field_payload) // ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_table_data = [
        ["Field\nBytes", "Type", "Description", "Value(s)"],
    ]

    for i in range(num_data_items):
        bstart = i * ditem_len + 8
        u16start = i * (ditem_len // 2)
        u32start = i * (ditem_len // 4)

        ref_string = summarize_ref(uint32s[u32start + 3], field_ids)

        field_payload_regions[i] = {}
        field_payload_regions[i]["data_type"] = uint16s[u16start]
        field_payload_regions[i]["label"] = ref_string[1:-1]
        field_payload_regions[i]["index"] = uint16s[u16start + 1]
        field_payload_regions[i]["num_words"] = uint32s[u32start + 1]
        field_payload_regions[i]["byte_offset"] = uint32s[u32start + 2]
        field_payload_regions[i]["word_size"] = uint32s[u32start + 5]
        field_payload_regions[i]["ref_field_type"] = uint16s[u16start + 13]

        if not quiet:
            byte_table_datitem = [
                [
                    "%d-%d" % (bstart, bstart + 1),
                    "uint16",
                    "Region %d Data Type" % i,
                    print_list_simple(uint16s[u16start : u16start + 1], bits=16),
                ],
                [
                    "",
                    "",
                    "",
                    "("
                    + REGION_DATA_TYPES.get(uint16s[u16start : u16start + 1][0], "")
                    + ")",
                ],
                [
                    "%d-%d" % (bstart + 2, bstart + 3),
                    "uint16",
                    "Region %d Index" % i,
                    print_list_simple(uint16s[u16start + 1 : u16start + 2], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 4, bstart + 7),
                    "uint32",
                    "Region %d Num Words" % i,
                    print_list_simple(uint32s[u32start + 1 : u32start + 2], bits=32),
                ],
                [
                    "%d-%d" % (bstart + 8, bstart + 11),
                    "uint32",
                    "Region %d Pointer Byte Offset" % i,
                    print_list_simple(uint32s[u32start + 2 : u32start + 3], bits=32),
                ],
                [
                    "%d-%d" % (bstart + 12, bstart + 15),
                    "uint32",
                    "Region %d Label (Reference)" % i,
                    print_list_simple(uint32s[u32start + 3 : u32start + 4], bits=32),
                ],
                ["", "", "", "(%s)" % ref_string],
                [
                    "%d-%d" % (bstart + 16, bstart + 19),
                    "uint16",
                    "Region %d Unknown1" % i,
                    print_list_simple(uint16s[u16start + 8 : u16start + 10], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 20, bstart + 23),
                    "uint32",
                    "Region %d Word Size (bytes)" % i,
                    print_list_simple(uint32s[u32start + 5 : u32start + 6], bits=32),
                ],
                [
                    "%d-%d" % (bstart + 24, bstart + 25),
                    "uint16",
                    "Region %d Unknown2" % i,
                    print_list_simple(uint16s[u16start + 12 : u16start + 13], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 26, bstart + 27),
                    "uint16",
                    "Region %d Field Type (non-16)\n  that Ref. points to" % i,
                    print_list_simple(uint16s[u16start + 13 : u16start + 14], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 28, bstart + 31),
                    "uint16",
                    "Region %d Unknown3" % i,
                    print_list_simple(uint16s[u16start + 14 : u16start + 16], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 32, bstart + 35),
                    "uint16",
                    "Region %d Unknown4" % i,
                    print_list_simple(uint16s[u16start + 16 : u16start + 18], bits=16),
                ],
                ["-" * 5, "-" * 6, "-" * 26, "-" * 14],
            ]
            byte_table_data.extend(byte_table_datitem)
    if not quiet:
        # get rid of last "----" row
        del byte_table_data[-1]

        print(AsciiTable(byte_table_data).table, file=file)

    field_info_payload["regions"] = field_payload_regions

    return field_info_payload


def process_payload_type101(
    field_payload, field_ids=None, file=sys.stdout, quiet=False
):
    if field_ids is None:
        field_ids = {}
    field_info_payload = {}
    field_payload_items = {}

    assert (
        len(field_payload) % 20 == 0
    ), "Field Type 101: payload size should be multiple of 20 bytes"

    # every 20 bytes is a new Data Item
    # each uint at bytes 8-11 + 20*N is a reference
    # each uint at bytes 16-19 + 20*N is a reference
    ditem_len = 20

    num_data_items = len(field_payload) // ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_table_data = [
        ["Field\nBytes", "Type", "Description", "Value(s)"],
    ]

    for i in range(num_data_items):
        bstart = i * ditem_len + 8
        u16start = i * (ditem_len // 2)
        u32start = i * (ditem_len // 4)

        ref_type100 = summarize_ref(uint32s[u32start + 2], field_ids)
        ref_label = summarize_ref(uint32s[u32start + 4], field_ids)

        data_field_type = uint16s[u16start]

        assert (
            field_payload_items.get(data_field_type, False) is False
        ), "Field Type 101: multiple entries, same data field type"

        field_payload_items[data_field_type] = {}
        field_payload_items[data_field_type]["num_regions"] = uint16s[u16start + 3]
        field_payload_items[data_field_type]["data_key_ref"] = uint32s[u32start + 2]
        field_payload_items[data_field_type]["total_bytes"] = uint32s[u32start + 3]
        field_payload_items[data_field_type]["label"] = ref_label[1:-1]

        if not quiet:
            byte_table_datitem = [
                [
                    "%d-%d" % (bstart, bstart + 1),
                    "uint16",
                    "Item %d Field Type\n  containing data" % i,
                    print_list_simple(uint16s[u16start : u16start + 1], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 2, bstart + 3),
                    "uint16",
                    "Item %d Unknown0\n  (4,5,6,7,16,20,21,22,23)" % i,
                    "  {0:d} (0b{0:05b})".format(uint16s[u16start + 1]),
                ],
                [
                    "%d-%d" % (bstart + 4, bstart + 5),
                    "uint16",
                    "Item %d Unknown1\n  (1000)" % i,
                    print_list_simple(uint16s[u16start + 2 : u16start + 3], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 6, bstart + 7),
                    "uint16",
                    "Item %d Num. Regions in key" % i,
                    print_list_simple(uint16s[u16start + 3 : u16start + 4], bits=16),
                ],
                [
                    "%d-%d" % (bstart + 8, bstart + 11),
                    "uint32",
                    "Item %d Data Key" % i,
                    print_list_simple(uint32s[u32start + 2 : u32start + 3], bits=32),
                ],
                ["", "", "  (Reference to Type 100)", "(%s)" % ref_type100],
                [
                    "%d-%d" % (bstart + 12, bstart + 15),
                    "uint32",
                    "Item %d Total bytes in key" % i,
                    print_list_simple(uint32s[u32start + 3 : u32start + 4], bits=32),
                ],
                [
                    "%d-%d" % (bstart + 16, bstart + 19),
                    "uint32",
                    "Item %d Label (Reference)" % i,
                    print_list_simple(uint32s[u32start + 4 : u32start + 5], bits=32),
                ],
                ["", "", "", "(%s)" % ref_label],
                ["-" * 5, "-" * 6, "-" * 24, "-" * 16],
            ]
            byte_table_data.extend(byte_table_datitem)

    if not quiet:
        # get rid of last "----" row
        del byte_table_data[-1]

        print(AsciiTable(byte_table_data).table, file=file)

    field_info_payload["items"] = field_payload_items

    return field_info_payload


def process_payload_type102(
    field_payload, field_ids=None, file=sys.stdout, quiet=False
):
    if field_ids is None:
        field_ids = {}
    field_info_payload = {}

    assert len(field_payload) == 16, "Field Type 102 should have length of 20"

    # every 16 bytes is a new Data Item
    # each uint at bytes 8-11 + 16*N is a reference
    # each uint at bytes 12-15 + 16*N is a reference
    ditem_len = 16

    num_data_items = len(field_payload) // ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    bstart = 8
    u16start = 0
    u32start = 0

    ref_type101 = summarize_ref(uint32s[u32start + 2], field_ids)
    ref_label = summarize_ref(uint32s[u32start + 3], field_ids)

    field_info_payload["collection_num_items"] = uint16s[u16start + 3]
    field_info_payload["collection_label"] = ref_label[1:-1]
    field_info_payload["collection_ref"] = uint32s[u32start + 2]

    if not quiet:
        byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],
            [
                "%d-%d" % (bstart, bstart + 1),
                "uint16",
                "Unknown0",
                print_list_simple(uint16s[u16start : u16start + 1], bits=16),
            ],
            [
                "%d-%d" % (bstart + 2, bstart + 3),
                "uint16",
                "Unknown1",
                print_list_simple(uint16s[u16start + 1 : u16start + 2], bits=16),
            ],
            [
                "%d-%d" % (bstart + 4, bstart + 5),
                "uint16",
                "Unknown2\n  (1000)",
                print_list_simple(uint16s[u16start + 2 : u16start + 3], bits=16),
            ],
            [
                "%d-%d" % (bstart + 6, bstart + 7),
                "uint16",
                "Items in Collection",
                print_list_simple(uint16s[u16start + 3 : u16start + 4], bits=16),
            ],
            [
                "%d-%d" % (bstart + 8, bstart + 11),
                "uint32",
                "Collection Reference",
                print_list_simple(uint32s[u32start + 2 : u32start + 3], bits=32),
            ],
            ["", "", "  (Reference to Type 101)", "(%s)" % ref_type101],
            [
                "%d-%d" % (bstart + 12, bstart + 15),
                "uint32",
                "Label (Reference)",
                print_list_simple(uint32s[u32start + 3 : u32start + 4], bits=32),
            ],
            ["", "", "", "(%s)" % ref_label],
        ]

        print(AsciiTable(byte_table_data).table, file=file)

    return field_info_payload


# TODO: we may not need this special case, the format may not be true in
#       general
def process_payload_type131(field_payload, field_ids=None, file=sys.stdout):
    if field_ids is None:
        field_ids = {}

    # every 12 bytes is a new Data Item
    # each uint at bytes 4-7 + 12*N is a reference
    ditem_len = 12

    num_data_items = len(field_payload) // ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_table_data = [
        ["Field\nBytes", "Type", "Description", "Value(s)"],
    ]

    for i in range(num_data_items):
        bstart = i * ditem_len + 8
        u16start = i * (ditem_len // 2)
        u32start = i * (ditem_len // 4)

        ref_string0 = summarize_ref(uint32s[u32start], field_ids)
        ref_string1 = summarize_ref(uint32s[u32start + 1], field_ids)

        byte_table_datitem = [
            [
                "%d-%d" % (bstart, bstart + 3),
                "uint32",
                "Item %d Reference" % i,
                print_list_simple(uint32s[u32start : u32start + 1], bits=32),
            ],
            ["", "", "", "(%s)" % ref_string0],
            [
                "%d-%d" % (bstart + 4, bstart + 7),
                "uint32",
                "Item %d Reference" % i,
                print_list_simple(uint32s[u32start + 1 : u32start + 2], bits=32),
            ],
            ["", "", "", "(%s)" % ref_string1],
            [
                "%d-%d" % (bstart + 8, bstart + 11),
                "uint32",
                "Item %d Length of string\n  in above Reference" % i,
                print_list_simple(uint32s[u32start + 2 : u32start + 3], bits=32),
            ],
            ["-" * 5, "-" * 6, "-" * 22, "-" * 16],
        ]
        byte_table_data.extend(byte_table_datitem)

    # get rid of last "----" row
    del byte_table_data[-1]

    print(AsciiTable(byte_table_data).table, file=file)


def get_payload_ref_idx(field_payload, field_ids):
    # find indicies of references
    len_0mod4 = len(field_payload) // 4 * 4
    len_2mod4 = (len(field_payload) - 2) // 4 * 4
    uint32s_0mod4 = unpack_uint32(field_payload[:len_0mod4], endian="<")
    uint32s_2mod4 = unpack_uint32(field_payload[2 : len_2mod4 + 2], endian="<")
    ref_idx0 = [(i, x) for (i, x) in enumerate(uint32s_0mod4) if x in field_ids]
    ref_idx2 = [(i, x) for (i, x) in enumerate(uint32s_2mod4) if x in field_ids]
    if ref_idx2:
        print("mod2 reference detected", sys.stderr)
    ref_idx0.sort()
    ref_idx2.sort()
    return (ref_idx0, ref_idx2)


def process_payload_generic_refs_data(
    field_payload, field_ids=None, file=sys.stdout, quiet=False
):
    if field_ids is None:
        field_ids = {}

    # just list groups of words between references
    (ref_idx0, ref_idx2) = get_payload_ref_idx(field_payload, field_ids)
    if ref_idx0:
        (this_ref_idx, this_ref) = ref_idx0.pop(0)
    else:
        this_ref_idx = None
    p_idx = 0
    while True:
        # get values until this_ref_idx or end of payload
        if this_ref_idx is not None:
            this_endbyte = this_ref_idx * 4
        else:
            this_endbyte = len(field_payload)

        # string also shows bytes in hex
        if p_idx < this_endbyte:
            debug_string(
                field_payload[p_idx:this_endbyte],
                p_idx,
                "bytes",
                multiline=True,
                file=file,
            )
            if len(field_payload[p_idx:this_endbyte]) % 2 == 0:
                debug_uint16s(
                    field_payload[p_idx:this_endbyte], p_idx, "uint16s", file=file
                )
            if len(field_payload[p_idx:this_endbyte]) % 4 == 0:
                (out_uints, _) = debug_uint32s(
                    field_payload[p_idx:this_endbyte], p_idx, "uint32s", file=file
                )
                if any([x > 0x7FFFFFFF for x in out_uints]):
                    # only print signed integers if one is different than uint
                    debug_int32s(
                        field_payload[p_idx:this_endbyte], p_idx, "int32s", file=file
                    )

        if this_ref_idx is not None:
            ref_string = summarize_ref(this_ref, field_ids)
            byte_table_data = [
                ["Field\nBytes", "Type", "Description", "Value(s)"],
                [
                    "%d-%d" % (this_endbyte, this_endbyte + 3),
                    "uint32",
                    "Reference",
                    "%d" % this_ref,
                ],
                ["", "", "", "(%s)" % ref_string],
            ]
            print(AsciiTable(byte_table_data).table, file=file)
        else:
            break

        # update next starting byte
        p_idx = this_endbyte + 4

        if ref_idx0:
            (this_ref_idx, this_ref) = ref_idx0.pop(0)
        else:
            this_ref_idx = None


# Debugging routine used to search backwards from known field to try and find
#   previous possible fields
# Not really used anymore
def search_backwards(in_bytes, field_start, level=0, min_search_idx=0, file=sys.stdout):
    idx = field_start - 2
    possibles = []
    while idx >= min_search_idx:
        test_uint16s = unpack_uint16(in_bytes[idx : idx + 2], endian="<")
        test_ushort = test_uint16s[0]
        if idx - 2 + test_ushort == field_start:
            possibles.append(idx - 2)
        idx = idx - 1
    for possible_idx in possibles:
        print(
            "  " * level
            + "idx=%d: possible field start, back from %d"
            % (possible_idx, field_start),
            file=file,
        )
        search_backwards(
            in_bytes, possible_idx, level=level + 1, min_search_idx=min_search_idx
        )


def parse_datablock(field_payload):
    out_uint32s = unpack_uint32(field_payload, endian="<")
    data_start = out_uint32s[0]
    data_len = out_uint32s[1]
    return (data_start, data_len)


def process_datablock_header(header_bytes, byte_idx, block_num, file=sys.stdout):
    # TODO: experimental
    data_block_comment = {
        0: "Data Block 00: 'Overlay Header' Format",
        1: "Data Block 01: 'Overlay Header' Data",
        2: "Data Block 02: 'Q1 Description' Format",
        3: "Data Block 03: 'Q1 Description' Data",
        4: "Data Block 04: 'DDB Description' Format",
        5: "Data Block 05: 'DDB Description' Data",
        6: "Data Block 06: 'Audit Trail' Format",
        7: "Data Block 07: 'Audit Trail' Data",
        8: "Data Block 08: 'Scan Header' Format",
        9: "Data Block 09: 'Scan Header' Data",
    }

    print("=" * 79, file=file)
    print("byte_idx = " + repr(byte_idx), file=file)
    print("Data Block %02d Header" % block_num, file=file)
    if data_block_comment.get(block_num, False):
        print(data_block_comment[block_num], file=file)
    print(file=file)

    # table header row
    byte_table_data = [
        ["Field\nBytes", "Type", "Description", "Value(s)"],
    ]

    uint32s = unpack_uint32(header_bytes, endian="<")

    bstart = 0

    byte_table_datitem = [
        [
            "%d-%d" % (bstart, bstart + 3),
            "uint32",
            "Data Block Length of\n  all fields (bytes)",
            print_list_simple(uint32s[0:1], bits=32),
        ],
        [
            "%d-%d" % (bstart + 4, bstart + 8),
            "uint32",
            "Data Block Number of\n  Different Field Types",
            print_list_simple(uint32s[1:2], bits=32),
        ],
    ]
    byte_table_data.extend(byte_table_datitem)

    print(AsciiTable(byte_table_data).table, file=file)


def process_datablock_footer(footer_bytes, byte_idx, block_num, file=sys.stdout):
    print("-" * 79, file=file)
    print("byte_idx = " + repr(byte_idx), file=file)
    print("Data Block %02d Footer" % block_num, file=file)

    # table header row
    byte_table_data = [
        ["Field\nBytes", "Type", "Description", "Value(s)"],
    ]

    for i in range(len(footer_bytes) // 14):
        uint16s = unpack_uint16(footer_bytes[i * 14 : (i + 1) * 14], endian="<")
        uint32s = unpack_uint32(footer_bytes[i * 14 + 2 : (i + 1) * 14], endian="<")

        # bstart is byte number in field
        bstart = i * 14

        # print this batch of 7 uint16s
        byte_table_datitem = [
            [
                "%d-%d" % (bstart, bstart + 1),
                "uint16",
                "Item %d Data Block\n  Field Type" % i,
                print_list_simple(uint16s[0:1], bits=16),
            ],
            [
                "%d-%d" % (bstart + 2, bstart + 5),
                "uint32",
                "Item %d Data Block\n  Num. Occurrences A" % i,
                print_list_simple(uint32s[0:1], bits=32),
            ],
            [
                "%d-%d" % (bstart + 6, bstart + 9),
                "uint32",
                "Item %d Data Block\n  Num. Occurrences B" % i,
                print_list_simple(uint32s[1:2], bits=32),
            ],
            [
                "%d-%d" % (bstart + 10, bstart + 13),
                "uint32",
                "Item %d Data Block\n  Unknown" % i,
                print_list_simple(uint32s[2:3], bits=32),
            ],
            ["-----", "------", "------------------", "----------------"],
        ]
        byte_table_data.extend(byte_table_datitem)

    # get rid of last "----" row
    del byte_table_data[-1]

    print(AsciiTable(byte_table_data).table, file=file)


def print_datablock(
    in_bytes,
    data_start,
    data_len,
    block_num,
    field_ids=None,
    file=sys.stdout,
    report_strings=True,
):
    if field_ids is None:
        field_ids = {}

    print("=" * 79, file=file)
    print("DATA BLOCK %s" % block_num, file=file)
    print("Start: %d" % (data_start), file=file)
    print("End:   %d" % (data_start + data_len), file=file)
    print(file=file)

    byte_idx = data_start
    process_datablock_header(
        in_bytes[byte_idx : byte_idx + 8], byte_idx, block_num, file=file
    )
    byte_idx += 8

    # print all fields in data block
    while byte_idx < data_start + data_len:
        (byte_idx, field_info) = read_field(
            in_bytes,
            byte_idx,
            field_ids=field_ids,
            file=file,
            report_strings=report_strings,
        )

        if field_info["type"] == 0:
            # End Of Data Block field
            break

    # Print Data Block Footer
    process_datablock_footer(
        in_bytes[byte_idx : data_start + data_len], byte_idx, block_num, file=file
    )


def get_next_data_block_end(byte_idx, data_start, data_len):
    for i in range(11):
        if byte_idx < data_start[i] + data_len[i]:
            block_num = i
            end_idx = data_start[i] + data_len[i]
            break
    return (block_num, end_idx)


def process_file_header(in_bytes, file=sys.stdout):
    uint16_0 = unpack_uint16(in_bytes[0:2], endian="<")[0]
    ascii_0 = str(in_bytes[2:32])[2:-1]
    ascii_1 = str(in_bytes[32:56])[2:-1]
    ascii_2 = str(in_bytes[56:96])[2:-1]
    ascii_3 = str(in_bytes[96:136])[2:-1]
    uint32_list = unpack_uint32(in_bytes[136:160], endian="<")
    byte_table_data = [
        ["File\nBytes", "Type", "Description", "Value(s)"],
        ["%d-%d" % (0, 1), "uint16", "Magic Number", "0x{0:04x}".format(uint16_0)],
        ["%d-%d" % (2, 31), "ASCII", "File Version", ascii_0],
        ["%d-%d" % (32, 55), "ASCII", "Endian Format", ascii_1],
        ["%d-%d" % (56, 95), "ASCII", "File Type, ID", ascii_2],
        ["%d-%d" % (96, 135), "ASCII", "Space Padding", ascii_3],
        [
            "%d-%d" % (136, 139),
            "uint32",
            "Unknown (200)",
            "0x{0:08x}".format(uint32_list[0]),
        ],
        [
            "%d-%d" % (140, 143),
            "uint32",
            "Unknown (3)",
            "0x{0:08x}".format(uint32_list[1]),
        ],
        [
            "%d-%d" % (144, 147),
            "uint32",
            "Unknown (0)",
            "0x{0:08x}".format(uint32_list[2]),
        ],
        [
            "%d-%d" % (148, 151),
            "uint32",
            "Start of\n  Data Block 0\n  (byte offset)",
            "{0:10d}".format(uint32_list[3]),
        ],
        [
            "%d-%d" % (152, 155),
            "uint32",
            "Length\n  Data Block 0\n  until EOF\n  (bytes)",
            "{0:10d}".format(uint32_list[4]),
        ],
        [
            "%d-%d" % (156, 159),
            "uint32",
            "Unknown (4096)",
            "0x{0:08x}".format(uint32_list[5]),
        ],
    ]

    print("=" * 79, file=file)

    print("File Header", file=file)
    print("byte_idx = " + repr(0), file=file)
    print(AsciiTable(byte_table_data).table, file=file)

    data_start0 = uint32_list[3]

    # read 11 fields to Data Block Pointers in File Header
    byte_idx = 160
    for i in range(11):
        (byte_idx, field_info) = read_field(in_bytes, byte_idx, file=file)

    print("-" * 79, file=file)
    print("byte_idx: %d-%d" % (byte_idx, data_start0 - 1), file=file)
    print(file=file)
    print("All Zeros", file=file)
    print(file=file)


def report_whole_file(
    in_bytes,
    field_ids,
    data_start,
    data_len,
    in_filepath,
    out_filedir,
    report_strings=True,
):
    out_filepath = os.path.join(out_filedir, "dump.txt")
    try:
        out_fh = open(out_filepath, "w")
    except:
        print("Error opening dump.txt")

    print(in_filepath, file=out_fh)

    # FILE HEADER

    process_file_header(in_bytes, file=out_fh)

    # DATA BLOCKS

    # get + print Data Block 0 Header
    byte_idx = data_start[0]
    process_datablock_header(
        in_bytes[byte_idx : byte_idx + 8], byte_idx, 0, file=out_fh
    )

    # start again at beginning of Data Block 0
    byte_idx = data_start[0] + 8
    # read all fields in file after File Header
    while byte_idx < len(in_bytes):
        field_start = byte_idx
        (byte_idx, field_info) = read_field(
            in_bytes,
            byte_idx,
            field_ids=field_ids,
            file=out_fh,
            report_strings=report_strings,
        )

        if field_info["type"] == 0:
            # we just saw an End Of Data Block Field
            (block_num, end_idx) = get_next_data_block_end(
                byte_idx, data_start, data_len
            )

            process_datablock_footer(
                in_bytes[byte_idx:end_idx], byte_idx, block_num, file=out_fh
            )

            byte_idx = end_idx
            if block_num + 1 < 10:
                process_datablock_header(
                    in_bytes[byte_idx : byte_idx + 8],
                    byte_idx,
                    block_num + 1,
                    file=out_fh,
                )

            byte_idx = end_idx + 8

        # break if we still aren't advancing
        if byte_idx == field_start:
            print("ERROR BREAK!!!!", file=out_fh)
            print("-" * 79, file=out_fh)
            break

        if byte_idx > data_start[10]:
            byte_idx = data_start[10]
            print("=" * 79, file=out_fh)
            print("byte_idx = " + repr(byte_idx), file=out_fh)
            print(file=out_fh)
            print("Data Block 10 Start", file=out_fh)
            print(file=out_fh)
            print(
                "%d-%d     Image Data" % (byte_idx, byte_idx + data_len[10]),
                file=out_fh,
            )
            print(file=out_fh)
            print("=" * 79, file=out_fh)
            break

    out_fh.close()


def report_datablocks(
    in_bytes, data_start, data_len, field_ids, filedir, filename, report_strings=True
):
    # parse data blocks 0-9
    for i in range(0, 10):
        # Data Block
        try:
            out_fh = open(os.path.join(filedir, "data%02d.txt" % i), "w")
        except:
            print("Error opening data%02d.txt" % i, file=sys.stderr)
            raise

        print(filename, file=out_fh)

        print_datablock(
            in_bytes,
            data_start[i],
            data_len[i],
            i,
            field_ids=field_ids,
            file=out_fh,
            report_strings=report_strings,
        )
        out_fh.close()

    # Data Block 10 - Image Data
    try:
        out_fh = open(os.path.join(filedir, "data10_img.txt"), "w")
    except:
        print("Error opening data10_img.txt")
    print(
        "===================================================================",
        file=out_fh,
    )
    print("IMAGE DATA BLOCK", file=out_fh)
    print(file=out_fh)
    data_end = data_start[10] + data_len[10]
    print("Image Data: (%d-%d)" % (data_start[10], data_end - 1), file=out_fh)
    print(file=out_fh)
    print(file=out_fh)


def recurse_item_hier(item, tablevel, file):
    tab = " " * 4 * (tablevel)
    print(tab + "-" * 20, file=file)
    print(tab + "Item: %s" % item["label"], file=file)
    print(tab + "Field Type: %d" % item["type"], file=file)
    print(tab + "Field ID: %d" % item["id"], file=file)
    tab = " " * 4 * (tablevel + 1)
    for region in item["data"]:
        print(tab + "-" * 20, file=file)
        print(tab + "Region: %s" % region["label"], file=file)
        print(tab + "Data Type    : %d" % (region["dtype_num"]), end="", file=file)
        if region["dtype"] is not None:
            print(" (%s)" % (region["dtype"]), file=file)
        else:
            print("", file=file)
        print(tab + "Region Index : %d" % (region["region_idx"]), file=file)
        print(tab + "Word Size    : %d" % (region["word_size"]), file=file)
        print(tab + "Num. Words   : %d" % (region["num_words"]), file=file)
        print(tab + "Data (raw)   : ", end="", file=file)
        print_raw_data(
            region["data"]["raw"], tab, len("Data (rawhex): "), hex=False, file=file
        )
        print(tab + "Data (rawhex): ", end="", file=file)
        print_raw_data(region["data"]["raw"], tab, len("Data (rawhex): "), file=file)
        if region["data"]["proc"] is not None:
            data_proc = repr(region["data"]["proc"])
        else:
            data_proc = "?"
        print(tab + "Data         : " + data_proc, file=file)
        if type(region["data"]["interp"]) is dict:
            print(tab + "Data (intrp): ", file=file)
            recurse_item_hier(region["data"]["interp"], tablevel + 2, file)
        elif type(region["data"]["interp"]) is str:
            print(tab + "Data (intrp): %s" % (region["data"]["interp"]), file=file)


def report_hierarchy(filename, filedir):
    out_filename = "hierarchy.txt"
    try:
        out_fh = open(os.path.join(filedir, out_filename), "w")
    except:
        print("Error opening %s" % out_filename)

    print(filename, file=out_fh)

    reader = biorad1sc_reader.Reader(filename)
    metadata = reader.get_metadata()

    for collection in metadata:
        print("-" * 79, file=out_fh)
        print("Data Collection", file=out_fh)
        print("'%s'" % collection["label"], file=out_fh)
        for item in collection["data"]:
            recurse_item_hier(item, 1, out_fh)


def update_field_ids(in_bytes, field_ids, data_start, data_len):
    if field_ids is None:
        field_ids = {}

    # reset byte_idx to right after Data Block 0 Header
    byte_idx = data_start[0] + 8

    # keep track of all fields that were referenced
    is_referenced = {}

    # now that we know all data_ids, find all references
    while byte_idx < data_start[10]:
        field_start = byte_idx

        (byte_idx, field_info) = read_field(
            in_bytes, byte_idx, quiet=True, field_ids=field_ids
        )

        if field_info["type"] == 0:
            # we just saw an End Of Data Block Field
            (block_num, end_idx) = get_next_data_block_end(
                byte_idx, data_start, data_len
            )

            # skip past Data Block Footer and Header to first field
            #   of next Data Block
            byte_idx = end_idx + 8

        if field_info["id"] != 0:
            # update references field using field_info
            field_ids[field_info["id"]] = field_info

            for ref in field_info["references"]:
                is_referenced[ref] = True

        # break if we still aren't advancing
        if byte_idx == field_start:
            raise Exception("Error parsing file: byte_idx == field_start")
            break

    return is_referenced


def get_all_field_info(in_bytes, field_ids):
    # reset loop variables
    byte_idx = 160
    data_start = {}
    data_len = {}

    # read 11 fields to Data Block Pointers in File Header
    byte_idx = 160
    for i in range(11):
        (byte_idx, field_info) = read_field(in_bytes, byte_idx, quiet=True)
        block_num = BLOCK_PTR_TYPES[field_info["type"]]
        (data_start[block_num], data_len[block_num]) = parse_datablock(
            field_info["payload"]
        )

    field_ids = {}
    update_field_ids(in_bytes, field_ids, data_start, data_len)
    is_referenced = update_field_ids(in_bytes, field_ids, data_start, data_len)

    return (field_ids, data_start, data_len, is_referenced)


def parse_file(filename, report_strings=True):
    print(filename, file=sys.stderr)

    filename = os.path.realpath(filename)
    (fileroot, _) = os.path.splitext(filename)
    out_filedir = fileroot + "_reports"
    try:
        os.mkdir(out_filedir)
    except FileExistsError:
        pass

    with open(filename, "rb") as in_fh:
        in_bytes = in_fh.read()

    # SEARCH DEBUG
    # search_backwards(in_bytes, len(in_bytes)-1, min_search_idx=59881)
    # exit()

    # dict of keys: field_ids, items: field_payloads
    field_ids = {}

    # PASS 1
    #   get all field info
    print("    Pass 1: getting Field IDs, pointers", file=sys.stderr)
    (field_ids, data_start, data_len, is_referenced) = get_all_field_info(
        in_bytes, field_ids
    )

    # PASS 2
    #   report on whole file to dump.txt
    print("    Pass 2: Reporting entire file to dump.txt", file=sys.stderr)
    report_whole_file(
        in_bytes,
        field_ids,
        data_start,
        data_len,
        filename,
        out_filedir,
        report_strings=report_strings,
    )

    # PASS 3
    #   report data blocks in separate files
    print("    Pass 3: Reporting data blocks to separate files", file=sys.stderr)
    report_datablocks(
        in_bytes,
        data_start,
        data_len,
        field_ids,
        out_filedir,
        filename,
        report_strings=report_strings,
    )

    # PASS 4
    #   report on hierarchy using biorad1sc_reader
    print("    Pass 4: Reporting hierarchical data to hierarchy.txt ", file=sys.stderr)
    print("            (using biorad1sc_reader)", file=sys.stderr)
    report_hierarchy(filename, out_filedir)


def get_cmdline_args():
    """
    Return args struct
    """

    # initialize the parser object:
    parser = argparse.ArgumentParser(
        description="Read/Parse Bio-Rad *.1sc file(s) and produce "
        "reports detailing their internal structure. "
        "Reports for <filename>.1sc are placed in "
        "<filename>_reports directory."
    )

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument("srcfile", nargs="+", help="Source 1sc file(s).")

    # switches/options:
    parser.add_argument(
        "-S",
        "--omit_strings",
        action="store_true",
        default=False,
        help="Do not include Type 16 String fields in reports. "
        "(But include the strings when listing references to them.)",
    )

    args = parser.parse_args()

    return args


def main():
    args = get_cmdline_args()
    for filename in args.srcfile:
        parse_file(filename, report_strings=not args.omit_strings)
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


# old method for determining end of block footer/header after
#   End Of Block Field below:
# Total:
#   14*N + 8 bytes
#   7*N + 4 uints
# each 7 uint16s:
#   non-zero, any, 0, any, 0, non-zero, 0
#   or
#   0, 0, 0, 0, 0, 0, 0
# last 4 uint16s:
#   preamble of next Data Block
#       (len of next Data Block), 0, non-zero, 0
#       (unless start of Image Data Block!  Then just Data)
# uint16 following last 3 uint16s is non-zero

# TODO: to make this absolutely robust, we should just look for byte
#   index to Data Block ends
