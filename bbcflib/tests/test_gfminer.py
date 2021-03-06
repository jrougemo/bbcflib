# Built-in modules #
import math

# Internal modules #
from bbcflib import genrep
from bbcflib.track import track, FeatureStream as fstream
from bbcflib.gfminer.common import sentinelize, copy, select, reorder, unroll, sorted_stream
from bbcflib.gfminer.common import shuffled, fusion, cobble, ordered, apply, duplicate
from bbcflib.gfminer.common import concat_fields, split_field, map_chromosomes, score_threshold
from bbcflib.gfminer.stream import getNearestFeature, concatenate, neighborhood, segment_features, intersect
from bbcflib.gfminer.stream import selection, exclude, require, disjunction, intersection, union, combine
from bbcflib.gfminer.stream import overlap, merge_scores, score_by_feature, window_smoothing, filter_scores, normalize
from bbcflib.gfminer.numeric import feature_matrix, summed_feature_matrix, vec_reduce, correlation

# Other modules #
import numpy

# Unitesting modules #
try:
    import unittest2 as unittest
    assert unittest
except ImportError:
    import unittest
from numpy.testing import assert_almost_equal

# Nosetest flag #
__test__ = True

# Numpy print options #
numpy.set_printoptions(precision=3,suppress=True)


class Test_Common(unittest.TestCase):
    def setUp(self):
        self.a = genrep.Assembly('sacCer2')

    def test_sentinelize(self):
        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        stream = sentinelize(stream,'Z')
        for y in stream: x = y
        self.assertEqual(x,'Z')

    def test_copy(self):
        feats = [(1,2),(3,4)]
        stream = fstream(feats,fields=['start','end'])
        res = copy(stream,3)
        for x in res: self.assertListEqual(list(x),feats)

    def test_ordered(self):
        @ordered
        def _test(stream):
            return reorder(stream,fields=['2','1'])
        stream = fstream([('A','B'),('C','D')], fields=['1','2'])
        res = list(_test(stream))
        self.assertListEqual(res,[('A','B'),('C','D')])

    def test_apply(self):
        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        res = list(apply(stream,'score',lambda x:2*x))
        expected = [(10,12,1.), (14,15,2.4)]
        self.assertListEqual(res,expected)

        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        res = list(apply(stream,['score','end'],[lambda x:2*x, lambda x:x-3]))
        expected = [(10,9,1.), (14,12,2.4)]
        self.assertListEqual(res,expected)

    def test_duplicate(self):
        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        res = duplicate(stream,'score','score2')
        expected = [(10,12,0.5,0.5), (14,15,1.2,1.2)]
        self.assertListEqual(res.fields,['start','end','score','score2'])
        self.assertEqual(list(res),expected)

        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        res = duplicate(stream,'score',['s2','s3','s4'])
        expected = [(10,12,0.5,0.5,0.5,0.5), (14,15,1.2,1.2,1.2,1.2)]
        self.assertListEqual(res.fields,['start','end','score','s2','s3','s4'])
        self.assertEqual(list(res),expected)

    def test_select(self):
        # by fields
        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        res = list(select(stream,['score','end']))
        expected = [(0.5,12),(1.2,15)]
        self.assertListEqual(res,expected)

        # by selection
        stream = fstream([('a',10,12), ('a',14,15), ('b',16,19)], fields=['name','start','end'])
        res = list(select(stream,None,{'name':['a','c']}))
        expected = [('a',10,12),('a',14,15)]
        self.assertListEqual(res,expected)

    def test_reorder(self):
        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        expected = [(12,0.5,10), (15,1.2,14)]
        res = list(reorder(stream,['end','score','start']))
        self.assertListEqual(res,expected)

    def test_unroll(self):
        stream = fstream([(10,12,0.5,'a'), (14,15,1.2,'b')], fields=['start','end','score','name'])
        expected = [(0,),(0.5,'a'),(0.5,'a'),(0,),(0,),(1.2,'b'),(0,)]
        res = list(unroll(stream,(9,16)))
        self.assertListEqual(res, expected)

        stream = fstream([(0,1,5),(1,2,9),(2,3,11)], fields=['start','end','score'])
        expected = [(5,),(9,),(11,)]
        res = list(unroll(stream,(0,3)))
        self.assertListEqual(res, expected)

    def test_sorted_stream(self):
        s = [(10,0.8),(15,2.8),(12,19.5),(12,1.4),(13,0.1)]

        stream = fstream(s, fields=['start','score'])
        res = list(sorted_stream(stream,fields=['start']))
        expected = [(10,0.8),(12,19.5),(12,1.4),(13,0.1),(15,2.8)]
        self.assertListEqual(res,expected)

        stream = fstream(s, fields=['start','score'])
        res = list(sorted_stream(stream,fields=['start','score']))
        expected = [(10,0.8),(12,1.4),(12,19.5),(13,0.1),(15,2.8)]
        self.assertListEqual(res,expected)

        s = [('chrX',0,1,0.8),('chrIX',3,5,2.8),('chrIX',3,9,1.4),('chrIX',2,10,0.1),('chrIX',7,10,0.8)]
        stream = fstream(s, fields=['chr','start','end','score'])
        res = list(sorted_stream(stream, fields=['start','chr']))
        expected = [('chrX',0,1,0.8),('chrIX',2,10,0.1),('chrIX',3,5,2.8),('chrIX',3,9,1.4),('chrIX',7,10,0.8)]
        self.assertListEqual(res,expected)

        stream = fstream(s, fields=['chr','start','end','score'])
        res = list(sorted_stream(stream, fields=['chr','start','score'], chrnames=self.a.chrnames))
        expected = [('chrIX',2,10,0.1),('chrIX',3,9,1.4),('chrIX',3,5,2.8),('chrIX',7,10,0.8),('chrX',0,1,0.8)]
        self.assertListEqual(res,expected)

    def test_shuffled(self):
        stream = fstream([(10,12,0.5), (14,15,1.2)], fields=['start','end','score'])
        res = list(shuffled(stream, chrlen=25))
        for f in res:
            self.assertItemsEqual([x[2] for x in res],[0.5,1.2])
            self.assertItemsEqual([x[1]-x[0] for x in res],[2,1])

    def test_fusion(self):
        stream = fstream([('chr1',10,15,'A',1),('chr1',13,18,'B',-1),('chr1',18,25,'C',-1)],
                         fields = ['chr','start','end','name','strand'])
        expected = [('chr1',10,18,'A|B',0),('chr1',18,25,'C',-1)]
        res = fusion(stream)
        self.assertEqual(list(res),expected)

        # stranded = True
        stream = fstream([('chr1',10,15,'A',1),('chr1',13,18,'B',-1),('chr1',15,25,'C',-1)],
                         fields = ['chr','start','end','name','strand'])
        expected = [('chr1',10,15,'A',1),('chr1',13,25,'B|C',-1)]
        res = fusion(stream, stranded=True)
        self.assertEqual(list(res),expected)

    def test_cobble(self): # more tests below
        stream = fstream([('chr1',10,20,'A',1),('chr1',12,22,'B',-1),('chr1',15,25,'C',-1)],
                         fields = ['chr','start','end','name','strand'])
        expected = [('chr1',10,12,'A',1),
                    ('chr1',12,15,'A|B',0),
                    ('chr1',15,20,'A|B|C',0),
                    ('chr1',20,22,'B|C',-1),
                    ('chr1',22,25,'C',-1)]
        res = list(cobble(stream))
        self.assertEqual(res,expected)

        # stranded = True
        stream = fstream([('chr1',10,20,'A',1),('chr1',12,22,'B',-1),('chr1',15,25,'C',-1)],
                         fields = ['chr','start','end','name','strand'])
        expected = [('chr1',10,20,'A',1),
                    ('chr1',12,15,'B',-1),
                    ('chr1',15,22,'B|C',-1),
                    ('chr1',22,25,'C',-1)]
        res = list(cobble(stream,stranded=True))
        self.assertEqual(res,expected)

        # scored = True
        stream = fstream([('chr1',10,20,'A',1,50.0),('chr1',12,22,'B',-1,100.0),('chr1',15,65,'C',-1,20.0)],
                         fields = ['chr','start','end','name','strand','score'])
        expected = [('chr1',10,12,'A',1, 10.0),
                    ('chr1',12,15,'A|B',0, 45.0),
                    ('chr1',15,20,'A|B|C',0, 77.0),
                    ('chr1',20,22,'B|C',-1, 20.8),
                    ('chr1',22,65,'C',-1, 17.2)]
        res = list(cobble(stream,scored=True))
        self.assertEqual(res,expected)

    def test_concat_fields(self):
        # Concatenate fields as strings
        stream = fstream([(10,12,0.5,'a'), (14,15,1.2,'b')], fields=['start','end','score','name'])
        res = concat_fields(stream,infields=['score','name'],outfield='mix',separator=';')
        expected = [(10,12,'0.5;a'), (14,15,'1.2;b')]
        self.assertListEqual(list(res),expected)
        self.assertListEqual(res.fields,['start','end','mix'])

        # As tuples
        stream = fstream([(10,12,0.5,'a'), (14,15,1.2,'b')], fields=['start','end','score','name'])
        res = concat_fields(stream,['score','name'],'mix',as_tuple=True)
        expected = [(10,12,(0.5,'a')), (14,15,(1.2,'b'))]
        self.assertListEqual(list(res),expected)
        self.assertListEqual(res.fields,['start','end','mix'])

    def test_split_field(self):
        stream = fstream([(10,12,(0.5,'a')), (14,15,(1.2,'b'))], fields=['start','end','mix'])
        res = split_field(stream,['score','name'],'mix')
        expected = [(10,12,'0.5','a'), (14,15,'1.2','b')]
        self.assertListEqual(list(res),expected)
        self.assertListEqual(res.fields,['start','end','score','name'])

        stream = fstream([(10,12,'0.5|a'), (14,15,'1.2|b')], fields=['start','end','mix'])
        res = split_field(stream,['score','name'],'mix',separator='|')
        expected = [(10,12,'0.5','a'), (14,15,'1.2','b')]
        self.assertListEqual(list(res),expected)
        self.assertListEqual(res.fields,['start','end','score','name'])

        stream = fstream([(10,12,'gene_id "A"; exon_number "1"; gene_name "a";'),
                          (14,15,'gene_id "B"; exon_number "2"; gene_name "b";')],
                         fields=['start','end','attributes'])
        res = split_field(stream,['gene_id','gene_name'],
                          infield='attributes', header_split=' ',
                          strip_input=True)
        expected = [(10,12,'exon_number "1"',"A","a"), (14,15,'exon_number "2"',"B","b")]
        self.assertListEqual(list(res),expected)
        self.assertListEqual(res.fields,['start', 'end', 'attributes', 'gene_id', 'gene_name'])

    def test_map_chromosomes(self):
        stream = fstream([('chrIV',1),('IV',2),(2780,3),('NC_001136.9',4),('sth',5)], fields=['chr','start'])
        assembly = genrep.Assembly('sacCer2')
        res = list(map_chromosomes(stream, assembly.chromosomes, keep=True))
        expected = [('chrIV',1),('chrIV',2),('chrIV',3),('chrIV',4),('sth',5)]
        self.assertListEqual(res, expected)

        # keep=False
        stream = fstream([('chrIV',1),('IV',2),(2780,3),('NC_001136.9',4),('sth',5)], fields=['chr','start'])
        res = list(map_chromosomes(stream, assembly.chromosomes, keep=False))
        self.assertListEqual(res, expected[:-1])

    def test_score_threshold(self):
        # Upper bound (lower=True))
        stream = fstream([(1,0.91),(2,0.45),(3,0.01)], fields=['start','score'])
        res = list(score_threshold(stream,threshold=0.05,fields='score',lower=False))
        expected = [(1,0.91),(2,0.45)]
        self.assertListEqual(res,expected)

        # Lower bound (lower=False)
        stream = fstream([(1,0.91),(2,0.45),(3,0.01)], fields=['start','score'])
        res = list(score_threshold(stream,threshold=0.05,fields='score',lower=True))
        expected = [(3,0.01)]
        self.assertListEqual(res,expected)


