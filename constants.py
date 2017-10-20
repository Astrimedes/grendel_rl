#!/usr/bin/env pytthon3
import colors

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
 
#size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 43
 
#sizes and coordinates relevant for the GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50
 
#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2

#monster pathing
DEFAULT_PATHSIZE = 25
 
#spell values
HEAL_AMOUNT = 6
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
CONFUSE_RANGE = 8
CONFUSE_NUM_TURNS = 10
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
 
# game / map settings
FOV_ALGO = 'SHADOW' # was 'BASIC'
FOV_ALGO_BAD = 'PERMISSIVE8'
FOV_RADIUS_BAD = 5
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 5 #was 10

# launcher settings
LIMIT_FPS = 20  #20 frames-per-second maximum
TITLE = 'Deathreek Dungeon'
AUTHOR = 'Astrimedes'

# main menu image
MENU_BACKGROUND = 'ddoor.png'

#state names
STATE_PLAYING = 'playing'
STATE_DEAD = 'dead'
STATE_EXIT = 'exit'

# map colors
color_dark_ground = colors.dark_azure
color_dark_wall = colors.darkest_azure

color_light_ground = colors.amber
color_light_wall = colors.dark_amber

# player colors
color_dead = colors.dark_crimson

# health 'thresholds'
THRESH_HEALTH = (1, 0.75, 0.5, 0.25)
THRESH_COLORS = (colors.white, colors.lightest_gray, colors.yellow, colors.red)