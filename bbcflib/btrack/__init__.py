"""
Examples::

    import btrack as track

    track.convert("data/test.bed","test0.sql",chrmeta='mm9')

Open a bed track & copy its info into another sql track::

    chrmeta = {'chr2':{'length':4000000}}
    info = {'datatype':'features'}
    track_in = track.track("data/test.bed",chrmeta=chrmeta)
    track_out = track.track("test1.sql",fields=['start','end','name'],chrmeta=chrmeta,info=info)
    track_out.write(track_in.read())
    track_out.close()
    track_in.close()

Copy a selection of a bed track into a wig track::

    track_in = track.track("data/HoxD13_4C_FB.sql")
    track_out = track.track("test2.wig")
    selection = [{'chr':'chr1','start':(7568000,9607000)},{'chr':'chr2','end':(3907400,4302000)}]
    track_out.write(track_in.read(selection=selection),mode='overwrite')
    track_out.close()
    track_in.close()

Read a track (see :func:`FeatureStream <bbcflib.btrack.FeatureStream>`)::

    track_in = track.track("data/Gene_TxS_chr2.bed.gz",chrmeta='mm9',format='bed')
    for x in track_in.read():
        print x  #('chr2', 3030497, 3032496, 'ENSMUST00000072955_txS')
        break

Split field::

    from bFlatMajor.common import split_field
    for x in split_field(track_in.read(),['name','extension'],'name','_'):
        print x  #['chr2', 3030497, 3032496, 'ENSMUST00000072955', 'txS']
        break

Random track::

    from bFlatMajor.common import shuffled
    for n,x in enumerate(shuffled(track_in.read('chr2'),chrlen=chrmeta['chr2']['length'])):
        print x
        if n>10: break

Do something with the scores of a signal track only if the location is present in another features track::

    selection = {'chr':'chr2','start':(7540000,75650000)}
    track_features = track.track("data/Bricks_HoxD4_FB_05_chr2.bed")
    track_scores = track.track("data/HoxD13_4C_FB.sql",readonly=True)
    score = float()
    length = float()
    for x in track_scores.read(selection=track_features.read(selection=selection),
                               fields=['start','end','score']):
        score += x[2]*(x[1]-x[0])
        length += (x[1]-x[0])
    track_features.close()
    track_scores.close()
    print score/length

"""

__all__ = ['Track','track','FeatureStream','convert',
           'strand_to_int','int_to_strand','format_float','format_int',
           'ucsc_to_ensembl','ensembl_to_ucsc']

import sys, os, re

_track_map = {
    'sql': ('bbcflib.btrack.sql','SqlTrack'),
    'db':  ('bbcflib.btrack.sql','SqlTrack'),
    'text':('bbcflib.btrack.text','TextTrack'),
    'txt': ('bbcflib.btrack.text','TextTrack'),
    'bed': ('bbcflib.btrack.text','BedTrack'),
    'bedGraph': ('bbcflib.btrack.text','BedGraphTrack'),
    'bedgraph': ('bbcflib.btrack.text','BedGraphTrack'),
    'sga': ('bbcflib.btrack.text','SgaTrack'),
    'wig': ('bbcflib.btrack.text','WigTrack'),
    'gff': ('bbcflib.btrack.text','GffTrack'),
    'gtf': ('bbcflib.btrack.text','GffTrack'),
    'bigWig': ('bbcflib.btrack.bin','BigWigTrack'),
    'bigwig': ('bbcflib.btrack.bin','BigWigTrack'),
    'bw':  ('bbcflib.btrack.bin','BigWigTrack'),
    'bam': ('bbcflib.btrack.bin','BamTrack'),
}