################### STREAM ######################


class Test_Annotate(unittest.TestCase):
    def setUp(self):
        self.assembly = genrep.Assembly('ce6')
        """
              |==========================|
        ----- 14,795,327 ---- 14,798,158 - 14,798,395 ---- 14,800,829 -----
              |                            |
               ->     Y54E2A.11             ->     Y54E2A.12
        """
    def test_getNearestFeature(self):
        features = fstream([('chrII',14795327,14798367)], fields=['chr','start','end'])
        expected = [('chrII',14795327, 14798367, 'Y54E2A.12|tbc-20_Y54E2A.11|eif-3.B', 'Promot_Included', '28_0')]
        annotations = self.assembly.gene_track(chromlist=['chrII'])
        res = list(getNearestFeature(features,annotations))
        self.assertItemsEqual(res,expected)


class Test_Intervals(unittest.TestCase):
    def setUp(self):
        pass

    def test_concatenate(self):
        s1 = [('chr',1,3,0.2,'n'), ('chr',5,9,0.5,'n'), ('chr',11,15,1.2,'n')]
        s2 = [('chr',1,4,0.6,'m'), ('chr',8,11,0.4,'m'), ('chr',11,12,0.1,'m')]
        stream1 = fstream(s1, fields=['chr','start','end','score','name'])
        stream2 = fstream(s2, fields=['chr','start','end','score','name'])
        res = list(concatenate([stream1,stream2], fields=['start','score','name']))
        expected = [(1,3,0.2,'n'),(1,4,0.6,'m'),(5,9,0.5,'n'),(8,11,0.4,'m'),(11,12,0.1,'m'),(11,15,1.2,'n')]
        self.assertListEqual(res,expected)

        # Keep chr and compare items w.r.t. chr
        s1 = [('chr',1,3,0.2,'n'), ('chr',5,9,0.5,'n'), ('chr',11,15,1.2,'n')]
        s2 = [('chr',1,4,0.6,'m'), ('chrX',8,11,0.4,'m'), ('chrX',11,12,0.1,'m')]
        stream1 = fstream(s1, fields=['chr','start','end','score','name'])
        stream2 = fstream(s2, fields=['chr','start','end','score','name'])
        res = list(concatenate([stream1,stream2], fields=['chr','start','end','score']))
        expected = [('chr',1,3,0.2),('chr',1,4,0.6),('chr',5,9,0.5),('chr',11,15,1.2),('chrX',8,11,0.4),('chrX',11,12,0.1)]
        self.assertListEqual(sorted(res),sorted(expected))

        # Remove duplicates
        stream1 = fstream([(1,2),(3,4),(5,6)], fields=['start','end'])
        stream2 = fstream([(3,4),(5,6),(7,8)], fields=['start','end'])
        res = list(concatenate([stream1,stream2], fields=['start','end'], remove_duplicates=True))
        expected = [(1,2),(3,4),(5,6),(7,8)]
        self.assertListEqual(res,expected)

        # Group by
        s1 = [('chr',1,4,0.2,'n'), ('chr',5,9,0.5,'n'), ('chr',11,15,1.2,'n')]
        s2 = [('chr',1,4,0.6,'m'), ('chr',8,11,0.4,'m'), ('chrX',11,15,0.1,'m')]
        group_by = ['chr','start','end']
        aggregate = {'score': lambda x:sum(x), 'name': lambda x:'-'.join(x)}
        stream1 = fstream(s1, fields=['chr','start','end','score','name'])
        stream2 = fstream(s2, fields=['chr','start','end','score','name'])
        res = list(concatenate([stream1,stream2], fields=['chr','start','score','name'], group_by=group_by, aggregate=aggregate))
        expected = [('chr',1,4,0.8,'m-n'),('chr',5,9,0.5,'n'),('chr',8,11,0.4,'m'),('chr',11,15,1.2,'n'),('chrX',11,15,0.1,'m')]
        self.assertListEqual(sorted(res),sorted(expected))

    def test_selection(self):
        s = [('chr1',1,3,0.2,'a'), ('chr2',5,9,0.5,'b'), ('chr2',11,15,1.2,'c')]

        stream = fstream(s,fields=['chr','start','end','score','name'])
        res = selection(stream,{'chr':'chr2', 'start':(5,11), 'name':['a','b','c']})
        expected = [('chr2',5,9,0.5,'b')]
        self.assertListEqual(list(res),expected)

        # Alternative selections
        stream = fstream(s,fields=['chr','start','end','score','name'])
        res = selection(stream,[{'start':(1,4)},{'end':(10,20)}])
        expected = [('chr1',1,3,0.2,'a'),('chr2',11,15,1.2,'c')]
        self.assertListEqual(list(res),expected)

    def test_overlap(self):
        s1 = [('chr',0,4,'n',1.), ('chr',7,12,'n',2.), ('chr',16,19,'n',3.), ('chr',22,27,'n',4.)]
        s2 = [('chr',2,9,'m'), ('chr',13,14,'m'), ('chr',22,23,'m'), ('chr',26,27,'m')]
        stream1 = fstream(s1, fields=['chr','start','end','name','score'])
        stream2 = fstream(s2, fields=['chr','start','end','name'])
        res = overlap(stream1,stream2)
        expected = [('chr',0,4,'n',1.),('chr',7,12,'n',2.),('chr',22,27,'n',4.)]
        self.assertListEqual(list(res),expected)

        # Stranded
        s1 = [('chr',0,3,'+'), ('chr',7,12,'+'), ('chr',16,19,'+'), ('chr',22,27,'+')]
        s2 = [('chr',2,9,'+'), ('chr',13,14,'-'), ('chr',25,30,'-')]
        stream1 = fstream(s1, fields=['chr','start','end','strand'])
        stream2 = fstream(s2, fields=['chr','start','end','strand'])
        res = overlap(stream1,stream2)
        expected = [('chr',0,3,'+'),('chr',7,12,'+')]
        self.assertListEqual(list(res),expected)

    def test_neighborhood(self):
        s = [(10,16,0.5,-1), (24,36,1.2,1)]

        stream = fstream(s, fields=['start','end','score','strand'])
        res = list(neighborhood(stream, before_start=1,after_end=4))
        expected = [(9,20,0.5,-1), (23,40,1.2,1)]
        self.assertListEqual(res,expected)

        stream = fstream(s, fields=['start','end','score','strand'])
        res = list(neighborhood(stream, before_start=1,after_start=4))
        expected = [(9,15,0.5,-1), (23,29,1.2,1)]
        self.assertListEqual(res,expected)

        stream = fstream(s, fields=['start','end','score','strand'])
        res = list(neighborhood(stream, before_end=1,after_end=4))
        expected = [(14,20,0.5,-1), (34,40,1.2,1)] # !
        self.assertListEqual(res,expected)

        stream = fstream(s, fields=['start','end','score','strand'])
        res = list(neighborhood(stream, before_start=1,after_start=2,before_end=3,after_end=4, on_strand=False))
        expected = [(9,13,0.5,-1),(12,20,0.5,-1), (23,27,1.2,1),(32,40,1.2,1)]
        self.assertListEqual(res,expected)

        stream = fstream(s, fields=['start','end','score','strand'])
        res = list(neighborhood(stream, before_start=1,after_start=2,before_end=3,after_end=4, on_strand=True))
        expected = [(6,14,0.5,-1),(13,17,0.5,-1), (23,27,1.2,1),(32,40,1.2,1)]
        self.assertListEqual(res,expected)

    def test_segment_features(self):
        stream = fstream([('X',10,16,'A'), ('X',18,30,'B'), ('I',10,16,'C')],
                         fields=['chr','start','end','name'])
        res = list(segment_features(stream,nbins=3,upstream=(2,1),downstream=(3,1)))
        expected = [('X',8,10,'A',0), ('X',10,12,'A',1),('X',12,14,'A',2),('X',14,16,'A',3), ('X',16,18,'B',0),
                    ('X',16,19,'A',4), ('X',18,22,'B',1),('X',22,26,'B',2),('X',26,30,'B',3), ('X',30,33,'B',4),
                    ('I',8,10,'C',0), ('I',10,12,'C',1),('I',12,14,'C',2),('I',14,16,'C',3), ('I',16,19,'C',4)]
        self.assertListEqual(res,expected)

        # With negative strand
        stream = fstream([(10,16,-1), (24,36,1)], fields=['start','end','strand'])
        res = list(segment_features(stream,nbins=2,upstream=(2,1),downstream=(3,1)))
        expected = [(7,10,-1,3), (10,13,-1,2),(13,16,-1,1), (16,18,-1,0),
                    (22,24,1,0), (24,30,1,1),(30,36,1,2), (36,39,1,3)]
        self.assertListEqual(res,expected)

    def test_exclude(self):
        # combine( ... , fn=exclude)
        self.assertEqual(exclude([True,True,False,False,False],[2,3,4]), True)
        self.assertEqual(exclude([True,True,False,False,False],[0,1]), False)
        self.assertEqual(exclude([True,True,False,False,False],[1,2,3]), False)

    def test_require(self):
        # combine( ... , fn=require)
        self.assertEqual(require([True,True,False,False,False],[2,3,4]), False)
        self.assertEqual(require([True,True,False,False,False],[0,1]), False) # !?
        self.assertEqual(require([True,True,False,True, False],[0,1]), True)
        self.assertEqual(require([True,True,False,False,False],[1,2,3]), False)

    def test_disjunction(self):
        # combine( ... , fn=disjunction)
        self.assertEqual(disjunction([True,True,False,False,False],[0,1]), True)
        self.assertEqual(disjunction([True,True,False,False,False],[0]), False)
        self.assertEqual(disjunction([True,True,False,False,False],[0,1,2]), True)
        self.assertEqual(disjunction([True,True,False,False,False],[2,3,4]), True)
        self.assertEqual(disjunction([True,True,False,False,False],[1,2,3]), False)

    def test_union(self):
        # combine( ... , fn=union)
        self.assertEqual(union([True,False,True]), True)
        self.assertEqual(union([False,False,False]), False)

    def test_intersection(self):
        # combine( ... , fn=intersection).
        self.assertEqual(intersection([True,True,True]), True)
        self.assertEqual(intersection([True,False,True]), False)

    def test_intersect(self):
        # Test from the snp workflow.
        expected = ('chr',91143,91144, ('C','*A','0','|EBMYCG00000002479|Rv0083',1,0))
        a = genrep.Assembly('mycoTube_H37RV')
        c = concat_fields(a.annot_track('CDS','chr'), infields=['name','strand','frame'], as_tuple=True)
        feat = fstream([('chr',91143,91144,('C','*A','0'))], fields=['chr','start','end','rest'])
        g = intersect([feat,c], win_size=10000)
        self.assertEqual(g.next(),expected)

        fields = ['chr','start','end','name','strand','score']
        s1 = fstream([('chr',0,20,'a1',1,6.),('chr',40,60,'b',1,3.)], fields=fields)
        s2 = fstream([('chr',10,30,'a2',1,8.),('chr',50,70,'b',-1,4.)], fields=fields)
        res = list(intersect([s1,s2]))
        expected = [('chr',10,20,'a1|a2',1,14.),('chr',50,60,'b|b',0,7.)]
        self.assertListEqual(res,expected)

    def test_combine(self):
        # Complement
        fields = ['chr','start','end','name','strand','score']
        s1 = fstream([('chr',0,20,'a1',1,6.),('chr',40,60,'b',1,3.)], fields=fields)
        s2 = fstream([('chr',0,20,'a1',1,6.),('chr',40,60,'b',1,3.)], fields=fields)
        res = list(combine([s1,s2],fn=lambda x:not any(x)))
        expected = [('chr',20,40,'0','0','0')]
        self.assertListEqual(res,expected)


