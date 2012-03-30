
# Built-in modules #

# Internal modules #
from bbcflib.rnaseq import *
from bein import execution

# Unitesting modules #
try: import unittest2 as unittest
except ImportError: import unittest
from numpy.testing import assert_almost_equal

# Other modules #
from numpy import array

# Nosetest flag #
__test__ = True


class Assem(object):
    def __init__(self):
        self.chrmeta = None

c = 'c'

class Test_Fusion(unittest.TestCase):
    def commonTest(self,X,R):
        T = [s for s in fusion(iter(X))]
        self.assertEqual(T,R)

    #@unittest.skip('')
    def test_fusion1(self):
        """
        |***---***---***|
        """
        X = [(c,0,5,5.),(c,10,15,4.),(c,20,25,2.)]
        R = [(c,0,5,5.),(c,10,15,4.),(c,20,25,2.)]
        self.commonTest(X,R)

    #@unittest.skip('')
    def test_fusion2(self):
        """
        |*********|
        |---***---|
        """
        X = [(c,0,15,5.),(c,5,10,4.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.)]
        self.commonTest(X,R)

    #@unittest.skip('')
    def test_fusion3(self):
        """
        |***************|
        |---***---***---|
        """
        X = [(c,0,25,5.),(c,5,10,4.),(c,15,20,2.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.),(c,15,20,7.),(c,20,25,5.)]
        self.commonTest(X,R)
    
    #@unittest.skip('')
    def test_fusion4(self):    
        """
        |*********---***|
        |---***---------|
        """
        X = [(c,0,15,5.),(c,5,10,4.),(c,20,25,2.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.),(c,20,25,2.)]
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion5(self):
        """
         .  .  .  .  .  .  .  .
        |***************---***|
        |---***---***---------|
        """
        X = [(c,0,25,5.),(c,5,10,4.),(c,15,20,2.),(c,30,35,1.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,5.),(c,15,20,7.),(c,20,25,5.),(c,30,35,1.)]
        self.commonTest(X,R)
    
    #@unittest.skip('')
    def test_fusion6(self):
        """
        |******---|
        |---******|
        """
        X = [(c,0,10,5.),(c,5,15,4.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,4.)]
        self.commonTest(X,R)
    
    #@unittest.skip('')
    def test_fusion7(self):
        """
         .  .  .  .  .  .
        |******------***|
        |---******------|
        """
        X = [(c,0,10,5.),(c,5,15,4.),(c,20,25,2.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,4.),(c,20,25,2.)]
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion8(self):
        """
         .  .  .  .  .  .
        |******---******|
        |---*********---|
        """
        X = [(c,0,10,5.),(c,5,20,4.),(c,15,25,2.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,4.),(c,15,20,6.),(c,20,25,2.)]
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion9(self):
        """
         0  5  10 15 20 25 30    40    50    60    70    80    90    100   110   120   130   140
         .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
        |******************---------------******---*********---***---******---************---***|
        |---***---***---******---------******---------***---------------*********---***---------|
        """
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
        
    #@unittest.skip('')
    def test_fusion10(self):
        """
         .  .  .  .  .  .
        |***************|
        |---*********---| 
        |------***------| 
        """
        X = [(c,0,25,5.),(c,5,20,4.),(c,10,15,2.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,11.),(c,15,20,9.),(c,20,25,5.)] 
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion11(self):
        """
         .  .  .  .  .  .
        |************---|
        |---************|
        |------***------
        """
        X = [(c,0,20,5.),(c,5,25,4.),(c,10,15,2.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,10,15,11.),(c,15,20,9.),(c,20,25,4.)] 
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion12(self):
        """
         .  .  .  .  .  .
        |***------***---|
        |******---******|
        """
        X = [(c,0,5,5.),(c,0,10,4.),(c,15,20,2.),(c,15,25,3.)]
        R = [(c,0,5,9.),(c,5,10,4.),(c,15,20,5.),(c,20,25,3.)]
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion13(self):
        """
         .  .  .  .  .  .
        |******---******|
        |---***------***|
        """
        X = [(c,0,10,5.),(c,5,10,4.),(c,15,25,2.),(c,20,25,3.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,15,20,2.),(c,20,25,5.)]
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion14(self):
        """
         .  .  .  .  .  .  .  .  .  .
        |******---******------******|
        |---***------******---***---|
        """
        X = [(c,0,10,5.),(c,5,10,4.),(c,15,25,2.),(c,20,30,3.),(c,35,40,7.),(c,35,45,6.)]
        R = [(c,0,5,5.),(c,5,10,9.),(c,15,20,2.),(c,20,25,5.),(c,25,30,3.),(c,35,40,13.),(c,40,45,6.)]
        self.commonTest(X,R)
        
    #@unittest.skip('')
    def test_fusion15(self):
        """
         .  .  .  .  .  .  .  .  .  .
        |---************------******|
        |---***------******---***---|
        """
        X = [(c,5,10,8.),(c,5,25,5.),(c,20,30,4.),(c,35,40,3.),(c,35,45,2.)]
        R = [(c,5,10,13.),(c,10,20,5.),(c,20,25,9.),(c,25,30,4.),(c,35,40,5.),(c,40,45,2.)]
        self.commonTest(X,R)


