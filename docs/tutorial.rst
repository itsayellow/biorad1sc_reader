Tutorial
========

Reading a 1sc file starts with an instance of the class `Reader`\ :

.. code:: python

    myreader = bio1sc_reader.Reader()

For convenience, you can specify the name of the file to read as an argument
of the class initialization:
.. code:: python

    myreader = bio1sc_reader.Reader("path/to/some/file.1sc")