class Test_Scores(unittest.TestCase):
    def setUp(self):
        pass

    def test_merge_scores(self):
        # Arithmetic mean
        s1 = fstream([('chr',10,20,6.,'A')], fields=['chr','start','end','score','name'])
        s2 = fstream([('chr',5,15,2.,'B')], fields=['chr','start','end','score','name'])
        res = list(merge_scores([s1,s2]))
        expected = [('chr',5,10,1.,'B'),('chr',10,15,4.,'A|B'),('chr',15,20,3.,'A')]
        self.assertListEqual(res,expected)
        # Geometric mean
        s1 = fstream([(10,20,6.)], fields=['start','end','score'])
        s2 = fstream([(5,15,2.)], fields=['start','end','score'])
        res = list(merge_scores([s1,s2], method='geometric'))
        expected = [(5,10,math.sqrt(2)),(10,15,math.sqrt(12)),(15,20,math.sqrt(6))]
        self.assertListEqual(res,expected)
        # Sum
        s1 = fstream([(10,20,6.)], fields=['start','end','score'])
        s2 = fstream([(5,15,2.)], fields=['start','end','score'])
        res = list(merge_scores([s1,s2], method='sum'))
        expected = [(5,10,2.),(10,15,8.),(15,20,6.)]
        self.assertListEqual(res,expected)

    def test_filter_scores(self):
        features = fstream([(5,15,'gene1'),(30,40,'gene2')], fields=['start','end','name'])
        scores = fstream([(10,20,6.),(30,40,6.)], fields=['start','end','score'])
        res = list(filter_scores(scores,features))
        expected = [(10,15,6.),(30,40,6.)]
        self.assertListEqual(res,expected)

        # annotate = True
        features = fstream([(0,30,'gene1','+'),(20,50,'gene2','-')], fields=['start','end','name','strand'])
        scores = fstream([(10,40,6.),(25,45,3.)], fields=['start','end','score'])
        res = list(filter_scores(scores,features,annotate=True))
        expected = [(10,20,6.,'gene1','+'),(20,30,6.,'gene1|gene2','0'),(30,40,6.,'gene2','-'),
                    (25,30,3.,'gene1|gene2','0'),(30,45,3.,'gene2','-')]
        self.assertListEqual(res,expected)

        # stranded, cobbled
        features = fstream([(0,30,'gene1','+'),(20,50,'gene2','-')], fields=['start','end','name','strand'])
        scores = fstream([(10,40,6.,'+'),(25,45,3.,'-')], fields=['start','end','score','strand'])
        res = list(filter_scores(scores,features,annotate=True))
        expected = [(10,30,6.,'+','gene1'),(25,45,3.,'-','gene2')]
        self.assertListEqual(res,expected)

        # stranded, fused
        features = fstream([(0,30,'gene1','+'),(20,50,'gene2','+')], fields=['start','end','name','strand'])
        scores = fstream([(10,40,6.,'+')], fields=['start','end','score','strand'])
        res = list(filter_scores(scores,features,annotate=True,flatten=fusion))
        expected = [(10,40,6.,'+','gene1|gene2')]
        self.assertListEqual(res,expected)

    def test_score_by_feature(self):
        features = fstream([('chr',5,15,'gene1'),('chr',30,40,'gene2')], fields=['chr','start','end','name'])
        scores1 = fstream([('chr',10,20,6.),('chr',30,40,6.)], fields=['chr','start','end','score'])
        scores2 = fstream([('chr',30,40,2.)], fields=['chr','start','end','score'])
        res = list(score_by_feature([scores1,scores2],features))
        expected = [('chr',5,15,'gene1',3.,0.),('chr',30,40,'gene2',6.,2.)]
        self.assertListEqual(res,expected)

        # normalize = False
        features = fstream([('chr',5,15,'gene1'),('chr',30,40,'gene2')], fields=['chr','start','end','name'])
        scores1 = fstream([('chr',10,20,6.),('chr',30,40,6.)], fields=['chr','start','end','score'])
        scores2 = fstream([('chr',2,8,2.),('chr',30,33,3.)], fields=['chr','start','end','score'])
        res = list(score_by_feature([scores1,scores2],features,method=sum))
        expected = [('chr',5,15,'gene1',30.,6.),('chr',30,40,'gene2',60.,9.)]
        self.assertListEqual(res,expected)

    def test_window_smoothing(self):
        stream = fstream([('chr1',4,5,10.)], fields=['chr','start','end','score'])
        res = list(window_smoothing(stream, window_size=2, step_size=1))
        expected = [('chr1',4,5,5.),('chr1',5,6,5.)]
        self.assertListEqual(res,expected)


