#!/usr/bin/env python3
import colors

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 54
TILE_SIZE = 16

#size of the map
MAP_WIDTH = 60
MAP_HEIGHT = 60

# sizes and coordinates relevant for the GUI
# messages panel
MSG_PANEL_HEIGHT = 12
MSG_PANEL_X = 0
MSG_PANEL_Y = SCREEN_HEIGHT - MSG_PANEL_HEIGHT - 1
MSG_PANEL_WIDTH = SCREEN_WIDTH - MSG_PANEL_X
 
# stat panel
STAT_PANEL_HEIGHT = SCREEN_HEIGHT - MSG_PANEL_HEIGHT - 1
STAT_PANEL_WIDTH = 18
STAT_PANEL_X = 0
STAT_PANEL_Y = 0
STATS_BEGIN_Y = round(STAT_PANEL_HEIGHT * 0.6)

# camera view console
CAMERA_PANEL_X = STAT_PANEL_WIDTH
CAMERA_PANEL_Y = 0
CAMERA_WIDTH = SCREEN_WIDTH - STAT_PANEL_WIDTH
CAMERA_HEIGHT = SCREEN_HEIGHT - MSG_PANEL_HEIGHT - 1

# inventory
INVENTORY_WIDTH = 50
 
#parameters for dungeon generator
ROOM_MAX_SIZE = 8
ROOM_MIN_SIZE = 3
MAX_ROOMS = 36

# monster qty
MONSTER_COUNT = 20
MONSTER_TOUGH = 0.19
MONSTER_WEAK = 1.0 - MONSTER_TOUGH

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
#MENU_BACKGROUND = 'Ogre_small.png'

#state names
STATE_PLAYING = 'playing'
STATE_DEAD = 'dead'
STATE_EXIT = 'exit'

# map colors
color_dark_ground = colors.darkest_azure
color_dark_wall = colors.darkest_gray

color_light_ground = colors.light_sepia
color_light_wall = colors.sepia

#ui colors
color_frame = colors.desaturated_azure

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
START_POWER = 7
START_SPEED = 1.25
START_ATK_SPEED = -0.25
START_DEFENSE = 2
START_VISION = 4

# worst stat levels
MIN_POWER = 1
MIN_DEFENSE = 0
MAX_SPEED = 3.0 # real stat
MIN_SPEED_DSP = 0.334 # inverted for display
MIN_VISION = 1

# best stat levels
MIN_SPEED = 0.34

# Display bars
# MIN
BARMIN_STR = MIN_POWER
BARMIN_SPD = MIN_SPEED_DSP
BARMIN_RES = MIN_DEFENSE
BARMIN_VIS = MIN_VISION
# MAX
BARMAX_STR = (MIN_POWER + START_POWER) * 2
BARMAX_SPD = (MAX_SPEED * 100)
BARMAX_RES = MIN_DEFENSE
BARMAX_VIS = MIN_VISION

# consumable body part names
PART_POWER = 'Muscles'
PART_DEFENSE = 'Torso'
PART_SPEED = 'Legs'
PART_FOV = 'Eyes'

# indicates 1 tile away
MIN_PDIST = 1.415

# start date/time in seconds
START_TIME = 26168400 #Oct 30, 1970 AD, 9:00 PM (convert years)
TIME_SUBTRACT_YEARS = 1522