####################################
Command-line Utilities Documentation
####################################

===========
bio1sc2tiff
===========

Convert input 1sc file(s) to TIFF image(s).

-----
Usage
-----

``bio1sc2tiff [-h] [-s] [-i] [-o OUTPUT_FILENAME] src_1sc_file [src_1sc_file ...]``

--------------------
Positional Arguments
--------------------

``src_1sc_file``
    Source 1sc file.

------------------
Optional Arguments
------------------

-h, --help            show this help message and exit
-s, --scale           Scale brightness of output image to maximize dynamic
                        range between darkest and lightest pixels in input
                        file.
-i, --invert          Invert brightness scale of image.
-o OUTPUT_FILENAME, --output_filename OUTPUT_FILENAME
                        Name of output image. (Defaults to <input_image>.tif)


==========
bio1scmeta
==========

Print all metadata contained in 1sc file(s).

-----
Usage
-----

``bio1scmeta [-h] [-v VERBOSITY] [-o OUTPUT_FILENAME] src_1sc_file [src_1sc_file ...]``

--------------------
Positional Arguments
--------------------

``src_1sc_file``
    Source 1sc file.

------------------
Optional Arguments
------------------

-h, --help            show this help message and exit
-v VERBOSITY, --verbosity VERBOSITY
                        Verbosity of report, number, 0, 1, or 2 (default 0).
-o OUTPUT_FILENAME, --output_filename OUTPUT_FILENAME
                        Name of output text file. (Defaults to
                        <filename>_meta.txt in same directory as source file.


==========
bio1scread
==========

Read/Parse Bio-Rad \*.1sc file(s) and produce reports detailing their internal structure

-----
Usage
-----

``bio1scread [-h] [-S] srcfile [srcfile ...]``

--------------------
Positional Arguments
--------------------

``srcfile``
    Source 1sc file(s).

------------------
Optional Arguments
------------------

-h, --help          show this help message and exit
-S, --omit_strings  Do not include Type 16 String fields in reports. (But
                      include the strings when listing references to them.)

