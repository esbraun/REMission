"""The visit button must not skip washouts or the day36/day72 reviews."""
import unittest
from services.foundation.nof1_clock import boundaries_at,phase_at


class Nof1ClockTests(unittest.TestCase):
    def test_eight_blocks_and_two_night_washouts_without_nightly_draws(self):
        draws=[d for d in range(73) if 'block_start' in boundaries_at(d)]
        washouts=[d for d in range(73) if 'washout_start' in boundaries_at(d)]
        self.assertEqual(draws,[0,9,18,27,36,45,54,63])
        self.assertEqual(washouts,[7,16,25,34,43,52,61,70])
        self.assertEqual(sum(phase_at(d)['phase']=='block' for d in range(72)),56)
        self.assertEqual(sum(phase_at(d)['phase']=='washout' for d in range(72)),16)
        self.assertEqual(boundaries_at(72),('review','complete'))
        self.assertEqual(boundaries_at(73),())

    def test_fourteen_day_steps_retain_intervening_reviews_in_order(self):
        crossed=[]
        for before,after in [(0,14),(14,28),(28,42),(42,56),(56,70),(70,84)]:
            crossed.extend((day,event) for day in range(before+1,after+1) for event in boundaries_at(day))
        self.assertEqual([d for d,e in crossed if e=='review'],[36,72])
        self.assertLess(crossed.index((36,'review')),crossed.index((36,'block_start')))
        self.assertLess(crossed.index((72,'review')),crossed.index((72,'complete')))
        self.assertEqual(phase_at(7),dict(phase='washout',block=1,protocol_day=7))
        self.assertEqual(phase_at(8)['phase'],'washout')
        self.assertEqual(phase_at(9),dict(phase='block',block=2,protocol_day=9))
