#!/usr/bin/env python3

# testbed to read, parse *.1sc files

import os
import os.path
import sys
import argparse
import struct
from terminaltables import AsciiTable

"""
test.1sc:
    BitsPerPixel   16
    DimensionOrder    XYCZT
    IsInterleaved    false
    IsRGB   false
    LittleEndian   true
    PixelType uint16
    Series 0 Name    test.1sc
    SizeC   1
    SizeT  1
    SizeX 696
    SizeY    520
    SizeZ   1
    Location    /Users/mclapp/git/cellcounter/docs/test.1sc
    Scanner name    ChemiDoc XRS

    696*520*2bytes = 723840bytes
    696*520*2bytes = 36190 ushorts(2-byte)

    image data 59946 - 783785 (last byte of file)
"""


BLOCK_PTR_TYPES = {142:0, 143:1, 132:2, 133:3, 141:4,
        140:5, 126:6, 127:7, 128:8, 129:9, 130:10, }


def print_list(byte_list, bits=8, address=None, var_tab=False, file=sys.stdout):
    """
    TODO: is this doing proper little-endian?
    """
    # log10(2**bits) = log10(2)*bits = 0.301*bits
    # log16(2**bits) = log16(2)*bits = 0.25*bits
    hex_digits = int(0.25 * bits)
    # add 3 chars for "0x" and ","
    # number of items in a line
    items = 72//(hex_digits+3)
    # round items down to multiple of 4
    items = items//4*4
    pr_str = "{:%dd},"%(hex_digits+2)
    pr_str_hex = "0x{:0%dx},"%(hex_digits)

    byte_groups = range(0, len(byte_list), items)
    byte_groups = [[x, min([x+items, len(byte_list)])] for x in byte_groups]

    if address is None:
        print("\t[", end="", file=file)
        first_loop = True
        for (i, byte_group) in enumerate(byte_groups):
            if first_loop:
                first_loop = False
            else:
                print("\t ", end="", file=file)

            # print decimal words
            for byte in byte_list[byte_group[0]:byte_group[1]]:
                print(pr_str.format(byte), end="", file=file)
            # print spacer
            print(file=file)
            print("         ", end="", file=file)
            # print hex words
            for byte in byte_list[byte_group[0]:byte_group[1]]:
                print(pr_str_hex.format(byte), end="", file=file)

            if i < len(byte_groups)-1:
                print(file=file)
        print("]", file=file)
    else:
        first_loop = True
        for (i, byte_group) in enumerate(byte_groups):
            # print address start
            if len(byte_groups) > 1:
                if var_tab is False:
                    print("    %6d: "%(address+i*items*bits/8), end="", file=file)
                else:
                    print("%s%4d: "%(var_tab, address+i*items*bits/8), end="", file=file)
            else:
                if var_tab is False:
                    print("            ", end="", file=file)
                else:
                    print("%s      "%(var_tab), end="", file=file)
            # print decimal words
            for byte in byte_list[byte_group[0]:byte_group[1]]:
                print(pr_str.format(byte), end="", file=file)
            print(file=file)

            # print spacer
            if var_tab is False:
                print("            ", end="", file=file)
            else:
                print("%s      "%(var_tab), end="", file=file)
            # print hex words
            for byte in byte_list[byte_group[0]:byte_group[1]]:
                print(pr_str_hex.format(byte), end="", file=file)
            print(file=file)


def print_list_simple(wordlist, bits=8, hexfmt=False):
    outstr = ""
    # print list of words
    first_time = True
    for myword in wordlist:
        if not first_time:
            outstr = outstr + ", "
        else:
            first_time = False

        if bits == 8:
            if hexfmt:
                outstr = outstr + "0x{:02x}".format(myword)
            else:
                outstr = outstr + "%4d"%myword
        if bits == 16:
            if hexfmt:
                outstr = outstr + "0x{:04x}".format(myword)
            else:
                outstr = outstr + "%6d"%myword
        if bits == 32:
            if hexfmt:
                outstr = outstr + "0x{:08x}".format(myword)
            else:
                outstr = outstr + "%10d"%myword

    return outstr


def str_safe_bytes(byte_stream):
    table_from = bytes(range(256))
    table_to = b'\x20' + b'\xff'*31 + bytes(range(32, 127)) + b'\xff'*129
    trans_table = byte_stream.maketrans(table_from, table_to)
    safe_byte_stream = byte_stream.translate(trans_table)
    return safe_byte_stream


def unpack_string(byte_stream):
    out_string = byte_stream.decode("utf-8", "replace")
    return out_string


def unpack_uint8(byte_stream):
    num_uint8 = len(byte_stream)
    out_uint8s = struct.unpack("B"*num_uint8, byte_stream)
    return out_uint8s


def unpack_uint16(byte_stream, endian="<"):
    num_uint16 = len(byte_stream)//2
    out_uint16s = struct.unpack(endian+"H"*num_uint16, byte_stream)
    return out_uint16s


def unpack_uint32(byte_stream, endian="<"):
    num_uint32 = len(byte_stream)//4
    out_uint32s = struct.unpack(endian+"I"*num_uint32, byte_stream)
    return out_uint32s


