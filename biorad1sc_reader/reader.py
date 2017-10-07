#!/usr/bin/env python3

"""
Main reader module for Bio-Rad 1sc files.  Includes public API class
Reader.
"""

#import sys
import os.path
import struct
from PIL import Image
from biorad1sc_reader.parsing import (
        unpack_string,
        unpack_uint16, unpack_uint32,
        process_payload_type102, process_payload_type101,
        process_payload_type100, process_payload_data_container
        )
from biorad1sc_reader.errors import (
        BioRadInvalidFileError, BioRadParsingError
        )
from biorad1sc_reader.constants import BLOCK_PTR_TYPES
try:
    import numpy as np
except ModuleNotFoundError:
    HAS_NUMPY = False
else:
    HAS_NUMPY = True

#import tictoc


def save_u16_to_tiff(u16in, size, tiff_filename):
    """
    Since Pillow has poor support for 16-bit TIFF, we make our own
    save function to properly save a 16-bit TIFF.
    """

    # takes  2-14ms currently for 696x520 (WITH numpy)
    # takes 15-41ms currently for 696x520 (NO numpy)
    #print("save_u16_to_tiff START")
    #mytimer = tictoc.Timer()
    # write 16-bit TIFF image

    # PIL interprets mode 'I;16' as "uint16, little-endian"
    img_out = Image.new('I;16', size)

    if HAS_NUMPY:
        # make sure u16in little-endian, output bytes
        outpil = u16in.astype(u16in.dtype.newbyteorder("<")).tobytes()
    else:
        # little-endian u16 format
        # TODO: is it ok to use *args with huge len(args) ??
        outpil = struct.pack(
                "<%dH"%(len(u16in)),
                *u16in
                )
    img_out.frombytes(outpil)
    img_out.save(tiff_filename)
    #mytimer.eltime_pr("save_u16_to_tiff END\t")