class Test_Expressions1(unittest.TestCase):
    """Two conditions, different lengths, invertible"""
    def setUp(self):
        e1="e1"; e2="e2"; t1="t1"; t2="t2"; g1="g1"; c="c";
        self.ncond = 2
        self.nreads = array([1e9]*self.ncond)
        self.counts = array([[27,12],[3,3]]) # [[cond1],[cond2]]
        self.rpkms = array([[27/3.,12/6.],[3/3.,3/6.]])
        self.exons_data = [[e1,e2]]+list(self.counts)+list(self.rpkms)+[[0.,3.],[3.,9.],[g1,g1],["gg1","gg1"],[c,c]]
        self.transcript_mapping = {t1:(g1,0,3,3.,c), t2:(g1,0,9,9.,c)}
        self.gene_mapping = {g1:("gg1",0,9,9.,c)}
        self.exon_lengths = {e1:3., e2:6.}
        self.exon_to_gene = {e1:g1, e2:g1}
        self.trans_in_gene = {g1:[t1,t2]}
        self.exons_in_trans = {t1:[e1], t2:[e1,e2]}
        """
           *Counts Cond1*             *Rpkm Cond1*
        g1 |===.======|               |===.===|
        t1 |---|         21           |---|      7
        t2 |---.------|  6  +  12     |---.---| (2) 2

             27    12                   9   2
           |.e1.||.e2.|               |e1| |e2|
        """
        """
           *Counts Cond2*             *Rpkm Cond2*
        g1 |===.======|               |===.===|
        t1 |---|         1.5          |---|      0.5
        t2 |---.------|  1.5 + 3      |---.---| (0.5) 0.5

             3     3                    1   0.5
           |.e1.||.e2.|               |e1| |e2|
        """
    def test_transcripts_expression(self):
        tcounts, trpkm = transcripts_expression(self.exons_data, self.exon_lengths, self.transcript_mapping,
                 self.trans_in_gene, self.exons_in_trans, self.ncond, self.nreads)
        assert_almost_equal(trpkm["t1"], array([7., 0.5]))
        assert_almost_equal(trpkm["t2"], array([2., 0.5]))
        assert_almost_equal(tcounts["t1"], array([21., 1.5]))
        assert_almost_equal(tcounts["t2"], array([18., 4.5]))
        self.assertEqual(sum(sum(tcounts.values())), sum(sum(self.counts)))

    def test_genes_expression(self):
        gcounts, grpkm = genes_expression(self.exons_data, self.gene_mapping,
                self.exon_to_gene, self.ncond, self.nreads)
        assert_almost_equal(gcounts["g1"], array([39., 6.]))
        assert_almost_equal(grpkm["g1"],array([39./9,6./9]))

    def test_coherence(self):
        # Test if sum of transcript counts equals gene counts
        tcounts, trpkmm = transcripts_expression(self.exons_data, self.exon_lengths, self.transcript_mapping,
                     self.trans_in_gene, self.exons_in_trans, self.ncond, self.nreads)
        gcounts, grpkms = genes_expression(self.exons_data, self.gene_mapping,
                self.exon_to_gene, self.ncond, self.nreads)
        self.assertEqual(sum(gcounts["g1"]), sum([sum(tcounts[t]) for t in self.trans_in_gene["g1"]]))


