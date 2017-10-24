#!/usr/bin/env pytthon3
import colors

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
TILE_SIZE = 16
 
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
ROOM_MAX_SIZE = 8
ROOM_MIN_SIZE = 4
MAX_ROOMS = 24
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2

#monster pathing
DEFAULT_PATHSIZE = 25

#spell values
HEAL_AMOUNT = 6
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
 
# game / map settings
FOV_ALGO = 'SHADOW' # was 'BASIC'
FOV_ALGO_BAD = 'BASIC'
FOV_RADIUS_BAD = 5
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 8 #was 10
FOV_BASIC = 'BASIC'

# launcher settings
LIMIT_FPS = 30  #20 frames-per-second maximum
TITLE = "Grendel's Last Stand"
AUTHOR = 'Astrimedes'

# main menu image
MENU_BACKGROUND = 'grendel.png'

#state names
STATE_PLAYING = 'playing'
STATE_DEAD = 'dead'
STATE_EXIT = 'exit'

# map colors
color_dark_ground = colors.darkest_azure
color_dark_wall = colors.darkest_gray

color_light_ground = colors.light_sepia
color_light_wall = colors.sepia

color_target = colors.light_orange

# player colors
color_dead = colors.dark_crimson

# health 'thresholds'
THRESH_HEALTH = (1, 0.66, 0.33)
THRESH_COLORS = (colors.darkest_green, colors.dark_yellow, colors.dark_red)

MOVE = 'moved'
MOVE_7 = 'moved_left-up'
MOVE_8 = 'moved_up'
MOVE_9 = 'moved right_up'
MOVE_4 = 'moved_left'
MOVE_6 = 'moved_right'
MOVE_1 = 'moved_left-down'
MOVE_2 = 'moved_down'
MOVE_3 = 'moved_right-down'


ATTACK = 'attacked'
INVENTORY = 'inventory'
WAIT = 'waited'
PICK_UP = 'picked up'
DROP = 'drop'


INPUT_REPEAT_DELAY = 1.0 / 50.0