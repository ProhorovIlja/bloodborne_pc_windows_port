# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from progress_v490 import inventory, ratio, shared_bodies

class Progress(unittest.TestCase):
    def test_boundaries(self):
        for milestone in (10,25,50,75,90,100):
            self.assertNotIn(milestone,ratio(milestone*100-1,10000)['reached'])
            self.assertIn(milestone,ratio(milestone*100,10000)['reached'])
        self.assertEqual(ratio(99999,100000)['percent'],'99.99')
        self.assertIsNone(ratio(1,1)['next'])
        for done,total in ((-1,2),(3,2),(0,0),(True,2)):
            with self.assertRaises(ValueError):
                ratio(done,total)

    def test_denominators(self):
        out=inventory(range(10),{'a':[1,2],'b':[3,4,5]},[1,1,9],1)
        self.assertEqual(out['metadata_start_generation']['percent'],'50.00')
        self.assertEqual(out['constructor_slots_generation']['percent'],'66.66')
        self.assertEqual(out['ordered_runtime_prefix']['percent'],'33.33')
        self.assertIsNone(out['gameplay_coverage'])
        self.assertIsNone(inventory(range(10),{'a':[1]},[1])['ordered_runtime_prefix'])
        for groups in ({'a':[1,1]},{'a':[1],'b':[1]},{'a':[11]}):
            with self.assertRaises(ValueError):
                inventory(range(10),groups,[1])

    def test_sharing(self):
        bodies,ids=shared_bodies([(1,b'a',['one']),(2,b'b',['one']),(3,b'c',['two'])])
        self.assertEqual(len(bodies),2)
        self.assertEqual(ids,{1:0,2:0,3:1})
        with self.assertRaises(ValueError):
            shared_bodies([(1,b'a',['one']),(1,b'b',['two'])])
