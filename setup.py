# setup for biorad1sc_reader package

import os.path
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(here, 'README.rst'), 'r') as f:
    long_description = f.read()

setup(
        name='biorad1sc_reader',
        version='0.5.1',
        description='Allows reading Bio-Rad *.1sc image/analysis files.',
        long_description=long_description,
        url='http://github.com/itsayellow/biorad1sc_reader/',
        author='Matthew A. Clapp',
        author_email='itsayellow+dev@gmail.com',
        license='MIT',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'Topic :: Multimedia :: Graphics',
            'Topic :: Scientific/Engineering :: Bio-Informatics',
            'Topic :: Scientific/Engineering :: Medical Science Apps.',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3'
            ],
        keywords='biorad 1sc biology scientific imaging',
        packages=['biorad1sc_reader'],
        install_requires=['Pillow'],
        python_requires='>=3',
        test_suite='nose2.collector.collector',
        tests_require=['nose2','numpy'],
        entry_points={
            'console_scripts': [
                'bio1sc2tiff = biorad1sc_reader.cmd_bio1sc2tiff:entry_point',
                'bio1scmeta = biorad1sc_reader.cmd_bio1scmeta:entry_point',
                'bio1scread = biorad1sc_reader.cmd_bio1scread:entry_point',
                ],
            },
        )
