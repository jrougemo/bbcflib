from bbcflib.track import FeatureStream
from functools import wraps
import sys, re, itertools, operator, random, string
from numpy import log as nlog
from numpy import asarray,mean,median,exp,nonzero,prod,around,argsort,float_

####################################################################
def ordered(fn):
    """
    Decorator. Keeps the original order of fields for a stream passing through one of
    gfminer functions that take and return a FeatureStream, or a list of FeatureStream objects.
    """
    @wraps(fn) # makes the wrapper take the same name as the wrapped function when called
    def wrapper(*args,**kwargs):
        tracks = None
        if len(args) > 0:
            tracks = args[0]
        elif len(kwargs) > 0:
            from bbcflib.gfminer import stream
            tracks = kwargs.get(stream.stream().loadable(fn.__name__)[0])
        if tracks is None:
            return fn(*args,**kwargs)
        if not (isinstance(tracks,(list,tuple))):
            tracks = [tracks]
        original_fields = [t.fields for t in tracks]

        returned = fn(*args,**kwargs) # original function call

        if not (isinstance(returned,(list,tuple))):
            new_fields = returned.fields
            original_fields = [f for f in original_fields[0] if all([f in tf for tf in original_fields[1:]])]
            return reorder(returned, [f for f in original_fields if f in new_fields])
        else:
            new_fields = [r.fields for r in returned]
            nl = len(original_fields)
            original_fields = [[f for f in original_fields[min(n,nl)] if f in nf]
                               for n,nf in enumerate(new_fields)]
            return [reorder(r, fields=original_fields[n]) for n,r in enumerate(returned)]

    return wrapper

####################################################################
def sentinelize(stream, sentinel=sys.maxint):
    """Append *sentinel* at the end of *iterable* (avoid StopIteration error)."""
    def _sentinelize(stream):
        for item in stream: yield item
        yield sentinel
    return FeatureStream(_sentinelize(stream), fields=stream.fields)

def copy(stream,n=2):
    """Return *n* independant copies of *stream*. Has to be called before iterating
    over *stream*, otherwise it will copy only the remaining items of *stream*. Will
    load at once the whole stream in memory."""
    if n==1: return stream
    return [FeatureStream(x,stream.fields) for x in itertools.tee(stream)]

####################################################################
def add_name_field(stream):
    """
    Adds a unique name to each record in the stream.
    """
    ci = stream.fields.index('chr')
    si = stream.fields.index('start')
    ei = stream.fields.index('end')
    _f = stream.fields+['name']
    return FeatureStream((r+("%s:%i-%i"%(r[ci],r[si],r[ei]),) for r in stream),
                         fields=_f)
####################################################################
def select(stream, fields=None, selection={}):
    """
    Keeps only specified *fields* from a stream, and/or only elements matching *selection*.

    :param stream: FeatureStream.
    :param fields: (list of str) list of fields to keep in the output.
    :param selection: (dict {*field*:*val*}) keep only lines s.t. *field* has a value
        equal to *val*, or is an element of *val*. E.g. `select(f,None,{'chr':['chr1','chr2']})`.
        *val* can also be a function returning True or False when applied to an element of the field;
        if True, the element is kept.
    :rtype: FeatureStream, or list of FeatureStream objects.
    """
    def _select(stream,idxs):
        if selection:
            sel = dict([(stream.fields.index(f),val) for f,val in selection.iteritems()])
            for x in stream:
                for k,val in sel.iteritems():
                    if isinstance(val,(list,tuple)):
                        if not x[k] in val: continue
                    elif hasattr(val,'__call__'):
                        if not val(x[k]): continue
                    else:
                        if not x[k] == val: continue
                    yield tuple([x[i] for i in idxs])
        else:
            for x in stream:
                yield tuple([x[i] for i in idxs])

    if not fields: fields=stream.fields
    idxs = [stream.fields.index(f) for f in fields]
    assert all([x > -1 for x in idxs]), "Can only select amongst fields %s." % stream.fields
    assert hasattr(stream,'fields') and stream.fields, "Object %s has no attribute 'fields'." % stream
    return FeatureStream(_select(stream,idxs), fields=fields)

