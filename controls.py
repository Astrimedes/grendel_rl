#!/usr/bin/env python3

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

def up_left(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP7', '7', 'y'])
    
def up(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP8', '8', 'k'])
    
def up_right(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP9', '9', 'u'])
    
def left(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP4', '4', 'h'])
    
def wait(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP5', '5', '.'])
    
def right(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP6', '6', 'l'])
    
def down_left(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP1', '1', 'b'])
    
def down(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP2', '2', 'j'])
    
def down_right(user_input):
    return user_input.type == 'KEYDOWN' and any(i in [user_input.key, user_input.text] for i in ['KP3', '3', 'n'])
    
def pick_up(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'g'
    
def inventory(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'i'
    
def drop(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'd'