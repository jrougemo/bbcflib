from bbcflib.btrack import FeatureStream
import sys

####################################################################
def sentinelize(iterable, sentinel):
    """Append *sentinel* at the end of *iterable* (avoid StopIteration error)."""
    for item in iterable: yield item
    yield sentinel

####################################################################
def reorder(stream,fields):
    """Reorders *stream.fields* so that *fields* come first.

    :param stream: FeatureStream object.
    :param fields: list of field names.
    :rtype: FeatureStream
    """
    if not(hasattr(stream, 'fields')) or stream.fields is None:
        return stream
    if not(all([f in stream.fields for f in fields])):
        raise ValueError("Need %s fields in stream."%(", ".join(fields)))
    if all(stream.fields[n] == f for n,f in enumerate(fields)):
        return stream
    _inds = [stream.fields.index(f) for f in fields]+[n for n,f in enumerate(stream.fields) if f not in fields]
    _flds = [stream.fields[n] for n in _inds]
    return FeatureStream((tuple(x[n] for n in _inds) for x in stream), fields=_flds)

####################################################################
def unroll( stream, regions, fields=['score'] ):
    """Creates a stream of *end*-*start* items with appropriate *fields* values at every base position.
    For example, ``unroll([(10,12,0.5,'a'), (14,15,1.2,'b')], start=9, end=16)`` returns::

        FeatureStream([(0,),(0.5,'a'),(0.5,'a'),(0,),(0,),(1.2,'b'),(0,)])
                        9     10     11    12   13    14    15

    :param stream: FeatureStream object.
    :param regions: either a pair (start,end) or a FeatureStream interpreted as bounds of the region(s) to return.
    :param fields: list of field names **in addition to 'start','end'**. [['score']]
    :rtype: FeatureStream
    """
    if not(isinstance(fields,(list,tuple))): fields = [fields]
    with_chrom = False
    if isinstance(regions,(list,tuple)):
        if len(regions) > 2: with_chrom = True
        regions = iter([regions])
    else:
        _f = ['start','end']
        if 'chr' in regions.fields:
            _f = ['chr']+_f
            with_chrom = True
        regions = reorder(regions,_f)
    if with_chrom:
        s = reorder(stream,['start','end','chr']+fields)
        nf = 3
    else:
        s = reorder(stream,['start','end']+fields)
        nf = 2
    item0 = (0,)+(None,)*(len(fields)-1)
    def _unr(s):
        for reg in regions:
            if with_chrom:
                chrom,pos,end = reg[:3]
            else:
                chrom = None
                pos,end = reg[:2]
            for x in s:
                if chrom and not(x[2] == chrom): continue
                if x[1] <= pos: continue
                while pos < min(x[0],end):
                    yield item0
                    pos+=1
                while pos < min(x[1],end):
                    yield x[nf:]
                    pos+=1
                if pos >= end: break
            while pos < end:
                yield item0
                pos+=1
    return FeatureStream(_unr(s),fields=s.fields[nf:])

####################################################################
def sorted_stream(stream,chrnames=[],fields=['chr','start','end'],reverse=False):
    """Sorts a stream according to *fields* values. Will load the entire stream in memory.
    The order of names in *chrnames* is used to sort the 'chr' field if available.

    :param stream: FeatureStream object.
    :param chrnames: list of chrmosome names.
    :param fields: list of field names. [['chr','start','end']]
    :param reverse: reverse order. [False]
    :rtype: FeatureStream
    """
    fidx = [stream.fields.index(f) for f in fields]
    chri = -1
    if 'chr' in fields: chri = fields.index('chr')
    feature_list = list(stream)
    sort_list = []
    for n,f in enumerate(feature_list):
        if chri>=0 and f[fidx[chri]] in chrnames: fchr = chrnames.index(f[fidx[chri]])
        else: fchr = f[fidx[chri]]
        x = tuple(f[i] for i in fidx[:chri])+(fchr,)+tuple(f[i] for i in fidx[chri+1:])+(n,)
        sort_list.append(x)
    sort_list.sort(reverse=reverse)
    return FeatureStream((feature_list[t[-1]] for t in sort_list), stream.fields)

####################################################################
def shuffled(stream, chrlen=sys.maxint, repeat_number=1, sorted=True):
    """Return a stream of randomly located features of the same length and annotation
    as these of the original stream.

    :param stream: FeatureStream object.
    :param chrlen: (int) chromosome length. [9223372036854775807]
    :param repeat_number: (int) *repeat_number* random features are yielded per input feature. [1]
    :rtype: FeatureStream
    """
    import random
    _f = ['start','end']
    features = reorder(stream,_f)
    def _shuffled(_s):
        randpos = []
        for feat in _s:
            feat_len = feat[1]-feat[0]
            for s in xrange(repeat_number):
                if len(randpos) == 0:
                    randpos = [random.randint(0, chrlen-feat_len) for i in xrange(10000)]
                start = randpos.pop()
                yield (start,start+feat_len)+feat[2:]
    if sorted:
        return sorted_stream(FeatureStream(_shuffled(features),features.fields),fields=_f)
    else:
        return FeatureStream(_shuffled(features),features.fields)

####################################################################
def strand_merge(x):
    """Return 1 (resp.-1) if all elements in x are 1 (resp.-1), 0 otherwise."""
    return all(x[0]==y for y in x[1:]) and x[0] or 0