####################################################################
def reorder(stream,fields,last=False):
    """Reorders *stream.fields* so that *fields* come first.

    :param stream: FeatureStream object.
    :param fields: list of field names.
    :param last: (bool) if True, reorders fields so that *fields* come last.
    :rtype: FeatureStream
    """
    if not(hasattr(stream, 'fields')) or stream.fields is None:
        return stream
    if not(all([f in stream.fields for f in fields])):
        raise ValueError("Need %s fields in stream."%(", ".join(fields)))
    if all(stream.fields[n] == f for n,f in enumerate(fields)):
        return stream
    if last:
        _inds = [n for n,f in enumerate(stream.fields) if f not in fields]+[stream.fields.index(f) for f in fields]
    else:
        _inds = [stream.fields.index(f) for f in fields]+[n for n,f in enumerate(stream.fields) if f not in fields]
    _flds = [stream.fields[n] for n in _inds]
    return FeatureStream((tuple(x[n] for n in _inds) for x in stream), fields=_flds)

####################################################################
def apply(stream,fields,functions):
    """
    Applies custom transformations to the respective fields.

    :param stream: FeatureStream object.
    :param fields: (list of str) list of fields to transform in the output.
    :param functions: list of functions to apply to the respective *fields*.
    :rtype: FeatureStream, or list of FeatureStream objects
    """
    def _apply(stream,fields,functions):
        nf = len(stream.fields)
        idx = [stream.fields.index(f) for f in fields]
        fct = dict(zip(idx,functions))
        for i in range(nf): fct.setdefault(i, lambda x:x)
        for x in stream:
            yield tuple([fct[i](x[i]) for i in range(nf)])

    if isinstance(fields,str): fields = [fields]
    if hasattr(functions,'__call__'): functions = [functions]
    assert len(fields) == len(functions),"The number of fields does not equal the number of functions."
    return FeatureStream(_apply(stream,fields,functions),fields=stream.fields)

####################################################################
def duplicate(stream,infield,outfields):
    """
    Duplicate one of *stream*'s fields. If outfields has more than one element,
    the field is copied as many times.

    :param stream: FeatureStream object.
    :param infield: (str) name of the field to be duplicated.
    :param outfields: (str, or list of str) the new field(s) to be created.
    """
    def _duplicate(stream,infield,outfields):
        in_idx = stream.fields.index(infield)
        for x in stream:
            yield x + (x[in_idx],)*len(outfields)

    assert infield in stream.fields, "Field %s not found." % infield
    assert isinstance(infield,str), "Expected string, %s found." % type(infield)
    assert isinstance(outfields,(str,list)), "Expected string or list, % found." % type(outfields)
    if isinstance(outfields,str): outfields = [outfields]
    return FeatureStream(_duplicate(stream,infield,outfields), fields=stream.fields+outfields)

####################################################################
def concat_fields( stream, infields, outfield='name', separator='|', as_tuple=False ):
    """
    Concatenate fields of a stream. Ex.:

    ('chr1', 12, 'aa', 'bb') -> ('chr1', 12, 'aa|bb')     # as_tuple=False
    ('chr1', 12, 'aa', 'bb') -> ('chr1', 12, ('aa','bb')) # as_tuple=True

    :param stream: FeatureStream object.
    :param infields: (list of str) list of fields to concatenate.
    :param outfield: (str) name of the new field created by concatenation of *infields*
        (can be an already existing one). ['name']
    :param separator: (str) char to add between entries from concatenated fields. ['|']
    :param as_tuple: (bool) join concatenated field entries in a tuple instead of a
        separator in a single string. [False]
    :rtype: FeatureStream object.
    """
    _infields = [f for f in stream.fields if not(f in infields)] # untouched fields
    in_out_indx = [stream.fields.index(f) for f in _infields]
    to_extend = []
    if not(outfield in _infields):
        _infields += [outfield]
        to_extend = [None]
    out_indx = _infields.index(outfield)
    in_indx = [stream.fields.index(f) for f in infields]
    def _concat(stream):
        for x in stream:
            y = [x[i] for i in in_out_indx]+to_extend
            if as_tuple:
                y[out_indx] = tuple((x[i] for i in in_indx))
            else:
                y[out_indx] = separator.join([str(x[i]) for i in in_indx])
            yield tuple(y)
    return FeatureStream(_concat(stream),_infields)

