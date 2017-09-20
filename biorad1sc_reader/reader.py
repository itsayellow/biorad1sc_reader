#!/usr/bin/env python3

# see LARGE amount of file format notes at end of this file

#import sys
import time
import os.path
import struct
from biorad1sc_reader.errors import BioRadInvalidFileError
#import tictoc

from PIL import Image
try:
    import numpy as np
except ModuleNotFoundError:
    HAS_NUMPY = False
else:
    HAS_NUMPY = True


# for debugging (DELETEME)
if HAS_NUMPY:
    print("YES Numpy")
else:
    print("No Numpy")


#DATA_TYPES = {
#        1:"u?byte",
#        2:"u?byte/ASCII",
#        3:"u?int16",
#        4:"uint16",
#        5:"u?int32",
#        6:"u?int32",
#        7:"uint64",
#        9:"uint32",
#        15:"uint32 Reference",
#        17:"uint32 Reference",
#        131:"12-byte??",
#        1001:"8- or 24-byte??",
#        1002:"24-byte??",
#        1003:"8-byte (x,y)??",
#        1004:"8- or 16-byte (x1,y1,x2,y2)??",
#        1005:"64-byte??",
#        1006:"640-byte??",
#        1010:"144-byte??",
#        1016:"440-byte??",
#        1020:"32-byte??",
#        1027:"8-byte??",
#        1032:"12-byte??",
#        }


def is_ascii(byte_stream):
    ok_ascii_byte = [0, 9, 10, 13] + list(range(32, 127))
    return all(
            [byte in ok_ascii_byte for byte in byte_stream]
            )


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


def unpack_uint64(byte_stream, endian="<"):
    num_uint64 = len(byte_stream)//8
    out_uint64s = struct.unpack(endian+"Q"*num_uint64, byte_stream)
    return out_uint64s


def update_item_datakey(this_collection, field_info):
    data_id = field_info['id']
    for item in this_collection['items']:
        if this_collection['items'][item]['data_key_ref'] == data_id:
            this_collection['items'][item]['data_key'] = field_info['regions']


