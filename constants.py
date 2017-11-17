#!/usr/bin/env python3
import colors

import math

#actual size of the window
SCREEN_WIDTH = 70 # was 80
SCREEN_HEIGHT = 52
TILE_SIZE = 16

#size of the map
MAP_WIDTH = 80
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
ROOM_MAX_SIZE = 5
ROOM_MIN_SIZE = 2
MAX_ROOMS = 32

BIGROOM_MIN_W = 6
BIGROOM_MAX_W = 12
BIGROOM_MIN_H = 6
BIGROOM_MAX_H = 12

# monster qty
MONSTER_COUNT = 34  #26
MONSTER_SPECIAL = 0.4
MONSTER_BARD = 0.45
MONSTER_TOUGH = 0.55
ENEMIES_FINAL = MONSTER_COUNT // 4

# ITEMS
ITEM_QTY = round(MONSTER_COUNT * 0.65)

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
STATE_WON = 'won'
STATE_EXIT = 'exit'

# map colors
color_dark_ground = colors.darkest_azure
color_dark_wall = colors.darkest_gray

color_light_ground = colors.light_sepia
color_light_wall = colors.sepia

#ui colors
# color_frame = colors.desaturated_azure
color_frame = (10,50,25)

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
START_SPEED = 10
START_ATK_SPEED = 8
START_DEFENSE = 2
START_VISION = 4

# worst stat levels
MIN_POWER = 1
MIN_DEFENSE = 0
MAX_SPEED = START_SPEED * 2 # real stat
MAX_ATK_SPEED = START_ATK_SPEED * 2
MIN_SPEED_DSP = 0.334 # inverted for display
MIN_VISION = 1

# best stat levels
MIN_SPEED = START_SPEED // 2
MIN_ATK_SPEED = START_ATK_SPEED // 2

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

# Noise
#distance at which monsters can be 'awaken' depending on their hearing and noise level
MAX_HEAR_DIST = 25
# max noise_strength
MAX_NOISE_STR = 10


# consumable body part names
PART_POWER = 'Muscle'
PART_DEFENSE = 'Torso'
PART_SPEED = 'Leg'
PART_FOV = 'Eye'
PART_HEALING = 'Heart'

# indicates 1 tile away
MIN_PDIST = math.sqrt(2) + 0.0001

# start date/time in seconds
START_TIME = 26172000 #Oct 30, 1970 AD, 9:00 PM (convert years)   26168400
TIME_SUBTRACT_YEARS = 1522

# stat bonus / penalty
### FLESH POWERUPS ###
PEN_FRAC = 0.5
SPEED_BONUS = -2
SPEED_PENALTY = -SPEED_BONUS * PEN_FRAC
POWER_BONUS = 4
POWER_PENALTY = -POWER_BONUS * PEN_FRAC
VISION_BONUS = 1
VISION_PENALTY = -VISION_BONUS * PEN_FRAC
DEFENSE_BONUS = 1
DEFENSE_PENALTY = -DEFENSE_BONUS * PEN_FRAC