####################################################################
def split_field( stream, outfields, infield='name', separator=';',
                 header_split=None, strip_input=False ):
    """
    Split one field of a stream containing multiple information, into multiple fields. Ex.:

    ('chr1', 12, 'aa;bb;cc') -> ('chr1', 12, 'aa', 'bb', 'cc')

    ('chr1', 12, 'name=aa;strand="+";score=143;additional="X"') -> ('chr1', 12, 'aa', 243, '+', 'additional="X"')

    :param stream: FeatureStream object.
    :param outfields: (list of str) list of new fields to be created.
    :param infield: (str) name of the field to be split. ['name']
    :param separator: (str) char separating the information in *infield*'s entries. [';']
    :param header_split: if split entries are field_name/field_value pairs, provides the separator to split them.
    :param strip_input: (bool) if True for a field of name/value pairs, will remove from the original field
        the values that have been succesfully parsed.
    """
    _outfields = stream.fields+[f for f in outfields if not(f in stream.fields)]
    in_indx = stream.fields.index(infield)
    more_len = len(_outfields)-len(stream.fields)
    if not strip_input: _outfields.remove(infield)
    out_indx = [_outfields.index(f) for f in outfields]
    def _split(stream):
        for x in stream:
            y = list(x)
            if not strip_input: y.pop(in_indx)
            y += [None for f in range(more_len)]
            if isinstance(x[in_indx],(list,tuple)):
                xsplit = [str(_) for _ in x[in_indx]]
            else:
                xsplit = x[in_indx].split(separator)
            if header_split is not None:
                xmore = dict([re.search(r'\s*(\S+?)\s*'+header_split+'\s*(\S*)',v+' '+header_split).groups()
                              for v in xsplit if v])
                for n,f in enumerate(outfields):
                    y[out_indx[n]] = xmore.get(f,'').strip('"')
                if strip_input:
                    y[in_indx] = separator.join([str(k)+header_split+str(v)
                                                 for k,v in xmore.iteritems()
                                                 if not(k in outfields)])
            else:
                for n,v in enumerate(xsplit):
                    if n >= len(out_indx):
                        raise ValueError("Input has more elements (%s) than the number (%d) of output fields provided:" \
                                          % (xsplit,len(outfields)))
                    y[out_indx[n]] = v
                if strip_input:
                    y[in_indx] = separator.join(xsplit[n:])
            yield tuple(y)

    return FeatureStream(_split(stream),_outfields)

####################################################################
def map_chromosomes( stream, chromosomes, keep=False ):
    """
    Translate the chromosome identifiers in *stream* into chromosome names of the type 'chr5'.

    :param stream: FeatureStream object.
    :param chromosomes: a dictionary of chromosomes, such as `genrep.Assembly.chromosomes`.
    :param keep: (bool) keep all features (True) or only those which chromosome identifier
        is recognized (False). [False]
    """
    if not('chr' in stream.fields): return stream
    ic = stream.fields.index('chr')
    chrom_map = {}
    for k,c in chromosomes.iteritems():
        cname = c['name']
        chrom_map[cname] = cname                                                  # {'chrIV': 'chrIV'}
        if cname.startswith('chr') and len(cname)>3: chrom_map[cname[3:]] = cname # {'IV': 'chrIV'}
        chrom_map[k[0]] = cname                                                   # {2780: 'chrIV'}
        chrom_map[str(k[1])+"."+str(k[2])] = cname                                # {'NC_001136.9': 'chrIV'}
        chrom_map[str(k[0])+"_"+str(k[1])+"."+str(k[2])] = cname                  # {'2780_NC_001136.9': 'chrIV'}
        if c.get('synonyms'):
            for s in c['synonyms'].split(','): chrom_map[s] = cname               # {synonym: 'chrIV'}
    if keep:
        return FeatureStream((x[:ic]+(chrom_map.get(x[ic],x[0]),)+x[ic+1:]
                              for x in stream),stream.fields)
    else:
        return FeatureStream((x[:ic]+(chrom_map[x[ic]],)+x[ic+1:]
                              for x in stream if x[ic] in chrom_map),stream.fields)

