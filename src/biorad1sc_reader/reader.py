#!/usr/bin/env python3

"""
Main reader module for Bio-Rad 1sc files.  Includes public API class
Reader.
"""

# import sys
import os.path
import struct
from PIL import Image
from biorad1sc_reader.parsing import (
    unpack_string,
    unpack_uint16,
    unpack_uint32,
    process_payload_type102,
    process_payload_type101,
    process_payload_type100,
    process_payload_data_container,
)
from biorad1sc_reader.errors import BioRadInvalidFileError, BioRadParsingError
from biorad1sc_reader.constants import BLOCK_PTR_TYPES

try:
    import numpy as np
except ModuleNotFoundError:
    HAS_NUMPY = False
else:
    HAS_NUMPY = True

# import tictoc


def save_u16_to_tiff(u16in, size, tiff_filename):
    """Save 16-bit uints to TIFF image file

    Since Pillow has poor support for 16-bit TIFF, we make our own
    save function to properly save a 16-bit TIFF.

    Args:
        u16in (list): u16int image pixel data
        size (tuple): (xsize, ysize) where xsize and ysize are integers
            specifying the size of the image in pixels
        tiff_filename (str): filepath for the output TIFF file
    """

    # takes  2-14ms currently for 696x520 (WITH numpy)
    # takes 15-41ms currently for 696x520 (NO numpy)
    # print("save_u16_to_tiff START")
    # mytimer = tictoc.Timer()
    # write 16-bit TIFF image

    # PIL interprets mode 'I;16' as "uint16, little-endian"
    img_out = Image.new("I;16", size)

    if HAS_NUMPY:
        # make sure u16in little-endian, output bytes
        outpil = u16in.astype(u16in.dtype.newbyteorder("<")).tobytes()
    else:
        # little-endian u16 format
        # TODO: is it ok to use *args with huge len(args) ??
        outpil = struct.pack("<%dH" % (len(u16in)), *u16in)
    img_out.frombytes(outpil)
    img_out.save(tiff_filename)
    # mytimer.eltime_pr("save_u16_to_tiff END\t")


