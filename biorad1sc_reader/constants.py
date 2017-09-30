#!/usr/bin/env python3
"""
Constants used in processing *.1sc files
"""

BLOCK_PTR_TYPES = {142:0, 143:1, 132:2, 133:3, 141:4,
        140:5, 126:6, 127:7, 128:8, 129:9, 130:10, }

# Data Types above 999 are unreliable, inconsistent
REGION_DATA_TYPES = {
        1:"byte",
        2:"byte/ASCII",
        3:"u?int16",
        4:"uint16",
        5:"u?int32",
        6:"u?int32",
        7:"uint64",
        9:"uint32",
        10:"8-byte - float?", # 53-bit coefficient, 11-bit exponent, 1 sign bit
        15:"uint32 Reference",
        17:"uint32 Reference",
        21:"u?int32",
        131:"12-byte??",
        1001:"8- or 24-byte??",
        1002:"24-byte??",
        1003:"8-byte (x,y)??",
        1004:"8- or 16-byte (x1,y1,x2,y2)??",
        1005:"64-byte??",
        1006:"640-byte??",
        1010:"144-byte??",
        1016:"440-byte??",
        1020:"32-byte??",
        1027:"8-byte??",
        1032:"12-byte??",
        }

# used if Word Size region in Field Type 100 is inexplicably 0
REGION_DATA_TYPE_BYTES = {
        1:1,
        2:1,
        3:2,
        4:2,
        5:4,
        6:4,
        7:8,
        9:4,
        10:8,
        15:4,
        17:4,
        21:4,
        131:12,
        }

# Data Types:
#    1:"u?byte",
#    2:"u?byte/ASCII",
#    3:"u?int16",
#    4:"uint16",
#    5:"u?int32",
#    6:"u?int32",
#    7:"uint64",
#    9:"uint32",
#    15:"uint32 Reference",
#    17:"uint32 Reference",
#
#    01100100 = 100:"8-byte?"
#    01100110 = 102:"16-byte?"
#    01100111 = 103:"8-byte?"
#    01101011 = 107:"8-byte?"
#    01101110 = 110:"8-byte?"
#    01110011 = 115:"4-byte?"
#    01111000 = 120:"8-byte?"
#    10000011 = 131:"12-byte??",
#    11_11101001 = 1001:"8- or 24-byte??",
#    11_11101010 = 1002:"24-byte??",
#    11_11101011 = 1003:"8- or 16-byte (x,y)??",
#    11_11101100 = 1004:"8- or 16-byte (x1,y1,x2,y2)??",
#    11_11101101 = 1005:"64-byte??",
#    11_11101110 = 1006:"12- or 640-byte??",
#    11_11110010 = 1010:"144-byte??",
#    11_11110011 = 1011:"8-byte??",
#    11_11110100 = 1012:"16-byte??",
#    11_11111000 = 1016:"440-byte??",
#    11_11111011 = 1019:"8-byte??",
#    11_11111100 = 1020:"32-byte??",
#    11_11111111 = 1023:"24-byte??",
#    1027:"8-byte??",
#    1032:"12-byte??",
#    1036:"8-byte??",
#    1048:"40-byte??",

