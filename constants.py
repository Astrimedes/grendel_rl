#!/usr/bin/env pytthon3
import colors

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 54
TILE_SIZE = 16
 
#size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 60

# camera view
CAMERA_WIDTH = 80
CAMERA_HEIGHT = 44
 
#sizes and coordinates relevant for the GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 10
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50
 
#parameters for dungeon generator
ROOM_MAX_SIZE = 8
ROOM_MIN_SIZE = 3
MAX_ROOMS = 38

#monster pathing
DEFAULT_PATHSIZE = 25

#spell values
HEAL_AMOUNT = 18
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
 
# game / map settings
FOV_ALGO = 'SHADOW' # was 'BASIC'
FOV_LIGHT_WALLS = True
FOV_BASIC = 'BASIC'
FOV_ALGO_BAD = 'BASIC'
FOV_RADIUS_BAD = 5

# launcher settings
LIMIT_FPS = 20  #20 frames-per-second maximum
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


# INPUT
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
MOUSE_MOVED = 'mouse'

INPUT_REPEAT_DELAY = 1.0 / (LIMIT_FPS / 2.0)

# starting stat levels
START_POWER = 5
START_SPEED = 1.25
START_ATK_SPEED = -0.25
START_DEFENSE = 2
START_VISION = 4

# worst stat levels
MIN_POWER = 3
MIN_DEFENSE = 0
MAX_SPEED = 2.0 # real stat
MIN_SPEED_DSP = 0.5 # inverted for display
MIN_VISION = 2

# best stat levels
MIN_SPEED = 0.34

# Display bars
# MIN
BARMIN_STR = MIN_POWER
BARMIN_SPD = 1.0 / MAX_SPEED 
BARMIN_RES = MIN_DEFENSE
BARMIN_VIS = MIN_VISION
# MAX
BARMIN_STR = MIN_POWER
BARMIN_SPD = 1.0 / MAX_SPEED 
BARMIN_RES = MIN_DEFENSE
BARMIN_VIS = MIN_VISION


# consumable body part names
PART_POWER = 'Muscles'
PART_DEF = 'Torso'
PART_SPEED = 'Legs'
PART_FOV = 'Eyes'

# indicates 1 tile away
MIN_PDIST = 1.415