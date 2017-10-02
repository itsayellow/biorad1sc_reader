#!/usr/bin/env python3

"""
Low-level routines to parse a Bio-Rad *.1sc file.  Intended to be
used internally only.
"""

import sys
import time
import struct
from biorad1sc_reader.constants import REGION_DATA_TYPES, REGION_DATA_TYPE_BYTES


def is_ascii(byte_stream):
    """
    If all bytes are normal ascii text with no control characters other
    than NULL, LF, CR, TAB, then return True, else False.
    """
    ok_ascii_byte = [0, 9, 10, 13] + list(range(32, 127))
    return all([byte in ok_ascii_byte for byte in byte_stream])


def unpack_string(byte_stream):
    """
    Return decoded ASCII string from bytestring.
    """
    out_string = byte_stream.decode("utf-8", "replace")
    return out_string


def unpack_double(byte_stream, endian="<"):
    """
    Return list of uint16s, (either endian) from bytestring.
    """
    num_double = len(byte_stream)//8
    out_double = struct.unpack(endian+"d"*num_double, byte_stream)
    return out_double


def unpack_uint8(byte_stream):
    """
    Return list of bytes from bytestring.
    """
    num_uint8 = len(byte_stream)
    out_uint8s = struct.unpack("B"*num_uint8, byte_stream)
    return out_uint8s


def unpack_uint16(byte_stream, endian="<"):
    """
    Return list of uint16s, (either endian) from bytestring.
    """
    num_uint16 = len(byte_stream)//2
    out_uint16s = struct.unpack(endian+"H"*num_uint16, byte_stream)
    return out_uint16s


def unpack_uint32(byte_stream, endian="<"):
    """
    Return list of uint32s, (either endian) from bytestring.
    """
    num_uint32 = len(byte_stream)//4
    out_uint32s = struct.unpack(endian+"I"*num_uint32, byte_stream)
    return out_uint32s


def unpack_uint64(byte_stream, endian="<"):
    """
    Return list of uint64s, (either endian) from bytestring.
    """
    num_uint64 = len(byte_stream)//8
    out_uint64s = struct.unpack(endian+"Q"*num_uint64, byte_stream)
    return out_uint64s


def process_payload_type102(field_payload, field_ids=None):
    """
    Process the payload of a 1sc Field Type 102, returning the relevant
    data to a dict.
    """
    if field_ids is None:
        field_ids = {}
    field_info_payload = {}

    assert len(field_payload) == 16, \
            "Field Type 102 should have length of 20"

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")
    ref_label = uint32s[3]
    collection_label = field_ids[ref_label]['payload'].rstrip(b"\x00")
    collection_label = collection_label.decode('utf-8', 'ignore')

    # number of items in this collection
    field_info_payload['collection_num_items'] = uint16s[3]
    # label for this collection
    field_info_payload['collection_label'] = collection_label
    # reference to next field type 101
    field_info_payload['collection_ref'] = uint32s[2]

    return field_info_payload


