Examples
========

.. code:: python

    # setup reader with input file
    import biorad1sc_reader
    myreader = biorad1sc_reader.Reader("my_biorad_file.1sc")
    
    # get list/dict of all metadata in 1sc file
    my_img_metadata = myreader.get_metadata()

    # get a more succinct data structure of all metadata in 1sc file
    my_img_metadata = myreader.get_metadata_compact()

    # get a quick summary of some metadata about the image in the 1sc file
    my_img_metadata = myreader.get_img_summary()

    # Different options for writing image data out as a TIFF file
    myreader.save_img_as_tif("unscaled_brightness.tif")
    myreader.save_img_as_tif("unscaled_inverted_brightness.tif", invert=True)
    myreader.save_img_as_tif_sc("scaled_brightness.tif")
    myreader.save_img_as_tif_sc("scaled_brightness_more.tif", scale=0.8)
    myreader.save_img_as_tif_sc("scaled_inverted_brightness.tif", invert=True)

