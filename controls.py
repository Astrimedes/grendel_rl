#!/usr/bin/env python3


"""
Capturing Input
"""
_upleft = ['KP7', 'y']
_up = ['KP8', 'k']
_upright = ['KP9', 'u']
_left = ['KP4', 'h']
_wait = ['KP5', '.']
_right = ['KP6', 'l']
_downleft = ['KP1', 'b']
_down = ['KP2', 'j']
_downright = ['KP3', 'n']


def up_left(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _upleft)
    
def up(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _up)
    
def up_right(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _upright)
    
def left(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _left)
    
def wait(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _wait)
    
def right(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _right)
    
def down_left(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _downleft)
    
def down(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _down)
    
def down_right(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in _downright)
    
def pick_up(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'g'
    
def inventory(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'i'
    
def drop(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'd'
    
    
"""
Displaying information
"""
# y k u
#  \|/ 
# h-.-l
#  /|\ 
# b j n

# 7 8 9
#  \|/
# 4-5-6
#  /|\
# 1 2 3

strlines_hjk = ['y k u',' \|/ ','h-.-l',' /|\ ', 'b j n']

strlines_numpad = ['7 8 9',' \|/ ','4-5-6',' /|\ ','1 2 3']

    
