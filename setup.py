from distutils.core import setup

setup(
        name            =   'bbcflib',
        version         =   '2.0.1',
        description     =   'Utility modules for deploying workflows in the BBCF',
        long_description=   open('README.md').read(),
        license         =   'GNU General Public License 3.0',
        url             =   'http://bbcf.epfl.ch/bbcflib',
        author          =   'EPFL BBCF',
        author_email    =   'webmaster.bbcf@epfl.ch',
        install_requires=   ['mailer', 'rpy2', 'pysam', 'scipy', 'numpy', 'sqlalchemy', 'sqlite3'],
        classifiers     =   ['Topic :: Scientific/Engineering :: Bio-Informatics'],
        packages        =   ['bbcflib',
                             'bbcflib.track',
                             'bbcflib.gfminer',
                             'bbcflib.gfminer.stream',
                             'bbcflib.gfminer.numeric',
                             'bbcflib.gfminer.figure',
                             'bein',
                            ],
    )