def save_u16_to_tiff(u16in, size, tiff_filename):
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
    def __init__(self, in_filename=None):
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
        self.__init__()


    def open_file(self, in_filename):
        """
        open file and read into memory
        """
        # very fast, usu ~600us

        # TODO: reset all atributes of instance?
        self.reset()

        self.filename = os.path.realpath(in_filename)
        self.filedir = os.path.dirname(self.filename)

        with open(self.filename, 'rb') as in_fh:
            self.in_bytes = in_fh.read()

        # test magic number of file, get pointers to start, len of all major
        #   data blocks in file
        #   from info at top of file
        status = self._parse_file_header()


    def _get_img_size(self):
        # get img_size x and y
        metadata = self.get_img_metadata()
        img_size = metadata['Number Of Pixels']
        img_size = img_size.strip('()')
        (img_size_x, img_size_y) = img_size.split(' x ')
        self.img_size_x = int(img_size_x)
        self.img_size_y = int(img_size_y)


    def get_img_data(self, invert=False):
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
        # takes  ~45ms currently for 696x520 (WITH numpy)
        # takes ~250ms currently for 696x520 (NO numpy)
        #print("save_img_as_tiff_sc START")
        #mytimer = tictoc.Timer()

        (img_x, img_y, img_data) = self.get_img_data(invert=invert)

        # TODO: find min/max based on %pixels above max, below min

        # image data min/max
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
            img_data = np.array(img_data, dtype='int32')
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


    def get_img_metadata(self):
        """
        Data Block 7 contains strings describing image:

        Scanner Name: ChemiDoc XRS
        Number of Pixels: (696 x 520)
        Image Area: (200.0 mm x 149.4 mm)
        Scan Memory Size: 836.32 Kb
        Old file name: Chemi 2017-05-17 10hr 56min-2.1sc
        New file name: A11 2017-05-17 10hr 56min-2 B.1sc
        CHEMIDOC\Chemi
        New Image Acquired
        Save As...
        Quantity One 4.6.8 build 027
        """
        # very fast, usu ~250us

        # init metadata dict
        metadata = {}

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
                    metadata[info_str_list[0]] = info_str_list[1]
                else:
                    if info_str.startswith('Quantity One'):
                        metadata['Quantity One'] = info_str
                    elif '\\' in info_str:
                        metadata['path'] = info_str
                    else:
                        # as a last resort, make key=item=info_str
                        metadata[info_str] = info_str

        return metadata


    def _get_next_data_block_end(self, byte_idx):
        #block_num = 0
        #end_idx = data_start[0] + data_len[0]

        for i in range(11):
            if byte_idx < self.data_start[i] + self.data_len[i]:
                block_num = i
                end_idx = self.data_start[i] + self.data_len[i]
                break
        return (block_num, end_idx)


    def _process_payload_type102(self, field_payload, field_ids=None):
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

    def _process_payload_type101(self, field_payload, field_ids=None):
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

        field_info_payload['items'] = field_payload_items

        return field_info_payload


    def _process_payload_type100(self, field_payload, field_ids=None):
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

        field_info_payload['regions'] = field_payload_regions

        return field_info_payload


    def _process_data_region(self, region, payload, field_ids, data_types):
        region_data = {}
        data_region_start = region['byte_offset']
        data_region_end = region['byte_offset'] + \
                region['word_size'] * region['num_words']
        data_raw = payload[data_region_start:data_region_end]
        region_data['raw'] = data_raw

        data_proc = None
        data_interp = None
        data_type_str = None

        if region['data_type'] in [1, 2]:
            # byte / ASCII
            if len(data_raw) > 1 and is_ascii(data_raw):
                data_proc = data_raw.rstrip(b"\x00").decode('utf-8', 'ignore')
                data_type_str = "ASCII"
            else:
                data_proc = unpack_uint8(data_raw)
                data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
                data_type_str = "byte"
        elif region['data_type'] in [3, 4]:
            # u?int16
            data_proc = unpack_uint16(data_raw, endian="<")
            data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
            data_type_str = "uint16"
        elif region['data_type'] in [5, 6, 9]:
            # u?int32
            data_proc = unpack_uint32(data_raw, endian="<")
            data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
            if region['label'].endswith("time"):
                # TODO: what time format?
                data_interp = time.asctime(time.gmtime(data_proc))
            data_type_str = "uint32"
        elif region['data_type'] in [7,]:
            # u?int64
            data_proc = unpack_uint64(data_raw, endian="<")
            data_proc = data_proc[0] if len(data_proc) == 1 else data_proc
            data_type_str = "uint64"
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
                    data_interp = self._process_payload_data_container(
                            field_info_ref,
                            data_types,
                            field_ids
                            )
            else:
                data_interp = None
            data_type_str = "uint32 Reference"
        else:
            pass
            # TODO: make generic data types work based on word_size?
            #print("Data Type "+ repr(region['data_type']) + " is Unknown",
            #        file=sys.stderr)
            #print("  word_size: " + repr(region['word_size']))
            #print("  num_words: " + repr(region['num_words']))

        region_data['proc'] = data_proc
        region_data['interp'] = data_interp
        region_data['type'] = data_type_str
        region_data['type_num'] = region['data_type']

        return region_data


    def _process_payload_data_container(self,
            field_info, data_types, field_ids):
        data_dict = {}
        this_data_field = data_types[field_info['type']]
        data_key = field_ids[this_data_field['data_key_ref']]['regions']

        for dkey in data_key:
            region = data_key[dkey]
            region_data = self._process_data_region(
                    region,
                    field_info['payload'],
                    field_ids,
                    data_types
                    )
            data_dict[region['label']] = region_data

        return data_dict


    def get_img_metadata2(self):
        """
        Fetch All Metadata in File
        """
        field_ids = {}
        collections = {}

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
        byte_idx = self.data_start[0] + 8
        while byte_idx < self.data_start[10]:
            (byte_idx, field_info) = self._read_field_lite(byte_idx)
            # TODO: remove payload before saving to field_ids?
            field_ids[field_info['id']] = field_info

            if field_info['type'] == 0:
                # we just saw an End Of Data Block Field
                (_, end_idx) = self._get_next_data_block_end(byte_idx)
                # skip to beginning of next data block
                byte_idx = end_idx + 8
            elif field_info['type'] in [2, 16]:
                # TODO: is type 2 ever useful?
                pass
            elif field_info['type'] == 102:
                # collection definition
                data_types = {}
                field_payload_info = self._process_payload_type102(
                        field_info['payload'], field_ids=field_ids)
                field_info.update(field_payload_info)
                collections[field_info['collection_label']] = {}
                this_coll = collections[field_info['collection_label']]
            elif field_info['type'] == 101:
                # collection items
                field_payload_info = self._process_payload_type101(
                        field_info['payload'], field_ids=field_ids)
                field_info.update(field_payload_info)
                data_types = field_info['items']
            elif field_info['type'] == 100:
                # data keys (data format)
                field_payload_info = self._process_payload_type100(
                        field_info['payload'], field_ids=field_ids)
                field_info.update(field_payload_info)
                field_ids[field_info['id']] = field_info
            elif field_info['type'] in data_types:
                # data containers
                data_dict = self._process_payload_data_container(
                        field_info,
                        data_types,
                        field_ids
                        )
                this_coll[data_types[field_info['type']]['label']] = data_dict
            else:
                raise Exception(
                        "Unknown Field Type %d in Collection"%field_info['type']
                        )

        return collections


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
            block_ptr_types = {
                    142:0, 143:1, 132:2, 133:3, 141:4,
                    140:5, 126:6, 127:7, 128:8, 129:9, 130:10}
            if field_info['type'] in block_ptr_types:
                block_num = block_ptr_types[field_info['type']]
                out_uint32s = unpack_uint32(
                        field_info['payload'], endian="<")
                self.data_start[block_num] = out_uint32s[0]
                self.data_len[block_num] = out_uint32s[1]

            if field_info['type'] == 0:
                break

            # break if we still aren't advancing
            if byte_idx == field_start:
                raise Exception("Problem parsing file header")