####################################################################
def score_threshold( stream, threshold=0.0, lower=False, strict=False, fields='score' ):
    """
    Filter the features of a track which score is above or below a certain threshold.

    :param stream: FeatureStream, or list of FeatureStream objects.
    :param threshold: (float) threshold above/below which features are retained
    :param lower: (bool) higher (False) or lower (True) bound.
    :param strict: (bool) strictly above/below threshold.
    :param fields: (str or list of str) names of the fields to apply the filter to.
    :rtype: FeatureStream, or list of FeatureStream objects
    """
    if not(isinstance(fields,(list,tuple))):
           fields = [fields]
    def _threshold(stream,th,lower,fields):
        gt = operator.gt if strict else operator.ge
        lower = -1 if lower else 1
        fidx = [stream.fields.index(f) for f in fields]
        for x in stream:
            if all([gt(lower*x[k],lower*th) for k in fidx]):
                yield x
    if isinstance(stream,(list,tuple)):
        return [FeatureStream(_threshold(s,threshold,lower,fields), fields=s.fields) for s in stream]
    else:
        return FeatureStream(_threshold(stream,threshold,lower,fields), fields=stream.fields)

####################################################################
def unroll( stream, regions, fields=['score'] ):
    """Creates a stream of *end*-*start* items with appropriate *fields* values at every base position.
    For example, ``unroll([(10,12,0.5,'a'), (14,15,1.2,'b')], regions=(9,16))`` returns::

        FeatureStream([(0,),(0.5,'a'),(0.5,'a'),(0,),(0,),(1.2,'b'),(0,)])
                        9      10        11      12   13     14      15

    :param stream: FeatureStream object.
    :param regions: either a pair (start,end) or an ordered list of such pairs or a FeatureStream
        interpreted as bounds of the region(s) to return.
    :param fields: list of field names **in addition to 'start','end'**. [['score']]
    :rtype: FeatureStream
    """
    if not(isinstance(fields,(list,tuple))): fields = [fields]
    with_chrom = False
    if isinstance(regions,(list,tuple)):
        if not isinstance(regions[0],(list,tuple)): regions = [regions]
        if len(regions[0]) > 2: with_chrom = True
        regions = iter(regions)
    elif isinstance(regions,FeatureStream):
        _f = ['start','end']
        if 'chr' in regions.fields:
            _f = ['chr']+_f
            with_chrom = True
        regions = reorder(regions,_f)
    else: raise ValueError("regions: Expected tuple or FeatureStream, got %s." % type(regions))
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
    fidx = [stream.fields.index(f) for f in fields if f in stream.fields]
    chri = -1
    if 'chr' in fields: chri = fields.index('chr')
    feature_list = list(stream)
    sort_list = []
    for n,f in enumerate(feature_list):
        if chri >= 0 and f[fidx[chri]] in chrnames: fchr = chrnames.index(f[fidx[chri]])
        else: fchr = f[fidx[chri]]
        x = tuple(f[i] for i in fidx[:chri])+(fchr,)+tuple(f[i] for i in fidx[chri+1:])+(n,)
        sort_list.append(x)
    sort_list.sort(reverse=reverse)
    return FeatureStream((feature_list[t[-1]] for t in sort_list), stream.fields)