################### NUMERIC ######################


class Test_Regions(unittest.TestCase):
    def setUp(self):
        pass

    def test_feature_matrix(self):
        # No segments
        features = fstream([(5,15,'gene1'),(30,40,'gene2')], fields=['start','end','name'])
        scores1 = fstream([(10,15,6.),(30,40,6.)], fields=['start','end','score'])
        scores2 = fstream([(5,15,2.)], fields=['start','end','score'])
        feat, res = feature_matrix([scores1,scores2],features)
        self.assertListEqual(list(feat),['gene1','gene2'])
        assert_almost_equal(res, numpy.array([[3,2],[6,0]]))

        # Segmenting each feature in 3 parts
        features = fstream([(5,15,'gene1'),(30,40,'gene2')], fields=['start','end','name'])
        scores1 = fstream([(10,15,6.),(30,40,6.)], fields=['start','end','score'])
        scores2 = fstream([(5,15,2.)], fields=['start','end','score'])
        feat, res = feature_matrix([scores1,scores2],features, segment=True, nbins=3)
        assert_almost_equal(res, numpy.array([[[0,2],[2,2],[6,2]],
                                              [[6,0],[6,0],[6,0]]]))
    def test_summed_feature_matrix(self):
        features = fstream([(5,15,'gene1'),(30,40,'gene2')], fields=['start','end','name'])
        scores1 = fstream([(10,15,6.),(30,40,6.)], fields=['start','end','score'])
        scores2 = fstream([(5,15,2.)], fields=['start','end','score'])
        res,n = summed_feature_matrix([scores1,scores2],features, nbins=3)
        res /= n*1.0
        assert_almost_equal(res, numpy.array([[3.,1.],[4.,1.],[6.,1.]]))


