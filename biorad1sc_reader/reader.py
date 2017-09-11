#!/usr/bin/env python3

# see LARGE amount of file format notes at end of this file

import os.path
import struct
#import tictoc

from PIL import Image
try:
    import numpy as np
except:
    HAS_NUMPY = False
else:
    HAS_NUMPY = True


# for debugging (DELETEME)
if HAS_NUMPY:
    print("YES Numpy")
else:
    print("No Numpy")


def save_u16_to_tiff(u16in, size, tiff_filename):
    # takes  2-14ms currently for 696x520 (WITH numpy)
    # takes 15-41ms currently for 696x520 (NO numpy)
    #print("save_u16_to_tiff START")
    #mytimer = tictoc.Timer()
    # write 16-bit TIFF image

    # PIL interprets mode 'I;16' as "uint16, little-endian"
    img_out = Image.new('I;16',size)

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

        # TODO: verify file magic number

        with open(self.filename, 'rb') as in_fh:
            self.in_bytes = in_fh.read()

        # get pointers to start, len of all major data blocks in file
        #   from info at top of file
        self._parse_data_blocks()


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
                # unsigned shorts (2-bytes)
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
                # little-endian unsigned shorts (2-bytes)
                img_data = list(
                        struct.unpack(
                            "%s%dH"%(self.endian, (img_end-img_start)/2),
                            self.in_bytes[img_start:img_end]
                            )
                        )
                # re-arrange image data so top-to-bottom
                #   1sc makes botttom to top originally
                self.img_data = []
                for i in range(len(img_data),0,-self.img_size_x):
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
            img_data = np.array(img_data,dtype='int32')
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
            img_data_scale = [min(max(x,0),2**16-1) for x in img_data_scale]

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

        # first 4 ushorts of data block are info about block
        byte_idx = self.data_start[7] + 8

        while byte_idx < (self.data_start[7] + self.data_len[7]):
            (byte_idx, field_info) = self._read_field_lite(byte_idx)
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


    def _get_generic(self, byte_stream, byte_start, format_str):
        # TODO: find endian (now we just assume little-endian)

        num_words = len(byte_stream) / struct.calcsize(format_str)
        out_words = list(
                struct.unpack(
                    "%s%d%s"%(self.endian, num_words, format_str),
                    byte_stream)
                )

        byte_idx = byte_start + len(byte_stream)
        return (out_words, byte_idx)


    def _get_uints(self, byte_stream, byte_start):
        (out_uints, byte_idx) = self._get_generic(byte_stream, byte_start, "I")
        return (out_uints, byte_idx)


    def _get_ushorts(self, byte_stream, byte_start):
        (out_shorts, byte_idx) = self._get_generic(byte_stream, byte_start, "H")
        return (out_shorts, byte_idx)


    def _process_field_header(self, byte_idx):
        # read header
        (header_ushorts, _) = self._get_ushorts(
                self.in_bytes[byte_idx:byte_idx+8], byte_idx)
        (header_uints, _) = self._get_uints(
                self.in_bytes[byte_idx:byte_idx+8], byte_idx)
        field_type = header_ushorts[0]
        field_len = header_ushorts[1]
        field_id = header_uints[1]

        # field_len of 1 or 2 means field_len=20
        if field_len == 1 or field_len == 2:
            field_len = 20

        return (field_type, field_len, field_id, header_ushorts, header_uints)


    def _process_payload_type0(self, payload_idx):
        # Finding the end of the jump algorithm
        # READ:
        #   ushort field_type=0
        #   ushort 8
        #   ushort 0
        #   ushort 0
        #   4*ushort
        #   ushort A
        #   if A==0 read 6*ushort, goto prev else exit, return this idx

        byte_idx = payload_idx
        byte_idx = byte_idx + 8
        while True:
            # do the next 7 ushorts start with a '0' value? if so keep looping
            (test_ushorts, _) = self._get_ushorts(
                    self.in_bytes[byte_idx:byte_idx+14], byte_idx)
            if test_ushorts[0] != 0:
                # next ushort was not 0, so it is valid field_type
                break
            byte_idx = byte_idx + 14

        field_len = byte_idx - (payload_idx - 8)
        return field_len


    def _read_field_lite(self, byte_idx, field_data={}, field_ids={}):
        field_info = {}
        # read header
        (field_type, field_len, field_id, _,
                _) = self._process_field_header(byte_idx)

        # get field_len if jump field
        if field_type == 0:
            field_len = self._process_payload_type0(byte_idx+8)

        # get payload bytes
        field_payload = self.in_bytes[byte_idx+8:byte_idx+field_len]

        # check for references
        references = []
        if len(field_payload) % 4 == 0:
            (out_uints, _) = self._get_uints(field_payload, byte_idx+8)
            references = [x for x in out_uints if x in field_ids]

        field_info['type'] = field_type
        field_info['id'] = field_id
        field_info['payload'] = field_payload
        field_info['references'] = references

        return (byte_idx+field_len, field_info)


    def _parse_data_blocks(self):
        # reset loop variables
        byte_idx = 160
        self.data_start = {}
        self.data_len = {}
        # init img data start at max 32-bit value
        self.data_start[10] = 0xffffffff

        while byte_idx < len(self.in_bytes):
            field_start = byte_idx

            (byte_idx, field_info) = self._read_field_lite(byte_idx)

            # record data blocks start, end
            block_ptr_types = {
                    142:0, 143:1, 132:2, 133:3, 141:4,
                    140:5, 126:6, 127:7, 128:8, 129:9, 130:10}
            if field_info['type'] in block_ptr_types:
                block_num = block_ptr_types[field_info['type']]
                (out_uints, _) = self._get_uints(field_info['payload'], 0)
                self.data_start[block_num] = out_uints[0]
                self.data_len[block_num] = out_uints[1]

            #if field_info['id'] != 0:
            #    field_ids[field_info['id']] = field_info

            # break if we still aren't advancing
            if byte_idx == field_start:
                print("ERROR!!")
                break

            if self.data_start[10] != 0xffffffff and len(self.data_start) > 10:
                # break when we get all data block pointers
                break


