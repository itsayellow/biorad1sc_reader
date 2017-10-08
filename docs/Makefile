# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python3 -msphinx
SPHINXPROJ    = biorad1sc_reader
SOURCEDIR     = .
BUILDDIR      = _build

# Matt added
SPHINXBUILDTARGETS   = html dirhtml singlehtml pickle json htmlhelp qthelp \
                       devhelp epub latex latexpdf latexpdfja text man \
                       texinfo info gettext changes xml pseudoxml linkcheck \
                       doctest coverage 

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Matt added
.PHONY: $(SPHINXBUILDTARGETS)

cmdline_utils.rst : make_cmdline_utils ../biorad1sc_reader/cmd_bio1sc2tiff.py \
    ../biorad1sc_reader/cmd_bio1scmeta.py ../biorad1sc_reader/cmd_bio1scread.py
	./make_cmdline_utils

# Matt modified
# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
$(SPHINXBUILDTARGETS): Makefile cmdline_utils.rst
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


# > python3 -msphinx help . _build
#Sphinx v1.6.4
#Please use `make target' where target is one of
#  html        to make standalone HTML files
#  dirhtml     to make HTML files named index.html in directories
#  singlehtml  to make a single large HTML file
#  pickle      to make pickle files
#  json        to make JSON files
#  htmlhelp    to make HTML files and an HTML help project
#  qthelp      to make HTML files and a qthelp project
#  devhelp     to make HTML files and a Devhelp project
#  epub        to make an epub
#  latex       to make LaTeX files, you can set PAPER=a4 or PAPER=letter
#  latexpdf    to make LaTeX and PDF files (default pdflatex)
#  latexpdfja  to make LaTeX files and run them through platex/dvipdfmx
#  text        to make text files
#  man         to make manual pages
#  texinfo     to make Texinfo files
#  info        to make Texinfo files and run them through makeinfo
#  gettext     to make PO message catalogs
#  changes     to make an overview of all changed/added/deprecated items
#  xml         to make Docutils-native XML files
#  pseudoxml   to make pseudoxml-XML files for display purposes
#  linkcheck   to check all external links for integrity
#  doctest     to run all doctests embedded in the documentation (if enabled)
#  coverage    to run coverage check of the documentation (if enabled)
