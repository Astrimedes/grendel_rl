import sys

import dungeon_generator as gen

sys.stdout = open('dungen_test.log', 'w')

gen.try_break_map(10000)
