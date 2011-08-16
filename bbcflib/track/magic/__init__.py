"""
===============================
Subpackage: bbcflib.track.magic
===============================

This function uses the python-magic project at ftp://ftp.astron.com/pub/file/ to guess formats.
The python-magic is part of file project (file unix command)

"""

# Built-in modules #
from pkg_resources import resource_filename

###############################################################################
def guess_file_format(path):
    '''
    Try to detect the file type.
    Return one of 'known_formats' value if successfull,
    otherwise return an empty string
    TODO : magic doesn't work on each systems.
    keep it or just rest with the extensions ??
     
    '''
    # Link between descriptions and file extension #
    known_formats = {
        'SQLite 3.x database':                          'sql',
        'SQLite database (Version 3)':                  'sql',
        'Hierarchical Data Format (version 5) data':    'hdf5',
        'BED Document':                                 'bed',
        'BEDGRAPH Document':                            'bedgraph',
        'PSL Document':                                 'psl',
        'GFF Document':                                 'gff',
        'GTF Document':                                 'gtf',
        'WIG Document':                                 'wig',
        'MAF Document':                                 'maf',
    }
    # Try import #
    try: import magic
    except ImportError: return ''
    # Try version #
    if not hasattr(magic, 'open'): return ''
    # Add our definitions #
    mime = magic.open(magic.NONE)
    mime.load(file=resource_filename(__name__, 'magic_data'))
    filetype = mime.file(path).rstrip(", ")
    # Otherwise try standard definitions #
    if not filetype in known_formats:
        mime = magic.open(magic.NONE)
        mime.load()
        filetype = mime.file(path)
        # Otherwise try standard definitions #
        if not filetype in known_formats:
            mime = magic.open(magic.MAGIC_NONE)
            mime.load()
            filetype = mime.file(path)
        # Try the conversion dict #
        return known_formats.get(filetype, '')
    except Exception: return ''
