#!/usr/bin/env python3

"""
Custom errors in reading/processing Bio-Rad *.1sc files.
"""


class BioRadInvalidFileError(Exception):
    """
    Indicates this file is not a valid Bio-Rad *.1sc file.
    """

    pass


class BioRadParsingError(Exception):
    """
    Internal Error parsing file.
    """

    pass