####################################################################
@ordered
def shuffled(stream, chrlen=sys.maxint, repeat_number=1, sorted=True):
    """Return a stream of randomly located features of the same length and annotation
    as these of the original stream.

    :param stream: FeatureStream object.
    :param chrlen: (int) chromosome length. [9223372036854775807]
    :param repeat_number: (int) *repeat_number* random features are yielded per input feature. [1]
    :param sorted: (bool) whether or not to sort the output stream. [True]
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
    return x[0] if all(x[0]==y for y in x[1:]) else type(x[0])(0)

def no_merge(x):
    """Assuming all elements of x are identical (chr) or irrelevant, return the first non-null element."""
    return x[0]

def generic_merge(x):
    """Sum numeric values; concatenate str values; stack tuples; None & None returns None."""
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

@ordered
def fusion(stream,aggregate={},stranded=False):
    """Fuses overlapping features in *stream* and applies *aggregate[f]* function to each field *f*.
    *stream* has to be sorted w.r.t. 'chr' (if any), 'start' and 'end'.

    Example::

        [('chr1',10,15,'A',1),('chr1',13,18,'B',-1),('chr1',18,25,'C',-1)]

        yields

        ('chr1', 10, 18, 'A|B', 0)
        ('chr1', 18, 25, 'C', -1)

    :param stream: FeatureStream object.
    :param stranded: (bool) if True, only features of the same strand are fused. [False]
    :rtype: FeatureStream
    """
    aggreg = dict(aggreg_functions)
    aggreg.update(aggregate)

    def _fuse(s,stranded):
        try:
            x = list(s.next())
        except StopIteration:
            return
        has_chr = 'chr' in s.fields
        if has_chr: chridx = s.fields.index('chr')
        if stranded: stridx = s.fields.index('strand')
        for y in s:
            new_chr = has_chr and (x[chridx] != y[chridx])
            new_str = stranded and (x[stridx] != y[stridx])
            if y[0] < x[1] and not (new_chr or new_str):
                x[1] = max(x[1], y[1])
                x[2:] = [aggreg.get(f,generic_merge)((x[n+2],y[n+2]))
                         for n,f in enumerate(s.fields[2:])]
            else:
                yield tuple(x)
                x = list(y)
        yield tuple(x)

    stream = reorder(stream,['start','end'])
    return FeatureStream( _fuse(stream,stranded), fields=stream.fields)

@ordered
def cobble(stream,aggregate={},stranded=False,scored=False):
    """Fragments overlapping features in *stream* and applies `aggregate[f]` function
    to each field `f` in common fragments.
    *stream* has to be sorted w.r.t. 'chr' (if any), 'start' and 'end'.

    Example::

        [('chr1',10,15,'A',1),('chr1',13,18,'B',-1),('chr1',18,25,'C',-1)]

        yields

        ('chr1', 10, 13, 'A', 1)
        ('chr1', 13, 15, 'A|B', 0)
        ('chr1', 15, 18, 'B', -1)
        ('chr1', 18, 25, 'C', -1)

    This is to avoid having overlapping coordinates of features from both DNA strands,
    which some genome browsers cannot handle for quantitative tracks.

    :param stream: FeatureStream object.
    :param stranded: (bool) if True, only features of the same strand are cobbled. [False]
    :param scored: (bool) if True, each fragment will be attributed a fraction of the
        original score, based on its length. [False]
    :rtype: FeatureStream
    """
    aggreg = dict(aggreg_functions)
    aggreg.update(aggregate)

    def _intersect(A,B,fields):
        """Return *z*, the part that must replace A in *toyield*, and
        *rest*, that must reenter the loop instead of B."""
        rest = None
        a = tuple(A[2:])
        b = tuple(B[2:])
        ab = tuple([aggreg.get(f,generic_merge)((A[k+2],B[k+2])) for k,f in enumerate(fields[2:])])
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
        try:
            K = 0 # feature ID
            X = stream.next() + (str(K),)
        except StopIteration:
            return
        if stranded: istrand = stream.fields.index('strand')
        toyield = [X]
        L = {str(K):X[1]-X[0]} # feature lengths
        while 1:
            try:
                X = stream.next()
                K+=1
                L[str(K)] = X[1]-X[0]
                x = X + (str(K),)
                intersected = False
                for y in toyield:
                    if stranded and x[istrand] != y[istrand]:
                        continue
                    replace, rest = _intersect(y,x,stream.fields)
                    if replace:
                        intersected = True
                        iy = toyield.index(y)
                        y = toyield.pop(iy)
                        for k in range(len(replace)):
                            toyield.insert(iy+k, replace[k])
                        x = rest
                        if not x: break
                if not intersected:
                    if scored:
                        _partial_scores(toyield,L)
                    while toyield:
                        y = toyield.pop(0)
                        yield tuple(y)[:-1]
                    toyield = [x]
                    L = {str(x[-1]):L[x[-1]]}
                elif x:
                    toyield.append(x)
            except StopIteration:
                if scored: _partial_scores(toyield,L)
                while toyield:
                    y = toyield.pop(0)
                    yield tuple(y)[:-1]
                break

    def _partial_scores(toyield,L):
        for j,y in enumerate(toyield):
            if not isinstance(y[2],tuple):
                scores = (y[2],)
            else:
                scores = y[2]
            LL = [L[k] for k in y[-1].split('|')]
            s = sum( scores[i] * (y[1]-y[0]) / LL[i] for i in range(len(scores)) )
            toyield[j] = y[:2]+(s,)+y[3:]
        return toyield

    _f = ['start','end']
    if scored and 'score' in stream.fields:
        def _score_merge(x):
            if isinstance(x[0],tuple):
                x0 = x[0]
                for y in x[1:]: x0 += (y,)
                return x0
            else: return x
        _f += ['score']
        aggreg['score'] = aggreg.get('score',_score_merge)
    stream = reorder(stream,_f)
    # Add a field for the track ID in last position; make sure its name is unused yet
    id_field = "".join([random.choice(string.letters + string.digits) for x in range(10)])
    stream.fields += [id_field]
    return FeatureStream( _fuse(stream), fields=stream.fields[:-1])

####################################################################
def normalize(M,method):
    """Normalize the vectors of a matrix *M* using the given *method*.
    To apply it to streams, use :func:`gfminer.stream.normalize
    <bbcflib.gfminer.stream.scores.normalize>`.

    :param M: (list of lists, or numpy array) matrix M to normalize.
    :param method: normalization method:
        * ``'total'`` divides every score vector by its sum (total number of reads) x 10^7 .
        * ``'deseq'`` applies DESeq's normalization ("size factors") - considering every track
            as belonging to a different group.
        * ``'quantile'`` applies quantile normalization.
    """
    def _total(M):
        for n,col in enumerate(M):
            M[n] = M[n]/sum(M[n])
        return M
    def _deseq(M):
        cnts = M[:,nonzero(prod(M,axis=0))[0]] # none of the counts is zero
        loggeomeans = mean(nlog(cnts),axis=0) # -inf if division by 0
        size_factors = exp(median(nlog(cnts)-loggeomeans,axis=1))
        M = around((M.T / size_factors).T,2)
        return M
    def _quantile(M):
        ordering = argsort(M)
        for n in range(len(M)):
            M[n] = M[n][ordering[n]]
        means = mean(M,0)
        for n in range(len(M)):
            M[n] = around(means[argsort(ordering[n])],2)
        return M
    M = asarray(M, dtype=float_)
    if method == 'total': return _total(M)
    elif method == 'deseq': return _deseq(M)
    elif method == 'quantile': return _quantile(M)
    elif hasattr(method,'__call__'): return method(M) # custom function
    else: raise ValueError("Unknown normalization method (got %s)" % method)

####################################################################