class Test_Signal(unittest.TestCase):
    def setUp(self):
        pass

    def test_normalize(self):
        s1 = [('a',64.),('b',256.),('c',16.)]
        s2 = [('a',16.),('b',16.),('c',16.)]

        # deseq
        scores1 = fstream(s1, fields=['name','score'])
        scores2 = fstream(s2, fields=['name','score'])
        res = normalize([scores1,scores2], method='deseq')
        expected = [[('a',32.),('b',128.),('c',8.)],[('a',32.),('b',32.),('c',32.)]]
        self.assertListEqual([list(r) for r in res],expected)

        # total
        scores1 = fstream(s1, fields=['name','score'])
        scores2 = fstream(s2, fields=['name','score'])
        res = normalize([scores1,scores2], method='total')
        scores = [[round(x[1],2) for x in r]for r in res]
        expected = [[0.19,0.76,0.05],[0.33,0.33,0.33]]
        self.assertListEqual(scores,expected)

        # total, only one
        scores1 = fstream(s1, fields=['name','score'])
        res = normalize(scores1, method='total')
        scores = [round(x[1],2) for x in res]
        expected = [0.19,0.76,0.05]
        self.assertListEqual(scores,expected)

        # quantiles
        scores1 = fstream(s1, fields=['name','score'])
        scores2 = fstream(s2, fields=['name','score'])
        res = normalize([scores1,scores2], method='quantile')
        scores = [[round(x[1],2) for x in r]for r in res]
        expected = [[40.,136.,16.],[16.,40,136.]]
        self.assertListEqual(scores,expected)

        # custom
        scores1 = fstream(s1, fields=['name','score'])
        res = normalize(scores1, method=lambda x:x/2.)
        scores = [round(x[1],2) for x in res]
        expected = [32.,128.,8.]
        self.assertListEqual(scores,expected)

    def test__normalize(self):
        x = [1,2,3,4,5] # mean=15/5=3, var=(1/5)*(4+1+0+1+4)=2
        assert_almost_equal(vec_reduce(x), numpy.array([-2,-1,0,1,2])*(1/math.sqrt(2)))

    def test_correlation(self):
        numpy.set_printoptions(precision=3,suppress=True)
        # Create 2 vectors of scores, zero everywhere except a random position
        N = 10
        x = numpy.zeros(N)
        y = numpy.zeros(N)
        xpeak = numpy.random.randint(0,N)
        ypeak = numpy.random.randint(0,N)
        x[xpeak] = 10
        y[ypeak] = 10
        x = (x-numpy.mean(x))/numpy.std(x)
        y = (y-numpy.mean(y))/numpy.std(y)

        # Make tracks out of them and compute cross-correlation with our own function
        X = [('chr',k,k+1,s) for k,s in enumerate(x)]
        Y = [('chr',k,k+1,s) for k,s in enumerate(y)]
        X = fstream(iter(X),fields=['chr','start','end','score'])
        Y = fstream(iter(Y),fields=['chr','start','end','score'])
        corr = correlation([X,Y], regions=(0,N))#, limits=[-N+1,N-1])

        # Compute cross-correlation "by hand" and using numpy.correlate(mode='valid')
        raw = []
        np_corr_valid = []
        for k in range(N):
            """
            X         |- - - - -|          k=0
            Y              <- |- - - - -|
            up to
            X         |- - - - -|          k=4
            Y         |- - - - -|
            """
            raw.append(numpy.dot(x[-k-1:],y[:k+1]) / N)
            np_corr_valid.extend(numpy.correlate(x[-k-1:],y[:k+1],mode='valid'))
        for k in range(N-1,0,-1):
            """
            X         |- - - - -|          k=4
            Y    <- |- - - - -|
            up to
            X         |- - - - -|          k=1
            Y |- - - - -|
            """
            raw.append(numpy.dot(x[:k],y[-k:]) / N)
            np_corr_valid.extend(numpy.correlate(x[:k],y[-k:],mode='valid'))

        # Compute cross-correlation using numpy.correlate(mode='full')
        np_corr_full = numpy.correlate(x,y,mode="full")[::-1] / N
        np_corr_valid = numpy.asarray(np_corr_valid) / N

        # Test if all methods yield the same result
        assert_almost_equal(corr, numpy.asarray(raw))
        assert_almost_equal(corr, np_corr_full)
        assert_almost_equal(corr, np_corr_valid)

        # Test if the lag between the two tracks is correcty detected
        self.assertEqual(numpy.argmax(corr)-(N-1), ypeak-xpeak)


