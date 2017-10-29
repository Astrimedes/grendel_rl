#!/usr/bin/env python3
from random import choice

_prefixes = ('Uth','Threk','Kur','Ro','Ar','Co','Wulf','Kor','Hroth','Be','Tho','Yor','Gor','Go','Bo','Hun','Un','Ec')
_suffixes = ('gar','nan','gorn','ruk','wor','tor','orn','kuk','ak','rak','laf','son','ferth')

def barb_name():
    return choice(_prefixes) + choice(_suffixes)