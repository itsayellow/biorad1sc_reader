#!/usr/bin/env python3

import biorad1sc_reader
from unittest import TestCase

class TestReader(TestCase):
    input_files = ['test1.1sc', 'test2.1sc', 'test3.1sc', 'test4.1sc',
            'test5.1sc']
    tiff_plain_files = ['test1.tif', 'test2.tif', 'test3.tif', 'test4.tif',
            'test5.tif']


