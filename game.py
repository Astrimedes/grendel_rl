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

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TurnEvent:
    # information about what transpired while resolving player input (did a turn pass?)
    def __init__(self, turns_used, description = '', move_x = 0, move_y = 0, attacked=False):
        self.turns_used = turns_used
        self.description = description
        self.move_x = move_x
        self.move_y = move_y
        self.attacked = attacked

class Game:
    def __init__(self):
        self.map_console = None
        self.root_console = None
        self.state = None
        self.dungeon = None
        self.messages = []
        self.message_panel = None
        self.mouse_coord = None
        
        self.total_time = time.process_time()
        self.last_command = None
        self.last_command_time = -999
        
        self.menu_invoked = False
    
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
                savefile['turn'] = self.dungeon.turn
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
                    self.dungeon.turn = savefile['turn']
                    if self.dungeon.player.fighter.hp > 0:
                        self.state = constants.STATE_PLAYING
                    else:
                        self.state = constants.STATE_DEAD
                        self.dungeon.player.fighter.died = True
                    # set dungeon reference
                    for obj in self.dungeon.objects:
                        obj.dungeon = self.dungeon
                    
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
            tdl.flush()
            del self.dungeon
            
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
        self.message('You sneak into Heorot, home of Beowulf and his men...', colors.red)
        self.message('Their music and merriment ends tonight - they all must die!', colors.red)
     
    ### MAIN LOOP ###
    def play_game(self):
     
        action = None
        self.mouse_coord = (0, 0)
        
        while not tdl.event.is_window_closed():
            action = None
     
            #draw all objects in the list
            if self.dungeon:
                self.render_all()
                tdl.flush()
                self.clear_obj_render()
                
            #track time
            newtime = time.process_time()
            self.total_time = newtime
            
            #handle keys and exit game if needed
            while not(action):
                action = self.handle_keys()
            
            if not action:
                desc = 'None'
            else:
                desc = action.description
                delta = 100
                
                if self.state == constants.STATE_PLAYING:
                    #avoid numpad's numlock-on multi key press sending 2 keys to repeat the action
                    moved = desc in [constants.MOVE_1, constants.MOVE_2, constants.MOVE_3, constants.MOVE_4, 
                        constants.MOVE_6, constants.MOVE_7, constants.MOVE_8, constants.MOVE_9]
                    if moved or desc in [constants.PICK_UP, constants.DROP, constants.INVENTORY, constants.WAIT]:
                        if desc == self.last_command:
                            delta = newtime - self.last_command_time
                        
                        self.last_command_time = newtime
                        self.last_command = desc
                        if delta < constants.INPUT_REPEAT_DELAY:
                            logging.info('COMMAND %s: delta (%s) < allowed delay (%s)', desc, delta, constants.INPUT_REPEAT_DELAY)
                            time.sleep(constants.INPUT_REPEAT_DELAY)
                            tdl.flush()
                            continue
                        else:
                            logging.info('desc = %s, %s = last_command, %s delta, %s total time', desc, self.last_command, delta, self.total_time)
                    
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
                                self.message('You see items here: ' + names + '. Press g to pick up.')
                        
                        #let monsters take their turn: during play state, when a turn has passed
                        if action.turns_used > 0:
                            self.dungeon.ai_act(action.turns_used)
                            
                            
                        
                
                    logging.debug('play_game, state = %s, action = %s', self.state, desc)
                    
                    logging.debug('%s - action taken', desc)
                    
                #exit if player pressed exit
                elif self.state == constants.STATE_EXIT:
                    self.save_game()
                    break
                    
               
     
    ### MAIN MENU ###
    def main_menu(self):
        
        img = tcod.image_load(constants.MENU_BACKGROUND)
        x = round((((constants.SCREEN_WIDTH * constants.TILE_SIZE)/2) - img.width) / 2 / constants.TILE_SIZE)
        y = 0
     
        while not tdl.event.is_window_closed():
        
            self.clear_all()
        
            #show the title image
            
            #img.blit(self.root_console, xcenter, ycenter, tcod.BKGND_SET, 0.25, 0.25, 0)
            img.blit_2x(self.root_console, x, y)
            
            #show the game's title, and some credits!
            title = constants.TITLE
            center = (constants.SCREEN_WIDTH - len(title)) // 2
            self.root_console.draw_str(center, constants.SCREEN_HEIGHT//2-4, title, bg=None, fg=colors.dark_azure)
            
            title = 'By ' + constants.AUTHOR
            center = (constants.SCREEN_WIDTH - len(title)) // 2
            self.root_console.draw_str(center, constants.SCREEN_HEIGHT-2, 'By Astrimedes', bg=None, fg=colors.dark_azure)
            
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
                    c = self.menu('No saved game to load!', ['Start new game', 'Quit'], 24)
                    logging.debug('Chose %s', c)
                    if c == 0:
                        self.new_game()
                        self.play_game()
                    elif c == 1:
                        logging.info('Player quit.')
                        return
            elif choice == EXIT:
                logging.info('Player quit.')
                break
                
    def clear_all(self):
        self.map_console.clear()
        self.root_console.clear()
        self.message_panel.clear()
        self.fov_recompute = True

    ### LAUNCH GAME ###
    def game_start(self):

        #tdl.set_font('arial10x10.png', greyscale=True, altLayout=True)
        tdl.set_font('terminal16x16.png', greyscale=True)
        self.root_console = tdl.init(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT, title="Roguelike", 
                        fullscreen=False)
        self.map_console = tdl.Console(constants.MAP_WIDTH, constants.MAP_HEIGHT)
        self.message_panel = tdl.Console(constants.SCREEN_WIDTH, constants.PANEL_HEIGHT)
        
        #tdl.setFPS(constants.LIMIT_FPS)
        
        ### start main menu ###
        self.main_menu()
        
        
    ### MESSAGES LOG ###
    def message(self, new_msg, color = colors.white):
        #split the message if necessary, among multiple lines
        new_msg_lines = textwrap.wrap(new_msg, constants.MSG_WIDTH)
     
        for line in new_msg_lines:
            #if the buffer is full, remove the first line to make room for the new one
            if len(self.messages) == constants.MSG_HEIGHT:
                del self.messages[0]
     
            #add the new line as a tuple, with the text and the color
            self.messages.append((line, color))
            
    ### POP UP ###
    def msgbox(self, text, width=50):
        self.menu(text, [], width)  #use menu() as a sort of "message box"
        
        
    ### MENU WITH INPUT ###
    def menu(self, header, options, width):
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
     
        #blit the contents of "window" to the root_console console
        x = constants.SCREEN_WIDTH//2 - width//2
        y = constants.SCREEN_HEIGHT//2 - height//2
        self.root_console.blit(window, x, y, width, height, 0, 0, fg_alpha=1.0, bg_alpha=0.7)
     
        #present the root_console console to the player and wait for a key-press
        tdl.flush()
        
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
    def inventory_menu(self, header='Press the key next to an item to ' +
                                             'use it, or any other to cancel.\n'):
        #show a menu with each item of the inventory as an option
        weapon = self.dungeon.player.weapon()
        if len(self.dungeon.inventory) == 0 and not weapon:
            options = ['Inventory is empty.']
        else:
            options = []
            for item in self.dungeon.inventory:
                if item == weapon:
                    options.append(item.name() + '----[Equipped Weapon]')
                else:
                    options.append(item.name())
     
        index = self.menu(header, options, constants.INVENTORY_WIDTH)
        logging.info('Inventory: chose index %s', index)
        
        #if an item was chosen, return it
        if index is None or len(self.dungeon.inventory) == 0:
            logging.info('Inv index: %s, inventory len: %s', index, len(self.dungeon.inventory))
            return None
            
        logging.info('Inv item chosen: %s', self.dungeon.inventory[index])
        return self.dungeon.inventory[index]

        
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
            x = self.mouse_coord[0]
            y = self.mouse_coord[1]
            
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
        (x, y) = self.mouse_coord
        return self.get_obj_names_at(x, y)
        
    def get_obj_names_at(self, x, y):
        #create a list with the names of all objects at the mouse's coordinates and in FOV
        names = [obj.name for obj in self.dungeon.objects if (obj.x, obj.y) == (x,y) and (obj.x, obj.y) in self.dungeon.visible_tiles]
            
        names = ', '.join(names)  #join the names, separated by commas
        return names.capitalize() 
        
    def get_items_at(self, x, y):
        return [obj.item for obj in self.dungeon.objects if (obj.x, obj.y) == (x,y) and obj.item and not(obj.fighter)]
        
    def get_item_names_at(self, x, y):
        #create a list with the names of all Items at the mouse's coordinates and in FOV
        items = self.get_items_at(x, y)
        hasitems = len(items) > 0
        names = []
        for itm in items:
            if itm:
                hasitems = True
                names.append(itm.name().capitalize())
        if hasitems:
            return ', '.join(names)
        else:
            return None
        
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
        
            if event.type == 'KEYDOWN':
                user_input = event
                keydown = True
                logging.info('Key Down detected!')
            elif event.type == 'MOUSEMOTION':
                self.mouse_coord = event.cell
                logging.debug("Mouse coord: %s", self.mouse_coord)
            if not (keydown):
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
            
                logging.info('Turn %s: Pressed key %s , text %s', self.dungeon.turn, user_input.key, user_input.text)
                
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
                    return TurnEvent(0, 'invalid key: didnt-take-turn')
                
        return TurnEvent(0, 'game not in Playing state or action cancelled')
        
        
        
    def do_drop(self, turn_action):
        chosen_item = self.inventory_menu('Press the key next to an item to' + 
        'drop it, or any other to cancel.\n')
        if chosen_item is not None:
            chosen_item.drop()
            turn_action.turns_used = self.dungeon.player.fighter.speed
            
    def do_pickup(self, turn_action):
        #pick up an item
        for obj in self.dungeon.objects:  #look for an item in the player's tile
            if obj.x == self.dungeon.player.x and obj.y == self.dungeon.player.y and obj.item:
                self.dungeon.pick_up(obj.item)
                turn_action.turns_used = self.dungeon.player.fighter.speed
                return True
                
    def do_inventory_use(self, turn_action):
        chosen_item = self.inventory_menu()
        if chosen_item:
            if chosen_item.use():
                turn_action.turns_used = self.dungeon.player.fighter.speed
        
    def do_move(self, turn_action):
        turn_action.turns_used = self.dungeon.player_move_or_attack(turn_action.move_x, turn_action.move_y)
    
    ### RENDERING ###
    def render_bar(self, x, y, total_width, name, value, maximum, bar_color, back_color):
        #render a bar (HP, experience, etc). first calculate the width of the bar
        bar_width = int(float(value) / maximum * total_width)
     
        #render the background first
        self.message_panel.draw_rect(x, y, total_width, 1, None, bg=back_color)
     
        #now render the bar on top
        if bar_width > 0:
            self.message_panel.draw_rect(x, y, bar_width, 1, None, bg=bar_color)
     
        #finally, some centered text with the values
        text = name + ': ' + str(value) + '/' + str(maximum)
        x_centered = x + (total_width-len(text))//2
        self.message_panel.draw_str(x_centered, y, text, fg=colors.white, bg=None)
     
    def render_all(self):
        logging.debug('render_all')
        
        if  not self.dungeon:
            return
        
        if self.fov_recompute:
            self.fov_recompute = False
            self.dungeon.visible_tiles = tdl.map.quickFOV(self.dungeon.player.x, self.dungeon.player.y,
                                             self.dungeon.is_visible_tile,
                                             fov=constants.FOV_ALGO,
                                             radius=constants.TORCH_RADIUS,
                                             lightWalls=constants.FOV_LIGHT_WALLS)
     
        #go through all tiles, and set their background color according to the FOV
        for y in range(constants.MAP_HEIGHT):
            for x in range(constants.MAP_WIDTH):
                visible = (x, y) in self.dungeon.visible_tiles
                wall = self.dungeon.map[x][y].block_sight
                if not visible:
                    #if it's not visible right now, the player can only see it 
                    #if it's explored
                    if self.dungeon.map[x][y].explored:
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
                    self.dungeon.map[x][y].explored = True
     
        #draw all objects in the list
        for obj in self.dungeon.objects:
            if obj != self.dungeon.player:
                self.draw_obj(obj)
        self.draw_obj(self.dungeon.player)
        
        #blit the contents of "self.map_console" to the self.root_console console and present it
        self.root_console.blit(self.map_console, 0, 0, constants.MAP_WIDTH, constants.MAP_HEIGHT, 0, 0)
     
        #prepare to render the GUI self.message_panel
        self.message_panel.clear(fg=colors.white, bg=colors.black)
     
        #print the game messages, one line at a time
        y = 1
        for (line, color) in self.messages:
            self.message_panel.draw_str(constants.MSG_X, y, line, bg=None, fg=color)
            y += 1
     
        #show the player's stats
        self.render_bar(1, 1, constants.BAR_WIDTH, 'HP', self.dungeon.player.fighter.hp, self.dungeon.player.fighter.max_hp,
            colors.light_red, colors.darker_red)
     
        #display names of objects under the mouse
        self.message_panel.draw_str(1, 0, self.get_obj_names_under_mouse(), bg=None, fg=colors.light_gray)
     
        #blit the contents of "self.message_panel" to the self.root_console console
        self.root_console.blit(self.message_panel, 0, constants.PANEL_Y, constants.SCREEN_WIDTH, constants.PANEL_HEIGHT, 0, 0)
        
        
    def clear_obj_render(self):
        #erase all objects at their old locations, before they move
        for obj in self.dungeon.objects:
            self.draw_clear(obj)
            
    def draw_obj(self, game_obj):
        #only show if it's visible to the player
        if (game_obj.x, game_obj.y) in self.dungeon.visible_tiles:
            #draw the character that represents this object at its position
            self.map_console.draw_char(game_obj.x, game_obj.y, game_obj.char, game_obj.color, bg=None)
            
    def draw_clear(self, game_obj):
        #erase the character that represents this object
        self.map_console.draw_char(game_obj.x, game_obj.y, ' ', game_obj.color, bg=None)
        
    ### Exit Game ###
    def exit_game(self):
        self.state = constants.STATE_EXIT

