#!/usr/bin/env python3

def up_left(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP7' or user_input.text == '7')
    
def up(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP8' or user_input.text == '8')
    
def up_right(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP9' or user_input.text == '9')
    
def left(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP4' or user_input.text == '4')
    
def wait(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP5' or user_input.text == '5' or user_input.text == '.')
    
def right(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP6' or user_input.text == '6')
    
def down_left(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP1' or user_input.text == '1')
    
def down(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP2' or user_input.text == '2')
    
def down_right(user_input):
    return user_input.type == 'KEYDOWN' and (user_input.key == 'KP3' or user_input.text == '3')
    
def pick_up(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'g'
    
def inventory(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'i'
    
def drop(user_input):
    return user_input.type == 'KEYDOWN' and user_input.text == 'd'