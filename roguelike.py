#!/usr/bin/env python3
 
import tdl
from tcod import image_load
from random import randint
import colors
import math
import textwrap
import shelve
 
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
 
#spell values
HEAL_AMOUNT = 4
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
CONFUSE_RANGE = 8
CONFUSE_NUM_TURNS = 10
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
 
 
FOV_ALGO = 'BASIC'
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10
 
LIMIT_FPS = 20  #20 frames-per-second maximum
 
 
color_dark_wall = (0, 0, 100)
color_light_wall = (130, 110, 50)
color_dark_ground = (50, 50, 150)
color_light_ground = (200, 180, 50)
 
 
class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked
 
        #all tiles start unexplored
        self.explored = False
 
        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: 
            block_sight = blocked
        self.block_sight = block_sight
 
class Rect:
    #a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
 
    def center(self):
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2
        return (center_x, center_y)
 
    def intersect(self, other):
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)
 
class GameObject:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, 
                 fighter=None, ai=None, item=None):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks = blocks
        self.fighter = fighter
 
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self
 
        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self
 
        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self
 
    def move(self, dx, dy):
        #move by the given amount, if the destination is not blocked
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
 
    def move_towards(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
 
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)
 
    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)
 
    def distance(self, x, y):
        #return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
 
    def send_to_back(self):
        #make this object be drawn first, so all others appear above it if 
        #they're in the same tile.
        global objects
        objects.remove(self)
        objects.insert(0, self)
 
    def draw(self):
        global visible_tiles
 
        #only show if it's visible to the player
        if (self.x, self.y) in visible_tiles:
            #draw the character that represents this object at its position
            con.draw_char(self.x, self.y, self.char, self.color, bg=None)
 
    def clear(self):
        #erase the character that represents this object
        con.draw_char(self.x, self.y, ' ', self.color, bg=None)
 
class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function
 
    def take_damage(self, damage):
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
 
            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
 
    def attack(self, target):
        #a simple formula for attack damage
        damage = self.power - target.fighter.defense
 
        if damage > 0:
            #make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name + 
                  ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + 
                  ' but it has no effect!')
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
 
class BasicMonster:
    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn. If you can see it, it can see you
        monster = self.owner
        if (monster.x, monster.y) in visible_tiles:
 
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
 
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
 
class ConfusedMonster:
    #AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns
 
    def take_turn(self):
        if self.num_turns > 0:  #still confused...
            #move in a random direction, and decrease the number of turns confused
            self.owner.move(randint(-1, 1), randint(-1, 1))
            self.num_turns -= 1
 
        else:  
            #restore the previous AI (this one will be deleted because it's not 
            #referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', colors.red)
 
class Item:
    #an item that can be picked up and used.
    def __init__(self, use_function=None):
        self.use_function = use_function
 
    def pick_up(self):
        #add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + 
                    self.owner.name + '.', colors.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', colors.green)
 
    def drop(self):
        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped a ' + self.owner.name + '.', colors.yellow)
 
    def use(self):
        #just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner)  #destroy after use, unless it was 
                                              #cancelled for some reason
 
def is_blocked(x, y):
    #first test the map tile
    if my_map[x][y].blocked:
        return True
 
    #now check for any blocking objects
    for obj in objects:
        if obj.blocks and obj.x == x and obj.y == y:
            return True
 
    return False
 
def create_room(room):
    global my_map
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            my_map[x][y].blocked = False
            my_map[x][y].block_sight = False
 
def create_h_tunnel(x1, x2, y):
    global my_map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        my_map[x][y].blocked = False
        my_map[x][y].block_sight = False
 
def create_v_tunnel(y1, y2, x):
    global my_map
    #vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        my_map[x][y].blocked = False
        my_map[x][y].block_sight = False
 
 
def is_visible_tile(x, y):
    global my_map
 
    if x >= MAP_WIDTH or x < 0:
        return False
    elif y >= MAP_HEIGHT or y < 0:
        return False
    elif my_map[x][y].blocked == True:
        return False
    elif my_map[x][y].block_sight == True:
        return False
    else:
        return True
 
