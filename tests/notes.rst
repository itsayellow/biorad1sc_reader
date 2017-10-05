Testing Notes
=============

Reference TIFF Files
--------------------

1. Open ImageLab 5.2.1 on Mac
#. Export File as Tiff
    1. File -> Export -> Export for Analysis...
    #. filename e.g. test1_imglab_analysis.tif
#. Convert colorspace to Monochrome grayscale from RGB using Graphicsmagick.
   We use "_inv" the opposite way ImageLab does, because ImageLab actually inverts
   the image data and calls that "non-inverted".
    1. ``gm convert -colorspace gray test1_imglab_analysis.tif test1_ref_inv.tif``
#. Create inverted grayscale version
    1. ``gm convert -negate test1_ref_inv.tif test1_ref.tif``
#. Create scaled inverted grayscale version
    1. ``gm convert set historgram-threshold 0 -normalize test1_ref_inv.tif test1_ref_inv_sc.tif``
#. Create scaled grayscale version
    1. ``gm convert set historgram-threshold 0 -normalize test1_ref.tif test1_ref_sc.tif``