"""
1sc FILE FORMAT NOTES:
--------
Header
    <2-byte field_type>
    <2-byte byte length of entire field (len(Header) + len(Payload))>
    <4-byte uint32 field_id>
Payload
    <bytes or uint16 or uint32 until end of field>

--------------------------
root type: 102
type 16 can be repeatedly referenced

--------------------------
102  ->  101 ->  100 ->  16
    \->  16 \->  16

--------------------------
0     End Of Data Block Field.
      Following this field is Data Block Footer, Data Block Header
--------------------------
126   Data Block 6 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

127   Data Block 7 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

128   Data Block 8 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

129   Data Block 9 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

130   Data Block 10 - Image Data Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

132   Data Block 2 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

133   Data Block 3 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

140   Data Block 5 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

141   Data Block 4 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

142   Data Block 0 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

143   Data Block 1 Info
      field_id = 0
      field_len = 20 (header_uint16s[1] = 1)

--------------------------
16    String field - text label assigned to previous data through data_id
      NO references to other fields
      YES referenced by: 100, 101, 102, 131, 1000

--------------------------
2     nop field? - payload is all 0's, otherwise normal header
      NO references to other fields
      YES referenced by: 1015
      field_id = one of { 0x1099c4a8, 0x10b9d4a8, 0x10d9e4a8, 0x11e4a4a8,
        0x128944a8, 0x144144a8}
      field_len = 208

100   Data field - contains multiple data assigned to future text labels
      YES references to: 16,
      YES referenced by: 101,
      Last 4 bytes of field headers of field_type=16 is data_id that match
      data_id uint32s in this field payload
      Every 36 bytes is data item
      Bytes 12-15 are uint32 data_id tag

101   Data field - contains multiple data assigned to future text labels
      YES references to: 16, 100
      YES referenced by: 102
      Last 4 bytes of field headers of field_type=16 is data_id that match
      data_id uint32s in this field payload
      Every 20 bytes is data item
      Bytes 16-19 are uint32 data_id tag

102   Data field - contains multiple data assigned to future text labels
      ROOT FIELD of hierarchy
      YES references to: 16, 101
      NOT referenced by other field
      Last 4 bytes of field headers of field_type=16 is data_id that match
      data_id uint32s in this field payload
      Every 16 bytes is data item
      Bytes 12-15 are uint32 data_id tag

> 102 Data Container Fields
      Contain Raw data, referred to by Fields Type 101, described by
            Data Key Field 100
"""