def make_map():
    global my_map, objects
 
    #the list of objects with those two
    objects = [player]
 
    #fill map with "blocked" tiles
    my_map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]
 
    rooms = []
    num_rooms = 0
 
    for r in range(MAX_ROOMS):
        #random width and height
        w = randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = randint(0, MAP_WIDTH-w-1)
        y = randint(0, MAP_HEIGHT-h-1)
 
        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)
 
        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
 
        if not failed:
            #this means there are no intersections, so this room is valid
 
            #"paint" it to the map's tiles
            create_room(new_room)
 
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
 
            if num_rooms == 0:
                #this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
 
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel
 
                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()
 
                #draw a coin (random number that is either 0 or 1)
                if randint(0, 1):
                    #first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)
 
            #add some contents to this room, such as monsters
            place_objects(new_room)
 
            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1
 
def place_objects(room):
    #choose random number of monsters
    num_monsters = randint(0, MAX_ROOM_MONSTERS)
 
    for i in range(num_monsters):
        #choose random spot for this monster
        x = randint(room.x1+1, room.x2-1)
        y = randint(room.y1+1, room.y2-1)
 
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            if randint(0, 100) < 80:  #80% chance of getting an orc
                #create an orc
                fighter_component = Fighter(hp=10, defense=0, power=3, 
                                            death_function=monster_death)
                ai_component = BasicMonster()
 
                monster = GameObject(x, y, 'o', 'orc', colors.desaturated_green,
                    blocks=True, fighter=fighter_component, ai=ai_component)
            else:
                #create a troll
                fighter_component = Fighter(hp=16, defense=1, power=4,
                                            death_function=monster_death)
                ai_component = BasicMonster()
 
                monster = GameObject(x, y, 'T', 'troll', colors.darker_green,
                    blocks=True, fighter=fighter_component, ai=ai_component)
 
            objects.append(monster)
 
    #choose random number of items
    num_items = randint(0, MAX_ROOM_ITEMS)
 
    for i in range(num_items):
        #choose random spot for this item
        x = randint(room.x1+1, room.x2-1)
        y = randint(room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            dice = randint(0, 100)
            if dice < 70:
                #create a healing potion (70% chance)
                item_component = Item(use_function=cast_heal)
 
                item = GameObject(x, y, '!', 'healing potion', 
                                  colors.violet, item=item_component)
 
            elif dice < 70+10:
                #create a lightning bolt scroll (15% chance)
                item_component = Item(use_function=cast_lightning)
 
                item = GameObject(x, y, '#', 'scroll of lightning bolt', 
                                  colors.light_yellow, item=item_component)
 
            elif dice < 70+10+10:
                #create a fireball scroll (10% chance)
                item_component = Item(use_function=cast_fireball)
 
                item = GameObject(x, y, '#', 'scroll of fireball', 
                                  colors.light_yellow, item=item_component)
 
            else:
                #create a confuse scroll (15% chance)
                item_component = Item(use_function=cast_confuse)
 
                item = GameObject(x, y, '#', 'scroll of confusion', 
                                  colors.light_yellow, item=item_component)
 
            objects.append(item)
            item.send_to_back()  #items appear below other objects
 
def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)
 
    #render the background first
    panel.draw_rect(x, y, total_width, 1, None, bg=back_color)
 
    #now render the bar on top
    if bar_width > 0:
        panel.draw_rect(x, y, bar_width, 1, None, bg=bar_color)
 
    #finally, some centered text with the values
    text = name + ': ' + str(value) + '/' + str(maximum)
    x_centered = x + (total_width-len(text))//2
    panel.draw_str(x_centered, y, text, fg=colors.white, bg=None)
 
def get_names_under_mouse():
 
    #return a string with the names of all objects under the mouse
    (x, y) = mouse_coord
 
    #create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
        if obj.x == x and obj.y == y and (obj.x, obj.y) in visible_tiles]
 
    names = ', '.join(names)  #join the names, separated by commas
    return names.capitalize()
 
