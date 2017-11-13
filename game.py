#!/usr/bin/env python3
# This game started from the excellent python roguelike tutorial at: http://www.roguebasin.com/index.php?title=Roguelike_Tutorial,_using_python3%2Btdl #

import tdl
import tcod

import textwrap
import shelve

import constants
import dungeon
import colors
import controls

import time

from strutil import strleft
from strutil import format_list
import strutil

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

"""
Describes the intent of player keypress captured
"""
class TurnEvent:
    # information about what transpired while resolving player input (did a turn pass?)
    def __init__(self, turns_used, description = '', move_x = 0, move_y = 0, attacked=False):
        self.turns_used = turns_used
        self.description = description
        self.move_x = move_x
        self.move_y = move_y
        self.attacked = attacked

"""
Runs game loop, menus, targeting
"""
class Game:
    def __init__(self):
        self.map_console = None
        self.root_console = None
        self.message_panel = None
        self.status_panel = None        
        
        self.state = None
        self.dungeon = None
        self.messages = []
        self.timestamps = []
        
        self.mouse_coord = None
        
        self.total_time = time.process_time()
        self.last_command = None
        self.last_command_time = -999
        
        self.menu_invoked = False
        
        # map x,y tile of camera position (should center on player)
        self.camera_x = 0
        self.camera_y = 0
    
    ### SAVE AND LOAD GAME ###
    def save_game(self):
        
        if self.dungeon and self.dungeon.player and not self.dungeon.player.fighter.died and self.dungeon.player.fighter.hp > 0:
        
            # clear dungeon reference from objects (we re-set upon load)
            for obj in self.dungeon.objects:
                obj.dungeon = None
            
            #open a new empty shelve (possibly overwriting an old one) to write the game data
            with shelve.open('savegame', 'n') as savefile:
                savefile['map'] = self.dungeon.map
                savefile['objects'] = self.dungeon.objects
                savefile['player_index'] = self.dungeon.objects.index(self.dungeon.player)  #index of player in objects list
                savefile['inventory'] = self.dungeon.inventory
                savefile['messages'] = self.messages
                savefile['timestamps'] = self.timestamps
                savefile['turn'] = self.dungeon.turn
                savefile['start_time'] = self.dungeon.start_time
                savefile['generator'] = self.dungeon.generator
        else:
            logging.info("Dead: clearing save file...")
            shelf = shelve.open('savegame', flag='n') # clears the file by opening a new empty one
            
            logging.info("Shelf contents: %s", shelf)
            shelf.close()
    
    def savegame_exists(self):
        try:
            savefile = shelve.open('savegame', 'r')
            if savefile:
                    savefile.close()
                    return True
            return False
        except:
            return False
     
    def load_game(self):
        #open the previously saved shelve and load the game data
        
        self.root_console.clear()
        
        if self.dungeon:
            del self.dungeon
        
        self.dungeon = dungeon.Dungeon(self)
        self.fov_recompute = True
        
        logging.debug('Before Loading: %s, %s, %s', self.dungeon.inventory, self.dungeon.player, self.dungeon.map)
        try:
            with shelve.open('savegame', 'r') as savefile:
                if savefile:
                    self.dungeon.map = savefile['map']
                    self.dungeon.objects = savefile['objects']
                    self.dungeon.player = self.dungeon.objects[savefile['player_index']]  #get index of player in objects list and access it
                    self.dungeon.inventory = savefile['inventory']
                    self.messages = savefile['messages']
                    self.timestamps = savefile['timestamps']
                    self.dungeon.turn = savefile['turn']
                    self.dungeon.start_time = savefile['start_time']
                    self.dungeon.generator = savefile['generator']
                    if self.dungeon.player.fighter.hp > 0:
                        self.state = constants.STATE_PLAYING
                    else:
                        self.state = constants.STATE_DEAD
                        self.dungeon.player.fighter.died = True
                    # set dungeon reference
                    for obj in self.dungeon.objects:
                        obj.dungeon = self.dungeon
                        
                    # fix time
                    self.dungeon.calc_date_time()
                    
                    # fix enemy count
                    self.dungeon.count_enemies()
                    
                    logging.debug('After Loading: %s, %s, %s', self.dungeon.inventory, self.dungeon.player, self.dungeon.map)
                    return True
                else:
                    return False
        except:
            return False
     
    ### NEW GAME ###
    def new_game(self):
        
        if self.dungeon:
            self.map_console.clear()
            del self.dungeon
            
        self.root_console.clear()
        tdl.flush()
            
        self.fov_recompute = True
        
        self.dungeon = dungeon.Dungeon(self)
     
        #generate map (at this point it's not drawn to the screen)
        self.dungeon.create_player()
        self.dungeon.make_map()
     
        self.state = constants.STATE_PLAYING
     
        #create the list of game messages and their colors, starts empty
        if self.messages:
            del self.messages
        self.messages = []
        
        #a warm welcoming message!
        msg = 'You sneak into Heorot, home of Beowulf and his men... Tonight they all must die!'
        self.message(msg, colors.light_flame)
     
    ### MAIN LOOP ###
    def play_game(self):
     
        action = None
        self.mouse_coord = (0, 0)
        self.last_command_time = 0
        
        while not tdl.event.is_window_closed():
            action = None
     
            #draw all objects in the list
            if self.dungeon:
                self.render_all()
                tdl.flush()
                self.clear_obj_render()
                            
            while not(action):
                #poll user input
                action = self.handle_keys()
                #get time
                newtime = time.process_time()
                # set total time
                self.total_time = newtime
                #avoid multi key presses
                if action and not(action.description == constants.MOUSE_MOVED):
                    delta = newtime - self.last_command_time
                    if delta < constants.INPUT_REPEAT_DELAY:
                        action = None
                    self.last_command_time = newtime
                
            
            if not action:
                desc = 'None'
            else:
                desc = action.description
                
                if self.state == constants.STATE_PLAYING:
                    #avoid numpad's numlock-on multi key press sending 2 keys to repeat the action
                    moved = desc in [constants.MOVE_1, constants.MOVE_2, constants.MOVE_3, constants.MOVE_4, 
                        constants.MOVE_6, constants.MOVE_7, constants.MOVE_8, constants.MOVE_9]
                    if moved or desc in [constants.PICK_UP, constants.DROP, constants.INVENTORY, constants.WAIT]:
                        picked_up = False
                        # evaluate delayed actions (selection screens mostly)
                        if moved:
                            self.do_move(action)
                        elif desc == constants.DROP:
                            self.do_drop(action)
                        elif desc == constants.PICK_UP:
                            picked_up = self.do_pickup(action)
                        elif desc == constants.INVENTORY:
                            self.do_inventory_use(action)
                        elif desc == constants.WAIT:
                            self.dungeon.player_wait()
                            
                        #report item names on tile if applicable
                        if moved or picked_up:
                            names = self.get_item_names_at(self.dungeon.player.x, self.dungeon.player.y)
                            if names:
                                text = format_list(names)
                                self.message('You see: ' + text + '. Press g to take.')
                        
                        #let monsters take their turn: during play state, when a turn has passed
                        if action.turns_used > 0:
                            self.dungeon.ai_act(action.turns_used)
                    
                #exit if player pressed exit
                elif self.state == constants.STATE_EXIT:
                    self.save_game()
                    break
                    
               
     
    ### MAIN MENU ###
    def main_menu(self):
        
        img = tcod.image_load(constants.MENU_BACKGROUND)
        img_x = round((((constants.SCREEN_WIDTH * constants.TILE_SIZE)/2) - img.width) / 2 / constants.TILE_SIZE)
        img_y = 0
        
        title = constants.TITLE
        
        title_console = tdl.Console(len(title)+2, 3)
        
        title_center = (title_console.width - len(title)) // 2
        
        author = 'By ' + constants.AUTHOR
        author_center = (title_console.width - len(author)) // 2
        
        tconsole_x = (constants.SCREEN_WIDTH - title_console.width) // 2
        tconsole_y = 4
     
        while not tdl.event.is_window_closed():
        
            self.clear_all()
        
            #show the title image
            
            #img.blit(self.root_console, xcenter, ycenter, tcod.BKGND_SET, 0.25, 0.25, 0)
            #img.blit_2x(self.root_console, img_x, img_y)
            img.blit(self.root_console, constants.SCREEN_WIDTH//2, constants.SCREEN_HEIGHT//2, tcod.BKGND_SET, 0.5, 0.5, 0)
            
            #show the game's title, and some credits!
            title_console.draw_str(title_center, 0, title, bg=None, fg=colors.dark_yellow)
            title_console.draw_str(author_center, 2, author, bg=None, fg=colors.darker_green)
            self.root_console.blit(title_console, tconsole_x, tconsole_y, title_console.width, title_console.height, 0, 0, fg_alpha=1.0, bg_alpha=0.7)
            
            tdl.flush()
     
            #show options and wait for the player's choice
            
            save_exists = self.savegame_exists()
            PLAY = 0
            if save_exists:
                LOAD = 1
                EXIT = 2
                choice = self.menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
            else:
                LOAD = -999999
                EXIT = 1
                choice = self.menu('', ['Play a new game', 'Quit'], 24)            
     
            if choice == PLAY:
                self.new_game()
                self.play_game()
            elif choice == LOAD:
                if self.load_game():
                    self.play_game()
                else:
                    self.root_console.clear()
                    c = self.menu('No saved game to load!', ['Start new game', 'Quit'], 24)
                    logging.debug('Chose %s', c)
                    if c == 0:
                        self.new_game()
                        self.play_game()
                    elif c == 1:
                        logging.info('Player quit.')
                        return
            elif choice == EXIT:
                self.clear_all()
                tdl.flush()
                logging.info('Player quit.')
                break
                
    def clear_all(self):
        self.map_console.clear()
        self.root_console.clear()
        self.message_panel.clear()
        self.status_panel.clear()
        self.fov_recompute = True

    ### LAUNCH GAME ###
    def game_start(self):

        #tdl.set_font('arial10x10.png', greyscale=True, altLayout=True)
        tdl.set_font('terminal16x16.png', greyscale=False)
        self.root_console = tdl.init(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT, title="Grendel", 
                        fullscreen=False)
        self.map_console = tdl.Console(constants.CAMERA_WIDTH, constants.CAMERA_HEIGHT)
        self.message_panel = tdl.Console(constants.MSG_PANEL_WIDTH, constants.MSG_PANEL_HEIGHT)
        self.status_panel = tdl.Console(constants.STAT_PANEL_WIDTH, constants.STAT_PANEL_HEIGHT)
        
        tdl.setFPS(constants.LIMIT_FPS)
        
        ### start main menu ###
        self.main_menu()
        
        
    ### MESSAGES LOG ###
    def message(self, new_msg, color = colors.white):
        #timestamps list
        tstamp = '[' + self.dungeon.time_string + '] '
        stamplen = len(tstamp)
        
        #split the message if necessary, among multiple lines
        # wrap text without timestamp, account for timestamp spacing...
        new_msg_lines = textwrap.wrap(new_msg, constants.MSG_PANEL_WIDTH - stamplen)
        height = len(new_msg_lines)
        
        #remove entries if necessary
        remove = (len(self.messages) + height) - (constants.MSG_PANEL_HEIGHT - 1)
        while remove > 0:
            self.timestamps.pop()
            self.messages.pop()
            remove -= 1
        
        #add new entries to top
        for i in range(height):
            if i == (height-1):
                stamp = tstamp
            else:
                stamp = ' ' * stamplen
            self.timestamps.insert(0, stamp)
            self.messages.insert(0, (new_msg_lines[height-i-1],color))
            
            
    ### POP UP ###
    def msgbox(self, text, width=50, tcolor=colors.white, map_window=False, sleeptime=None):
            self.menu(text, [], width, map_window, tcolor=tcolor, sleeptime=sleeptime)  #use menu() as a sort of "message box"
        
        
    ### MENU WITH INPUT ###
    def menu(self, header, options, width, map_window=False, tcolor=colors.white, sleeptime=None):
        if len(options) > 26:
            raise ValueError ('Cannot have a menu with more than 26 options.')
     
        #calculate total height for the header (after textwrap) and one line per option
        header_wrapped = textwrap.wrap(header, width)
        header_height = len(header_wrapped)
        if header == '':
            header_height = 0
        height = len(options) + header_height + 2
     
        #create an off-screen console that represents the menu's window
 
        window = tdl.Console(width, height)
     
        #print the header, with wrapped text
        window.draw_rect(0, 1, width, height, None, fg=tcolor, bg=None)
        for i, line in enumerate(header_wrapped):
            window.draw_str(0, 1+i, header_wrapped[i], fg=tcolor)
     
        #print all the options
        y = header_height + 1
        letter_index = ord('a')
        c2 = (colors.lightest_grey, colors.lighter_grey)
        for idx, option_text in enumerate(options):
            text = '(' + chr(letter_index) + ') ' + option_text
            if idx % 2 == 0:
                c = c2[0]
            else:
                c = c2[1]
            window.draw_str(0, y, text, fg=c, bg=None)
            y += 1
            letter_index += 1
     
        #blit the contents of "window" to...
        # top of dungeon map window
        if map_window:
            x = constants.STAT_PANEL_WIDTH+1
            y = 0
        # center of screen
        else:
            x = constants.SCREEN_WIDTH//2 - width//2
            y = constants.SCREEN_HEIGHT//2 - height//2
            
        self.root_console.blit(window, x, y, width, height, 0, 0, fg_alpha=1.0, bg_alpha=0.7)
     
        #present the root_console console to the player and wait for a key-press
        tdl.flush()
        
        if sleeptime:
            time.sleep(sleeptime)
        
        # mark as having brought up a menu (ignore this input event after processing here)
        self.menu_invoked = True
        
        key = tdl.event.key_wait()
        key_char = key.char
        if key_char == '':
            key_char = ' ' # placeholder
     
        if key.key == 'ENTER' and key.alt:
            #Alt+Enter: toggle fullscreen
            tdl.set_fullscreen(not tdl.get_fullscreen())
     
        #convert the ASCII code to an index; if it corresponds to an option, return it
        index = ord(key_char) - ord('a')
        logging.debug('Pressed key %s, index %s', key.char, index)
        
        # clear menu window in dungeon
        if self.dungeon:
            self.map_console.clear()
            self.render_all()
            tdl.flush()
        
        if index >= 0 and index < len(options):
            return index
        return None

        
    ### INVENTORY ###
    def inventory_menu(self, header="Press an item's key to eat it, or any other to cancel.\n"):
        #show a menu with each item of the inventory as an option
        if len(self.dungeon.inventory) == 0:
            options = ['No items.  Kill more men!']
        else:
            d = self.dungeon.get_inv_item_dict()
            keys = list(d.keys())
            options = keys
        
        # bring up menu
        index = self.menu(header, options, constants.CAMERA_WIDTH - 2, map_window=True)
        logging.info('Inventory: chose index %s', index)
        
        #exit early if invalid choice or no inventory
        if index is None or len(self.dungeon.inventory) == 0:
            logging.info('Inv index: %s, inventory len: %s', index, len(self.dungeon.inventory))
            return None
            
        item = d[keys[index]]
        del d
        
        logging.info('Inv item chosen: %s', item)
        return item

        
    ### Camera ###
    def to_camera_coordinates(self, x, y):
        #convert coordinates on the map to coordinates on the screen
        (x, y) = (int(x - self.camera_x), int(y - self.camera_y))
 
        if (x < 0 or y < 0 or x >= constants.CAMERA_WIDTH or y >= constants.CAMERA_HEIGHT):
                return (None, None)  #if it's outside the view, return nothing
 
        return (x, y)
        
    def move_camera(self, target_x, target_y):
 
        #new camera coordinates (top-left corner of the screen relative to the map)
        x = round(target_x - ((constants.CAMERA_WIDTH) / 2))  #coordinates so that the target is at the center of the screen
        y = round(target_y - ((constants.CAMERA_HEIGHT) / 2))
 
        #make sure the camera doesn't see outside the map
        if x < -1: x = -1
        if y < -1: y = -1
        if x > constants.MAP_WIDTH - constants.CAMERA_WIDTH + 1: x = constants.MAP_WIDTH - constants.CAMERA_WIDTH + 1
        if y > constants.MAP_HEIGHT - constants.CAMERA_HEIGHT + 1: y = constants.MAP_HEIGHT - constants.CAMERA_HEIGHT + 1
 
        if x != self.camera_x or y != self.camera_y: self.fov_recompute = True
        (self.camera_x, self.camera_y) = (x, y)
        
    
    ### TARGETING ###
    def target_tile(self, max_range=None, target_size=0):
        #return the position of a tile left-clicked in player's FOV (optionally in 
        #a range), or (None,None) if right-clicked.
        
        # rendering background
        self.render_all()
        tdl.flush()
        
        last_coord = (-999,-999)
        
        while True:
            
            clicked = False
            for event in tdl.event.get():
                if event.type == 'MOUSEMOTION':
                    self.mouse_coord = event.cell
                if event.type == 'MOUSEDOWN' and event.button == 'LEFT':
                    clicked = True
                elif ((event.type == 'MOUSEDOWN' and event.button == 'RIGHT') or 
                      (event.type == 'KEYDOWN' and event.key == 'ESCAPE')):
                    return (None, None)
            
            #accept the target if the player clicked in FOV, and in case a range is 
            #specified, if it's in that range
            x = self.mouse_coord[0] + self.camera_x
            y = self.mouse_coord[1] + self.camera_y
            
            #update targeting area
            if (x,y) != last_coord or clicked:
            
                self.render_all()
                
                logging.debug('(%s,%s) mouse move', x, y)
                # set last value 
                last_coord = self.mouse_coord
                if (x,y) in self.dungeon.visible_tiles:
                    # render new target area
                    if not(self.dungeon.map[x][y].blocked) and (not(max_range) or (self.dungeon.distance(self.dungeon.player.x, self.dungeon.player.y, x, y) <= max_range)):
                        self.map_console.draw_char(x, y, None, fg=None, bg=constants.color_target)
                        logging.debug('drew to %s',last_coord)
                        if target_size > 0:
                            #target on map
                            target = tdl.map.quickFOV(x, y, self.dungeon.is_visible_tile,
                                                         fov=constants.FOV_BASIC,
                                                         radius=target_size,
                                                         lightWalls=False)
                            for tile in target:
                                if not self.dungeon.map[tile[0]][tile[1]].blocked and tile in self.dungeon.visible_tiles:
                                    self.map_console.draw_char(tile[0], tile[1], None, fg=None, bg=constants.color_target)
            
            # rendering background (overwrite previous target squares)
            self.root_console.blit(self.map_console, 0, 0, constants.MAP_WIDTH, constants.MAP_HEIGHT, 0, 0)
            tdl.flush()
            
            if (clicked and self.mouse_coord in self.dungeon.visible_tiles and
                (max_range is None or self.dungeon.distance(player.x, player.y, x, y) <= max_range)):
                self.fov_recompute = True
                return self.mouse_coord
 
    def get_obj_names_under_mouse(self):
        #return a string with the names of all objects under the mouse
        if self.mouse_coord:
            x = self.mouse_coord[0] - constants.CAMERA_PANEL_X + self.camera_x
            y = self.mouse_coord[1] - constants.CAMERA_PANEL_Y  + self.camera_y
            return self.get_obj_names_at(x, y)
        else:
            return None
        
    def get_obj_names_at(self, x, y, use_article=False):
        #create a list with the names of all objects at the mouse's coordinates and in FOV
        names = [obj.name for obj in self.dungeon.objects if (obj.x, obj.y) == (x,y) and (obj.x, obj.y) in self.dungeon.visible_tiles]
        # if names:
            # logging.info(str(names))
        names = ', '.join(names)  #join the names, separated by commas
        if use_article:
            article = strutil.get_article(names)
            if article:
                return article + ' ' + names
        return names
        
    def get_items_at(self, x, y):
        return [obj.item for obj in self.dungeon.objects if (obj.x, obj.y) == (x,y) and obj.item and not(obj.fighter)]
        
    def get_item_names_at(self, x, y):
        #create a list with the names of all Items at the mouse's coordinates and in FOV
        items = self.get_items_at(x, y)
        if len(items) > 0:
            names = [itm.name() for itm in items]
            return names
        else:
            return None
            
    def sort_obj_at(self, x, y):
        junk = []
        items = []
        ftrs = []
        
        for obj in self.dungeon.objects:
            if (obj.x, obj.y) == (x,y):
                if obj.fighter:
                    ftrs.append(obj)
                elif obj.item:
                    items.append(obj)
                else:
                    junk.append(obj)
        # send to back in reverse order to sort
        for f in ftrs:
            self.dungeon.send_to_back(f)
        for i in items:
            self.dungeon.send_to_back(i)
        for j in junk:
            self.dungeon.send_to_back(j)
            
        
    def target_monster(self, max_range=None):
        #returns a clicked monster inside FOV up to a range, or None if right-clicked
        while True:
            (x, y) = self.target_tile(max_range)
            if x is None:  #player cancelled
                return None
     
            #return the first clicked monster, otherwise continue looping
            for obj in self.dungeon.objects:
                if obj.x == x and obj.y == y and obj.fighter and obj != self.dungeon.player:
                    return obj
 
    
    ### PLAYER INPUT ###
    def handle_keys(self):
        
        for event in tdl.event.get():
            
            keydown = False
            mousemove = False
        
            if event.type == 'KEYDOWN':
                user_input = event
                keydown = True
                logging.info('Key Down detected!')
            elif event.type == 'MOUSEMOTION':
                if event.cell != self.mouse_coord:
                    mousemove = True
                    self.mouse_coord = event.cell
                    logging.debug("Mouse coord: %s", self.mouse_coord)
            if not (keydown):
                if mousemove:
                    return TurnEvent(0, description=constants.MOUSE_MOVED)
                return
            
            if user_input.key == 'ENTER' and user_input.alt:
                #Alt+Enter: toggle fullscreen
                tdl.set_fullscreen(not tdl.get_fullscreen())
                return TurnEvent(0, 'Full screen toggle')
            elif user_input.key == 'ESCAPE':
                self.exit_game()
                self.clear_all()
                tdl.flush()
                return TurnEvent(0, 'exiting')  #exit game
                
            if self.state == constants.STATE_PLAYING and not(self.dungeon.player.fighter.died):
            
                # ignore menu input carrying through
                if self.menu_invoked:
                    self.menu_invoked = False
                    return
            
                logging.debug('Turn %s: Pressed key %s , text %s', self.dungeon.turn, user_input.key, user_input.text)
                
                #movement keys
                #up left
                if controls.up_left(user_input):
                    return TurnEvent(0, move_x=-1, move_y=-1, description=constants.MOVE_7)
                #up
                elif controls.up(user_input):
                    return TurnEvent(0, move_x=-0, move_y=-1, description=constants.MOVE_8)
                #up right
                elif controls.up_right(user_input):
                    return TurnEvent(0, move_x=1, move_y=-1, description=constants.MOVE_9)
                #left
                elif controls.left(user_input):
                    return TurnEvent(0, move_x=-1, move_y=0, description=constants.MOVE_4)
                #right
                elif controls.right(user_input):
                    return TurnEvent(0, move_x=1, move_y=0, description=constants.MOVE_6)
                #down left
                elif controls.down_left(user_input):
                    return TurnEvent(0, move_x=-1, move_y=1, description=constants.MOVE_1)
                #down
                elif controls.down(user_input):
                    return TurnEvent(0, move_x=0, move_y=1, description=constants.MOVE_2)
                #down right
                elif controls.down_right(user_input):
                    return TurnEvent(0, move_x=1, move_y=1, description=constants.MOVE_3)
                # Rest for 1 turn
                elif controls.wait(user_input):
                    return TurnEvent(self.dungeon.player.fighter.speed, constants.WAIT)
                # drop an item show the inventory; if an item is selected, drop it
                elif controls.drop(user_input):
                    return TurnEvent(0, constants.DROP)
                # pick up an item
                elif controls.pick_up(user_input):
                    return TurnEvent(0, constants.PICK_UP)
                # inventory
                elif controls.inventory(user_input):
                    #show the inventory; if an item is selected, use it
                    return TurnEvent(0, constants.INVENTORY)
                else:
                    return #invalid key: didnt-take-turn
                
        return #game not in Playing state or action cancelled
        
        
        
    def do_drop(self, turn_action):
        chosen_item = self.inventory_menu('Press the key next to an item to' + 
        'drop it, or any other to cancel.\n')
        if chosen_item is not None:
            chosen_item.drop(self.dungeon.player)
            turn_action.turns_used = self.dungeon.player.fighter.speed
            
    def do_pickup(self, turn_action):
        #pick up items here
        found = []
        for obj in self.dungeon.objects:  #look for any items in player's tile
            if obj.x == self.dungeon.player.x and obj.y == self.dungeon.player.y and obj.item:
                logging.info('Pickup SUCCESS: %s at %s', obj.name, (obj.x, obj.y))
                found.append(obj)
                
        if len(found) < 1:
            return False
        
        turn_action.turns_used = self.dungeon.player.fighter.speed
        self.dungeon.pick_up(found)
                
        return True
                
    def do_inventory_use(self, turn_action):
        chosen_item = self.inventory_menu()
        if chosen_item:
            if chosen_item.use():
                turn_action.turns_used = self.dungeon.player.fighter.speed
        
    def do_move(self, turn_action):
        turn_action.turns_used = self.dungeon.player_move_or_attack(turn_action.move_x, turn_action.move_y)
    
    ### RENDERING ###
    def render_bar(self, x, y, total_width, name, value, minimum, maximum, bar_color, back_color):
        #render a bar (HP, experience, etc). first calculate the width of the bar
        bar_width = int((float(value)-minimum) / maximum * total_width)
     
        #render the background first
        self.status_panel.draw_rect(x, y, total_width, 1, None, bg=back_color)
     
        #now render the bar on top
        if bar_width > 0:
            self.status_panel.draw_rect(x, y, bar_width, 1, None, bg=bar_color)
     
        #finally, some centered text with the values
        text = name + ': ' + str(value) + '/' + str(maximum)
        x_centered = x + (total_width-len(text))//2
        self.status_panel.draw_str(x_centered, y, text, fg=colors.white, bg=None)
        
        
    def render_stat_bar(self, x, y, total_width, name, diff_value, bonus_amt):
        
        #render the background first
        #self.status_panel.draw_rect(x, y, total_width, 1, None, bg=colors.darkest_yellow)
        
        # determine color and text displaying bonus/penalty
        c = None
        t = None
        t, c = make_mod_text_color(diff_value)
        
        x_offset_pos = x + 7
        
        # calc bar width
        raw_value = round(abs(diff_value) / bonus_amt,2)
        bar_width = min(int(raw_value), total_width)
        
        # stat bar
        if diff_value != 0:
            bar_width = max(1,bar_width)
            if diff_value > 0:
                self.status_panel.draw_rect(x_offset_pos, y, bar_width, 1, None, bg=colors.darker_green)
            elif diff_value < 0:
                self.status_panel.draw_rect(x_offset_pos, y, bar_width, 1, None, bg=colors.darker_red)
     
        #text with the value
        #pos
        x_offset_pos = x + total_width - 5
        #string
        t = str(raw_value)
        s = '+'
        if diff_value < 0:
            s = '-'
        t = s+t
        # stat name
        self.status_panel.draw_str(x, y, name, fg=colors.white, bg=None)
        # modifier
        self.status_panel.draw_str(x_offset_pos, y, t, fg=colors.white, bg=None)
        
     
     
    def render_all(self):
        logging.debug('render_all')
        
        if  not self.dungeon:
            return
        
        # adjust camera
        self.move_camera(self.dungeon.player.x, self.dungeon.player.y)
        
        # recompute fov if required
        if self.fov_recompute:
            self.fov_recompute = False
            self.dungeon.visible_tiles = tdl.map.quickFOV(self.dungeon.player.x, self.dungeon.player.y,
                                             self.dungeon.is_visible_tile,
                                             fov=constants.FOV_ALGO,
                                             radius=self.dungeon.player.fov,
                                             lightWalls=constants.FOV_LIGHT_WALLS)
        
        # draw frame around map
        self.map_console.draw_frame(0, 0, self.map_console.width, self.map_console.height, string=None, fg=None, bg=constants.color_frame)
        
        #go through all tiles in camera view, and set their background color according to the FOV
        for y in range(1, constants.CAMERA_HEIGHT-1):
            for x in range(1, constants.CAMERA_WIDTH-1):
                map_x, map_y = (self.camera_x + x, self.camera_y + y)
                visible = (map_x, map_y) in self.dungeon.visible_tiles
                wall = self.dungeon.map[map_x][map_y].block_sight
                if not visible:
                    #if it's not visible right now, the player can only see it 
                    #if it's explored
                    if self.dungeon.map[map_x][map_y].explored:
                        if wall:
                            self.map_console.draw_char(x, y, None, fg=None, bg=constants.color_dark_wall)
                        else:
                            self.map_console.draw_char(x, y, None, fg=None, bg=constants.color_dark_ground)
                else:
                    if wall:
                        self.map_console.draw_char(x, y, None, fg=None, bg=constants.color_light_wall)
                    else:
                        self.map_console.draw_char(x, y, None, fg=None, bg=constants.color_light_ground)
                    #since it's visible, explore it
                    self.dungeon.map[map_x][map_y].explored = True
     
        #draw all objects in the list
        for obj in self.dungeon.objects:
            self.draw_obj(obj)
        
        #blit the contents of "self.map_console" to the self.root_console console and present it
        self.root_console.blit(self.map_console, constants.CAMERA_PANEL_X, constants.CAMERA_PANEL_Y, constants.CAMERA_WIDTH, constants.CAMERA_HEIGHT, 0, 0)
        
        # clear map_console before next update
        self.map_console.clear()
     
        #prepare to render the messages
        self.render_messages()
        
        #blit the contents of "self.message_panel" to the self.root_console console
        self.root_console.blit(self.message_panel, constants.MSG_PANEL_X, constants.MSG_PANEL_Y, constants.MSG_PANEL_WIDTH, constants.MSG_PANEL_HEIGHT, 0, 0)
     
        # prepare to render status and hp
        self.render_stats()
        
        #blit the contents of status_panel to root console
        self.root_console.blit(self.status_panel, constants.STAT_PANEL_X, constants.STAT_PANEL_Y, constants.STAT_PANEL_WIDTH, constants.STAT_PANEL_HEIGHT, 0, 0)
        
        
    def render_messages(self):
        self.message_panel.clear(fg=colors.white, bg=colors.black)
        
        #display names of objects under the mouse
        msg = self.get_obj_names_under_mouse()
        if len(msg) > 1:
            self.message_panel.draw_str(0, 0, 'Looking at: ' + msg, bg=None, fg=colors.light_yellow)
         
        #print the game messages, one line at a time
        x = 0
        y = 1
        count = max(len(self.messages),5)
        for i, msg in enumerate(self.messages):
            #get iteration values
            (line, color) = msg
            #calc darkness ratio
            darkness = (y / count)
            
            #draw timestamp
            c = colors.mutate_color(colors.white, colors.darkest_grey, darkness)
            self.message_panel.draw_str(x, y, self.timestamps[i], fg=c)
            
            #draw message line
            c = colors.mutate_color(color, colors.darkest_grey, darkness)
            self.message_panel.draw_str(x+len(self.timestamps[i]), y, line, bg=None, fg=c)
            
            y += 1
    
    
    def render_stats(self):
    
        self.status_panel.clear()
        
        # draw top and bottom 'frame'
        self.status_panel.draw_frame(0, 0, constants.STAT_PANEL_WIDTH, 1, ' ', fg=None, bg=constants.color_frame)
        self.status_panel.draw_frame(0, constants.STAT_PANEL_HEIGHT-1, constants.STAT_PANEL_WIDTH, 1, ' ', fg=None, bg=constants.color_frame)
        
        x = 1
        y = 2
        
        tcolor = colors.green
        
        # time of day (dungeon turn)
        self.drawtitle_stats('Time', y, fgcolor=tcolor)
        # title = 'Time'
        # xpos = (constants.STAT_PANEL_WIDTH - len(title)) // 2
        # self.status_panel.draw_str(xpos, y, title, bg=None, fg=tcolor)
        y += 1
        # day, month, year
        self.status_panel.draw_str(x, y, self.dungeon.date_string, bg=None, fg=colors.light_grey)
        # time
        y += 1
        self.status_panel.draw_str(x, y, self.dungeon.time_string, bg=None, fg=colors.light_grey)
        
        # draw inventory counts
        # get dict of items (name: count)
        item_dict = self.dungeon.get_inv_count_dict()
        y += 4
        self.drawtitle_stats('Inventory', y, fgcolor=tcolor)
        y += 1
        self.drawtitle_stats('(press i to use)', y, fgcolor=colors.dark_grey)
        for k in sorted(item_dict.keys()):
            y += 1
            line = k + ': ' + str(item_dict[k])
            self.status_panel.draw_str(x, y, line, bg=None, fg=colors.light_grey)
        if len(item_dict) < 5:
            y += 5 - len(item_dict)
        
        #show player stats
        y += 2
        self.drawtitle_stats('Grendel', y, fgcolor=tcolor)
        #show player's hp bar
        y += 1
        self.render_bar(x, y, constants.STAT_PANEL_WIDTH-2, 'HP', self.dungeon.player.fighter.hp, 0, self.dungeon.player.fighter.max_hp,
            self.dungeon.player.fighter.get_health_color(), colors.darkest_red)
        
        # show character stats
        pfighter = self.dungeon.player.fighter

        # Strength
        y += 2
        stat = round(pfighter.power,1)
        diff = round(pfighter.power - constants.START_POWER,1)
        self.render_stat_bar(x, y, constants.STAT_PANEL_WIDTH-2, 'Str', diff, constants.POWER_BONUS)
        
        # Toughness
        y += 1
        stat = round(pfighter.defense, 1)
        diff = round(pfighter.defense - constants.START_DEFENSE,1)
        self.render_stat_bar(x, y, constants.STAT_PANEL_WIDTH-2, 'Tough', diff, constants.DEFENSE_BONUS)
        
        # Speed (inverse!)
        # calc display for speed: how many tiles per 1 turn?
        y += 1
        stat =  round(round(1.0 + (1.0 - pfighter.move_speed()),2) * 100.0)
        diff =  stat - round(round(1.0 + (1.0 - constants.START_SPEED),2) * 100)
        self.render_stat_bar(x, y, constants.STAT_PANEL_WIDTH-2, 'Speed', diff, (-constants.SPEED_BONUS * 100))
        
        # Vision
        y += 1
        stat = round(self.dungeon.player.fov,1)
        diff = round(self.dungeon.player.fov - constants.START_VISION,1)
        self.render_stat_bar(x, y, constants.STAT_PANEL_WIDTH-2, 'Vision', diff, constants.VISION_BONUS)
        
        # Visible Enemies #
        # get visible enemies first names...
        enemy_names = [strleft(obj.name, ' the') for obj in self.dungeon.calc_visible_enemies()]
        c = tcolor
        y += 3
        if enemy_names:
            self.drawtitle_stats('Visible Enemies', y, fgcolor=tcolor)
            y += 1
            #self.status_panel.draw_str(x, y, ', '.join(enemy_names), fg=colors.yellow)
            self.drawtitle_stats(', '.join(sorted(enemy_names)), y, fgcolor=colors.yellow)
        else:
            self.drawtitle_stats('Visible Enemies', y, fgcolor=colors.dark_grey)
            y += 1
            
        
        # enemies left!
        y = constants.STAT_PANEL_HEIGHT - 4
        self.drawtitle_stats('Enemies Left', y, fgcolor=tcolor)
        y += 1
        self.drawtitle_stats(str(self.dungeon.enemies_left), y, fgcolor=colors.light_flame)
        
    def drawtitle_stats(self, title, y, fgcolor=colors.white, bgcolor=None):
        # wrap multi line title
        if len(title) > constants.STAT_PANEL_WIDTH - 2:
            lines = textwrap.wrap(title, constants.STAT_PANEL_WIDTH - 2)
            for i, l in enumerate(lines):
                self.drawtitle_stats(l, y+i, fgcolor, bgcolor)
            return
    
        xpos = (constants.STAT_PANEL_WIDTH - len(title)) // 2
        self.status_panel.draw_str(xpos, y, title, fg=fgcolor, bg=bgcolor)
        
        
    def clear_obj_render(self):
        #erase all objects at their old locations, before they move
        for obj in self.dungeon.objects:
            self.draw_clear(obj)
            
    def draw_obj(self, game_obj):
        #only show if it's visible to the player
        if (game_obj.x, game_obj.y) in self.dungeon.visible_tiles:
            cam_x, cam_y = self.to_camera_coordinates(game_obj.x, game_obj.y)
            #draw the character that represents this object at its position
            self.map_console.draw_char(cam_x, cam_y, game_obj.char, game_obj.color, bg=None)
            
    def draw_clear(self, game_obj):
        #erase the character that represents this object
        cam_x, cam_y = self.to_camera_coordinates(game_obj.x, game_obj.y)
        if cam_x or cam_y:
            self.map_console.draw_char(cam_x, cam_y, ' ', game_obj.color, bg=None)
        
    ### Exit Game ###
    def exit_game(self):
        self.state = constants.STATE_EXIT
        
"""
Returns a tuple with (text,color)
"""
def make_mod_text_color(diff):
    note = str(round(diff, 2))
    c = colors.white
    if diff >= 0:
        note = '+'+note
        if diff > 0:
            c = colors.green
    else:
        c = colors.red
        
    return (note), c
    