###########################################################################


# From old rnaseq.fusion
class Test_Cobble(unittest.TestCase):
    def commonTest(self,X,R):
        T = list(cobble(fstream(X,fields=['chr','start','end','score'])))
        print T
        self.assertEqual(T,R)

    def test_cobble(self):
        c = 'chr'

        X = [(c,0,5,5.),(c,10,15,4.),(c,20,25,2.)]  # |***---***---***|
        R = [(c,0,5,5.),(c,10,15,4.),(c,20,25,2.)]
        self.commonTest(X,R)

        X = [(c,0,15,5.),(c,5,10,4.)]               # |*********|
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.)]   # |---***---|
        self.commonTest(X,R)

        X = [(c,0,25,5.),(c,5,10,4.),(c,15,20,2.)]                             # |***************|
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.),(c,15,20,7.),(c,20,25,5.)]    # |---***---***---|
        self.commonTest(X,R)

        X = [(c,0,15,5.),(c,5,10,4.),(c,20,25,2.)]              # |*********---***|
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.),(c,20,25,2.)]  # |---***---------|
        self.commonTest(X,R)

        X = [(c,0,25,5.),(c,5,10,4.),(c,15,20,2.),(c,30,35,1.)]                            #  .  .  .  .  .  .  .  .
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.),(c,15,20,7.),(c,20,25,5.),(c,30,35,1.)]   # |***************---***|
        self.commonTest(X,R)                                                               # |---***---***---------|

        X = [(c,0,10,5.),(c,5,15,4.)]               # |******---|
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,4.)]   # |---******|
        self.commonTest(X,R)

        X = [(c,0,10,5.),(c,5,15,4.),(c,20,25,2.)]              #  .  .  .  .  .  .
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,4.),(c,20,25,2.)]  # |******------***|
        self.commonTest(X,R)                                    # |---******------|

        X = [(c,0,10,5.),(c,5,20,4.),(c,15,25,2.)]                           #  .  .  .  .  .  .
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,4.),(c,15,20,6.),(c,20,25,2.)]  # |******---******|
        self.commonTest(X,R)                                                 # |---*********---|

        #  0  5  10 15 20 25 30    40    50    60    70    80    90    100   110   120   130   140
        #  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
        # |******************---------------******---*********---***---******---************---***|
        # |---***---***---******---------******---------***---------------*********---***---------|
        X = [(c,0,30,5.),(c,5,10,4.),(c,15,20,3.),(c,25,35,8.),(c,50,60,1.),
             (c,55,65,3.),(c,70,85,8.),(c,75,80,3.),(c,90,95,2.),(c,100,110,4.),
             (c,105,120,3.),(c,115,135,2.),(c,125,130,6.),(c,140,145,9.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.),(c,15,20,8.),
             (c,20,25,5.),(c,25,30,13.),(c,30,35,8.),(c,50,55,1.),
             (c,55,60,4.),(c,60,65,3.),(c,70,75,8.),(c,75,80,11.),
             (c,80,85,8.),(c,90,95,2.),(c,100,105,4.),(c,105,110,7.),
             (c,110,115,3.),(c,115,120,5.),(c,120,125,2.),(c,125,130,8.),
             (c,130,135,2.),(c,140,145,9.)]
        self.commonTest(X,R)
                                                                               #  .  .  .  .  .  .
        X = [(c,0,25,5.),(c,5,20,4.),(c,10,15,2.)]                             # |***************|
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,11.),(c,15,20,9.),(c,20,25,5.)]   # |---*********---|
        self.commonTest(X,R)                                                   # |------***------|
                                                                                   #  .  .  .  .  .  .
        X = [(c,0,20,5.),(c,5,25,4.),(c,10,15,2.)]                                 # |************---|
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,11.),(c,15,20,9.),(c,20,25,4.)]       # |---************|
        self.commonTest(X,R)                                                       # |------***------|
                                                                                   #  .  .  .  .  .  .
        X = [(c,0,20,5.),(c,5,15,4.),(c,10,25,2.)]                             # |************---|
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,11.),(c,15,20,7.),(c,20,25,2.)]   # |---******------|
        self.commonTest(X,R)                                                   # |------*********|
                                                                                   #  .  .  .  .  .  .
        X = [(c,0,15,4.),(c,0,25,5.),(c,0,25,2.)]                                  # |*********------|
        R = [(c,0,15,11.),(c,15,25,7.)]                                            # |***************|
        self.commonTest(X,R)                                                       # |***************|
                                                                               #  .  .  .  .  .  .
        X = [(c,0,15,4.),(c,0,20,5.),(c,0,25,2.)]                              # |*********------|
        R = [(c,0,15,11.),(c,15,20,7.),(c,20,25,2.)]                           # |************---|
        self.commonTest(X,R)                                                   # |***************|
                                                                                   #  .  .  .  .  .  .  .  .
        X = [(c,5,20,8.),(c,10,25,5.),(c,15,30,4.)]                                # |---*********---------|
        R = [(c,5,10,8.),(c,10,15,13.),(c,15,20,17.),(c,20,25,9.),(c,25,30,4.)]    # |------*********------|
        self.commonTest(X,R)                                                       # |---------*********---|

        X = [(c,0,5,5.),(c,0,10,4.),(c,15,20,2.),(c,15,25,3.)]  #  .  .  .  .  .  .
        R = [(c,0,5,9.),(c,5,10,4.),(c,15,20,5.),(c,20,25,3.)]  # |***------***---|
        self.commonTest(X,R)                                    # |******---******|

        X = [(c,0,10,5.),(c,5,10,4.),(c,15,25,2.),(c,20,25,3.)]  #  .  .  .  .  .  .
        R = [(c,0,5,5.),(c,5,10,9.),(c,15,20,2.),(c,20,25,5.)]   # |******---******|
        self.commonTest(X,R)                                     # |---***------***|

        #  .  .  .  .  .  .  .  .  .  .
        # |******---******------******|
        # |---***------******---***---|
        X = [(c,0,10,5.),(c,5,10,4.),(c,15,25,2.),(c,20,30,3.),(c,35,40,7.),(c,35,45,6.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,15,20,2.),(c,20,25,5.),(c,25,30,3.),(c,35,40,13.),(c,40,45,6.)]
        self.commonTest(X,R)

        #  .  .  .  .  .  .  .  .  .  .
        # |---************------******|
        # |---***------******---***---|
        X = [(c,5,10,8.),(c,5,25,5.),(c,20,30,4.),(c,35,40,3.),(c,35,45,2.)]
        R = [(c,5,10,13.),(c,10,20,5.),(c,20,25,9.),(c,25,30,4.),(c,35,40,5.),(c,40,45,2.)]
        self.commonTest(X,R)