class Reader:
    """
    Object to manage reading a Bio-Rad 1sc file and extracting
    data from it, including image.

    Assumes the 1sc file does not change while this instance has it open.

    Instantiation:
        Args:
            in_file (str or file-like obj): filepath (str) or file-like
                object, 1sc file to read with this instance

        Raises:
            BioRadInvalidFileError if file is not a valid Bio-Rad 1sc file
    """

    def __init__(self, in_file=None):
        """Initialize Reader class

        Args:
            in_file (str or file-like obj): filepath (str) or file-like
                object, 1sc file to read with this instance

        Raises:
            BioRadInvalidFileError if file is not a valid Bio-Rad 1sc file
        """
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

        if in_file is not None:
            if isinstance(in_file, str):
                self.open_file(in_file)
            else:
                self.read_stream(in_file)

    def reset(self):
        """Reset all internal state.  (Must load file afterwards.)"""
        self.__init__()

    def refresh(self):
        """Reset and refresh all internal state using same input 1sc file."""
        self.__init__(self.filename)

    def open_file(self, in_filename):
        """Open file and read into memory.

        Raises Errors if File is not valid 1sc file.

        Args:
            in_filename (str): filepath to 1sc file to read with object
                instance

        Raises:
            BioRadInvalidFileError if file is not a valid Bio-Rad 1sc file
        """
        # very fast, usu ~600us

        # reset all atributes of instance
        self.reset()

        self.filename = os.path.realpath(in_filename)
        self.filedir = os.path.dirname(self.filename)

        with open(self.filename, "rb") as in_fh:
            self.read_stream(in_fh)

    def read_stream(self, in_fh):
        """Read file-like object into memory.

        Raises Errors if File is not valid 1sc file.  Give it object returned
        by: open(<filename>, 'rb')

        Args:
            in_fh (byte stream): filehandle to 1sc filedata to read with object
                instance.  e.g. result from open(<filename>, 'rb')

        Raises:
            BioRadInvalidFileError if file is not a valid Bio-Rad 1sc file
        """
        self.in_bytes = in_fh.read()

        # test magic number of file, get pointers to start, len of all major
        #   data blocks in file
        #   from info at top of file
        # raises Error if something is not right
        self._parse_file_header()

    def _first_region(self, item, region_name):
        """Fetch data from first region in item with name region_name

        Convenience function to fetch data for the first region with label
        region_name in item

        Args:
            item (list): list of regions from get_metadata() or
                get_metadata_compac()
            region_name (str): region label to search for

        Returns:
            various: whatever is contained in 'data' key of region dict
        """
        return next(x["data"] for x in item if x["label"] == region_name)

    def _get_img_size(self):
        """Get img_size x and y, load into instance

        Determine image size from metadata of 1sc file and set internal
        instance attributes self.img_size_x and self.img_size_y
        """
        metadata = self.get_metadata_compact()
        scn_metadata = metadata["Scan Header"]["SCN"]
        self.img_size_x = self._first_region(scn_metadata, "nxpix")
        self.img_size_y = self._first_region(scn_metadata, "nypix")

    def get_img_data(self, invert=False):
        """
        Return image_x_size, image_y_size, and list containing image data.
        Also ability to invert brightness.

        Args:
            invert (bool, optional): True to invert the brightness scale of
                output image data compared to 1sc image data (black <-> white)

        Returns:
            tuple: (xsize, ysize, image_data) where xsize and ysize are
            integers specifying the size of the image.

            image_data is
            a list of uint16 numbers comprising the image data starting
            from upper-left and progressing to lower-right.

        """
        # when extracting from file:
        # takes  ~60ms currently for 696x520 (WITH numpy)
        # takes ~500ms currently for 696x520 (NO numpy)
        # print("get_img_data START")
        # mytimer = tictoc.Timer()

        if self.img_size_x or self.img_size_y is None:
            self._get_img_size()

        if self.img_data is None:
            img_start = self.data_start[10]
            img_end = self.data_start[10] + self.data_len[10]

            if HAS_NUMPY:
                # unsigned uint16s (2-bytes)
                img_data = np.frombuffer(
                    self.in_bytes[img_start:img_end],
                    np.dtype("uint16").newbyteorder(self.endian),
                )
                # re-arrange image data so top-to-bottom
                #   1sc makes botttom to top originally

                # create index array
                rowsz = int(self.img_size_x)
                img_data_idx = np.zeros(len(img_data), dtype="uint32")
                for row in range(0, len(img_data) // rowsz):
                    img_data_idx[row * rowsz : (row + 1) * rowsz] = range(
                        len(img_data) - (row + 1) * rowsz,
                        len(img_data) - row * rowsz,
                    )
                # assign using index array
                self.img_data = img_data[img_data_idx]

            else:
                # little-endian unsigned uint16s (2-bytes)
                img_data = list(
                    struct.unpack(
                        "%s%dH" % (self.endian, (img_end - img_start) / 2),
                        self.in_bytes[img_start:img_end],
                    )
                )
                # re-arrange image data so top-to-bottom
                #   1sc makes botttom to top originally
                self.img_data = []
                for i in range(len(img_data), 0, -self.img_size_x):
                    self.img_data = self.img_data + img_data[i - self.img_size_x : i]

        if invert:
            if HAS_NUMPY:
                img_data = 2 ** 16 - 1 - self.img_data
            else:
                img_data = [2 ** 16 - 1 - x for x in self.img_data]
        else:
            img_data = self.img_data

        # mytimer.eltime_pr("get_img_data END\t")
        return (self.img_size_x, self.img_size_y, img_data)

    def save_img_as_tiff(self, tiff_filename, invert=False):
        """Save image data as TIFF image

        Also ability to invert brightness

        Args:
            tiff_filename (str): filepath for output TIFF file
            invert (bool, optional): True to invert the brightness scale of output
                TIFF image compared to 1sc image data (black <-> white)
        """
        # takes ~14ms currently for 696x520 (WITH numpy)
        # takes ~65ms currently for 696x520 (NO numpy)
        # print("save_img_as_tiff: START")
        # mytimer = tictoc.Timer()

        (img_x, img_y, img_data) = self.get_img_data(invert=invert)

        # save to tiff file
        save_u16_to_tiff(img_data, (img_x, img_y), tiff_filename)

        # mytimer.eltime_pr("save_img_as_tiff END\t")

    def save_img_as_tiff_sc(self, tiff_filename, imgsc=1.0, invert=False):
        """Save image data as TIFF image, with brightness dynamic range expanded

        Also ability to invert brightness

        Args:
            tiff_filename (str): filepath for output TIFF file
            imgsc (float, optional): Expand brightness scale. Value of 1.0
                means that dynamic range of output TIFF will be maximum, with
                brightest pixel having value 65535 and darkest pixel having
                value 0.

                imgsc > 1.0 will cause the brightness dynamic range to be
                expanded less than imgsc=1.0, and imgsc < 1.0 will cause the
                dynamic range to be expanded more than the imgsc=1.0 case.

                For non-inverted images, the pixel with the minimum brightness
                will always be 0.  For inverted images, the pixel with the
                maximum brightness will always be 65535.

            invert (bool, optional): True to invert the brightness scale of
                output TIFF image compared to 1sc image data (black <-> white)
        """
        # takes  ~45ms currently for 696x520 (WITH numpy)
        # takes ~250ms currently for 696x520 (NO numpy)
        # print("save_img_as_tiff_sc START")
        # mytimer = tictoc.Timer()

        (img_x, img_y, img_data) = self.get_img_data(invert=invert)

        img_min = min(img_data)
        img_max = max(img_data)
        img_span = img_max - img_min

        # scale min/max to scale brightness
        if invert:
            # anchor at img_max if inverted img data
            img_min = img_max - img_span * imgsc
        else:
            # anchor at img_min if inverted img data
            img_max = img_min + img_span * imgsc

        if HAS_NUMPY:
            # scale brightness of pixels
            # linear map: img_min-img_max to 0-(2**16-1)
            # make sure we use signed int dtype for numpy
            #   unsigned dtypes cause negative values to wrap to large pos
            #   signed dtypes automatically adjust to size of value,
            #       positive or negative
            # need 64-bit signed int, because we multiply 16-bit by 16-bit
            #   which can be maximum positive 32-bits
            img_data = np.array(img_data, dtype="int64")
            img_data_scale = (img_data - img_min) * (2 ** 16 - 1) / img_span

            # enforce max and min via clipping
            np.clip(img_data_scale, 0, 2 ** 16 - 1, out=img_data_scale)

            # cast back to int16 after clipping
            img_data_scale = img_data_scale.astype("uint16")
        else:
            # scale brightness of pixels
            # linear map: img_min-img_max to 0-(2**16-1)
            img_data_scale = [
                int((x - img_min) * (2 ** 16 - 1) / img_span) for x in img_data
            ]

            # enforce max and min via clipping
            img_data_scale = [min(max(x, 0), 2 ** 16 - 1) for x in img_data_scale]

        # save to tiff file
        save_u16_to_tiff(img_data_scale, (img_x, img_y), tiff_filename)

        # mytimer.eltime_pr("save_img_as_tiff_sc END\t")

    def get_img_summary(self):
        """
        NOTE: Safer to use get_metadata() or get_metadata_compact()

        Read from Data Block 7, containing strings describing image.

        Returns:
            dict: dict containing data from strings in Data Block 7::

                {
                    'Scanner Name':'ChemiDoc XRS'
                    'Number of Pixels':'(<x pix size> x <y pix size>)'
                    'Image Area':'(<x float size> mm x <y float size> mm)'
                    'Scan Memory Size': '<size in bytes>'
                    'Old file name': '<orig file name>'
                    'New file name': '<new file name>'
                    'path':'CHEMIDOC\\Chemi'
                    'New Image Acquired':'New Image Acquired'
                    'Save As...':'Save As...'
                    'Quantity One':'Quantity One <version> build <build number>'
                }
        """
        # very fast, usu ~250us

        # init summary dict
        summary = {}

        # first 4 uint16s of data block are info about block
        byte_idx = self.data_start[7] + 8

        while byte_idx < (self.data_start[7] + self.data_len[7]):
            (byte_idx, field_info) = self._read_field_lite(byte_idx)
            if field_info["type"] == 0:
                # we just saw an End Of Data Block Field
                (_, end_idx) = self._get_next_data_block_end(byte_idx)
                # skip to beginning of next data block
                byte_idx = end_idx + 8

            if field_info["type"] == 16:
                info_str = field_info["payload"][:-1].decode("utf-8")
                if ": " in info_str:
                    # 'maxsplit' is incompatible with python 2.x
                    info_str_list = info_str.split(": ", maxsplit=1)
                    # <key_name>: <item_name>
                    summary[info_str_list[0]] = info_str_list[1]
                else:
                    if info_str.startswith("Quantity One"):
                        summary["Quantity One"] = info_str
                    elif "\\" in info_str:
                        summary["path"] = info_str
                    else:
                        # as a last resort, make key=item=info_str
                        summary[info_str] = info_str

        return summary

    def _get_next_data_block_end(self, byte_idx):
        """
        Given a byte index, find the next Data Block end, return byte at
        start of the following Data Block

        Args:
            byte_idx (int): file byte offset to search for the end of the
                next Data Block

        Returns:
            tuple: (block_num, end_idx) where block_num is the Data Block
                that ends at end_idx-1
        """
        for i in range(11):
            if byte_idx < self.data_start[i] + self.data_len[i]:
                block_num = i
                end_idx = self.data_start[i] + self.data_len[i]
                break
        return (block_num, end_idx)

    def get_metadata(self):
        """Fetch All Metadata in File, return hierarchical dict/list

        Returns:
            list: collections where each item in list collections is a dict::

                collection_dict = {
                    'data':<list items>
                    'label':'<str name of collection>'
                }

            where items is a list of dicts, each with the structure::

                item_dict = {
                    'data':<list regions>
                    'id':<uint32 Field ID>
                    'label':'<str name of item>'
                    'type':'<int Field Type>'
                }

            where regions is a list of dicts, each with the structure::

                region_dict = {
                    'data': <dict data_of_region>
                    'dtype': <str written type of data>
                    'dtype_num': <int data type code of data>
                    'key_iter': <??>
                    'label': <str name of region>
                    'num_words': <int number of words in data>
                    'region_idx': <int 1sc-given index>
                    'word_size': <int number of bytes per word of data>
                }

            where data_of_region has the structure::

                data_of_region = {
                    'raw': <bytes raw bytes, unconverted data>
                    'proc': <various unpacked/decoded data from bytes>
                    'interp': <various 'interpreted' data>
                }

            data_of_region['interp'] can also be another item_dict, if this
                region contained a reference to another field, creating
                a hierarchical structure.

            e.g. ``collections[0]['data'][0]['data'][0]['label'] = 'array'``

        Raises:
           BioRadParsingError: if there was an error in parsing the file
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
            field_ids[field_info["id"]] = field_info

            if field_info["type"] == 0:
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

            if field_info["type"] == 0:
                # we just saw an End Of Data Block Field
                (_, end_idx) = self._get_next_data_block_end(byte_idx)
                # skip to beginning of next data block
                byte_idx = end_idx + 8
            elif field_info["type"] in [2, 16]:
                # 2=NOP field
                # 16=string field (will be referenced later by other fields)
                pass
            elif field_info["type"] == 102:
                # collection definition
                field_types = {}
                field_payload_info = process_payload_type102(
                    field_info["payload"], field_ids=field_ids
                )
                field_info.update(field_payload_info)
                collections.append({"label": field_info["collection_label"]})
                collections[-1]["data"] = []
                this_coll = collections[-1]["data"]
            elif field_info["type"] == 101:
                # collection items
                field_payload_info = process_payload_type101(
                    field_info["payload"], field_ids=field_ids
                )
                field_info.update(field_payload_info)
                field_types = field_info["items"]
            elif field_info["type"] == 100:
                # data keys (data format)
                data_key_total_bytes = field_ids[field_info["id"]][
                    "data_key_total_bytes"
                ]
                field_payload_info = process_payload_type100(
                    field_info["payload"], data_key_total_bytes, field_ids=field_ids
                )
                field_info.update(field_payload_info)
                field_ids[field_info["id"]] = field_info
            elif field_info["type"] in field_types:
                # data containers
                if field_info["id"] not in visited_ids:
                    # if this ID was visited by hierarchical Reference, we don't
                    #   need to report it on its own at top-level
                    regions_list = process_payload_data_container(
                        field_info, field_types, field_ids, visited_ids
                    )
                    this_coll.append({})
                    this_coll[-1]["data"] = regions_list
                    this_coll[-1]["label"] = field_types[field_info["type"]]["label"]
                    this_coll[-1]["id"] = field_info["id"]
                    this_coll[-1]["type"] = field_info["type"]
                else:
                    # we have already visited this field in the hierarchy
                    pass
            else:
                raise BioRadParsingError(
                    "Unknown Field Type %d in Collection" % field_info["type"]
                )

        return collections

    def _make_compact_item(self, item):
        """
        Given an Item from metadata data collection, return a compact version
        of it for use in get_metadata_compact()

        Remove everything except 'label' and most-interpreted form of 'data'
        available

        Args:
            item (dict): item_dict from get_metadata(), e.g.
                collections[<num>]['data'][<num>]

        Returns:
            dict: compact representation of input dict for
                get_metadata_compact()

        """
        item_compact = {}
        item_compact["label"] = item["label"]
        item_compact["data"] = []
        for region in item["data"]:
            region_compact = {}
            region_compact["label"] = region["label"]
            if region["data"]["interp"] is not None:
                if isinstance(region["data"]["interp"], dict):
                    item_compact_hier = self._make_compact_item(
                        region["data"]["interp"]
                    )
                    region_compact["data"] = item_compact_hier["data"]
                else:
                    region_compact["data"] = region["data"]["interp"]
            elif region["data"]["proc"] is not None:
                region_compact["data"] = region["data"]["proc"]
            else:
                region_compact["data"] = region["data"]["raw"]

            item_compact["data"].append(region_compact)

        return item_compact

    def get_metadata_compact(self):
        """
        Fetch All Metadata in File, return compact version of hierarchical
        dict/list

        Convert dict(list()) of Collections, Items to dict().  Leave Regions as
        list, because they are not guaranteed to have unique labels.

        Remove everything except 'label' and most-interpreted form of 'data'
        available.

        Returns:
            dict: collections::

                collections = {
                    '<collection name1>':<dict collection_dict1>
                    '<collection name2>':<dict collection_dict2>
                    ...
                }

            where each collection_dict is::

                collection_dict = {
                    '<name of item1>':<list regions1>
                    '<name of item2>':<list regions2>
                    ...
                }

            where regions is a list of dicts, each with the structure::

                region_dict = {
                    'data': <various most interpreted version possible of data>
                    'label': <str name of region>
                }

            region_dict['data'] can also be another regions list, if this
                region contained a reference to another field, creating
                a hierarchical structure.

            e.g. ``collections['Overlay Header']['OverlaySaveArray'][0]['label]
            = 'array'``
        """
        collections = self.get_metadata()
        collections_compact = {}
        for coll in collections:
            assert (
                coll["label"] not in collections_compact
            ), "Multiple collections of the same name."
            collections_compact[coll["label"]] = {}
            for item in coll["data"]:
                item_compact = self._make_compact_item(item)
                assert (
                    item["label"] not in collections_compact[coll["label"]]
                ), "Multiple items of the same name in collection."
                collections_compact[coll["label"]][item["label"]] = item_compact["data"]

        return collections_compact

    def _process_field_header(self, byte_idx):
        """

        Args:
            byte_idx (int): file byte offset, start of the field to read header

        Returns:
            tuple: (field_type, field_len, field_id) where field_type is
                uint16 Field Type, field_len is int length in bytes of
                field, field_id is uint32 Field ID

        """
        # read header
        header_uint16s = unpack_uint16(
            self.in_bytes[byte_idx : byte_idx + 8], endian="<"
        )
        header_uint32s = unpack_uint32(
            self.in_bytes[byte_idx : byte_idx + 8], endian="<"
        )
        field_type = header_uint16s[0]
        field_len = header_uint16s[1]
        field_id = header_uint32s[1]

        # field_len of 1 means field_len=20 (only known to occur in
        #   Data Block pointer fields in file header)
        if field_len == 1:
            field_len = 20

        return (field_type, field_len, field_id)

    def _read_field_lite(self, byte_idx):
        """

        Args:
            byte_idx (int): file byte offset, start of the field to read

        Returns:
            tuple: (file_byte_offset_next_field, field_info) where field info
                is a dict::

                    {
                        'type':<uint16 Field Type>
                        'id':<uint32 Field ID>
                        'start':<byte offset of start of field>
                        'len':<total length in bytes of field>
                        'payload':<field payload bytes>
                    }
        """
        field_info = {}
        # read header
        (field_type, field_len, field_id) = self._process_field_header(byte_idx)

        # get payload bytes
        field_payload = self.in_bytes[byte_idx + 8 : byte_idx + field_len]

        field_info["type"] = field_type
        field_info["id"] = field_id
        field_info["start"] = byte_idx
        field_info["len"] = field_len
        field_info["payload"] = field_payload

        return (byte_idx + field_len, field_info)

    def _parse_file_header(self):
        """Read and process the start of the file (header)

        Raises:
            BioRadInvalidFileError if file is not a valid Bio-Rad 1sc file
        """
        # reset loop variables
        byte_idx = 160
        self.data_start = {}
        self.data_len = {}

        # Verify magic file number indicates 1sc file
        magic_number = unpack_uint16(self.in_bytes[0:2], endian="<")
        if magic_number[0] != 0xAFAF:
            raise BioRadInvalidFileError("Bad Magic Number")

        # Verify which endian, e.g. Intel Format == little-endian
        endian_format = unpack_string(self.in_bytes[32:56])
        if endian_format.startswith("Intel Format"):
            # little-endian
            self.endian = "<"
        else:
            # big-endian
            # TODO: find a non Intel Format file to verify this?
            self.endian = ">"

        # Verify Scan File ID Text
        biorad_id = unpack_string(self.in_bytes[56:136])
        if not biorad_id.startswith("Bio-Rad Scan File"):
            raise BioRadInvalidFileError("Bad File Header")

        # get end of file header / start of data block 0
        file_header_end = unpack_uint32(self.in_bytes[148:152], endian="<")
        file_header_end = file_header_end[0]

        # get all data block pointers
        while byte_idx < file_header_end:
            field_start = byte_idx

            (byte_idx, field_info) = self._read_field_lite(byte_idx)

            # record data blocks start, end
            if field_info["type"] in BLOCK_PTR_TYPES:
                block_num = BLOCK_PTR_TYPES[field_info["type"]]
                out_uint32s = unpack_uint32(field_info["payload"], endian="<")
                self.data_start[block_num] = out_uint32s[0]
                self.data_len[block_num] = out_uint32s[1]

            if field_info["type"] == 0:
                break

            # break if we still aren't advancing
            if byte_idx == field_start:
                raise Exception("Problem parsing file header")