def render_all():
    global fov_recompute
    global visible_tiles
 
    if fov_recompute:
        fov_recompute = False
        visible_tiles = tdl.map.quickFOV(player.x, player.y,
                                         is_visible_tile,
                                         fov=FOV_ALGO,
                                         radius=TORCH_RADIUS,
                                         lightWalls=FOV_LIGHT_WALLS)
 
        #go through all tiles, and set their background color according to the FOV
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = (x, y) in visible_tiles
                wall = my_map[x][y].block_sight
                if not visible:
                    #if it's not visible right now, the player can only see it 
                    #if it's explored
                    if my_map[x][y].explored:
                        if wall:
                            con.draw_char(x, y, None, fg=None, bg=color_dark_wall)
                        else:
                            con.draw_char(x, y, None, fg=None, bg=color_dark_ground)
                else:
                    if wall:
                        con.draw_char(x, y, None, fg=None, bg=color_light_wall)
                    else:
                        con.draw_char(x, y, None, fg=None, bg=color_light_ground)
                    #since it's visible, explore it
                    my_map[x][y].explored = True
 
 
    #draw all objects in the list
    for obj in objects:
        if obj != player:
            obj.draw()
    player.draw()
    #blit the contents of "con" to the root console and present it
    root.blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0)
 
    #prepare to render the GUI panel
    panel.clear(fg=colors.white, bg=colors.black)
 
    #print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        panel.draw_str(MSG_X, y, line, bg=None, fg=color)
        y += 1
 
    #show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
        colors.light_red, colors.darker_red)
 
    #display names of objects under the mouse
    panel.draw_str(1, 0, get_names_under_mouse(), bg=None, fg=colors.light_gray)
 
    #blit the contents of "panel" to the root console
    root.blit(panel, 0, PANEL_Y, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0)
 