class Test_Expressions2(unittest.TestCase):
    """One condition, equal lengths, invertible"""
    def setUp(self):
        e1="e1"; e2="e2"; e3="e3"; t1="t1"; t2="t2"; t3="t3"; g1="g1"; c="c"
        self.ncond = 1
        self.nreads = array([1e9])
        self.counts = array([[10,15,10]]) # [[cond1]]
        self.rpkms = array([[10/5.,15/5.,10/5.]])
        self.exons_data = [[e1,e2,e3]]+list(self.counts)+list(self.rpkms)+\
               [[0.,5.,10],[5.,10.,15.],["g1"]*3,["gg1"]*3,[c]*3]
        self.transcript_mapping = {t1:(g1,0,10,10.,c), t2:(g1,5,15,10.,c), t3:(g1,0,15,15.,c)}
        self.gene_mapping = {g1:("gg1",0,9,9.,c)}
        self.exon_lengths = {e1:5., e2:5., e3:5.}
        self.exon_to_gene = {e1:g1, e2:g1, e3:g1}
        self.trans_in_gene = {g1:[t1,t2,t3]}
        self.exons_in_trans = {t1:[e1,e2], t2:[e2,e3], t3:[e1,e2,e3]}
        """
           *Counts Cond1*
        g1 |===.===.===|
        t1 |-------|      5 + 5
        t2     |-------|  5 +     5
        t3 |-----------|  5 + 5 + 5

            10  15   10
           |e1||e2| |e3|
        """
    def test_transcripts_expression(self):
        tcounts, trpkm = transcripts_expression(self.exons_data, self.exon_lengths, self.transcript_mapping,
                 self.trans_in_gene, self.exons_in_trans, self.ncond, self.nreads)
        assert_almost_equal(tcounts["t1"], array([10.]))
        assert_almost_equal(tcounts["t2"], array([10.]))
        assert_almost_equal(tcounts["t3"], array([15.]))
        assert_almost_equal(trpkm["t1"], array([1.]))
        assert_almost_equal(trpkm["t2"], array([1.]))
        assert_almost_equal(trpkm["t3"], array([1.]))
        self.assertEqual(sum(sum(tcounts.values())), sum(sum(self.counts)))

    def test_genes_expression(self):
        gcounts, grpkm = genes_expression(self.exons_data, self.gene_mapping,
                self.exon_to_gene, self.ncond, self.nreads)
        assert_almost_equal(gcounts["g1"], array([35.]))
        assert_almost_equal(grpkm["g1"],array([35./9]))


class Test_Expressions3(unittest.TestCase):
    """Underdetermined system"""
    def setUp(self):
        e1="e1"; e2="e2"; e3="e3"; t1="t1"; t2="t2"; t3="t3"; t4="t4"; g1="g1"; c="c"
        self.ncond = 1
        self.nreads = array([1e9])
        self.counts = array([[10,15,10]]) # [[cond1]]
        self.rpkms = array([[10/5.,15/5.,10/5.]])
        self.exons_data = [[e1,e2,e3]]+list(self.counts)+list(self.rpkms)+\
               [[0.,5.,10],[5.,10.,15.],[g1]*3,["gg1"]*3,[c]*3]
        self.transcript_mapping = {t1:(g1,0,10,10.,c), t2:(g1,5,15,10.,c), \
                                   t3:(g1,0,15,15.,c), t4:(g1,0,15,10.,c)}
        self.gene_mapping = {g1:("gg1",0,9,9.,c)}
        self.exon_lengths = {e1:5., e2:5., e3:5.}
        self.exon_to_gene = {e1:g1, e2:g1, e3:g1}
        self.trans_in_gene = {g1:[t1,t2,t3,t4]}
        self.exons_in_trans = {t1:[e1,e2], t2:[e2,e3], t3:[e1,e2,e3], t4:[e1,e3]}
        """
           *Counts Cond1*
        g1 |===.===.===|
        t1 |-------|      7.5 + 7.5
        t2     |-------|        7.5 + 7.5
        t3 |-----------|  0     0     0
        t4 |---|   |---|  2.5 +       2.5

            10  15   10
           |e1||e2| |e3|
        """
    def test_transcripts_expression(self):
        tcounts, trpkm = transcripts_expression(self.exons_data, self.exon_lengths, self.transcript_mapping,
                 self.trans_in_gene, self.exons_in_trans, self.ncond, self.nreads)
        self.assertEqual(sum(sum(tcounts.values())), sum(sum(self.counts)))