def track( path, format=None, **kwargs):
    """
    Guess file format and return a Track object of the corresponding subclass (e.g. BedTrack).

    :param path: (str) name of/path to a track-like file. If the file does not exist yet,
        a new track-like file of the requested *format* will be created at this location
        on closure, if data is added to the track (using `write()`).
    :param format: (str) format of the file. If not provided, the format is set according
        to the file's extension.
    :param **kwargs: (dict) parameters of the Track subclass' constructor.
        Typically `assembly` or `chrmeta`.
    """
    assert isinstance(path,str), "*path*: Expected string, %s found." % type(path)
    if format is None:
        path2, format = os.path.splitext(path)
        format = format.lstrip('.')
        if format in ['gz','gzip']:
            format = os.path.splitext(path2)[1].lstrip('.')
        if format == '':
            with open(path, 'r') as file:
                rstart = file.read(15)
                if rstart == "SQLite format 3": format='sql'
                else:
                    while rstart.startswith("#"):
                        rstart = file.readline()
                        rstart = file.read(1)
                    rstart += file.readline()
                    head = re.search(r'track\s+type=(\S+)',rstart)
                    if head: format = head.groups()[0]
    if not(format in _track_map):
        raise Exception("The format '%s' is not supported."%format)
    __import__(_track_map[format][0])
    return getattr(sys.modules[_track_map[format][0]],
                   _track_map[format][1])(path,**kwargs)

def convert( source, target, chrmeta=None, info=None ):
    """
    Converts a file from one format to another. Format can be explicitly specified::

        convert(('file1','bed'), ('file2','sql')) ,

    otherwise it is guessed first from file extension::

        convert('file1.bed', 'file2.sql')

    or in the worst case, by reading the first lines of the file.

    :param source: (str or tuple) path to the source file, or tuple of the form (path, format).
    :param target: (str or tuple) path to the target file, or tuple of the form (path, format).
    """
    if isinstance(source, tuple):
        tsrc = track(source[0], format=source[1], chrmeta=chrmeta)
    else:
        tsrc = track(source, chrmeta=chrmeta)
    if isinstance(target, tuple):
        ttrg = track(target[0], format=target[1], chrmeta=tsrc.chrmeta, fields=tsrc.fields, info=info)
    else:
        ttrg = track(target, chrmeta=tsrc.chrmeta, fields=tsrc.fields, info=info)
    ttrg.write( tsrc.read() )
    ttrg.close()
    tsrc.close()
    return ttrg

def strand_to_int(strand=None):
    """Convert +/- into 1/-1 notation for DNA strands."""
    if strand == '+': return 1
    if strand == '-': return -1
    return 0

def int_to_strand(num=0):
    """Convert 1/-1 into +/- notation for DNA strands."""
    num = int(num)
    if num > 0: return '+'
    if num < 0: return '-'
    return '.'

def format_float(f=float()):
    """Return a formatted string from a float or a string representing a float.
    Limit to 4 decimals after the comma."""
    return '%.4g' % float(f)

def format_int(i=int()):
    """Return a formatted string from an integer or a string representing an integer."""
    return '%i' % int(i)

def ucsc_to_ensembl(start):
    """Add +1 to start coordinates going from UCSC to Ensembl annotation."""
    return format_int(int(start)+1)

def ensembl_to_ucsc(start):
    """Substract 1 to start coordinates going from Ensembl to UCSC annotation."""
    return format_int(int(start)-1)

################################################################################

class Track(object):
    """
    Metaclass regrouping the track properties. Subclasses for each specific format
    are respectively in `btrack/text.py`, `btrack/bin.py`, `btrack/sql.py`,
    and are instanciated when ``btrack.track()`` is called on a file.

    .. attribute:: path

        Path to the file the Track was generated from.

    .. attribute:: filehandle

        The Python opened file object from the file found in *self.path*. Can read() and write() it.

    .. attribute:: format

        Format of the file the track was generated from.

    .. attribute:: fields

        Fields defining the info contained in the track items.

    .. attribute:: assembly

        GenRep assembly ID.

    .. attribute:: chrmeta

        A dictionary with information about the species' chromosomes, or a genrep assembly name.

    .. attribute:: info

        A dictionary with meta-data about the track, e.g. data type, such as::

            {'datatype': 'signal'}

    """
    def __init__(self, path, **kwargs):
        self.path = path
        self.filehandle = None
        self.format = kwargs.get("format")
        self.fields = kwargs.get("fields",[])
