# Built-in modules #
import os, shutil

# Internal modules #
from ... import track
from ..common import named_temporary_path
from ..track_collection import track_collections, yeast_chr_file

# Unittesting module #
try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Nosetest flag #
__test__ = True

###################################################################################
class Test_Read(unittest.TestCase):
    def runTest(self):
        t = track_collections['Validation'][1]
        with track.load(t['path'], chrmeta=t['chrmeta']) as t['track']:
            # Just the first feature #
            data = t['track'].read()
            self.assertEqual(data.next(), ('chr1', 0, 10, 'Validation feature 1', 10.0, 0))
            # Number of features #
            data = t['track'].read()
            self.assertEqual(len(list(data)), 12)

#-----------------------------------------------------------------------------#
class Test_Write(unittest.TestCase):
    def runTest(self):
        path = named_temporary_path('.bed')
        with track.new(path, chrmeta=yeast_chr_file) as t:
            features = {}
            features['chr1'] = [(10, 20, 'Lorem', 1.0, 1),
                                (30, 40, 'Ipsum', 2.0, 1)]
            features['chr2'] = [(10, 20, 'Dolor', 3.0, 1)]
            for chrom, data in sorted(features.items()):
                t.write(chrom, data)
        with open(path,                                      'r') as f: A = f.read().split('\n')
        with open(track_collections['Validation'][4]['path'],'r') as f: B = f.read().split('\n')
        self.assertEqual(A[1:], B)
        os.remove(path)

#-----------------------------------------------------------------------------#
class Test_Roundtrips(unittest.TestCase):
    def runTest(self):
        path = named_temporary_path('.bed')
        for i in (2,3,4):
            track_dict = track_collections['Validation'][i]
            with track.load(track_dict['path'], chrmeta=track_dict['chrmeta']) as t: t.dump(path)
            with open(path,              'r') as f: A = f.read().split('\n')
            with open(track_dict['path'],'r') as f: B = f.read().split('\n')
            self.assertEqual(A[1:], B)
            os.remove(path)

#-----------------------------------------------------------------------------#
class Test_Format(unittest.TestCase):
    def runTest(self):
        t = track_collections['Validation'][1]
        with track.load(t['path'], chrmeta=t['chrmeta']) as t:
            self.assertEqual(t.format, 'sql')
            self.assertEqual(t._format, 'bed')

#-----------------------------------------------------------------------------#
class Test_NoExtension(unittest.TestCase):
    def runTest(self):
        old = track_collections['Validation'][1]['path']
        new = named_temporary_path()
        shutil.copyfile(old, new)
        with track.load(new, 'bed', chrmeta=yeast_chr_file) as t:
            self.assertEqual(t._format, 'bed')
        os.remove(new)

#-----------------------------------------------------------------------------#
class Test_NoFormat(unittest.TestCase):
    def runTest(self):
        old = track_collections['Yeast']['RP genes']['path']
        new = named_temporary_path()
        shutil.copyfile(old, new)
        with track.load(new, chrmeta=yeast_chr_file) as t:
            self.assertEqual(t._format, 'bed')
        os.remove(new)

#-----------------------------------------------------------------------------#
class Test_Genrep(unittest.TestCase):
    def runTest(self):
        t = track_collections['Validation'][1]
        with track.load(t['path'], chrmeta='hg19') as t:
            self.assertEqual(t.meta_chr[0]['length'], 249250621)

#-----------------------------------#
# This code was written by the BBCF #
# http://bbcf.epfl.ch/              #
# webmaster.bbcf@epfl.ch            #
#-----------------------------------#