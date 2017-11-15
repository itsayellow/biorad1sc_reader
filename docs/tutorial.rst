Tutorial
========

Reading a 1sc file starts with importing the ``biorad1sc_reader`` package

.. code:: python

    import biorad1sc_reader

Then to access the data of a given 1sc file, we instance the class ``Reader``

.. code:: python

    myreader = biorad1sc_reader.Reader()

For convenience, you can specify the name of the file to read as an argument
of the class initialization

.. code:: python

    myreader = biorad1sc_reader.Reader("path/to/some/file.1sc")

You can also initialize the class with a file-like object set for read/binary
access:

.. code:: python

    my1sc_fh = open("path/to/some/file.1sc", 'rb')
    myreader = biorad1sc_reader.Reader(my1sc_fh)

After you instance the class ``Reader`` into your own variable, you can use
that to access and decode the 1sc file's data.

For example, to get a succinct data structure of all metadata in 1sc file:

.. code:: python

    my_img_metadata = myreader.get_metadata_compact()

To save the image data as a 16-bit TIFF with no processing, use:

.. code:: python

    myreader.save_img_as_tif("exactly_as_in_1sc.tif")