#        self.types = {}
        self.assembly = kwargs.get('assembly')
        self.chrmeta = self._get_chrmeta(kwargs.get('chrmeta'))
        self.info = self._get_info(info=kwargs.get('info'))

    def _get_chrmeta(self,chrmeta=None):
        """:param chrmeta: (str or dict) assembly name, or dict of the type {chr: {'length': 1234}}."""
        if isinstance(chrmeta,dict):
            return chrmeta
        if isinstance(chrmeta,basestring):
            self.assembly = chrmeta
        if self.assembly is None:
            return {}
        from bbcflib import genrep
        return genrep.Assembly(self.assembly).chrmeta

    def _get_info(self,info=None):
        pass

    def __enter__(self):
        """Called when evaluating the 'with' statement."""
        return self

    def __exit__(self, errtype, value, traceback):
        self.close()

    def __iter__(self):
        """Iterates on the list of features."""
        return iter(self.read())

    def open(self):
        pass

    def close(self):
        pass

    def save(self):
        self.open()
        self.close()

    def read(self, **kw):
        pass

    def write(self, **kw):
        pass

################################################################################
class FeatureStream(object):
    """
    Contains an iterator yielding features, and an extra fields attribute.
    It can be constructed from either an iterator, a cursor, a list or a tuple.

    Example::

        stream = FeatureStream([('chr',1,2),('chr',3,4)])
        stream = FeatureStream((('chr',1,2),('chr',3,4)))
        stream = FeatureStream(iter([('chr',1,2),('chr',3,4)]))

        def gen():
            for k in range(2):
                yield ('chr',2*k+1,2*k+2)

        stream = FeatureStream(gen())

    Example of usage::

        >>> stream = FeatureStream([('chr',1,2),('chr',3,4)], fields=['chromosome','start','end'])
        >>> stream.next()
        ('chr', 1, 2)
        >>> stream.next()
        ('chr', 3, 4)
        >>> stream.data
        <listiterator object at 0x10183b650>

        >>> stream = FeatureStream([('chr',1,2),('chr',3,4)], fields=['chromosome','start','end'])
        >>> for s in stream: print s
        ('chr', 1, 2)
        ('chr', 3, 4)

    .. attribute:: data

        An iterator, cursor, list or tuple. Each item is a tuple with as many members as the number of *fields*.

    .. attribute:: fields

        The list of field names.

    .. method:: __iter__()

        ``iter(self)`` returns self.data, which is an iterator itself.

    .. method:: next()

        Iterating over the stream is iterating over its data.

    """

    def __init__(self, data, fields=None, basetrack=None):
        if isinstance(data,(list,tuple)):
            basetrack = data
            data = iter(data)
        if not fields:
            if hasattr(data, 'description'):
                fields = [x[0] for x in data.description]
            else: raise ValueError("Must specify a 'fields' attribute for %s." % self.__str__())
        self.data = data
        self.fields = fields
        self.basetrack = basetrack # (Track,selection,fields,..., kw) if read from track

    def __iter__(self):
        return self.data

    def next(self):
        return self.data.next()

    def reset(self):
        if self.basetrack:
            try:
                if isinstance(self.basetrack[0],Track):
                    args = self.basetrack[1:-1]
                    kwargs = self.basetrack[-1]
                    self.data = self.basetrack[0].read(*args, **kwargs)
                elif isinstance(self.basetrack,(list,tuple)):
                    self.data = iter(self.basetrack)
            except:
                print "Warning: Only Track- or list-based streams can be reset."


################################################################################