class Reader():
    """
    Object to manage reading a Bio-Rad 1sc file and extracting
    data from it, including image.

    Assumes the 1sc file does not change while this instance has it open.
    """
    def __init__(self, in_filename=None):
        self.collections = None
        self.data_start = None
        self.data_len = None
        self.filename = None
        self.filedir = None
        self.in_bytes = None
        self.img_size_x = None
        self.img_size_y = None
        self.img_data = None
        # TODO: find endian (now we just assume little-endian)
        # "<" = little-endian, ">" = big-endian
        self.endian = "<"

        if in_filename is not None:
            self.open_file(in_filename)


    def reset(self):
        """
        Reset all internal state.  (Must load file afterwards.)
        """
        self.__init__()


    def refresh(self):
        """
        Reset and refresh all internal state using same input 1sc file.
        """
        self.__init__(self.filename)


    def open_file(self, in_filename):
        """
        Open file and read into memory.
        Raises Errors if File is not valid 1sc file.
        """
        # very fast, usu ~600us

        # reset all atributes of instance
        self.reset()

        self.filename = os.path.realpath(in_filename)
        self.filedir = os.path.dirname(self.filename)

        with open(self.filename, 'rb') as in_fh:
            self.in_bytes = in_fh.read()

        # test magic number of file, get pointers to start, len of all major
        #   data blocks in file
        #   from info at top of file
        # raises Error if something is not right
        self._parse_file_header()


    def _first_region(self, item, region_name):
        """
        Convenience function to fetch data for the first region with label
        region_name in item
        """
        return next(x['data'] for x in item if x['label'] == region_name)


    def _get_img_size(self):
        """
        Get img_size x and y, load into instance
        """
        metadata = self.get_metadata_compact()
        scn_metadata = metadata['Scan Header']['SCN']
        self.img_size_x = self._first_region(scn_metadata, 'nxpix')
        self.img_size_y = self._first_region(scn_metadata, 'nypix')


    def get_img_data(self, invert=False):
        """
        Return image_x_size, image_y_size, and list containing image data.
        Also ability to invert brightness.
        """
        # when extracting from file:
        # takes  ~60ms currently for 696x520 (WITH numpy)
        # takes ~500ms currently for 696x520 (NO numpy)
        #print("get_img_data START")
        #mytimer = tictoc.Timer()

        if self.img_size_x or self.img_size_y is None:
            self._get_img_size()

        if self.img_data is None:
            img_start = self.data_start[10]
            img_end = self.data_start[10] + self.data_len[10]

            if HAS_NUMPY:
                # unsigned uint16s (2-bytes)
                img_data = np.frombuffer(
                        self.in_bytes[img_start:img_end],
                        np.dtype("uint16").newbyteorder(self.endian)
                        )
                # re-arrange image data so top-to-bottom
                #   1sc makes botttom to top originally

                # create index array
                rowsz = int(self.img_size_x)
                img_data_idx = np.zeros(len(img_data), dtype="uint32")
                for row in range(0, len(img_data)//rowsz):
                    img_data_idx[row * rowsz:(row + 1) * rowsz] = range(
                            len(img_data) - (row + 1) * rowsz,
                            len(img_data) - row * rowsz,
                            )
                # assign using index array
                self.img_data = img_data[img_data_idx]

            else:
                # little-endian unsigned uint16s (2-bytes)
                img_data = list(
                        struct.unpack(
                            "%s%dH"%(self.endian, (img_end-img_start)/2),
                            self.in_bytes[img_start:img_end]
                            )
                        )
                # re-arrange image data so top-to-bottom
                #   1sc makes botttom to top originally
                self.img_data = []
                for i in range(len(img_data), 0, -self.img_size_x):
                    self.img_data = self.img_data + img_data[i-self.img_size_x:i]

        if invert:
            if HAS_NUMPY:
                img_data = 2**16 - 1 - self.img_data
            else:
                img_data = [2**16-1-x for x in self.img_data]
        else:
            img_data = self.img_data

        #mytimer.eltime_pr("get_img_data END\t")
        return(self.img_size_x, self.img_size_y, img_data)


    def save_img_as_tiff(self, tiff_filename, invert=False):
        """
        Save image data from file as tiff.
        Also ability to invert brightness
        """
        # takes ~14ms currently for 696x520 (WITH numpy)
        # takes ~65ms currently for 696x520 (NO numpy)
        #print("save_img_as_tiff: START")
        #mytimer = tictoc.Timer()

        (img_x, img_y, img_data) = self.get_img_data(invert=invert)

        # save to tiff file
        save_u16_to_tiff(
                img_data,
                (img_x, img_y),
                tiff_filename
                )

        #mytimer.eltime_pr("save_img_as_tiff END\t")


    def save_img_as_tiff_sc(self, tiff_filename, imgsc=1.0, invert=False):
        """
        Save image data from file as tiff, with brightness scale expanded from
        min to max.
        Also ability to invert brightness
        """
        # takes  ~45ms currently for 696x520 (WITH numpy)
        # takes ~250ms currently for 696x520 (NO numpy)
        #print("save_img_as_tiff_sc START")
        #mytimer = tictoc.Timer()

        (img_x, img_y, img_data) = self.get_img_data(invert=invert)

        img_min = min(img_data)
        img_max = max(img_data)

        # scale min/max to scale brightness
        if invert:
            # anchor at img_max if inverted img data
            #img_max = img_max
            img_min = img_max - (img_max - img_min) * imgsc
        else:
            # anchor at img_min if inverted img data
            #img_min = img_min
            img_max = img_min + (img_max - img_min) * imgsc

        img_span = (img_max - img_min)

        if HAS_NUMPY:
            # scale brightness of pixels
            # linear map: img_min-img_max to 0-(2**16-1)
            # make sure we use signed integer dtype for numpy
            #   unsigned dtypes cause negative values to wrap to large pos
            #   signed dtypes automatically adjust to size of value,
            #       positive or negative
            # need 64-bit signed int, because we multiply 16-bit by 16-bit
            #   which can be maximum positive 32-bits
            img_data = np.array(img_data, dtype='int64')
            img_data_scale = (img_data-img_min)*(2**16-1)/img_span

            # enforce max and min via clipping
            np.clip(img_data_scale, 0, 2**16-1, out=img_data_scale)

            # cast back to int16 after clipping
            img_data_scale = img_data_scale.astype('uint16')
        else:
            # scale brightness of pixels
            # linear map: img_min-img_max to 0-(2**16-1)
            img_data_scale = [int((x-img_min)*(2**16-1)/img_span) for x in img_data]

            # enforce max and min via clipping
            img_data_scale = [min(max(x, 0), 2**16-1) for x in img_data_scale]

        # save to tiff file
        save_u16_to_tiff(
                img_data_scale,
                (img_x, img_y),
                tiff_filename
                )

        #mytimer.eltime_pr("save_img_as_tiff_sc END\t")


    def get_img_summary(self):
        """
        NOTE: Safer to use get_metadata() or get_metadata_compact()

        Read from Data Block 7, containing strings describing image.
        Return dict containing data.

        Scanner Name: ChemiDoc XRS
        Number of Pixels: (696 x 520)
        Image Area: (200.0 mm x 149.4 mm)
        Scan Memory Size: 836.32 Kb
        Old file name: Chemi 2017-05-17 10hr 56min-2.1sc
        New file name: A11 2017-05-17 10hr 56min-2 B.1sc
        CHEMIDOC\\Chemi
        New Image Acquired
        Save As...
        Quantity One 4.6.8 build 027
        """
        # very fast, usu ~250us

        # init summary dict
        summary = {}

        # first 4 uint16s of data block are info about block
        byte_idx = self.data_start[7] + 8

        while byte_idx < (self.data_start[7] + self.data_len[7]):
            (byte_idx, field_info) = self._read_field_lite(byte_idx)
            if field_info['type'] == 0:
                # we just saw an End Of Data Block Field
                (_, end_idx) = self._get_next_data_block_end(byte_idx)
                # skip to beginning of next data block
                byte_idx = end_idx + 8

            if field_info['type'] == 16:
                info_str = field_info['payload'][:-1].decode("utf-8")
                if ': ' in info_str:
                    # 'maxsplit' is incompatible with python 2.x
                    info_str_list = info_str.split(': ', maxsplit=1)
                    #<key_name>: <item_name>
                    summary[info_str_list[0]] = info_str_list[1]
                else:
                    if info_str.startswith('Quantity One'):
                        summary['Quantity One'] = info_str
                    elif '\\' in info_str:
                        summary['path'] = info_str
                    else:
                        # as a last resort, make key=item=info_str
                        summary[info_str] = info_str

        return summary


    def _get_next_data_block_end(self, byte_idx):
        """
        Given a byte index, find the next Data Block end, return byte at
        start of the following Data Block
        """
        for i in range(11):
            if byte_idx < self.data_start[i] + self.data_len[i]:
                block_num = i
                end_idx = self.data_start[i] + self.data_len[i]
                break
        return (block_num, end_idx)


    def get_metadata(self):
        """
        Fetch All Metadata in File, return hierarchical dict/list
        """

        # do not process again if we already have processed the file
        if self.collections is not None:
            return self.collections

        field_ids = {}
        collections = []

        # start at first field of Data Block 0, get all ids
        byte_idx = self.data_start[0] + 8
        while byte_idx < self.data_start[10]:
            (byte_idx, field_info) = self._read_field_lite(byte_idx)
            field_ids[field_info['id']] = field_info

            if field_info['type'] == 0:
                # we just saw an End Of Data Block Field
                (_, end_idx) = self._get_next_data_block_end(byte_idx)
                # skip to beginning of next data block
                byte_idx = end_idx + 8

        # start at first field of Data Block 0, process hierarchical
        #   metadata
        visited_ids = []
        byte_idx = self.data_start[0] + 8
        while byte_idx < self.data_start[10]:
            (byte_idx, field_info) = self._read_field_lite(byte_idx)

            if field_info['type'] == 0:
                # we just saw an End Of Data Block Field
                (_, end_idx) = self._get_next_data_block_end(byte_idx)
                # skip to beginning of next data block
                byte_idx = end_idx + 8
            elif field_info['type'] in [2, 16]:
                # 2=NOP field
                # 16=string field (will be referenced later by other fields)
                pass
            elif field_info['type'] == 102:
                # collection definition
                data_types = {}
                field_payload_info = process_payload_type102(
                        field_info['payload'], field_ids=field_ids)
                field_info.update(field_payload_info)
                collections.append({'label':field_info['collection_label']})
                collections[-1]['data'] = []
                this_coll = collections[-1]['data']
            elif field_info['type'] == 101:
                # collection items
                field_payload_info = process_payload_type101(
                        field_info['payload'], field_ids=field_ids)
                field_info.update(field_payload_info)
                data_types = field_info['items']
            elif field_info['type'] == 100:
                # data keys (data format)
                data_key_total_bytes = field_ids[field_info['id']]['data_key_total_bytes']
                field_payload_info = process_payload_type100(
                        field_info['payload'],
                        data_key_total_bytes, field_ids=field_ids)
                field_info.update(field_payload_info)
                field_ids[field_info['id']] = field_info
            elif field_info['type'] in data_types:
                # data containers
                if field_info['id'] not in visited_ids:
                    # if this ID was visited by hierarchical Reference, we don't
                    #   need to report it on its own at top-level
                    regions_list = process_payload_data_container(
                            field_info,
                            data_types,
                            field_ids,
                            visited_ids
                            )
                    this_coll.append({})
                    this_coll[-1]['data'] = regions_list
                    this_coll[-1]['label'] = data_types[field_info['type']]['label']
                    this_coll[-1]['id'] = field_info['id']
                    this_coll[-1]['type'] = field_info['type']
                else:
                    # we have already visited this field in the hierarchy
                    pass
            else:
                raise BioRadParsingError(
                        "Unknown Field Type %d in Collection"%field_info['type']
                        )

        return collections


    def _make_compact_item(self, item):
        """
        Given an Item from metadata data collection, return a compact version
        of it for use in get_metadata_compact()

        Remove everything except 'label' and most-interpreted form of 'data'
        available
        """
        item_compact = {}
        item_compact['label'] = item['label']
        item_compact['data'] = []
        for region in item['data']:
            region_compact = {}
            region_compact['label'] = region['label']
            if region['data']['interp'] is not None:
                if isinstance(region['data']['interp'], dict):
                    item_compact_hier = self._make_compact_item(
                            region['data']['interp'])
                    region_compact['data'] = item_compact_hier['data']
                else:
                    region_compact['data'] = region['data']['interp']
            elif region['data']['proc'] is not None:
                region_compact['data'] = region['data']['proc']
            else:
                region_compact['data'] = region['data']['raw']

            item_compact['data'].append(region_compact)

        return item_compact


    def get_metadata_compact(self):
        """
        Fetch All Metadata in File, return compact version of hierarchical
        dict/list

        Convert dict(list()) of Collections, Items to dict().  Leave Regions as
        list, because they are not guaranteed to have unique labels.

        Remove everything except 'label' and most-interpreted form of 'data'
        available.
        """
        collections = self.get_metadata()
        collections_compact = {}
        for coll in collections:
            assert coll['label'] not in collections_compact, \
                    "Multiple collections of the same name."
            collections_compact[coll['label']] = {}
            for item in coll['data']:
                item_compact = self._make_compact_item(item)
                assert item['label'] not in collections_compact[coll['label']], \
                        "Multiple items of the same name in collection."
                collections_compact[coll['label']][item['label']] = item_compact['data']

        return collections_compact


    def _process_field_header(self, byte_idx):
        # read header
        header_uint16s = unpack_uint16(
                self.in_bytes[byte_idx:byte_idx+8], endian="<")
        header_uint32s = unpack_uint32(
                self.in_bytes[byte_idx:byte_idx+8], endian="<")
        field_type = header_uint16s[0]
        field_len = header_uint16s[1]
        field_id = header_uint32s[1]

        # field_len of 1 means field_len=20 (only known to occur in
        #   Data Block pointer fields in file header)
        if field_len == 1:
            field_len = 20

        return (field_type, field_len, field_id)


    def _read_field_lite(self, byte_idx):
        field_info = {}
        # read header
        (field_type, field_len, field_id) = self._process_field_header(byte_idx)

        # get payload bytes
        field_payload = self.in_bytes[byte_idx+8:byte_idx+field_len]

        field_info['type'] = field_type
        field_info['id'] = field_id
        field_info['start'] = byte_idx
        field_info['len'] = field_len
        field_info['payload'] = field_payload

        return (byte_idx+field_len, field_info)


    def _parse_file_header(self):
        # reset loop variables
        byte_idx = 160
        self.data_start = {}
        self.data_len = {}

        # Verify magic file number indicates 1sc file
        magic_number = unpack_uint16(self.in_bytes[0:2], endian="<")
        if magic_number[0] != 0xafaf:
            raise BioRadInvalidFileError("Bad Magic Number")

        # Verify which endian, e.g. Intel Format == little-endian
        endian_format = unpack_string(self.in_bytes[32:56])
        if endian_format.startswith('Intel Format'):
            # little-endian
            self.endian = "<"
        else:
            # big-endian
            # TODO: find a non Intel Format file to verify this?
            self.endian = ">"

        # Verify Scan File ID Text
        biorad_id = unpack_string(self.in_bytes[56:136])
        if not biorad_id.startswith('Bio-Rad Scan File'):
            raise BioRadInvalidFileError("Bad File Header")

        # get end of file header / start of data block 0
        file_header_end = unpack_uint32(self.in_bytes[148:152], endian="<")
        file_header_end = file_header_end[0]

        # get all data block pointers
        while byte_idx < file_header_end:
            field_start = byte_idx

            (byte_idx, field_info) = self._read_field_lite(byte_idx)

            # record data blocks start, end
            if field_info['type'] in BLOCK_PTR_TYPES:
                block_num = BLOCK_PTR_TYPES[field_info['type']]
                out_uint32s = unpack_uint32(
                        field_info['payload'], endian="<")
                self.data_start[block_num] = out_uint32s[0]
                self.data_len[block_num] = out_uint32s[1]

            if field_info['type'] == 0:
                break

            # break if we still aren't advancing
            if byte_idx == field_start:
                raise Exception("Problem parsing file header")