def debug_generic(byte_stream, byte_start, note_str, format_str,
        var_tab=False, quiet=False, file=sys.stdout):
    bytes_per = struct.calcsize(format_str)
    num_shorts = len(byte_stream)//(bytes_per)
    out_shorts = struct.unpack("<"+format_str*num_shorts, byte_stream)
    byte_idx = byte_start + len(byte_stream)
    if not quiet:
        if var_tab is not False:
            print("%s%d-%d: %s"%(var_tab, byte_start, byte_idx-1, note_str),
                    file=file)
        else:
            print("%6d-%6d: %s"%(byte_start, byte_idx-1, note_str), file=file)
        print_list(
                out_shorts,
                bits=bytes_per*8,
                address=byte_start,
                var_tab=var_tab,
                file=file
                )
    return (out_shorts, byte_idx)


def debug_ints(byte_stream, byte_start, note_str, quiet=False, file=sys.stdout):
    (out_ints, byte_idx) = debug_generic(
            byte_stream, byte_start, note_str, "i", quiet=quiet, file=file)
    return (out_ints, byte_idx)


def debug_uints(byte_stream, byte_start, note_str, quiet=False, file=sys.stdout):
    (out_uints, byte_idx) = debug_generic(
            byte_stream, byte_start, note_str, "I", quiet=quiet, file=file)
    return (out_uints, byte_idx)


def debug_ushorts(byte_stream, byte_start, note_str, var_tab=False,
        quiet=False, file=sys.stdout):
    (out_shorts, byte_idx) = debug_generic(
            byte_stream, byte_start, note_str, "H", var_tab=var_tab,
            quiet=quiet, file=file)
    return (out_shorts, byte_idx)


def debug_bytes(byte_stream, byte_start, note_str, quiet=False, file=sys.stdout):
    (out_bytes, byte_idx) = debug_generic(
            byte_stream, byte_start, note_str, "B", quiet=quiet, file=file)
    return (out_bytes, byte_idx)

def debug_string(byte_stream, byte_start, note_str, multiline=False,
        quiet=False, file=sys.stdout):
    chars_in_line = 30
    out_string = byte_stream.decode("utf-8", "replace")
    byte_idx = byte_start + len(byte_stream)
    if not quiet:
        print("%6d-%6d: %s"%(byte_start, byte_idx - 1, note_str), file=file)
        if multiline:
            for i in range(1+len(byte_stream)//chars_in_line):
                byte_substream = byte_stream[i*chars_in_line:(i+1)*chars_in_line]
                byte_substring = str_safe_bytes(byte_substream)
                out_substring = byte_substring.decode("utf-8", "replace")
                print("    %5d: "%(byte_start+i*chars_in_line), end="", file=file)
                for char in out_substring:
                    print(" %s"%(char), end="", file=file)
                print(file=file)
                print("           "+byte_substream.hex(), file=file)
        else:
            if len(out_string) > 0 and out_string[-1] == '\x00':
                print("\t"+out_string[:-1], file=file)
            else:
                print("\t"+out_string, file=file)
    return (out_string, byte_idx)


def debug_nullterm_string(in_bytes, byte_start, note_str, quiet=False,
        file=sys.stdout):
    byte_idx = byte_start
    while in_bytes[byte_idx] != 0:
        byte_idx += 1
    return debug_string(
            in_bytes[byte_start:byte_idx+1],
            byte_start, note_str, quiet=quiet, file=file
            )


def is_valid_string(byte_stream):
    try:
        byte_stream.decode("utf-8", "strict")
    except:
        return False
    return True


def print_field_header(in_bytes, byte_idx, file=sys.stdout, quiet=False):
    # read header
    header_uint16s = unpack_uint16(in_bytes[byte_idx:byte_idx+8], endian="<")
    header_uint32s = unpack_uint32(in_bytes[byte_idx:byte_idx+8], endian="<")

    field_type = header_uint16s[0]
    field_len = header_uint16s[1]
    field_id = header_uint32s[1]

    # field_len of 1 or 2 means field_len=20
    #   IS THERE EVER LEN 2??
    if field_len == 1:
        field_len = 20
    elif field_len == 2:
        raise Exception("Found Field Length = 2")

    # print header (unless quiet)
    if not quiet:
        print("-"*79, file=file)
        print("byte_idx = "+repr(byte_idx), file=file)
        print("Field Header:", file=file)
        print(file=file)
        print("Field Type  %4d"%field_type, file=file)
        print("Field ID    0x{0:08x} ({0:d})".format(field_id), file=file)
        print("Field Len   %4d"%field_len, file=file)
        print("Field Payload Len   %4d"%(field_len-8), file=file)
        print(file=file)

    return (field_type, field_len, field_id, header_uint16s, header_uint32s)


def read_field(in_bytes, byte_idx, note_str="??", field_ids={},
        file=sys.stdout, quiet=False, report_strings=True):
    field_info = {}

    # quiet=True if Field Type is String and we're not reporting them
    field_type_pre = unpack_uint16(in_bytes[byte_idx:byte_idx+2], endian="<")[0]
    if field_type_pre == 16 and report_strings == False:
        quiet = True

    # read header
    (field_type, field_len, field_id, _, _) = print_field_header(
            in_bytes, byte_idx, file=file, quiet=quiet)

    # get payload bytes
    field_payload = in_bytes[byte_idx+8:byte_idx+field_len]

    # check for references
    # TODO: this will fail if reference is offset by 2 bytes
    references = []
    if len(field_payload) % 4 == 0:
        out_uint32s = unpack_uint32(field_payload, endian="<")
        references = [x for x in out_uint32s if x in field_ids]
        if references and not quiet:
            print("Links to: ", end="", file=file)
            for ref in references:
                print("%d (type %d),"%(ref, field_ids[ref]['type']),
                        end="", file=file)
            print("\n", file=file)

    # report payload if not quiet
    if not quiet:
        print("Field Payload:", file=file)

        if field_type == 0:
            process_payload_type0(in_bytes, byte_idx+8, file=file)
        elif field_type == 16:
            process_payload_type16(field_payload, byte_idx+8, file=file)
        elif field_type in BLOCK_PTR_TYPES:
            process_payload_blockptr(field_payload, field_type=field_type,
                    file=file)
        elif field_type == 100:
            process_payload_type100(field_payload, field_ids=field_ids,
                    file=file)
        elif field_type == 101:
            process_payload_type101(field_payload, field_ids=field_ids,
                    file=file)
        elif field_type == 102:
            process_payload_type102(field_payload, field_ids=field_ids,
                    file=file)
        elif field_type == 131:
            process_payload_type131(field_payload, field_ids=field_ids,
                    file=file)
        elif field_type == 1000:
            process_payload_type1000(field_payload, field_ids=field_ids,
                    file=file)
        else:
            process_payload_generic(field_payload, byte_idx+8, note_str,
                    file=file)

    field_info['type'] = field_type
    field_info['id'] = field_id
    field_info['payload'] = field_payload
    field_info['references'] = references

    return (byte_idx+field_len, field_info)


def process_payload_generic(field_payload, payload_idx, note_str,
        file=sys.stdout, quiet=False):
    # string also shows bytes in hex
    debug_string(
            field_payload, payload_idx, note_str, multiline=True,
            file=file, quiet=quiet)
    if len(field_payload)%2 == 0:
        debug_ushorts(
                field_payload, payload_idx, "ushorts",
                file=file, quiet=quiet)
    if len(field_payload)%4 == 0:
        (out_uints, _) = debug_uints(
                field_payload, payload_idx, "uints",
                file=file, quiet=quiet)
        if any([x > 0x7FFFFFFF for x in out_uints]):
            # only print signed integers if one is different than uint
            debug_ints(
                    field_payload, payload_idx, "ints",
                    file=file, quiet=quiet)


def process_payload_type0(in_bytes, payload_idx, file=sys.stdout, quiet=False):
    # Simple.  End Of Data Block field has no payload
    print(file=file)
    print("** End Of Data Block Field **", file=file)
    print(file=file)


def process_payload_type16(field_payload, payload_idx, file=sys.stdout):
    field_end = len(field_payload) + 8 - 1
    out_string = unpack_string(field_payload)

    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],
            ["8-%d"%field_end, "ASCII", "Null-terminated\n  string", out_string[:-1]],
            ]

    print(AsciiTable(byte_table_data).table, file=file)

    if not is_valid_string(field_payload):
        # some byte does not resolve to valid utf-8 character
        print("Invalid character in string!  Error.", file=file)
        debug_bytes(field_payload, payload_idx, "bytes", file=file)


