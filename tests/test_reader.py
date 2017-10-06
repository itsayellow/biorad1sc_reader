#!/usr/bin/env python3

import os
import os.path
import shutil
import unittest
import json
from PIL import Image
from PIL import ImageChops
import biorad1sc_reader


class TestTiffExport(unittest.TestCase):
    tests_dir = os.path.dirname(__file__)
    testdata_dir = os.path.join(tests_dir, 'testdata')
    scratch_dir = os.path.join(tests_dir, 'scratch')
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
            shutil.rmtree(self.scratch_dir)
            os.mkdir(self.scratch_dir)
        # record state of HAS_NUMPY
        self.has_numpy = biorad1sc_reader.reader.HAS_NUMPY


    def tearDown(self):
        """
        Occurs after every test method
        """
        # put HAS_NUMPY back to orig state
        biorad1sc_reader.reader.HAS_NUMPY = self.has_numpy
        # remove scratch dir
        shutil.rmtree(self.scratch_dir)


    def compare_images(self, ref_img_file, test_img_file):
        im_ref = Image.open(ref_img_file)
        im_test = Image.open(test_img_file)

        self.assertEqual(im_ref.size, im_test.size)

        # the following in PIL makes a ResourceWarning: unclosed file
        #   TODO: how to work-around??
        im_ref_data = list(im_ref.getdata())
        im_test_data = list(im_test.getdata())

        # do these to fail fast if they are not matching
        self.assertEqual(max(im_test_data), max(im_ref_data))
        self.assertEqual(min(im_test_data), min(im_ref_data))
        # check row by row
        # we could check all data points at once, but this takes way too long
        #   (hangs) on unequal lists
        (row_size, col_size) = im_ref.size
        for i in range(col_size):
            self.assertEqual(
                    im_ref_data[i*row_size:(i+1)*row_size],
                    im_test_data[i*row_size:(i+1)*row_size]
                    )


    def test_tif_with_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = True
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff(test_img_file)

            self.compare_images(ref_img_file, test_img_file)


    def test_tif_no_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = False
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff(test_img_file)

            self.compare_images(ref_img_file, test_img_file)


    def test_tif_inv_with_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = True
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test_inv.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_inv_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff(test_img_file, invert=True)

            self.compare_images(ref_img_file, test_img_file)


    def test_tif_inv_no_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = False
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test_inv.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_inv_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff(test_img_file, invert=True)

            self.compare_images(ref_img_file, test_img_file)


    def test_tif_sc_with_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = True
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test_sc.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_sc_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff_sc(test_img_file)

            self.compare_images(ref_img_file, test_img_file)


    def test_tif_sc_no_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = False
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test_sc.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_sc_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff_sc(test_img_file)

            self.compare_images(ref_img_file, test_img_file)


    def test_tif_inv_sc_with_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = True
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test_inv_sc.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_inv_sc_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff_sc(test_img_file, invert=True)

            self.compare_images(ref_img_file, test_img_file)


    def test_tif_inv_sc_no_numpy(self):
        biorad1sc_reader.reader.HAS_NUMPY = False
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            test_img_file = os.path.join(self.scratch_dir, inroot + "_test_inv_sc.tif")
            ref_img_file = os.path.join(self.testdata_dir, self.tiff_ref_inv_sc_files[i])

            myread = biorad1sc_reader.Reader(infile_fullpath)
            myread.save_img_as_tiff_sc(test_img_file, invert=True)

            self.compare_images(ref_img_file, test_img_file)


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        # handle bytes if found
        if isinstance(obj, bytes):
            ret_obj = {}
            ret_obj['__bytes__'] = True
            ret_obj['data'] = list(obj)
            return ret_obj
        # for all else use default encoder
        return json.JSONEncoder.default(self, obj)


class TestMetadataExport(unittest.TestCase):
    tests_dir = os.path.dirname(__file__)
    testdata_dir = os.path.join(tests_dir, 'testdata')
    input_files = ['test1.1sc', 'test2.1sc', 'test3.1sc', 'test4.1sc',
            'test5.1sc']
    meta_ref_files = ['test1_ref_meta.json', 'test2_ref_meta.json',
            'test3_ref_meta.json', 'test4_ref_meta.json', 'test5_ref_meta.json'] 
    meta_compact_ref_files = ['test1_ref_meta_compact.json',
            'test2_ref_meta_compact.json', 'test3_ref_meta_compact.json',
            'test4_ref_meta_compact.json', 'test5_ref_meta_compact.json'] 

    def test_get_metadata(self):
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            ref_meta_file = os.path.join(self.testdata_dir, self.meta_ref_files[i])

            testread = biorad1sc_reader.Reader(infile_fullpath)
            testmeta = testread.get_metadata()
            testmeta_json = json.dumps(testmeta, cls=BytesEncoder, sort_keys=True)

            with open(ref_meta_file, 'r') as in_fh:
                refmeta_json = in_fh.read()

            self.assertEqual(refmeta_json, testmeta_json)


    def test_get_metadata_compact(self):
        for (i, infile) in enumerate(self.input_files):
            infile_fullpath = os.path.join(self.testdata_dir, infile)
            (inroot, _) = os.path.splitext(infile)

            ref_metac_file = os.path.join(self.testdata_dir, self.meta_compact_ref_files[i])

            testread = biorad1sc_reader.Reader(infile_fullpath)
            testmetac = testread.get_metadata_compact()
            testmetac_json = json.dumps(testmetac, cls=BytesEncoder, sort_keys=True)

            with open(ref_metac_file, 'r') as in_fh:
                refmetac_json = in_fh.read()

            self.assertEqual(refmetac_json, testmetac_json)


if __name__ == '__main__':
    unittest.main()