class Test_Expressions4(unittest.TestCase):
    """Overdetermined system"""
    def setUp(self):
        e1="e1"; e2="e2"; e3="e3"; e4="e4"; t1="t1"; t2="t2"; t3="t3"; g1="g1"; c="c"
        self.ncond = 1
        self.nreads = array([1e9])
        self.counts = array([[10.,10.,10.,10.]]) # [[cond1]]
        self.rpkms = array([[10/5.,10/5.,10/5.,10/5.]])
        self.exons_data = [[e1,e2,e3,e4]]+list(self.counts)+list(self.rpkms)+\
               [[0,5,10,15],[5,10,15,20],[g1]*4,["gg1"]*4,[c]*4]
        self.transcript_mapping = {t1:(g1,0,10,10.,c), t2:(g1,5,20,15.,c), t3:(g1,5,20,10.,c)}
        self.gene_mapping = {g1:("gg1",0,12,12.,c)}
        self.exon_lengths = {e1:5., e2:5., e3:5., e4:5.}
        self.exon_to_gene = {e1:g1, e2:g1, e3:g1, e4:g1}
        self.trans_in_gene = {g1:[t1,t2,t3]}
        self.exons_in_trans = {t1:[e1,e2], t2:[e2,e3,e4], t3:[e2,e4]}
        """
           *Counts Cond1*
        g1 |===.===.===.===|
        t1 |-------|          12 + 12
        t2     |-----------|       4  + 4  + 4
        t3     |---|   |---|  0    0    0    0

            10  10  10   10
           |e1||e2||e3| |e4|
        """
    def test_transcripts_expression(self):
        tcounts, trpkm = transcripts_expression(self.exons_data, self.exon_lengths, self.transcript_mapping,
                 self.trans_in_gene, self.exons_in_trans, self.ncond, self.nreads)
        self.assertGreater(sum(sum(tcounts.values()))/sum(sum(self.counts)), 0.9)


class Test_Expressions5(unittest.TestCase):
    """Even more underdetermined system"""
    def setUp(self):
        e1="e1"; e2="e2"; e3="e3"; e4="e4"; e5="e5"; t1="t1"; t2="t2"; t3="t3"; g1="g1"; c="c"
        self.ncond = 1
        self.nreads = array([1e9])
        self.counts = array([[10.,10.,10.,10.,10.]]) # [[cond1]]
        self.rpkms = array([[10/5.,10/5.,10/5.,10/5.,10/5.]])
        self.exons_data = [[e1,e2,e3,e4,e5]]+list(self.counts)+list(self.rpkms)+\
               [[0,5,10,15,20],[5,10,15,20,25],[g1]*5,["gg1"]*5,[c]*5]
        self.transcript_mapping = {t1:(g1,0,15,10.,c), t2:(g1,10,25,15.,c), t3:(g1,5,25,10.,c)}
        self.gene_mapping = {g1:("gg1",0,15,15.,c)}
        self.exon_lengths = {e1:5., e2:5., e3:5., e4:5., e5:5.}
        self.exon_to_gene = {e1:g1, e2:g1, e3:g1, e4:g1, e5:g1}
        self.trans_in_gene = {g1:[t1,t2,t3]}
        self.exons_in_trans = {t1:[e1,e2,e3], t2:[e3,e4,e5], t3:[e2,e4,e5]}
        """
           *Counts Cond1*
        g1 |===.===.===.===.===|
        t1 |-----------|          4.6 + 4.6 + 4.6
        t2         |-----------|              4.6 + 4.6 + 4.6
        t3     |---|   |-------|        3.0 +       3.0 + 3.0

            10  10  10   10  10
           |e1||e2||e3| |e4||e5|
        """
    def test_transcripts_expression(self):
        tcounts, trpkm = transcripts_expression(self.exons_data, self.exon_lengths, self.transcript_mapping,
                 self.trans_in_gene, self.exons_in_trans, self.ncond, self.nreads)
        self.assertGreater(sum(sum(tcounts.values()))/sum(sum(self.counts)), 0.9)