def process_payload_blockptr(field_payload, field_type,
        file=sys.stdout):
    # payload is 12 bytes long
    uint8s = unpack_uint8(field_payload)
    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    block_num = BLOCK_PTR_TYPES[field_type]

    print("\nField Type %d - Data Block %02d"%(field_type, block_num),
            file=file)

    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],
            ["8-11", "uint32", "Data Block start\n  Byte offset from file start", "%d"%(uint32s[0])],
            ["12-15", "uint32", "Data Block length\n  Length in bytes", "%d"%(uint32s[1])],
            ["16-19", "??", "Unknown", ""],
            ["", "bytes", "", print_list_simple(uint8s[-4:], bits=8, hexfmt=True)],
            ["", "", "", print_list_simple(uint8s[-4:], bits=8)],
            ["", "uint16", "", print_list_simple(uint16s[-2:], bits=16, hexfmt=True)],
            ["", "", "", print_list_simple(uint16s[-2:], bits=16)],
            ["", "uint32", "", print_list_simple(uint32s[-1:], bits=32, hexfmt=True)],
            ["", "", "", print_list_simple(uint32s[-1:], bits=32)],
            ]

    print(AsciiTable(byte_table_data).table, file=file)


def summarize_ref(field_id, field_ids):
    if field_ids.get(field_id, False):
        ref_type = field_ids[field_id]['type']
        if ref_type == 16:
            payload_str = field_ids[field_id]['payload'][:-1].decode("utf-8", "ignore")
            ref_string = "'"+payload_str+"'"
        else:
            ref_string = "Field Type %d"%ref_type
    else:
        ref_string = "??"

    return ref_string