def no_merge(x):
    """Assuming all elements of x are identical (chr) or irrelevant, return only the first one."""
    return x[0]

def generic_merge(x):
    """Sum numeric values; concatenate str values; stack tuples."""
    if isinstance(x[0],(int, long, float, complex)):
        return sum(x)
    if isinstance(x[0],basestring):
        return "|".join(x)
    if isinstance(x[0],tuple):
        x0 = x[0]
        for y in x[1:]:
            x0 += tuple(y)
        return x0

aggreg_functions = {'strand': strand_merge, 'chr': no_merge}

def fusion(stream,aggregate=aggreg_functions):
    """Fuses overlapping features in *stream* and applies *aggregate[f]* function to each field $f$.

    Example::

        [('chr1',10,15,'A',1),('chr1',13,18,'B',-1),('chr1',18,25,'C',-1)]

        yields

        (10, 18, 'chr1', 'A|B', 0)
        (18, 25, 'chr1', 'C', -1)

    :param stream: FeatureStream object.
    :rtype: FeatureStream
    """
    def _fuse(s):
        s = reorder(s,['start','end'])
        try:
            x = list(s.next())
        except StopIteration:
            return
        has_chr = 'chr' in s.fields
        if has_chr: chridx = s.fields.index('chr')
        for y in s:
            new_chr = has_chr and (x[chridx] != y[chridx])
            if y[0] < x[1] and not(new_chr):
                x[1] = max(x[1], y[1])
                x[2:] = [aggregate.get(f,generic_merge)((x[n+2],y[n+2]))
                         for n,f in enumerate(s.fields[2:])]
            else:
                yield tuple(x)
                x = list(y)
        yield tuple(x)

    info = [f for f in stream.fields if f not in ['start','end']]
    return reorder(FeatureStream( _fuse(stream), fields=['start','end']+info), stream.fields )

def cobble(stream,aggregate=aggreg_functions):
    """Fragments overlapping features in *stream* and applies `aggregate[f]` function
    to each field `f` in common fragments.

    Example::

        [('chr1',10,15,'A',1),('chr1',13,18,'B',-1),('chr1',18,25,'C',-1)]

        yields

        (10, 13, 'chr1', 'A', 1)
        (13, 15, 'chr1', 'A|B', 0)
        (15, 18, 'chr1', 'B', -1)
        (18, 25, 'chr1', 'C', -1)

    This is to avoid having overlapping coordinates of features from both DNA strands,
    which some genome browsers cannot handle for quantitative tracks.

    :param stream: FeatureStream object.
    :rtype: FeatureStream
    """
    def _intersect(A,B,fields):
        """Return *z*, the part that must replace A in *toyield*, and
        *rest*, that must reenter the loop instead of B."""
        rest = None
        a = tuple(A[2:])
        b = tuple(B[2:])
        ab = tuple([aggregate.get(f,generic_merge)((A[k+2],B[k+2])) for k,f in enumerate(fields[2:])])
        if B[0] < A[1]:           # has an intersection
            if B[1] < A[1]:
                if B[0] == A[0]:  # same left border, A is bigger
                    z = [(B[0],B[1])+ab, (B[1],A[1])+a]
                elif B[0] < A[0]: # B shifted to the left wrt A
                    z = [(B[0],A[0])+b, (A[0],B[1])+ab, (B[1],A[1])+a]
                else:             # B embedded in A
                    z = [(A[0],B[0])+a, (B[0],B[1])+ab, (B[1],A[1])+a]
            elif B[1] == A[1]:
                if B[0] == A[0]:  # identical
                    z = [(A[0],A[1])+ab]
                elif B[0] < A[0]: # same right border, B is bigger
                    z = [(B[0],A[0])+b, (A[0],B[1])+ab]
                else:             # same right border, A is bigger
                    z = [(A[0],B[0])+a, (B[0],B[1])+ab]
            else:
                if B[0] == A[0]:  # same left border, B is bigger
                    z = [(A[0],A[1])+ab]
                    rest = (A[1],B[1])+b
                elif B[0] < A[0]: # B contains A
                    z = [(B[0],A[0])+b, (A[0],A[1])+ab]
                    rest = (A[1],B[1])+b
                else:             # B shifted to the right wrt A
                    z = [(A[0],B[0])+a, (B[0],A[1])+ab]
                    rest = (A[1],B[1])+b
        else: z = None            # no intersection
        return z, rest

    def _fuse(stream):
        stream = reorder(stream,['start','end'])
        try:
            x = stream.next()
        except StopIteration:
            return
        toyield = [x]
        while 1:
            try:
                x = stream.next()
                intersected = False
                for y in toyield:
                    replace, rest = _intersect(y,x,stream.fields)
                    print x,replace,rest
                    if replace:
                        intersected = True
                        iy = toyield.index(y)
                        y = toyield.pop(iy)
                        for k in range(len(replace)):
                            toyield.insert(iy+k, replace[k])
                        x = rest
                        if not x: break
                if not intersected:
                    while toyield:
                        y = toyield.pop(0)
                        yield tuple(y)
                    toyield = [x]
                elif x:
                    toyield.append(x)
            except StopIteration:
                while toyield:
                    y = toyield.pop(0)
                    yield tuple(y)
                break

    info = [f for f in stream.fields if f not in ['start','end']]
    return reorder(FeatureStream( _fuse(stream), fields=['start','end']+info), stream.fields )

####################################################################
