#!/usr/bin/env python3
from random import choice

_prefixes = ('Uth','Threk','Kur','Ro','Ar','Co','Wulf','Kor','Hroth')
_suffixes = ('gar','nan','gorn','ruk','','wor','tor')

def barb_name():
    return choice(_prefixes) + choice(_suffixes)