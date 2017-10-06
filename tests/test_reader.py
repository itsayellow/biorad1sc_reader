#!/usr/bin/env python3

import os
import os.path
import shutil
from PIL import Image
from PIL import ImageChops
import biorad1sc_reader
import unittest


class TestReader(unittest.TestCase):
    testdata_dir = './testdata'
    scratch_dir = './scratch'
    input_files = ['test1.1sc', 'test2.1sc', 'test3.1sc', 'test4.1sc',
            'test5.1sc']
    tiff_ref_files = ['test1_ref.tif', 'test2_ref.tif', 'test3_ref.tif',
            'test4_ref.tif', 'test5_ref.tif']
    tiff_ref_inv_files = ['test1_ref_inv.tif', 'test2_ref_inv.tif',
            'test3_ref_inv.tif', 'test4_ref_inv.tif', 'test5_ref_inv.tif']
    tiff_ref_sc_files = ['test1_ref_sc.tif', 'test2_ref_sc.tif', 'test3_ref_sc.tif',
            'test4_ref_sc.tif', 'test5_ref_sc.tif']
    tiff_ref_inv_sc_files = ['test1_ref_inv_sc.tif', 'test2_ref_inv_sc.tif',
            'test3_ref_inv_sc.tif', 'test4_ref_inv_sc.tif', 'test5_ref_inv_sc.tif']

    def setUp(self):
        """
        Occurs before every test method
        """
        try:
            os.mkdir(self.scratch_dir)
        except FileExistsError:
            # if dir exists, remove it and create new one
            # start with fresh dir
            #shutil.rmtree(self.scratch_dir)
            #os.mkdir(self.scratch_dir)
            pass


    def tearDown(self):
        """
        Occurs after every test method
        """
        pass
        #try:
        #    shutil.rmtree(self.scratch_dir)
        #except:
        #    raise


    def test_tif(self):
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)
            test_img_file = os.path.join(self.scratch_dir, inroot + "_test.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff(test_img_file)

            im_ref = Image.open(ref_img_file)
            im_test = Image.open(test_img_file)

            self.assertEqual(im_ref.size, im_test.size)

            # the following in PIL makes a ResourceWarning: unclosed file
            #   TODO: how to work-around??
            im_ref_data = im_ref.getdata()
            im_test_data = im_test.getdata()

            self.assertEqual(list(im_ref_data), list(im_test_data))


    def test_tif_inv(self):
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)
            print(infile_fullpath)
            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff(
                    os.path.join(self.scratch_dir, inroot + "_test_inv.tif"),
                    invert=True
                    )

    def test_tif_sc(self):
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)
            print(infile_fullpath)
            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff_sc(
                    os.path.join(self.scratch_dir, inroot + "_test_sc.tif")
                    )

    def test_tif_inv_sc(self):
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)
            print(infile_fullpath)
            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff_sc(
                    os.path.join(self.scratch_dir, inroot + "_test_inv_sc.tif"),
                    invert=True
                    )


if __name__ == '__main__':
    unittest.main()