def message(new_msg, color = colors.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
 
    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
 
        #add the new line as a tuple, with the text and the color
        game_msgs.append((line, color))
 
def player_move_or_attack(dx, dy):
    global fov_recompute
 
    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy
 
    #try to find an attackable object there
    target = None
    for obj in objects:
        if obj.fighter and obj.x == x and obj.y == y:
            target = obj
            break
 
    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
    else:
        player.move(dx, dy)
        fov_recompute = True
 
def player_wait():
	message('You wait.')
 
def menu(header, options, width):
    if len(options) > 26:
        raise ValueError ('Cannot have a menu with more than 26 options.')
 
    #calculate total height for the header (after textwrap) and one line per option
    header_wrapped = textwrap.wrap(header, width)
    header_height = len(header_wrapped)
    if header == '':
        header_height = 0
    height = len(options) + header_height
 
    #create an off-screen console that represents the menu's window
    window = tdl.Console(width, height)
 
    #print the header, with wrapped text
    window.draw_rect(0, 0, width, height, None, fg=colors.white, bg=None)
    for i, line in enumerate(header_wrapped):
        window.draw_str(0, 0+i, header_wrapped[i])
 
    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        window.draw_str(0, y, text, bg=None)
        y += 1
        letter_index += 1
 
    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH//2 - width//2
    y = SCREEN_HEIGHT//2 - height//2
    root.blit(window, x, y, width, height, 0, 0, fg_alpha=1.0, bg_alpha=0.7)
 
    #present the root console to the player and wait for a key-press
    tdl.flush()
    key = tdl.event.key_wait()
    key_char = key.char
    if key_char == '':
        key_char = ' ' # placeholder
 
    if key.key == 'ENTER' and key.alt:
        #Alt+Enter: toggle fullscreen
        tdl.set_fullscreen(not tdl.get_fullscreen())
 
    #convert the ASCII code to an index; if it corresponds to an option, return it
    index = ord(key_char) - ord('a')
    if index >= 0 and index < len(options):
        return index
    return None
 
def inventory_menu(header):
    #show a menu with each item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = [item.name for item in inventory]
 
    index = menu(header, options, INVENTORY_WIDTH)
 
    #if an item was chosen, return it
    if index is None or len(inventory) == 0:
        return None
    return inventory[index].item
 
def msgbox(text, width=50):
    menu(text, [], width)  #use menu() as a sort of "message box"
 
def handle_keys():
    global playerx, playery
    global fov_recompute
    global mouse_coord
 
    keypress = False
    for event in tdl.event.get():
        if event.type == 'KEYDOWN':
            user_input = event
            keypress = True
        if event.type == 'MOUSEMOTION':
            mouse_coord = event.cell
 
    if not keypress:
        return 'didnt-take-turn' #TODO: Add to tutorial
 
    if user_input.key == 'ENTER' and user_input.alt:
        #Alt+Enter: toggle fullscreen
        tdl.set_fullscreen(not tdl.get_fullscreen())
 
    elif user_input.key == 'ESCAPE':
        return 'exit'  #exit game
 
    if game_state == 'playing':
        #movement keys
        #up left
        if user_input.key == 'KP7':
            player_move_or_attack(-1, -1)
        #up
        elif user_input.key == 'UP' or user_input.key == 'KP8':
            player_move_or_attack(0, -1)
        #up right
        elif user_input.key == 'KP9':
            player_move_or_attack(1, -1)
        #left
        elif user_input.key == 'LEFT' or user_input.key == 'KP4':
            player_move_or_attack(-1, 0)
        #right
        elif user_input.key == 'RIGHT' or user_input.key == 'KP6':
            player_move_or_attack(1, 0)
        #down left
        if user_input.key == 'KP1':
            player_move_or_attack(-1, 1)
        #down
        elif user_input.key == 'DOWN' or user_input.key == 'KP2':
            player_move_or_attack(0, 1)
        #down right
        elif user_input.key == 'KP3':
            player_move_or_attack(1, 1)
        # Rest for 1 turn
        elif user_input.key == 'KP5':
            player_wait()
        else:
            #test for other keys
            if user_input.text == 'g':
                #pick up an item
                for obj in objects:  #look for an item in the player's tile
                    if obj.x == player.x and obj.y == player.y and obj.item:
                        obj.item.pick_up()
                        break
 
            if user_input.text == 'i':
                #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Press the key next to an item to ' +
                                             'use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()
 
            if user_input.text == 'd':
                #show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to' + 
                'drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop()
 
            return 'didnt-take-turn'
 
def player_death(player):
    #the game ended!
    global game_state
    message('You died!', colors.red)
    game_state = 'dead'
 
    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = colors.dark_red
 
def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message(monster.name.capitalize() + ' is dead!', colors.orange)
    monster.char = '%'
    monster.color = colors.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()
 
def target_tile(max_range=None):
    #return the position of a tile left-clicked in player's FOV (optionally in 
    #a range), or (None,None) if right-clicked.
    global mouse_coord
    while True:
        #render the screen. this erases the inventory and shows the names of
        #objects under the mouse.
        tdl.flush()
 
        clicked = False
        for event in tdl.event.get():
            if event.type == 'MOUSEMOTION':
                mouse_coord = event.cell
            if event.type == 'MOUSEDOWN' and event.button == 'LEFT':
                clicked = True
            elif ((event.type == 'MOUSEDOWN' and event.button == 'RIGHT') or 
                  (event.type == 'KEYDOWN' and event.key == 'ESCAPE')):
                return (None, None)
        render_all()
 
        #accept the target if the player clicked in FOV, and in case a range is 
        #specified, if it's in that range
        x = mouse_coord[0]
        y = mouse_coord[1]
        if (clicked and mouse_coord in visible_tiles and
            (max_range is None or player.distance(x, y) <= max_range)):
            return mouse_coord
 
def target_monster(max_range=None):
    #returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  #player cancelled
            return None
 
        #return the first clicked monster, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj
 
def closest_monster(max_range):
    #find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  #start with (slightly more than) maximum range
 
    for obj in objects:
        if obj.fighter and not obj == player and (obj.x, obj.y) in visible_tiles:
            #calculate distance between this object and the player
            dist = player.distance_to(obj)
            if dist < closest_dist:  #it's closer, so remember it
                closest_enemy = obj
                closest_dist = dist
    return closest_enemy
 
def cast_heal():
    #heal the player
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', colors.red)
        return 'cancelled'
 
    message('Your wounds start to feel better!', colors.light_violet)
    player.fighter.heal(HEAL_AMOUNT)
 
def cast_lightning():
    #find closest enemy (inside a maximum range) and damage it
    monster = closest_monster(LIGHTNING_RANGE)
    if monster is None:  #no enemy found within maximum range
        message('No enemy is close enough to strike.', colors.red)
        return 'cancelled'
 
    #zap it!
    message('A lighting bolt strikes the ' + monster.name + ' with a loud ' +
            'thunder! The damage is ' + str(LIGHTNING_DAMAGE) + ' hit points.', 
            colors.light_blue)
 
    monster.fighter.take_damage(LIGHTNING_DAMAGE)
 
def cast_confuse():
    #ask the player for a target to confuse
    message('Left-click an enemy to confuse it, or right-click to cancel.', 
            colors.light_cyan)
    monster = target_monster(CONFUSE_RANGE)
    if monster is None:
        message('Cancelled')
        return 'cancelled'
 
    #replace the monster's AI with a "confused" one; after some turns it will 
    #restore the old AI
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster  #tell the new component who owns it
    message('The eyes of the ' + monster.name + ' look vacant, as he starts to ' +
            'stumble around!', colors.light_green)
 
def cast_fireball():
    #ask the player for a target tile to throw a fireball at
    message('Left-click a target tile for the fireball, or right-click to ' +
            'cancel.', colors.light_cyan)
 
    (x, y) = target_tile()
    if x is None: 
        message('Cancelled')
        return 'cancelled'
    message('The fireball explodes, burning everything within ' + 
            str(FIREBALL_RADIUS) + ' tiles!', colors.orange)
 
    for obj in objects:  #damage every fighter in range, including the player
        if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burned for ' + 
                    str(FIREBALL_DAMAGE) + ' hit points.', colors.orange)
 
            obj.fighter.take_damage(FIREBALL_DAMAGE)
 
