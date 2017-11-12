#!/usr/bin/env python3
import random

_prefixes = ('Mo','Here','Sig','Ae','Wig','Uth','Thr','Kur','Ro','Ar','Co','Wulf','Kor','Hroth','Be','Tho','Yor','Gor','Go','Bo','Be','Hun','Un','Ec','Hy')
_suffixes = ('gar','nan','gorn','wor','tor','orn','yth','rak','laf','son','th','mund','hulf','ere','wulf','gd','eow','mond','rth')
_middles = ('o','e','sch','fer','gel','gth','ek','thy','')

middle_chance = 0.4

forbidden = ['Beowulf', 'Hrothgar']

def barb_name():
    if random.uniform(0,1) < middle_chance:
        name = random.choice(_prefixes) + random.choice(_middles) + random.choice(_suffixes)
    else:
        name = random.choice(_prefixes) + random.choice(_suffixes)
    while name in forbidden:
        name = barb_name()
    return name
    
if __name__ == '__main__':
    repeats = 0
    names = [barb_name() for i in range(0,100)]
    for i, n in enumerate(names):
        if n in names[:i]:
            repeats += 1
        print(n)
    print(str(repeats) + ' repeats')