class Test_Expressions_Solenne(unittest.TestCase):
    def setUp(self):
        e1="ENSMUSE00000139423"; e2="ENSMUSE00000139425"; t1="ENSMUST00000015723";
        g1="ENSMUSG00000015579"; c="chr17"; gname="Nkx2-5"
        self.ncond = 6
        self.nreads = array([1e9]*self.ncond)
        self.counts = array([[0,6.8],[0,10.6],[0,28.9],
                                   [4.4,160.9],[1.9,87.2],[2.7,58.5]])
        self.rpkms = array([[0,0.00691],[0,0.01077],[0,0.02937],
                                  [0.008133,0.16352],[0.00351,0.08862],[0.00499,0.05945]])
        self.exons_data = [[e1,e2]]+list(self.counts)+list(self.rpkms)+\
               [[26978510,26976592],[26977970,26975609],[g1]*2,[gname]*2,[c]*2]
        self.transcript_mapping = {t1:(g1,26975609,26978510,1525.,c)}
        self.gene_mapping = {g1:(gname,26975609,26978510,2901.,c)}
        self.exon_lengths = {e1:541., e2:984.}
        self.exon_to_gene = {e1:g1, e2:g1}
        self.trans_in_gene = {g1:[t1]}
        self.exons_in_trans = {t1:[e1,e2]}
        """
        g1 |===.===.===|  6.8
        t1 |-----------|  6.8
             0      6.8
           |e1-|   |-e2|
        """
    def test_transcripts_expression(self):
        tcounts, trpkm = transcripts_expression(self.exons_data, self.exon_lengths, self.transcript_mapping,
                 self.trans_in_gene, self.exons_in_trans, self.ncond, self.nreads)
        # Exact solution, special case len(tg)==1
        assert_almost_equal(tcounts["ENSMUST00000015723"],
                            array([6.8,10.6,28.9,165.3,89.1,61.2]))
        assert_almost_equal(trpkm["ENSMUST00000015723"],
                            array([0.00446,0.00695,0.01895,0.10839,0.05843,0.04013]), 5)
        self.assertAlmostEqual(sum(sum(tcounts.values())), sum(sum(self.counts)))
        # Pseudo-inverse solution
        #assert_almost_equal(tcounts["ENSMUST00000015723"], array([7.25,11.31,30.83,175.52,94.7,64.78]))
        #self.assertAlmostEqual(sum(sum(tcounts.values())), 384.39) #pinv solution


class Test_others(unittest.TestCase):
    def setUp(self):
        self.counts = array([[27,12],[3,3]]) # [[cond1],[cond2]]
        self.assembly = Assem()

    def test_estimate_size_factors(self):
        res, size_factors = estimate_size_factors(self.counts)
        self.assertIsInstance(self.counts, numpy.ndarray)
        self.assertEqual(type(self.counts), type(res))
        self.assertEqual(self.counts.shape, res.shape)
        assert_almost_equal(size_factors, array([2.5, 0.41666]), decimal=3)
        assert_almost_equal(res, array([[10.8, 4.8],[7.2, 7.2]]))

    @unittest.skip("")
    def test_save_results(self):
        with execution(None) as ex:
            save_results(ex,cols=[[1,2,3],('a','b','c','d'),[],[],[],[],[]],
                     conditions=["num.1","char.1"],
                     group_ids={'num':1,'char':2}, assembly=self.assembly,
                     header=["num","char","e","e","e","e","e"], feature_type="test")

    def test_to_rpkm(self):
        lengths = array([3.,6.])
        nreads = array([10e6])
        # array form
        rpkm = to_rpkm(self.counts, lengths, nreads)
        assert_almost_equal(rpkm, array([[900.,200.],[100.,50.]]))
        # numeric form
        rpkm = to_rpkm(35., 7, 10e6)
        self.assertEqual(rpkm, 500)
        # dict form
        counts = dict(zip(["a","b"],self.counts))
        rpkm = to_rpkm(counts, lengths, nreads)
        assert_almost_equal(rpkm["a"], array([900.,200.]))
        assert_almost_equal(rpkm["b"], array([100.,50.]))