"""
1sc FILE FORMAT NOTES:
--------
Header
    <2-byte field_type>
    <2-byte byte length of entire field (len(Header) + len(Payload))>
    <4-byte uint field_id>
Payload
    <bytes or ushort or uint until end of field>

--------------------------
root types: 102, 1000, 1004, 1015
type 16 can be repeatedly referenced

--------------------------
102  ->  101 ->  100 ->  16
    \->  16 \->  16

1015 -> 1008 -> 1007 -> 16
    \-> 1024 -> 1022 -> 16
    \-> 2

1000 -> 1020 -> 1011 -> 1010 -> 1040 -> 131  -> 16
    |       |               |       |       \-> 1000 -> ...
    |       |               |       \-> 1000 -> ...
    |       |               \-> 1000 -> ...
    |       \-> 1000 -> ...
    \-> 1030 -> 1040 -> ...
    |       \-> 1000 -> ...
    \-> 1000 -> ...
    \-> 16

--------------------------
0     Jump Field - nop filler data
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      Around data block boundaries
      Contains info about data block, at end and beginning of data block

--------------------------
126   Data Block 6 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=6180 4 uints before end of Jump Field,
      right before field_type=102, data corresponding to text label
      "Audit Trail"
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=140's data block

127   Data Block 7 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=1020 4 uints before end of Jump Field,
      right before field_type=1000 with "Audit Trail" text inside
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=126's data block

128   Data Block 8 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=7293 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=127's data block

129   Data Block 9 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=1533 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=128's data block

130   Data Block 10 - Image Data Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=68 4 uints before end of Jump Field,
      right at IMAGE DATA START
      ends at end of image data (could be end of file)
      Image data pointer
      uint[0] = img data start, uint[1] = img data length
      this starts after end of field_type=129's data block

132   Data Block 2 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=?? 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=143's data block

133   Data Block 3 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=?? 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=132's data block

140   Data Block 5 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=?? 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=141's data block

141   Data Block 4 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=?? 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=133's data block

142   Data Block 0 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=40 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of long zero fill after 160-380 fields

143   Data Block 1 Info
      NO references to other fields
      NOT referenced by other field
      field_id = 0
      field_len = 20 (header_ushorts[1] = 1)
      1st uint a pointer to byte val=40 4 uints before end of Jump Field,
      ends at another spot 4 uints before end of Jump Field
      uint[0] = data block start, uint[1] = data length
      this starts after end of field_type=142's data block

--------------------------
16    String field - text label assigned to previous data through data_id
      NO references to other fields
      YES referenced by: 100, 101, 102, 131, 1000
      field_id: MSShort: one of {0x0085, 0x0086, 0x0087, 0x0088, 0x008a, 0x014a,
        0x014c, 0x014d, 0x0919, 0x091b, 0x1004, 0x1043, 0x1045, 0x107b, 0x107d,
        0x1083, 0x1097, 0x1099, 0x10b9, 0x10d9, 0x11e4, 0x1289, 0x1441}

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
      data_id uints in this field payload
      Every 36 bytes is data item
      Bytes 12-15 are uint data_id tag

101   Data field - contains multiple data assigned to future text labels
      YES references to: 16, 100
      YES referenced by: 102
      Last 4 bytes of field headers of field_type=16 is data_id that match
      data_id uints in this field payload
      Every 20 bytes is data item
      Bytes 16-19 are uint data_id tag

102   Data field - contains multiple data assigned to future text labels
      ROOT FIELD of hierarchy
      YES references to: 16, 101
      NOT referenced by other field
      Last 4 bytes of field headers of field_type=16 is data_id that match
      data_id uints in this field payload
      Every 16 bytes is data item
      Bytes 12-15 are uint data_id tag

131   Data field - contains multiple data assigned to future text labels
      YES references to: 16, 1000
      YES referenced by: 1040
      Last 4 bytes of field headers of field_type=16 is data_id that match
      data_id uints in this field payload
      Every 12 bytes is data item
      Bytes 4-7 are uint data_id tag

1000  pointed from data in 100 (and other types?)
      ROOT FIELD of hierarchy
      YES references to: 16, 1000, 1020, 1030
      YES referenced by: 131, 1000, 1010, 1020, 1030, 1040,
      Sometimes for field_type= 16, sometimes not (??)
      Is format fixed based on which data block?

1004  nop field? - payload is all 0's, otherwise normal header
      ROOT FIELD of hierarchy
      NO references to other fields
      NOT referenced by other field

1007
      YES references to: 16
      YES referenced by: 1008

1008
      YES references to: 1007
      YES referenced by: 1015

1010
      YES references to: 1000, 1040
      YES referenced by: 1011

1011
      YES references to: 1010
      YES referenced by: 1020

1015
      ROOT FIELD of hierarchy
      YES references to: 1008, 1024, 2
      NOT referenced by other field

1020
      YES references to: 1000, 1011
      YES referenced by: 1000

1022  No data items, only data_id tags?
      YES references to: 16
      YES referenced by: 1024
      4 uints in payload, first 3 uints are data_id tags
      Every 4 bytes is data item, last 4 bytes are not used (??)
      Bytes 0-3 are uint data_id tag

1024
      YES references to: 1022
      YES referenced by: 1015

1030
      YES references to: 1000, 1040
      YES referenced by: 1000

1040
      YES references to: 131, 1000
      YES referenced by: 1010, 1030

--------------------------
Data Block 00
    Fields type 16, 100, 101, 102

Data Block 01
    Fields type 1004
    Either NOP (no data) field, or no data in example 1sc files in possession

Data Block 02
    Fields type 16, 100, 101, 102

Data Block 03
    Fields type 16, 1000

    Strings (field_type=16):
	Mol. Wt.
	KDa
	Chemi 2017-05-17 10hr 56min-2
	C:\files del Chemidoc\E Colla
	Chemi 2017-05-17 10hr 56min-2.1sc

Data Block 04
    Fields type 16, 100, 101, 102

Data Block 05
    Fields type 2, 16, 10007, 1008, 1015, 1022, 1024

    Strings (field_type=16):
        C:\files del Chemidoc\E Colla
        Chemi 2017-05-17 10hr 56min-2.1sc
        Chemi 2017-05-17 10hr 56min-2 (Raw 1-D I
        Base Pairs, Base Pairs, BP,
	Isoelectric Point, Iso. Pt., pI,
	Isoelectric Point, Iso. Pt., pI
	Molecular Weight, Mol. Wt., KDa
	Normalized Rf, Norm. Rf, NRf

Data Block 06
    Fields type 16, 100, 101, 102

Data Block 07
    Fields type 16, 131, 1000, 1010, 1011, 1020, 1030, 1040

    Strings (field_type=16):
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

Data Block 08
    Fields type 16, 100, 101, 102 with
        text of and byte pointers to data in data block 09:
        filevers, creation_date, last_use_date, user_id, prog_name, scanner,
        old_description, old_comment, desc, pH_orient, Mr_orient, nxpix, nypix,
        data_fmt, bytes_per_pix, endian, max_OD, pix_at_max_OD,
        img_size_x, img_size_y, min_pix, max_pix, mean_pix, data_ceiling,
        data_floor, cal, formula, imgstate, qinf, params, history, color,
        light_mode, size_mode, norm_pix, bkgd_pix, faint_loc, small_loc,
        large_box, bkgd_box, dtct_parm_name, m_id32, m_scnId, m_imagePK, SCN,

        calfmt, dettyp, isotop, gel_run_date, cnts_loaded, xpo_start_date,
        xpo_length, ScnCalibInfo

        type, units, c_pro, c_exp, ScnFormula

        x, y, ScnImgloc

        first, last, ScnImgbox

        mincon, maxcon, in, out, low_frac, high_frac, state, gamma, aspect,
        ScnImgState

        qty_range, qty_units, blackIsZero, scanner_maxpix, scanner_units,
        scanner_bias, scanner_maxqty, calstep_count, calstep_raw, calstep_qty,
        calstep_qty_offset, gray_response_data, gray_response_len,
        gray_response_factor, ScnQtyInfo

        x, y, ScnCrdloc

        x, y, ScnCrdres

        first, last, ScnCrdbox

        resolution, scan_area, exposure_time, ref_bkg_time, gain_setting,
        light_mode, color, intf_type, size_mode, imaging_mode,
        filter_name1, filter_name2, filter_name3, filter_name4, filter_name5,
        filter_id1, filter_id2, filter_id3, filter_id4, filter_id5,
        laser_name1, laser_name2, laser_name3, laser_name4, laser_name5,
        laser_id1, laser_id2, laser_id3, laser_id4, laser_id5,
        pmt_voltage, dark_type, live_count, app_name, flat_field, ScnParams

        GR_Data, GrayResponseData, Scan Header

Data Block 09
    Field type 1000 with
        data for:
        filevers, creation_date, last_use_date, user_id, prog_name, scanner,
        old_description, old_comment, desc, pH_orient, Mr_orient, nxpix, nypix,
        data_fmt, bytes_per_pix, endian, max_OD, pix_at_max_OD,
        img_size_x, img_size_y, min_pix, max_pix, mean_pix, data_ceiling,
        data_floor, cal, formula, imgstate, qinf, params, history, color,
        light_mode, size_mode, norm_pix, bkgd_pix, faint_loc, small_loc,
        large_box, bkgd_box, dtct_parm_name, m_id32, m_scnId, m_imagePK, SCN,

Data Block 10
    Only image data, no fields
"""