def save_game():
    #open a new empty shelve (possibly overwriting an old one) to write the game data
    with shelve.open('savegame', 'n') as savefile:
        savefile['my_map'] = my_map
        savefile['objects'] = objects
        savefile['player_index'] = objects.index(player)  #index of player in objects list
        savefile['inventory'] = inventory
        savefile['game_msgs'] = game_msgs
        savefile['game_state'] = game_state
 
 
def load_game():
    #open the previously saved shelve and load the game data
    global my_map, objects, player, inventory, game_msgs, game_state
 
    with shelve.open('savegame', 'r') as savefile:
        my_map = savefile['my_map']
        objects = savefile['objects']
        player = objects[savefile['player_index']]  #get index of player in objects list and access it
        inventory = savefile['inventory']
        game_msgs = savefile['game_msgs']
        game_state = savefile['game_state']
 
def new_game():
    global player, inventory, game_msgs, game_state
 
    #create object representing the player
    fighter_component = Fighter(hp=30, defense=2, power=5, 
                                death_function=player_death)
 
    player = GameObject(0, 0, '@', 'player', colors.white, blocks=True, 
                    fighter=fighter_component)
 
    #generate map (at this point it's not drawn to the screen)
    make_map()
 
    game_state = 'playing'
    inventory = []
 
    #create the list of game messages and their colors, starts empty
    game_msgs = []
 
    #a warm welcoming message!
    message('Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.', colors.red)
 
def play_game():
    global mouse_coord, fov_recompute
 
    player_action = None
    mouse_coord = (0, 0)
    fov_recompute = True
    con.clear() #unexplored areas start black (which is the default background color)
 
    while not tdl.event.is_window_closed():
 
        #draw all objects in the list
        render_all()
        tdl.flush()
 
        #erase all objects at their old locations, before they move
        for obj in objects:
            obj.clear()
 
        #handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break
 
        #let monsters take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for obj in objects:
                if obj.ai:
                    obj.ai.take_turn()
 
def main_menu():
    img = image_load('menu_background.png')
 
    while not tdl.event.is_window_closed():
        #show the background image, at twice the regular console resolution
        img.blit_2x(root, 0, 0)
 
        #show the game's title, and some credits!
        title = 'TOMBS OF THE ANCIENT KINGS'
        center = (SCREEN_WIDTH - len(title)) // 2
        root.draw_str(center, SCREEN_HEIGHT//2-4, title, bg=None, fg=colors.light_yellow)
 
        title = 'By Jotaf'
        center = (SCREEN_WIDTH - len(title)) // 2
        root.draw_str(center, SCREEN_HEIGHT-2, title, bg=None, fg=colors.light_yellow)
 
        #show options and wait for the player's choice
        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
 
        if choice == 0:  #new game
            new_game()
            play_game()
        if choice == 1:  #load last game
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
                continue
            play_game()
        elif choice == 2:  #quit
            break
 
 
tdl.set_font('arial10x10.png', greyscale=True, altLayout=True)
root = tdl.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Roguelike", 
                fullscreen=False)
tdl.setFPS(LIMIT_FPS)
con = tdl.Console(MAP_WIDTH, MAP_HEIGHT)
panel = tdl.Console(SCREEN_WIDTH, PANEL_HEIGHT)
 
main_menu()