class Test_NNLS(unittest.TestCase):
    def test_lsqnonneg(self):
        C = array([[0.0372, 0.2869],
                         [0.6861, 0.7071],
                         [0.6233, 0.6245],
                         [0.6344, 0.6170]])
        C1 = array([[0.0372, 0.2869, 0.4],
                          [0.6861, 0.7071, 0.3],
                          [0.6233, 0.6245, 0.1],
                          [0.6344, 0.6170, 0.5]])
        C2 = array([[0.0372, 0.2869, 0.4],
                          [0.6861, 0.7071,-0.3],
                          [0.6233, 0.6245,-0.1],
                          [0.6344, 0.6170, 0.5]])
        d = array([0.8587, 0.1781, 0.0747, 0.8405])

        [x, resnorm, residual] = lsqnonneg(C, d)
        dres = abs(resnorm - 0.8315)          # compare with matlab result
        self.assertLess(dres, 0.001)

        [x, resnorm, residual] = lsqnonneg(C1, d)
        dres = abs(resnorm - 0.1477)          # compare with matlab result
        self.assertLess(dres, 0.01)

        [x, resnorm, residual] = lsqnonneg(C2, d)
        dres = abs(resnorm - 0.1027)          # compare with matlab result
        self.assertLess(dres, 0.01)

        k = array([[0.1210, 0.2319, 0.4398, 0.9342, 0.1370],
                         [0.4508, 0.2393, 0.3400, 0.2644, 0.8188],
                         [0.7159, 0.0498, 0.3142, 0.1603, 0.4302],
                         [0.8928, 0.0784, 0.3651, 0.8729, 0.8903],
                         [0.2731, 0.6408, 0.3932, 0.2379, 0.7349],
                         [0.2548, 0.1909, 0.5915, 0.6458, 0.6873],
                         [0.8656, 0.8439, 0.1197, 0.9669, 0.3461],
                         [0.2324, 0.1739, 0.0381, 0.6649, 0.1660],
                         [0.8049, 0.1708, 0.4586, 0.8704, 0.1556],
                         [0.9084, 0.9943, 0.8699, 0.0099, 0.1911]])
        k1 = k-0.5
        l = array([0.4225, 0.8560, 0.4902, 0.8159, 0.4608, 0.4574, 0.4507, 0.4122, 0.9016, 0.0056])

        [x, resnorm, residual] = lsqnonneg(k, l)
        dres = abs(resnorm - 0.3695)          # compare with matlab result
        self.assertLess(dres, 0.01)

        [x, resnorm, residual] = lsqnonneg(k1, l)
        dres = abs(resnorm - 2.8639)          # compare with matlab result
        self.assertLess(dres, 0.01)


class Test_Pileup(unittest.TestCase):
    def setUp(self):
        self.gene_name = "Gapdh"
        self.gene_id = "ENSG00000111640"
        self.bam = "test_data/Gapdh.bam"

    def test_fetch_labels(self):
        self.exons = fetch_labels(self.bam)
        exons = [("ENSMUSE00000569415|ENSMUSG00000057666|125115289|125115329|-1", 41),
                 ("ENSMUSE00000709315|ENSMUSG00000057666|125114615|125115329|-1", 715)]
        self.assertIn(exons[0],self.exons); self.assertIn(exons[1],self.exons)
        self.assertEqual(len(self.exons),19)

    def test_build_pileup(self):
        self.exons = fetch_labels(self.bam)
        self.counts = build_pileup(self.bam, self.exons)
        self.assertEqual([self.counts[e[0].split('|')[0]] for e in self.exons],\
                         [0, 35, 0, 0, 0, 0, 0, 3679, 3707, 0, 0, 0, 149, 3, 0, 0, 55, 0, 161])
        counts = {'ENSMUSE00000745781': 3, 'ENSMUSE00000886744': 0, 'ENSMUSE00000719706': 0, 'ENSMUSE00000511617': 0, 'ENSMUSE00000873350': 0, 'ENSMUSE00000775454': 0, 'ENSMUSE00000709315': 35, 'ENSMUSE00000822668': 149, 'ENSMUSE00000472146': 0, 'ENSMUSE00000487077': 3679, 'ENSMUSE00000751942': 3707, 'ENSMUSE00000740765': 0, 'ENSMUSE00000512722': 0, 'ENSMUSE00000569415': 0, 'ENSMUSE00000879959': 0, 'ENSMUSE00000815727': 55, 'ENSMUSE00000491786': 0, 'ENSMUSE00000721118': 161, 'ENSMUSE00000881196': 0}
        self.assertItemsEqual(self.counts,counts)


#-----------------------------------#
# This code was written by the BBCF #
# http://bbcf.epfl.ch/              #
# webmaster.bbcf@epfl.ch            #
#-----------------------------------#
