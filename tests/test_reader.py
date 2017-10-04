#!/usr/bin/env python3

import biorad1sc_reader
from unittest import TestCase

class TestReader(TestCase):
    testdata_dir = './testdata'
    input_files = ['test1.1sc', 'test2.1sc', 'test3.1sc', 'test4.1sc',
            'test5.1sc']
    tiff_ref_files = ['test1_ref.tif', 'test2_ref.tif', 'test3_ref.tif',
            'test4_ref.tif', 'test5_ref.tif']
    tiff_ref_inv_files = ['test1_ref_inv.tif', 'test2_ref_inv.tif',
            'test3_ref_inv.tif', 'test4_ref_inv.tif', 'test5_ref_inv.tif']

    def test_tif(self):
        pass