def process_payload_type101(field_payload, field_ids=None):
    """
    Process the payload of a 1sc Field Type 101, returning the relevant
    data to a dict.
    """
    if field_ids is None:
        field_ids = {}
    field_info_payload = {}
    field_payload_items = {}

    assert len(field_payload) % 20 == 0, \
            "Field Type 101: payload size should be multiple of 20 bytes"

    # every 20 bytes is a new Data Item
    # each uint at bytes 8-11 + 20*N is a reference
    # each uint at bytes 16-19 + 20*N is a reference
    ditem_len = 20

    num_data_items = len(field_payload)//ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    for i in range(num_data_items):
        u16start = i*(ditem_len//2)
        u32start = i*(ditem_len//4)

        ref_label = uint32s[u32start+4]
        item_label = field_ids[ref_label]['payload'].rstrip(b"\x00")
        item_label = item_label.decode('utf-8', 'ignore')

        data_field_type = uint16s[u16start]

        assert field_payload_items.get(data_field_type, False) is False, \
                "Field Type 101: multiple entries, same data field type"

        field_payload_items[data_field_type] = {}
        field_payload_items[data_field_type]['num_regions'] = uint16s[u16start+3]
        field_payload_items[data_field_type]['data_key_ref'] = uint32s[u32start+2]
        field_payload_items[data_field_type]['total_bytes'] = uint32s[u32start+3]
        field_payload_items[data_field_type]['label'] = item_label

        # put indicator in id for data_key as to total bytes explained
        #   by data key, in case it is missing the word_size bytes
        field_ids[uint32s[u32start+2]]['data_key_total_bytes'] = uint32s[u32start+3]

    field_info_payload['items'] = field_payload_items

    return field_info_payload


def fix_wordsize_zero(field_payload_regions, byte_offsets,
        data_key_total_bytes):
    """
    Fix Datakey data when Field Type 100 doesn't list word_size for one
    or more data regions of a data type
    """
    # The following is based on two problemmatic files seen, having:
    #   0 where word_size should be
    # we need to now go back and fix all word_size fields, because in those
    #   annoying 1sc files the datakey subfield is often (not always) 0

    byte_offsets.sort()
    # add an extra offset for next byte after datakey definition
    byte_offsets.append(data_key_total_bytes)
    # regions sizes is a dict where key is byte_offset, item is region_size
    region_sizes = {}
    for i in range(len(byte_offsets)-1):
        region_sizes[byte_offsets[i]] = byte_offsets[i+1] - byte_offsets[i]

    for pay_reg_num in field_payload_regions:
        pay_reg = field_payload_regions[pay_reg_num]
        if pay_reg['word_size'] == 0:
            # broken so fix
            if pay_reg['data_type'] in REGION_DATA_TYPE_BYTES:
                pay_reg['word_size'] = REGION_DATA_TYPE_BYTES[pay_reg['data_type']]
            else:
                # if we don't know word_size from data_type, fall back on this
                #   method, not 100% reliable
                # declare word_size as enough for word_size*num_words to be
                #   total bytes until next known region or end of payload
                pay_reg['word_size'] = region_sizes[pay_reg['byte_offset']]//pay_reg['num_words']


def process_payload_type100(field_payload, data_key_total_bytes,
        field_ids=None):
    """
    Process the payload of a 1sc Field Type 100, returning the relevant
    data to a dict.
    """
    if field_ids is None:
        field_ids = {}
    field_info_payload = {}
    field_payload_regions = {}

    assert len(field_payload) % 36 == 0, \
            "Field Type 100: payload size should be multiple of 36 bytes"

    # every 36 bytes is a new Data Item
    # each uint at bytes 12-15 + 36*N is a reference to Field Type 16
    ditem_len = 36

    num_data_items = len(field_payload)//ditem_len

    uint16s = unpack_uint16(field_payload, endian="<")
    uint32s = unpack_uint32(field_payload, endian="<")

    byte_offsets = []
    has_wordsize_zero = False
    for i in range(num_data_items):
        u16start = i*(ditem_len//2)
        u32start = i*(ditem_len//4)

        ref_label = uint32s[u32start+3]
        region_label = field_ids[ref_label]['payload'].rstrip(b"\x00")
        region_label = region_label.decode('utf-8', 'ignore')

        field_payload_regions[i] = {}
        field_payload_regions[i]['data_type'] = uint16s[u16start]
        field_payload_regions[i]['label'] = region_label
        field_payload_regions[i]['index'] = uint16s[u16start+1]
        field_payload_regions[i]['num_words'] = uint32s[u32start+1]
        field_payload_regions[i]['byte_offset'] = uint32s[u32start+2]
        field_payload_regions[i]['word_size'] = uint32s[u32start+5]
        field_payload_regions[i]['ref_field_type'] = uint16s[u16start+13]

        byte_offsets.append(field_payload_regions[i]['byte_offset'])
        if uint32s[u32start+5] == 0:
            has_wordsize_zero = True

    if has_wordsize_zero:
        # fix data_key data if any word_size=0 in data_key
        fix_wordsize_zero(field_payload_regions, byte_offsets,
                data_key_total_bytes)

    field_info_payload['regions'] = field_payload_regions

    return field_info_payload


def process_data_region(region, payload, field_ids, data_types, visited_ids):
    """
    Process one region of one data container field.
    """
    region_data = {}
    data_region_start = region['byte_offset']
    data_region_end = region['byte_offset'] + \
            region['word_size'] * region['num_words']
    data_raw = payload[data_region_start:data_region_end]
    region_data['raw'] = data_raw

    # DEBUG DELETEME
    #print("region" + repr(region), file=sys.stderr)
    #print("payload" + repr(payload), file=sys.stderr)
    #print("data_region_start " + repr(data_region_start), file=sys.stderr)
    #print("data_region_end " + repr(data_region_end), file=sys.stderr)
    #print("data_raw " + repr(data_raw), file=sys.stderr)

    data_proc = None
    data_interp = None

    if region['data_type'] in [1, 2]:
        # byte / ASCII
        if len(data_raw) > 1 and is_ascii(data_raw):
            data_proc = data_raw.rstrip(b"\x00").decode('utf-8', 'ignore')
        else:
            data_proc = unpack_uint8(data_raw)
            data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
    elif region['data_type'] in [3, 4]:
        # u?int16
        data_proc = unpack_uint16(data_raw, endian="<")
        data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
    elif region['data_type'] in [5, 6, 9, 21]:
        # u?int32
        data_proc = unpack_uint32(data_raw, endian="<")
        data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
        if region['label'].endswith("time"):
            data_interp = time.asctime(time.gmtime(data_proc)) + " UTC"
    elif region['data_type'] in [7,]:
        # u?int64
        data_proc = unpack_uint64(data_raw, endian="<")
        data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
    elif region['data_type'] in [10,]:
        # double (float)
        data_proc = unpack_double(data_raw, endian="<")
        data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
    elif region['data_type'] in [15, 17]:
        # uint32 Reference
        data_proc = unpack_uint32(data_raw, endian="<")
        data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
        this_ref = data_proc
        if this_ref != 0:
            if field_ids[this_ref]['type'] == 16:
                region_str = field_ids[this_ref]['payload'][:-1]
                data_interp = region_str.decode("utf-8", "ignore")
            else:
                field_info_ref = field_ids[this_ref]
                # recurse into the data container field referenced
                regions_list = process_payload_data_container(
                        field_info_ref,
                        data_types,
                        field_ids,
                        visited_ids
                        )
                data_interp = {}
                data_interp['data'] = regions_list
                data_interp['label'] = data_types[field_info_ref['type']]['label']
                data_interp['id'] = field_info_ref['id']
                data_interp['type'] = field_info_ref['type']

                visited_ids.append(field_info_ref['id'])
        else:
            data_interp = None
    else:
        pass
        # TODO: make generic data types work based on word_size?
        #print("Data Type "+ repr(region['data_type']) + " is Unknown",
        #        file=sys.stderr)
        #print("  word_size: " + repr(region['word_size']))
        #print("  num_words: " + repr(region['num_words']))

    region_data['proc'] = data_proc
    region_data['interp'] = data_interp

    return region_data


def process_payload_data_container(
        field_info, data_types, field_ids, visited_ids):
    """
    Process the payload of a 1sc Field Type > 102, (a data container field,)
    returning the relevant data to a dict.
    """
    try:
        regions_list = []
        this_data_field = data_types[field_info['type']]
        data_key = field_ids[this_data_field['data_key_ref']]['regions']
        payload_len = len(field_info['payload'])
        data_key_len = this_data_field['total_bytes']

        # Sometimes Field 101 specifies total bytes in regions that is less
        #   than eventual data container field payload size.
        # In this case, data container field payload has a multiple of total bytes
        #   specified in the data key, and one must repeatedly go through
        #   the regions specified in the data key until the entire payload
        #   of the data container field is processed.

        data_key_multiple = payload_len // data_key_len
        assert payload_len % data_key_len == 0, \
                "Payload Length is not a multiple of Data Key description"

        for i in range(data_key_multiple):
            for dkey in data_key:
                region = data_key[dkey]
                region_data = process_data_region(
                        region,
                        field_info['payload'][i*data_key_len:(i+1)*data_key_len],
                        field_ids,
                        data_types,
                        visited_ids
                        )
                regions_list.append({})
                regions_list[-1]['label'] = region['label']
                regions_list[-1]['data'] = region_data
                regions_list[-1]['dtype'] = REGION_DATA_TYPES.get(
                        region['data_type'], None
                        )
                regions_list[-1]['dtype_num'] = region['data_type']
                regions_list[-1]['word_size'] = region['word_size']
                regions_list[-1]['num_words'] = region['num_words']
                regions_list[-1]['region_idx'] = region['index']
                regions_list[-1]['key_iter'] = i
    except:
        # before error, display some info
        print("ERROR in process_payload_data_container, " 
                "dumping current field_info:", file=sys.stderr)
        print(field_info, file=sys.stderr)
        raise

    return regions_list
