#!/usr/bin/env python3
# This game started from the excellent python roguelike tutorial at: http://www.roguebasin.com/index.php?title=Roguelike_Tutorial,_using_python3%2Btdl #

import tdl
import tcod

import textwrap
import shelve

import constants
import dungeon
import colors 

class TurnEvent:
    # information about what transpired while resolving player input (did a turn pass?)
    def __init__(self, turn_passed = False, description = ''):
        self.turn = turn_passed
        self.description = description

class Game:

    def __init__(self):
        self.map_console = None
        self.root_console = None
        self.state = None
        self.dungeon = None
        self.messages = None
        self.message_panel = None
        self.mouse_coord = None
    
    
    ### SAVE AND LOAD GAME ###
    def save_game(self):
        #open a new empty shelve (possibly overwriting an old one) to write the game data
        with shelve.open('savegame', 'n') as savefile:
            savefile['map'] = self.dungeon.map
            savefile['objects'] = self.dungeon.objects
            savefile['player_index'] = self.dungeon.objects.index(self.player)  #index of player in objects list
            savefile['inventory'] = self.dungeon.inventory
            
            savefile['game_msgs'] = self.messages
            savefile['game_state'] = self.state
     
     
    def load_game(self):
        #open the previously saved shelve and load the game data
     
        with shelve.open('savegame', 'r') as savefile:
            self.dungeon.map = savefile['map']
            self.dungeon.objects = savefile['objects']
            self.dungeon.player = dungeon.objects[savefile['player_index']]  #get index of player in objects list and access it
            self.dungeon.inventory = savefile['inventory']
            
            self.game_msgs = savefile['game_msgs']
            self.state = savefile['self.state']
     
    ### NEW GAME ###
    def new_game(self):
        
        self.dungeon = dungeon.Dungeon(self)
     
        #generate map (at this point it's not drawn to the screen)
        self.dungeon.create_player()
        self.dungeon.make_map()
     
        self.state = constants.STATE_PLAYING
     
        #create the list of game messages and their colors, starts empty
        self.messages = []
     
        #a warm welcoming message!
        self.message('Welcome stranger! Prepare to perish in ' + constants.TITLE, colors.red)
     
    ### MAIN LOOP ###
    def play_game(self):
     
        player_action = None
        self.mouse_coord = (0, 0)
        
        self.map_console.clear() #unexplored areas start black (which is the default background color)
     
        while not tdl.event.is_window_closed():
     
            #draw all objects in the list
            self.render_all()
            tdl.flush()
     
            #handle keys and exit game if needed
            action = self.handle_keys()
            
            #let monsters take their turn: during play state, when a turn has passed
            if self.state == constants.STATE_PLAYING and action.turn:
                self.dungeon.ai_act()
            #exit if player pressed exit
            elif self.state == constants.STATE_EXIT:
                self.save_game()
                break
     
     ### MAIN MENU ###
    def main_menu(self):
        img = tcod.image_load(constants.MENU_BACKGROUND)
     
        while not tdl.event.is_window_closed():
            #show the title image
            xcenter = (constants.SCREEN_WIDTH) // 2
            ycenter = (constants.SCREEN_HEIGHT) // 2
            img.blit(self.root_console, xcenter, ycenter, tcod.BKGND_SET, 0.5, 0.5, 0)
            
            #show the game's title, and some credits!
            title = constants.TITLE
            center = (constants.SCREEN_WIDTH - len(title)) // 2
            self.root_console.draw_str(center, constants.SCREEN_HEIGHT//2-4, title, bg=None, fg=colors.light_yellow)
            
            title = 'By ' + constants.AUTHOR
            center = (constants.SCREEN_WIDTH - len(title)) // 2
            self.root_console.draw_str(center, constants.SCREEN_HEIGHT-2, 'By Astrimedes', bg=None, fg=colors.light_yellow)
     
            #show options and wait for the player's choice
            choice = self.menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
     
            if choice == 0:  #new game
                self.new_game()
                self.play_game()
            if choice == 1:  #load last game
                try:
                    self.load_game()
                except:
                    self.msgbox('\n No saved game to load.\n', 24)
                    continue
                self.play_game()
            elif choice == 2:  #quit
                break


    ### LAUNCH GAME ###
    def game_start(self):

        tdl.set_font('arial10x10.png', greyscale=True, altLayout=True)
        self.root_console = tdl.init(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT, title="Roguelike", 
                        fullscreen=False)
        self.map_console = tdl.Console(constants.MAP_WIDTH, constants.MAP_HEIGHT)
        self.message_panel = tdl.Console(constants.SCREEN_WIDTH, constants.PANEL_HEIGHT)
        
        tdl.setFPS(constants.LIMIT_FPS)
        
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
        menu(text, [], width)  #use menu() as a sort of "message box"
        
        
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

        
    ### INVENTORY ###
    def inventory_menu(self, header):
        #show a menu with each item of the inventory as an option
        if len(self.dungeon.inventory) == 0:
            options = ['Inventory is empty.']
        else:
            options = [item.name for item in dungeon.inventory]
     
        index = menu(header, options, constants.INVENTORY_WIDTH)
     
        #if an item was chosen, return it
        if index is None or len(dungeon.inventory) == 0:
            return None
        return dungeon.inventory[index].item

        
    ### TARGETING ###
    def target_tile(self, max_range=None):
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
                (max_range is None or distance(player, x, y) <= max_range)):
                return mouse_coord
 
    def get_names_under_mouse(self):
        #return a string with the names of all objects under the mouse
        (x, y) = self.mouse_coord
        
        #create a list with the names of all objects at the mouse's coordinates and in FOV
        names = [obj.name for obj in self.dungeon.objects
            if obj.x == x and obj.y == y and (obj.x, obj.y) in self.dungeon.visible_tiles]
            
        names = ', '.join(names)  #join the names, separated by commas
        return names.capitalize() 
        
    def target_monster(self, max_range=None):
        #returns a clicked monster inside FOV up to a range, or None if right-clicked
        while True:
            (x, y) = self.dungeon.target_tile(max_range)
            if x is None:  #player cancelled
                return None
     
            #return the first clicked monster, otherwise continue looping
            for obj in self.dungeon.objects:
                if obj.x == x and obj.y == y and obj.fighter and obj != self.dungeon.player:
                    return obj
 
    
    ### PLAYER INPUT ###
    def handle_keys(self):
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
            return TurnEvent(False, 'No key press')
     
        if user_input.key == 'ENTER' and user_input.alt:
            #Alt+Enter: toggle fullscreen
            tdl.set_fullscreen(not tdl.get_fullscreen())
            return TurnEvent(False, 'Full screen toggle')
     
        elif user_input.key == 'ESCAPE':
            self.exit_game()
            return TurnEvent(False, 'exiting')  #exit game
     
        if self.state == constants.STATE_PLAYING:
            #movement keys
            #up left
            if user_input.key == 'KP7':
                return TurnEvent(self.dungeon.player_move_or_attack(-1, -1), 'moved')
            #up
            elif user_input.key == 'UP' or user_input.key == 'KP8':
                return TurnEvent(self.dungeon.player_move_or_attack(0, -1), 'moved')
            #up right
            elif user_input.key == 'KP9':
                return TurnEvent(self.dungeon.player_move_or_attack(1, -1), 'moved')
            #left
            elif user_input.key == 'LEFT' or user_input.key == 'KP4':
                return TurnEvent(self.dungeon.player_move_or_attack(-1, 0), 'moved')
            #right
            elif user_input.key == 'RIGHT' or user_input.key == 'KP6':
                return TurnEvent(self.dungeon.player_move_or_attack(1, 0), 'moved')
            #down left
            if user_input.key == 'KP1':
                return TurnEvent(self.dungeon.player_move_or_attack(-1, 1), 'moved')
            #down
            elif user_input.key == 'DOWN' or user_input.key == 'KP2':
                return TurnEvent(self.dungeon.player_move_or_attack(0, 1), 'moved')
            #down right
            elif user_input.key == 'KP3':
                return TurnEvent(self.dungeon.player_move_or_attack(1, 1), 'moved')
            # Rest for 1 turn
            elif user_input.key == 'KP5':
                self.dungeon.player_wait()
                return TurnEvent(True, 'waited')
            else:
                #test for other keys
                if user_input.text == 'g':
                    #pick up an item
                    for obj in self.dungeon.objects:  #look for an item in the player's tile
                        if obj.x == self.dungeon.player.x and obj.y == self.dungeon.player.y and obj.item:
                            obj.item.pick_up()
                            return TurnEvent(True, 'picked up item')
     
                if user_input.text == 'i':
                    #show the inventory; if an item is selected, use it
                    chosen_item = self.inventory_menu('Press the key next to an item to ' +
                                                 'use it, or any other to cancel.\n')
                    if chosen_item is not None:
                        return TurnEvent(chosen_item.use(), 'used item')
     
                if user_input.text == 'd':
                    #show the inventory; if an item is selected, drop it
                    chosen_item = inventory_menu('Press the key next to an item to' + 
                    'drop it, or any other to cancel.\n')
                    if chosen_item is not None:
                        chosen_item.drop()
                        return TurnEvent(True, 'dropped item')
     
                return TurnEvent(False, 'didnt-take-turn')
                
        return TurnEvent(False, 'game not in Playing state')
    
    
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
     
        if self.dungeon.fov_recompute:
            self.dungeon.fov_recompute = False
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
        self.message_panel.draw_str(1, 0, self.get_names_under_mouse(), bg=None, fg=colors.light_gray)
     
        #blit the contents of "self.message_panel" to the self.root_console console
        self.root_console.blit(self.message_panel, 0, constants.PANEL_Y, constants.SCREEN_WIDTH, constants.PANEL_HEIGHT, 0, 0)
        
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

