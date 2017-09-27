#!/usr/bin/env python3
"""
Constants used in processing *.1sc files
"""

BLOCK_PTR_TYPES = {142:0, 143:1, 132:2, 133:3, 141:4,
        140:5, 126:6, 127:7, 128:8, 129:9, 130:10, }

REGION_DATA_TYPES = {
        1:"byte",
        2:"byte/ASCII",
        3:"u?int16",
        4:"uint16",
        5:"u?int32",
        6:"u?int32",
        7:"uint64",
        9:"uint32",
        10:"8-byte - float?",
        15:"uint32 Reference",
        17:"uint32 Reference",
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