def process_payload_type100(field_payload, field_ids={},
        file=sys.stdout):
    # every 36 bytes is a new Data Item
    # each uint at bytes 12-15 + 36*N is a reference to Field Type 16
    ditem_len = 36

    num_data_items = len(field_payload)//ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],]

    for i in range(num_data_items):
        bstart = i*ditem_len + 8
        u16start = i*(ditem_len//2)
        u32start = i*(ditem_len//4)

        ref_string = summarize_ref(uint32s[u32start+3], field_ids)

        byte_table_datitem = [
                ["%d-%d"%(bstart, bstart+3), "uint16", "Item %d Unknown0"%i,
                    print_list_simple(uint16s[u16start:u16start+2], bits=16)],
                ["%d-%d"%(bstart+4, bstart+7), "uint32", "Item %d Num Words"%i,
                    print_list_simple(uint32s[u32start+1:u32start+2], bits=32)],
                ["%d-%d"%(bstart+8, bstart+11), "uint32", "Item %d Pointer Byte Offset"%i,
                    print_list_simple(uint32s[u32start+2:u32start+3], bits=32)],
                ["%d-%d"%(bstart+12, bstart+15), "uint32", "Item %d Reference"%i,
                    print_list_simple(uint32s[u32start+3:u32start+4], bits=32)],
                ["", "", "", "(%s)"%ref_string],
                ["%d-%d"%(bstart+16, bstart+19), "uint16", "Item %d Unknown1"%i,
                    print_list_simple(uint16s[u16start+8:u16start+10], bits=16)],
                ["%d-%d"%(bstart+20, bstart+23), "uint32", "Item %d Word Size (bytes)"%i,
                    print_list_simple(uint32s[u32start+5:u32start+6], bits=32)],
                ["%d-%d"%(bstart+24, bstart+27), "uint16", "Item %d Unknown2"%i,
                    print_list_simple(uint16s[u16start+12:u16start+14], bits=16)],
                ["%d-%d"%(bstart+28, bstart+31), "uint16", "Item %d Unknown3"%i,
                    print_list_simple(uint16s[u16start+14:u16start+16], bits=16)],
                ["%d-%d"%(bstart+32, bstart+35), "uint16", "Item %d Unknown4"%i,
                    print_list_simple(uint16s[u16start+16:u16start+18], bits=16)],
                ["-----", "------", "------------------", "----------------"],
                ]
        byte_table_data.extend(byte_table_datitem)

    # get rid of last "----" row
    del byte_table_data[-1]

    print(AsciiTable(byte_table_data).table, file=file)


def process_payload_type101(field_payload, field_ids={},
        file=sys.stdout):
    # every 20 bytes is a new Data Item
    # each uint at bytes 8-11 + 20*N is a reference
    # each uint at bytes 16-19 + 20*N is a reference
    ditem_len = 20

    num_data_items = len(field_payload)//ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],]

    for i in range(num_data_items):
        bstart = i*ditem_len + 8
        u16start = i*(ditem_len//2)
        u32start = i*(ditem_len//4)

        ref_string0 = summarize_ref(uint32s[u32start+2], field_ids)
        ref_string1 = summarize_ref(uint32s[u32start+4], field_ids)

        byte_table_datitem = [
                ["%d-%d"%(bstart, bstart+3), "uint16", "Item %d Unknown0"%i,
                    print_list_simple(uint16s[u16start:u16start+2], bits=16)],
                ["%d-%d"%(bstart+4, bstart+7), "uint16", "Item %d Unknown1"%i,
                    print_list_simple(uint16s[u16start+2:u16start+4], bits=16)],
                ["%d-%d"%(bstart+8, bstart+11), "uint32", "Item %d Reference"%i,
                    print_list_simple(uint32s[u32start+2:u32start+3], bits=32)],
                ["", "", "", "(%s)"%ref_string0],
                ["%d-%d"%(bstart+12, bstart+15), "uint32",
                    "Item %d Total bytes pointed\n  to by above reference"%i,
                    print_list_simple(uint32s[u32start+3:u32start+4], bits=32)],
                ["%d-%d"%(bstart+16, bstart+19), "uint32", "Item %d Reference"%i,
                    print_list_simple(uint32s[u32start+4:u32start+5], bits=32)],
                ["", "", "", "(%s)"%ref_string1],
                ["-----", "------", "----------------", "----------------"],
                ]
        byte_table_data.extend(byte_table_datitem)

    # get rid of last "----" row
    del byte_table_data[-1]

    print(AsciiTable(byte_table_data).table, file=file)


def process_payload_type102(field_payload, field_ids={},
        file=sys.stdout):
    # every 16 bytes is a new Data Item
    # each uint at bytes 8-11 + 16*N is a reference
    # each uint at bytes 12-15 + 16*N is a reference
    ditem_len = 16

    num_data_items = len(field_payload)//ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],]

    for i in range(num_data_items):
        bstart = i*ditem_len + 8
        u16start = i*(ditem_len//2)
        u32start = i*(ditem_len//4)

        ref_string0 = summarize_ref(uint32s[u32start+2], field_ids)
        ref_string1 = summarize_ref(uint32s[u32start+3], field_ids)

        byte_table_datitem = [
                ["%d-%d"%(bstart, bstart+3), "uint16", "Item %d Unknown0"%i,
                    print_list_simple(uint16s[u16start:u16start+2], bits=16)],
                ["%d-%d"%(bstart+4, bstart+7), "uint16", "Item %d Unknown1"%i,
                    print_list_simple(uint16s[u16start+2:u16start+4], bits=16)],
                ["%d-%d"%(bstart+8, bstart+11), "uint32", "Item %d Reference"%i,
                    print_list_simple(uint32s[u32start+2:u32start+3], bits=32)],
                ["", "", "", "(%s)"%ref_string0],
                ["%d-%d"%(bstart+12, bstart+15), "uint32", "Item %d Reference"%i,
                    print_list_simple(uint32s[u32start+3:u32start+4], bits=32)],
                ["", "", "", "(%s)"%ref_string1],
                ["-----", "------", "----------------", "----------------"],
                ]
        byte_table_data.extend(byte_table_datitem)

    # get rid of last "----" row
    del byte_table_data[-1]

    print(AsciiTable(byte_table_data).table, file=file)


def process_payload_type131(field_payload, field_ids={},
        file=sys.stdout):
    # every 12 bytes is a new Data Item
    # each uint at bytes 4-7 + 12*N is a reference
    ditem_len = 12

    num_data_items = len(field_payload)//ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],]

    for i in range(num_data_items):
        bstart = i*ditem_len + 8
        u16start = i*(ditem_len//2)
        u32start = i*(ditem_len//4)

        ref_string0 = summarize_ref(uint32s[u32start], field_ids)
        ref_string1 = summarize_ref(uint32s[u32start+1], field_ids)

        byte_table_datitem = [
                ["%d-%d"%(bstart, bstart+3), "uint32", "Item %d Reference"%i,
                    print_list_simple(uint32s[u32start:u32start+1], bits=32)],
                ["", "", "", "(%s)"%ref_string0],
                ["%d-%d"%(bstart+4, bstart+7), "uint32", "Item %d Reference"%i,
                    print_list_simple(uint32s[u32start+1:u32start+2], bits=32)],
                ["", "", "", "(%s)"%ref_string1],
                ["%d-%d"%(bstart+8, bstart+11), "uint16", "Item %d Unknown"%i,
                    print_list_simple(uint16s[u16start+4:u16start+6], bits=16)],
                ["-----", "------", "----------------", "----------------"],
                ]
        byte_table_data.extend(byte_table_datitem)

    # get rid of last "----" row
    del byte_table_data[-1]

    print(AsciiTable(byte_table_data).table, file=file)


def process_payload_type1000(field_payload, field_ids={},
        file=sys.stdout, quiet=False):
    # string also shows bytes in hex
    debug_string(
            field_payload, 0, "bytes", multiline=True,
            file=file)
    if len(field_payload)%2 == 0:
        debug_ushorts(
                field_payload, 0, "uint16s",
                file=file)
    if len(field_payload)%4 == 0:
        (out_uints, _) = debug_uints(
                field_payload, 0, "uint32s",
                file=file)
        if any([x > 0x7FFFFFFF for x in out_uints]):
            # only print signed integers if one is different than uint
            debug_ints(
                    field_payload, 0, "int32s",
                    file=file)


#def read_field_type1007(in_bytes, byte_idx, note_str="??", field_data={},
#        file=sys.stdout):
#    # TODO: extract data for future field_type=16
#    field_info = {}
#    # read header
#    (field_type, field_len, field_id, header_ushorts, header_uints) = print_field_header(
#            in_bytes, byte_idx, file=file)
#
#    # read payload
#    print("Field Payload:", file=file)
#    field_payload = in_bytes[byte_idx+8:byte_idx+field_len]
#
#    (out_string, _) = debug_string(
#            field_payload, 0, "string", multiline=True, file=file)
#    (out_uints, _) = debug_uints(
#            field_payload, byte_idx+8, "uints", file=file)
#    if any([x>0x7FFFFFFF for x in out_uints]):
#        (out_ints, _) = debug_ints(
#                field_payload, byte_idx+8, "ints", file=file)
#
#    # TODO: what is the format of this??
#    #for i in range(len(out_uints)//4):
#    #    field_data[out_uints[i*4+3]] = out_uints[i*4:i*4+4]
#
#    field_info['type'] = field_type
#    field_info['payload'] = field_payload
#    field_info['data'] = field_data
#    return (byte_idx+field_len, field_info)


#def read_field_type1022(in_bytes, byte_idx, note_str="??", field_data={},
#        file=sys.stdout):
#    field_info = {}
#    # read header
#    (field_type, field_len, field_id, header_ushorts, header_uints) = print_field_header(
#            in_bytes, byte_idx, file=file)
#
#    # read payload
#    print("Field Payload:", file=file)
#    field_payload = in_bytes[byte_idx+8:byte_idx+field_len]
#
#    (out_string, _) = debug_string(
#            field_payload, 0, "string", multiline=True, file=file)
#    (out_uints, _) = debug_uints(
#            field_payload, byte_idx+8, "uints", file=file)
#    if any([x>0x7FFFFFFF for x in out_uints]):
#        (out_ints, _) = debug_ints(
#                field_payload, byte_idx+8, "ints", file=file)
#
#    # first three uints are data_id tags, no associated data
#    field_data[out_uints[0]] = [b'', 1022, byte_idx, byte_idx+8]
#    field_data[out_uints[1]] = [b'', 1022, byte_idx, byte_idx+8+4]
#    field_data[out_uints[2]] = [b'', 1022, byte_idx, byte_idx+8+8]
#
#    field_info['type'] = field_type
#    field_info['payload'] = field_payload
#    field_info['data'] = field_data
#    return (byte_idx+field_len, field_info)


#def jump_idx(jump_from, jump_to, chk_field_start, chk_byte_idx,
#        file=sys.stdout):
#    if chk_field_start==jump_from and chk_byte_idx==jump_from:
#        print("---------------------------------------------------------", file=file)
#        print("jump of delta {0:d}=0x{0:x}".format(jump_to-jump_from), file=file)
#
#        # find how many zeros:
#        test_byte_stream = in_bytes[jump_from:jump_to].lstrip(b'\x00')
#        num_zeros = len(in_bytes[jump_from:jump_to])-len(test_byte_stream)
#        if num_zeros > 0:
#            print("%6d-%6d"%(jump_from,jump_from+num_zeros-1), end="", file=file)
#            print("   All Zeros %d*(0,)"%(num_zeros), file=file)
#            jump_from = jump_from+num_zeros
#
#        #(out_bytes, _) = debug_bytes(
#        #        in_bytes[jump_from:jump_to], jump_from, "jumped bytes",
#        #        file=file)
#        (out_shorts, _) = debug_ushorts(
#                in_bytes[jump_from:jump_to], jump_from, "jumped shorts",
#                file=file)
#        return jump_to
#    else:
#        return byte_idx


# Debugging routine used to search backwards from known field to try and find
#   previous possible fields
# Not really used anymore
def search_backwards(in_bytes, field_start, level=0, min_search_idx=0, file=sys.stdout):
    idx = field_start - 2
    possibles = []
    while idx >= min_search_idx:
        test_uint16s = unpack_uint16(in_bytes[idx:idx+2], endian="<")
        test_ushort = test_uint16s[0]
        if idx - 2 + test_ushort == field_start:
            #read_field(in_bytes, idx-2, note_str="field")
            possibles.append(idx-2)
        idx = idx-1
    for possible_idx in possibles:
        print("  "*level+"idx=%d: possible field start, back from %d"%(possible_idx, field_start), file=file)
        search_backwards(
                in_bytes,
                possible_idx,
                level=level+1,
                min_search_idx=min_search_idx
                )


def parse_datablock(field_payload):
    out_uint32s = unpack_uint32(field_payload, endian="<")
    data_start = out_uint32s[0]
    data_len = out_uint32s[1]
    return(data_start, data_len)


def process_datablock_header(header_bytes, byte_idx, block_num,
        file=sys.stdout):
    print("="*79, file=file)
    print("byte_idx = "+repr(byte_idx), file=file)
    print("Data Block %02d Header"%block_num, file=file)

    # table header row
    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],]

    uint32s = unpack_uint32(header_bytes, endian="<")

    bstart = 0

    byte_table_datitem = [
            ["%d-%d"%(bstart, bstart+3), "uint32",
                "Data Block Length of\n  all fields (bytes)",
                print_list_simple(uint32s[0:1], bits=32)],
            ["%d-%d"%(bstart+4, bstart+8), "uint32",
                "Data Block Number of\n  Different Field Types",
                print_list_simple(uint32s[1:2], bits=32)],
            ]
    byte_table_data.extend(byte_table_datitem)

    print(AsciiTable(byte_table_data).table, file=file)



def process_datablock_footer(footer_bytes, byte_idx, block_num,
        file=sys.stdout):
    print("-"*79, file=file)
    print("byte_idx = "+repr(byte_idx), file=file)
    print("Data Block %s Footer"%block_num, file=file)

    # table header row
    byte_table_data = [
            ["Field\nBytes", "Type", "Description", "Value(s)"],]

    for i in range(len(footer_bytes)//14):
        uint16s = unpack_uint16(footer_bytes[i*14:(i+1)*14], endian="<")
        uint32s = unpack_uint32(footer_bytes[i*14+2:(i+1)*14], endian="<")

        # bstart is byte number in field
        bstart = i * 14

        # print this batch of 7 uint16s
        byte_table_datitem = [
                ["%d-%d"%(bstart, bstart+1), "uint16",
                    "Item %d Data Block\n  Field Type"%i,
                    print_list_simple(uint16s[0:1], bits=16)],
                ["%d-%d"%(bstart+2, bstart+5), "uint32",
                    "Item %d Data Block\n  Num. Occurrences A"%i,
                    print_list_simple(uint32s[0:1], bits=32)],
                ["%d-%d"%(bstart+6, bstart+9), "uint32",
                    "Item %d Data Block\n  Num. Occurrences B"%i,
                    print_list_simple(uint32s[1:2], bits=32)],
                ["%d-%d"%(bstart+10, bstart+13), "uint32",
                    "Item %d Data Block\n  Unknown"%i,
                    print_list_simple(uint32s[2:3], bits=32)],
                ["-----", "------", "------------------", "----------------"],
                ]
        byte_table_data.extend(byte_table_datitem)

    # get rid of last "----" row
    del byte_table_data[-1]

    print(AsciiTable(byte_table_data).table, file=file)

def print_datablock(in_bytes, data_start, data_len, block_num, field_ids={},
        file=sys.stdout, report_strings=True):
    print("="*78, file=file)
    print("DATA BLOCK %s"%block_num, file=file)
    print("Start: %d"%(data_start), file=file)
    print("End:   %d"%(data_start + data_len), file=file)
    print(file=file)

    byte_idx = data_start
    process_datablock_header(in_bytes[byte_idx:byte_idx+8], byte_idx, block_num,
        file=file)
    byte_idx += 8

    # print all fields in data block
    while byte_idx < data_start + data_len:
        (byte_idx, field_info) = read_field(in_bytes, byte_idx,
                field_ids=field_ids, file=file,
                report_strings=report_strings)

        if field_info['type'] == 0:
            # End Of Data Block field
            break

    # Print Data Block Footer
    process_datablock_footer(in_bytes[byte_idx:data_start+data_len],
            byte_idx, block_num, file=file)


def get_next_data_block_end(byte_idx, data_start, data_len):
    #block_num = 0
    #end_idx = data_start[0] + data_len[0]

    for i in range(11):
        if byte_idx < data_start[i] + data_len[i]:
            block_num = i
            end_idx = data_start[i] + data_len[i]
            break
    return (block_num, end_idx)


def report_whole_file(in_bytes, field_ids, data_start, data_len,
        filedir, filename, report_strings=True):
    try:
        out_fh = open(os.path.join(filedir, "dump.txt"), "w")
    except:
        print("Error opening dump.txt")

    print(filename, file=out_fh)

    # FILE HEADER

    # read 11 fields to Data Block Pointers in File Header
    byte_idx = 160
    for i in range(11):
        (byte_idx, field_info) = read_field(
                in_bytes, byte_idx, field_ids=field_ids, file=out_fh)

    print("-"*78, file=out_fh)
    print("byte_idx: %d-%d"%(byte_idx,data_start[0]-1),file=out_fh)
    print(file=out_fh)
    print("All Zeros",file=out_fh)
    print(file=out_fh)

    # DATA BLOCKS

    # get + print Data Block 0 Header
    byte_idx = data_start[0]
    process_datablock_header(in_bytes[byte_idx:byte_idx+8], byte_idx, 0,
        file=out_fh)

    # start again at beginning of Data Block 0
    byte_idx = data_start[0] + 8
    # read all fields in file after File Header
    while byte_idx < len(in_bytes):
        field_start = byte_idx
        (byte_idx, field_info) = read_field(
                in_bytes, byte_idx, field_ids=field_ids, file=out_fh,
                report_strings=report_strings)
        
        if field_info['type'] == 0:
            # we just saw an End Of Data Block Field
            (block_num, end_idx) = get_next_data_block_end(
                    byte_idx, data_start, data_len)

            process_datablock_footer(in_bytes[byte_idx:end_idx],
                    byte_idx, block_num, file=out_fh)

            byte_idx = end_idx
            if block_num + 1 < 10:
                process_datablock_header(in_bytes[byte_idx:byte_idx+8],
                        byte_idx, block_num+1, file=out_fh)

            byte_idx = end_idx + 8

        # break if we still aren't advancing
        if byte_idx == field_start:
            print("ERROR BREAK!!!!", file=out_fh)
            print("-----------------------------------------------------------",
                    file=out_fh)
            break

        if byte_idx > data_start[10]:
            byte_idx = data_start[10]
            print("="*79, file=out_fh)
            print("byte_idx = "+repr(byte_idx), file=out_fh)
            print(file=out_fh)
            print("Data Block 10 Start", file=out_fh)
            print(file=out_fh)
            print("%d-%d     Image Data"%(byte_idx,byte_idx+data_len[10]),
                file=out_fh)
            print(file=out_fh)
            print("="*79, file=out_fh)
            break

    out_fh.close()


def report_datablocks(in_bytes, data_start, data_len, field_ids,
        filedir, filename, report_strings=True):
    # parse data blocks 0-9
    for i in range(0, 10):
        # Data Block
        try:
            out_fh = open(os.path.join(filedir, "data%02d.txt"%i), "w")
        except:
            print("Error opening data%02d.txt"%i, file=sys.stderr)
            raise

        print(filename, file=out_fh)

        print_datablock(
                in_bytes,
                data_start[i], data_len[i], i,
                field_ids=field_ids, file=out_fh,
                report_strings=report_strings)
        out_fh.close()

    # Data Block 10 - Image Data
    try:
        out_fh = open(os.path.join(filedir, "data10_img.txt"), "w")
    except:
        print("Error opening data10_img.txt")
    print("===================================================================",
            file=out_fh)
    print("IMAGE DATA BLOCK", file=out_fh)
    print(file=out_fh)
    #print_datablock(data_start[10], data_len[10], "10", file=out_fh)
    data_end = data_start[10] + data_len[10]
    print("Image Data: (%d-%d)"%(data_start[10], data_end-1), file=out_fh)
    #(img_ushorts, _) = debug_ushorts(
    #        in_bytes[data_start[10]:data_end],
    #        data_start[10], "img_data", file=out_fh)
    #for img_ushort in img_ushorts:
    #    print(img_ushort, file=out_fh)
    print(file=out_fh)
    print(file=out_fh)


def indent_str(recurse_level):
    return "    "*recurse_level


def recurse_fields(field_id, field_ids, recurse_level, found_ids,
        file=sys.stdout):
    this_field = field_ids[field_id]
    this_payload = this_field['payload']

    ind = indent_str(recurse_level)
    print("%sfield_type=%4d"%(ind, this_field['type']), end="", file=file)
    print("  field_id=0x{0:08x} ({0:d})".format(this_field['id']),
            file=file)

    if field_id not in found_ids:
        found_ids.append(field_id)
    else:
        # prevent loops and return of not just text
        #print("repeated ID: %d, type %d"%(field_id,this_field['type']))
        #print("  payload: %s"%(this_field['payload'].decode("utf-8","ignore")))
        if this_field['type'] != 16:
            print("%sRepeated ID (loop)"%ind, file=file)
            return

    if this_field.get('references', None):
        if len(this_payload)%4 == 0:
            if this_field['type'] == 100:
                i = 0
                while i < len(this_payload):
                    debug_ushorts(this_payload[i:i+12], i,
                            "", var_tab=ind, file=file)
                    out_uint32s = unpack_uint32(this_payload[i+12:i+16], endian="<")
                    recurse_fields(out_uint32s[0], field_ids, recurse_level+1,
                            found_ids, file=file)
                    debug_ushorts(this_payload[i+16:i+36],
                            i+16, "", var_tab=ind, file=file)
                    i = i+36
            else:
                out_uint32s = unpack_uint32(this_payload, endian="<")

                last_i = 0
                for (i, x) in enumerate(out_uint32s):
                    if x in this_field['references']:
                        if last_i < i*4:
                            debug_ushorts(
                                    this_payload[last_i:i*4], last_i, "",
                                    var_tab=ind, file=file)
                        ref = x
                        last_i = (i+1)*4
                        print("%s%d-%d:"%(ind, i*4, i*4+3), file=file)
                        recurse_fields(ref, field_ids, recurse_level+1, found_ids,
                                file=file)
                if last_i < len(this_payload):
                    debug_ushorts(this_payload[last_i:], last_i, "", var_tab=ind,
                            file=file)
        else:
            raise Exception("references, but payload not a multiple of 4!!")
    else:
        if this_field['type'] == 16:
            print(ind+this_payload[:-1].decode('utf-8', 'ignore'), file=file)
        else:
            debug_ushorts(this_payload, 0, "", var_tab=ind,
                    file=file)
    #print(file=file)


def report_hierarchy(field_ids, is_referenced, filedir):
    # roots types: 102, 1000, 1004, 1015
    # type 1000 hierarchy may have loops!
    try:
        out_fh = open(os.path.join(filedir, "hierarchy.txt"), "w")
    except:
        print("Error opening hierarchy.txt")
        raise

    found_ids = []
    missed_ids = [x for x in field_ids]

    field_ids_norefs = [x for x in field_ids if not is_referenced.get(x, False)]
    field_ids_norefs = [x for x in field_ids_norefs if field_ids[x]['type'] != 16]
    field_ids_norefs.sort()
    root_ids = field_ids_norefs

    root_types = [102, 1000, 1004, 1015]
    root_ids = [x for x in field_ids if field_ids[x]['type'] in root_types]

    for field_id in root_ids:
        print("-------------------------------------------------------------",
                file=out_fh)
        recurse_fields(field_id, field_ids, 0, found_ids, file=out_fh)
    print("-------------------------------------------------------------",
            file=out_fh)

    for this_id in found_ids:
        missed_ids.remove(this_id)
    print("missed_ids:", end="", file=out_fh)
    print(missed_ids, file=out_fh)

    out_fh.close()


def parse_file(filename, report_strings=True):
    print(filename)

    filename = os.path.realpath(filename)
    filedir = os.path.dirname(filename)

    with open(filename, 'rb') as in_fh:
        in_bytes = in_fh.read()

    byte_idx = 160

    #SEARCH DEBUG
    #search_backwards(in_bytes, len(in_bytes)-1, min_search_idx=59881)
    #exit()

    # dict of keys: field_ids, items: field_payloads
    field_ids = {}

    # PASS 1
    #   get all fields, field_id

    # reset loop variables
    byte_idx = 160
    data_start = {}
    data_len = {}
    
    # read 11 fields to Data Block Pointers in File Header
    byte_idx = 160
    for i in range(11):
        (byte_idx, field_info) = read_field(in_bytes, byte_idx, quiet=True)
        block_num = BLOCK_PTR_TYPES[field_info['type']]
        (data_start[block_num], data_len[block_num]) = parse_datablock(
            field_info['payload'])
    
    # read all remaining fields in file after Data Block 0 Header
    byte_idx = data_start[0] + 8
    while byte_idx < len(in_bytes):
        field_start = byte_idx

        (byte_idx, field_info) = read_field(
                in_bytes, byte_idx,
                note_str="",
                quiet=True
                )

        if field_info['type'] == 0:
            # we just saw an End Of Data Block Field
            (block_num, end_idx) = get_next_data_block_end(
                    byte_idx, data_start, data_len)

            # skip past Data Block Footer and Header to first field
            #   of next Data Block
            byte_idx = end_idx + 8

        if field_info['id'] != 0:
            field_ids[field_info['id']] = field_info

        # break if we still aren't advancing
        if byte_idx == field_start:
            break

        if byte_idx > data_start[10]:
            break

    # reset byte_idx to right after Data Block 0 Header
    byte_idx = data_start[0]+8

    # keep track of all fields that were referenced
    is_referenced = {}

    # now that we know all data_ids, find all references
    while byte_idx < len(in_bytes):
        field_start = byte_idx

        (byte_idx, field_info) = read_field(
                in_bytes, byte_idx,
                note_str="",
                quiet=True,
                field_ids=field_ids
                )

        if field_info['id'] != 0:
            # update references field using field_info
            field_ids[field_info['id']] = field_info

            for ref in field_info['references']:
                is_referenced[ref] = True

        # break if we still aren't advancing
        if byte_idx == field_start:
            break

        if byte_idx > data_start[10]:
            break

    # PASS 2
    #   report on whole file to dump.txt
    report_whole_file(in_bytes, field_ids, data_start, data_len,
            filedir, filename, report_strings=report_strings)

    # PASS 3
    #   report data blocks in separate files
    report_datablocks(in_bytes, data_start, data_len, field_ids,
            filedir, filename, report_strings=report_strings)

    # PASS 4
    #   report on hierarchy
    report_hierarchy(field_ids, is_referenced,
            filedir)


def process_command_line(argv):
    """
    Return args struct
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    #script_name = argv[0]
    argv = argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(
            description="Recurse through srcdir, copying all images to top-level of destdir")

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument('srcfile', nargs='+',
            help="Source 1sc file(s)."
            )

    # switches/options:
    parser.add_argument(
        '-S', '--omit_strings', action='store_true', default=False,
        help='Do not include Type 16 String fields in reports. ' \
                '(But include the strings when listing references to them.)')
    #parser.add_argument(
    #    '-o', '--omit_hidden', action='store_true',
    #    help='Do not copy picasa hidden images to destination directory.')

    #(settings, args) = parser.parse_args(argv)
    args = parser.parse_args(argv)

    return args


def main(argv=None):
    args = process_command_line(argv)
    for filename in args.srcfile:
        parse_file(filename, report_strings=not args.omit_strings)
    return 0


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        # exit error code for Ctrl-C
        status = 130

    sys.exit(status)


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
