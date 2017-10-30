#!/usr/bin/env python3
# This game started from the excellent python roguelike tutorial at: http://www.roguebasin.com/index.php?title=Roguelike_Tutorial,_using_python3%2Btdl #

import tcod
import tdl

import constants
import colors
import game

from random import randint
from random import choice
from random import random
from random import uniform as randfloat

import dungeon_generator

import numpy as np

import math

from barbarian_names import barb_name

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

_dungeon = None

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
        
class Item:
    #an item that can be picked up and used.
    def __init__(self, use_function=None):
        self.use_function = use_function
        self.owner = None
 
    def drop(self, obj_dropper):
        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        _dungeon.objects.append(self.owner)
        if obj_dropper == _dungeon.player:
            _dungeon.inventory.remove(self)
        elif self == obj_dropper.item:
            obj_dropper.item = None
            
        self.owner.x = obj_dropper.x
        self.owner.y = obj_dropper.y
        
        _dungeon.game.sort_obj_at(self.owner.x, self.owner.y)
        _dungeon.game.message(obj_dropper.name + ' dropped ' + self.owner.name + '.', colors.yellow)
    
    def name(self):
        return self.owner.name
 
    def use(self):
        #just call the "use_function" if it is defined
        if self.use_function is None:
            _dungeon.game.message('The ' + self.owner.name + ' cannot be used.')
            return False
        else:
            if self.use_function():
                _dungeon.inventory.remove(self)  #destroy after use, unless it was 
                                              #cancelled for some reason
                return True
        return False
 
class GameObject:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, dungeon, x, y, char, name, color, blocks=False, 
                 fighter=None, ai=None, item=None):
                 
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks = blocks
        self.fighter = fighter
        
        self.dungeon = dungeon
 
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self
 
        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self
 
        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self
            
class HealingPotion(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(cast_heal)
        GameObject.__init__(self, _dungeon, x, y, 'o', 'intact human heart',
            colors.flame, item=itm)
        #self, dungeon, x, y, char, name, color, blocks=False, 
                 #fighter=None, ai=None, item=None):
                 
class ToughFlesh(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_power)
        GameObject.__init__(self, _dungeon, x, y, 'x', 'tough tasty flesh',
            colors.dark_sepia, item=itm)
            
class StringyFlesh(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_speed)
        GameObject.__init__(self, _dungeon, x, y, '~', 'stringy tasty flesh',
            colors.light_flame, item=itm)
            
class Eyes(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_vision)
        GameObject.__init__(self, _dungeon, x, y, '*', 'intact eyes',
            colors.light_blue, item=itm)
            
class Bones(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_defense)
        GameObject.__init__(self, _dungeon, x, y, '-', 'large bones',
            colors.white, item=itm)
       
            
class LightningScroll(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(cast_lightning)
        GameObject.__init__(self, _dungeon, x, y, '#', 'scroll of lightning bolt',
            colors.light_blue, item=itm)
        
            
class FireballScroll(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(cast_fireball)
        GameObject.__init__(self, _dungeon, x, y, '#', 'scroll of fireball',
            colors.light_flame, item=itm)
        
        
class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, speed=1, atk_speed=0, death_function=None, weapon=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function
        self.owner = None
        self.died = False
        
        self.weapon = None
        
        # used to determine when to act
        self.speed = speed
        self.atk_speed = atk_speed
        self.last_turn = 0
        
    def pass_time(self):
        logging.debug('%s fighter.pass_time()', self.owner.name)
        if self.owner.ai:
            while self.owner.dungeon.turn - self.last_turn >= self.speed:
                self.last_turn += self.owner.ai.take_turn()
                logging.debug('%s ai.take_turn()', self.owner.name)
        else:
            self.last_turn = self.owner.dungeon.turn
            logging.debug('%s - No ai - set last_turn = %s', self.owner.name, self.last_turn)
            
    def set_health_color(self):
        
        # set color according to health
        if not self.died:
            fraction = (self.hp / self.max_hp)
            self.owner.color = constants.THRESH_COLORS[0]
            for idx in range(len(constants.THRESH_COLORS)-1, 0, -1):
                if fraction <= constants.THRESH_HEALTH[idx]:
                    self.owner.color = constants.THRESH_COLORS[idx]
                    logging.debug('set_health_color %s idx used, fraction %s', idx, fraction)
                    break
 
    def take_damage(self, attacker_name, attack_verb, weapon_name, attack_color, damage):
        if damage > 0:
        
            selfname = self.owner.name
            
            newhp = max(self.hp - damage, 0)
            
            fraction = 1 - (newhp / self.max_hp)
            
            cc = colors.mutate_color(colors.white, attack_color, fraction)
                
            self.owner.dungeon.game.message(attacker_name + "'s " + weapon_name + ' ' + attack_verb + 
                  ' ' + selfname + ' for ' + str(damage) + ' damage.', cc)
                  
            self.take_dmg_silent(damage)
            
            if self.owner == self.owner.dungeon.player:
                self.set_health_color()
            
    def take_dmg_silent(self, damage):
        self.hp -= damage
        
        #check for death. if there's a death function, call it
        if self.hp <= 0:
            self.died = True
            function = self.death_function
            if function is not None:
                function()
                
    def attack(self, target):
    
        if not self.weapon:
            logging.debug('%s No weapon equipped', self.owner.name)
            #a simple formula for attack damage
            damage = randint((self.power//2)+_dungeon.level, self.power+_dungeon.level+1) - target.fighter.defense
        else:
            damage = self.weapon.roll_dmg(self, target.fighter)
            
        atk_color = colors.light_red
        if self.owner == self.owner.dungeon.player:
            atk_color = colors.light_blue
        
        if damage > 0:
            #make the target take some damage
            if not self.weapon:
                target.fighter.take_damage(self.owner.name, choice(self.attack_verbs), choice(self.weapon_names), atk_color, damage)
            else:
                target.fighter.take_damage(self.owner.name, self.weapon.atk_verb(), self.weapon.atk_name(), atk_color, damage)
        else:
            self.owner.dungeon.game.message(self.owner.name + ' attacks ' + target.name + 
                  ' but it has no effect!')
                      
            # add atk speed for monsters (player's last_turn is set based on his already-added atk_spd at turn advancement)
            if not self.owner == self.owner.dungeon.player:
                self.last_turn += self.atk_speed
                if self.weapon:
                    self.last_turn += self.weapon.speed
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.owner == _dungeon.player:
                self.set_health_color()
        if self.hp > self.max_hp:
            self.hp = self.max_hp

            
class Player(GameObject):
    def __init__(self, dungeon, x, y):
    
        #create object representing the player
        fighter_component = Fighter(hp=50, defense=constants.START_DEFENSE, power=constants.START_POWER, 
                                    speed=constants.START_SPEED, atk_speed=constants.START_ATK_SPEED, death_function=self.death)
        fighter_component.attack_verbs = ['rake', 'scratch', 'tear', 'attack']
        fighter_component.weapon_names = ['claws', 'great claws', 'bloody claws']
        
        GameObject.__init__(self, dungeon, 0, 0, 'G', 'Grendel', constants.THRESH_COLORS[0], blocks=True, 
                        fighter=fighter_component)
                        
        self.fov = constants.TORCH_RADIUS
                        
                        
    def weapon(self):
        return self.fighter.weapon
    
                        
    def death(self):
        #the game ended!
        self.dungeon.game.message('You died!', colors.red)
        self.dungeon.game.state = constants.STATE_DEAD
        
        logging.info('Died! State:%s, Player_Died:%s', self.dungeon.game.state, self.dungeon.player.fighter.died)
     
        #for added effect, transform the player into a corpse!
        self.char = '%'
        self.color = constants.color_dead
            
class Barbarian(GameObject):
    #Barbarian monster GameObject
    def __init__(self, dungeon, x, y):
        barb_ai = BasicMonster(dungeon, fov_algo=constants.FOV_ALGO_BAD, 
            vision_range=constants.FOV_RADIUS_BAD)
            
        barb_fighter = Fighter(hp=6+dungeon.level, defense=1+dungeon.level, power=3+dungeon.level, 
            speed=1, atk_speed=-0.34, death_function=self.death)
            
        barb_fighter.attack_verbs = ['chops', 'cuts', 'connects with']
        barb_fighter.weapon_names = ['handaxe', 'wildly swinging axe', 'axe']
        
        # objects that drop upon death
        self.drop_objects = []
                 
        GameObject.__init__(self, dungeon, x, y, 'd', barb_name() + ' the Dane', colors.dark_orange, blocks=True, 
                 fighter=barb_fighter, ai=barb_ai, item=None)
                 
                 
    def death(self):
        #transform it into a nasty corpse! it doesn't block, can't be
        #attacked and doesn't move
        self.dungeon.game.message(self.name + 
            choice([' dies!', 
            ' is destroyed!', 
            " dies screaming!"]), colors.orange)                
                
        for itm in self.drop_objects:
            # give it this position
            itm.x = self.x
            itm.y = self.y
            # add to dungeon
            _dungeon.objects.append(itm)
            # announce
            _dungeon.game.message('You spot ' + itm.name + ' in ' + self.name + "'s fresh corpse!", colors.light_orange)
                
        # transform to corpse
        self.name = 'corpse of ' + self.name
        self.char = '%'
        self.color = constants.color_dead
        self.blocks = False
        self.fighter = None
        self.ai = None
        
        # sort this tile properly
        _dungeon.game.sort_obj_at(self.x, self.y)
        
        
                 
class BarbarianTough(Barbarian):
    #BarbarianTough monster GameObject
    def __init__(self, dungeon, x, y):
        zombi_ai = BasicMonster(dungeon, fov_algo=constants.FOV_ALGO_BAD, 
            vision_range=constants.FOV_RADIUS_BAD, flee_health = 0.1, flee_chance = 0.4)
        
        zombi_fighter = Fighter(hp=10+dungeon.level, defense=2+dungeon.level, power=5+dungeon.level,
            speed=1.5, atk_speed = -0.5, death_function=self.death)
        zombi_fighter.attack_verbs = ['cleaves', 'chops', 'carves']
        zombi_fighter.weapon_names = ['battle axe', 'mighty axe', 'well-worn axe']
        
        # objects that drop upon death
        self.drop_objects = []
        
        GameObject.__init__(self, dungeon, x, y, 'D', barb_name() + ' the Dane Chieftan', colors.dark_orange, blocks=True, 
                 fighter=zombi_fighter, ai=zombi_ai, item=None)
            
        
        
class Weapon(Item):
    def __init__(self, min_dmg=1, max_dmg=6, speed=0, attack_names=['club','medium stick', 'bat'], attack_verbs=['bashes','bonks','hits'], map_char = 'w', map_color = colors.white):
        
        Item.__init__(self)
        
        self.min_dmg = min_dmg
        self.max_dmg = max_dmg
        self.speed = speed
        self.attack_names = attack_names
        self.attack_verbs = attack_verbs
        
        self.type = 'weapon'
        
        self.fighter = None
        
        self.owner = GameObject(_dungeon, -999, -999, map_char, self.name(), map_color, blocks=False, 
                 item=self)
        
    def roll_dmg(self, owner_ftr, target_ftr):
        return randint(self.min_dmg, self.max_dmg) + (owner_ftr.power//2) - target_ftr.defense
    
    #override Item
    def name(self):
        return self.attack_names[0]
        
    def atk_name(self):
        return choice(self.attack_names)
        
    def atk_verb(self):
        return choice(self.attack_verbs)
        
    def equip(self, fighter):
        if not fighter.weapon is self:
            self.fighter = fighter
            fighter.weapon = self
            _dungeon.game.message(fighter.owner.name + ' wields a ' + self.name() + '!', colors.white)
        return False
        
    def unequip(self):
        if self.fighter and self.fighter.weapon is self:
            _dungeon.game.message(self.fighter.owner.name + ' stops using a ' + self.name() + '.', colors.white)
            self.fighter.weapon = None
            self.fighter = None
            return True
        return False
            
    def drop(self):
        self.unequip()
        Item.drop(self)
        
    # override Item: equip from player's inventory and don't consume item
    def use(self):
        if not self.equip(_dungeon.player.fighter):
            _dungeon.game.message('You are already using the ' + self.name() + '!')
            return False
        return True
            
class Dungeon:

    def __init__(self, game):
        global _dungeon
        
        if _dungeon:
            del _dungeon
        _dungeon = self
        
        self.game = game
    
        self.player = None
        self.objects = []
        self.map = None
        self.inventory = []
        self.visible_tiles = []
        self.level = 1
        
        # keeps track of turns passed (use monster/player speed to check when to act)
        self.turn = 0
        
        self.combatants = []

    def create_player(self):
        if self.player:
            del self.player
    
        self.player = Player(self, 0, 0)
        
        # player creates the objects list when made 'new'
        self.objects.append(self.player)
        
        # give the player some items
        # self.inventory.append(HealingPotion().item)
        # self.inventory.append(LightningScroll().item)
        # self.inventory.append(FireballScroll().item)
        # self.inventory.append(Weapon())
            
    ### MAP CREATION ###
    def make_map(self):
    
        if self.map:
            del self.map
     
        #fill map with "blocked" tiles
        self.map = [[ Tile(True)
            for y in range(constants.MAP_HEIGHT) ]
                for x in range(constants.MAP_WIDTH) ]
     
        rooms = []
        num_rooms = 0
        
        items_left = 0
        monsters_left = (self.level * 4) + 16
        
        # generate layout
        gen = dungeon_generator.Generator(width=constants.MAP_WIDTH, height=constants.MAP_HEIGHT,
                max_rooms=constants.MAX_ROOMS, min_room_xy=constants.ROOM_MIN_SIZE,
                max_room_xy=constants.ROOM_MAX_SIZE, rooms_overlap=False, random_connections=0,
                random_spurs=0)
        gen.gen_level()
        
        # populate tiles
        for row_num, row in enumerate(gen.level):
            for col_num, col in enumerate(row):
                if col == 'floor':
                    t = self.map[col_num][row_num]
                    t.blocked = False
                    t.block_sight = False
                    
        # add player to first room
        # room = (x, y, w, h)
        room = gen.room_list[0]
        self.player.x = room[0]
        self.player.y = room[1]
        
        gen.gen_tiles_level()
        
        # add items to rooms
        while monsters_left > 0 or items_left > 0:
            for new_room in gen.room_list:
                # add some contents to this room, such as monsters
                items = randint(0, min(items_left, 2))
                items_left -= items
                
                monsters = randint(0, min(monsters_left, 2))
                monsters_left -= monsters
                
                # add them!
                self.place_objects_gen(new_room, monsters, items)
                

                
    def place_objects_gen(self, room, num_monsters, num_items):        
        # room = (x, y, w, h)
     
        #choose random number of items
        #num_items = randint(0, constants.MAX_ROOM_ITEMS)
        
        num_items = min(8 + (self.level * 2), num_monsters)
                    
        added = num_monsters == 0
        for i in range(num_monsters):
            while not added:
                #choose random spot for this monster
                x = randint(room[0] - room[2] + 1, room[0] + room[2] - 1)
                y = randint(room[1] - room[3] + 1, room[1] + room[3] - 1)
         
                #only place it if the tile is not blocked
                if not self.is_blocked(x, y):
                    added = True
                    if randint(0, 100) < 65:  #65% chance of getting a skeleton
                        #create a Barbarian
                        monster = Barbarian(self, x, y)
                    else:
                        #create a BarbarianTough
                        monster = BarbarianTough(self, x, y)
                        
                    # give it an item to drop on death if there are items left
                    if num_items > 0:
                        num_items = num_items - 1
                        itmtype = randint(0,4)
                        if itmtype == 0:
                            itm = StringyFlesh(-1, -1)
                        elif itmtype == 1:
                            itm = ToughFlesh(-1, -1)
                        elif itmtype == 2:
                            itm = Bones(-1, -1)
                        elif itmtype == 3:
                            itm = HealingPotion(-1, -1)
                        else:
                            itm = Eyes(-1, -1)
                        # add item to monster
                        monster.drop_objects.append(itm)
         
                    # add monster to dungeon
                    self.objects.append(monster)

                
    ### MAP QUERIES ###
    def distance_to(self, game_obj, other_game_obj):
        #return the distance to another object
        return self.distance(game_obj.x, game_obj.y, other_game_obj.x, other_game_obj.y)
        
    def distance(self, x1, y1, x2, y2):
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def is_visible_tile(self, x, y):
     
        if x >= constants.MAP_WIDTH or x < 0:
            return False
        elif y >= constants.MAP_HEIGHT or y < 0:
            return False
        elif self.map[x][y].blocked == True:
            return False
        elif self.map[x][y].block_sight == True:
            return False
        else:
            return True

    def is_blocked(self, x, y):
        #first test the map tile
        if self.map[x][y].blocked:
            return True
     
        #now check for any blocking self.objects
        for obj in self.objects:
            if obj.blocks and obj.x == x and obj.y == y:
                return True
        return False
        
    def closest_monster(self, from_gameobj, max_range):
        #find closest enemy, up to a maximum range, and in the player's FOV
        closest_enemy = None
        closest_dist = max_range + 1  #start with (slightly more than) maximum range
     
        for obj in self.objects:
            if obj.fighter and not obj == from_gameobj and (obj.x, obj.y) in self.visible_tiles:
                #calculate distance between this object and from_gameobj
                dist = self.distance_to(from_gameobj, obj)
                if dist < closest_dist:  #it's closer, so remember it
                    closest_enemy = obj
                    closest_dist = dist
        return closest_enemy
        
    ### MOVEMENT AND PATHING FOR GAMEOBJECTS ###
    def move(self, game_obj, dx, dy):
        #move by the given amount, if the destination is not blocked
        if not self.is_blocked(game_obj.x + dx, game_obj.y + dy):
            game_obj.x += dx
            game_obj.y += dy
            # send items here to back
            _dungeon.game.sort_obj_at(game_obj.x, game_obj.y)
            return True
        return False
 
    # try to move towards the target
    def move_towards(self,  game_obj, target_x, target_y):
        direction = self.get_direction(game_obj, target_x, target_y)
        moved = False
        tries = 0
        turn = randint(0,1) == 0
        while not(moved) and tries < 8:
            moved = self.move(game_obj, direction[0], direction[1])
            direction = rotate_pt(direction, turn)
            tries += 1
        
    
    # returns an (x,y) tuple with one of the set of clockwise directional coordinates
    def get_direction(self, game_obj, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - game_obj.x
        dy = target_y - game_obj.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
 
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        return (dx,dy)
        
        
    def move_astar(self, game_obj, x, y):
        #Create a FOV map that has the dimensions of the map
        fov = tcod.map_new(constants.MAP_WIDTH, constants.MAP_HEIGHT)
 
        #Scan the current map each turn and set all the walls as unwalkable
        for y1 in range(constants.MAP_HEIGHT):
            for x1 in range(constants.MAP_WIDTH):
                tcod.map_set_properties(fov, x1, y1, not self.map[x1][y1].block_sight, not self.map[x1][y1].blocked)
                
 
        #Scan all the objects to see if there are objects that must be navigated around
        #Check also that the object isn't game_obj or the target (so that the start and the end points are free)
        #The AI class handles the situation if self is next to the target so it will not use this A* function anyway   
        for obj in self.objects:
            if obj.blocks and obj != game_obj and (obj.x != x or obj.y != y):
                #Set the tile as a wall so it must be navigated around
                tcod.map_set_properties(fov, obj.x, obj.y, True, False)
 
        #Allocate a A* path
        my_path = tcod.path_new_using_map(fov, 1.0)
        
        #Compute the path between self's coordinates and the target's coordinates
        tcod.path_compute(my_path, game_obj.x, game_obj.y, x, y)
        
        logging.info('%s moves a-star: start from %s,%s', game_obj.name, game_obj.x, game_obj.y)
        
        moved = False
 
        #Check if the path exists, and in this case, also the path is shorter than 25 tiles
        #The path size matters if you want the monster to use alternative longer paths (for example through other rooms) if for example the player is in a corridor
        #It makes sense to keep path size relatively low to keep the monsters from running around the map if there's an alternative path really far away        
        if not tcod.path_is_empty(my_path) and tcod.path_size(my_path) < constants.DEFAULT_PATHSIZE:
            #Find the next coordinates in the computed full path
            x, y = tcod.path_walk(my_path, True)
            if not (x is None or y is None) and not self.is_blocked(x, y):
                #Set game_obj's coordinates to the next path tile
                game_obj.x = x
                game_obj.y = y
                self.game.sort_obj_at(x,y)
                logging.info('A-star move to %s,%s', x, y)
                moved = True
       
        #Keep the old move function as a backup so that if there are no paths (for example another monster blocks a corridor)
        #it will still try to move towards the player
        if not(moved):
            self.move_towards(game_obj, x, y) 
            logging.info('Simple move towards %s,%s', x, y)
 
        #Delete the path to free memory
        tcod.path_delete(my_path)
        
    
    ### FIGHTER ACTIONS ###
    def player_move_or_attack(self, dx, dy):
     
        #the coordinates the player is moving to/attacking
        x = self.player.x + dx
        y = self.player.y + dy
     
        #try to find an attackable object there
        target = None
        for obj in self.objects:
            if obj.fighter and obj.x == x and obj.y == y:
                target = obj
                break
        
        turns_used = 0
        
        #attack if target found, move otherwise
        if target is not None:
            self.player.fighter.attack(target)
            turns_used = self.player.fighter.speed + self.player.fighter.atk_speed
            if self.player.fighter.weapon:
                turns_used += self.player.fighter.weapon.speed
        else:
            if self.move(self.player, dx, dy):
                turns_used = self.player.fighter.speed
                self.game.fov_recompute = True
        return turns_used

    def player_wait(self):
        self.game.message('You wait.')
        
    def ai_act(self, turns_passed):
        # determine which monsters player is near or in combat with (ai uses in decisions)
        self.combatants = []
        fighters = [obj.fighter for obj in self.objects if obj.fighter]
        for ftr in fighters:
            if ftr != self.player.fighter and self.distance_to(_dungeon.player, ftr.owner) < 3:
                self.combatants.append(ftr)
    
        # advance dungeon 'clock'
        self.turn += turns_passed
        logging.info('%s turns passed in dungeon', self.turn)
        # ai acts based on current turns passed
        for ftr in fighters:
            # ai will take turns, player will only update last_turn counter
            ftr.pass_time()
 
    def send_to_back(self, game_obj):
        #make this object be drawn first, so all others appear above it if 
        #they're in the same tile.
        self.objects.remove(game_obj)
        self.objects.insert(0, game_obj)
    
    def pick_up(self, item):
        logging.info('pick up attempt')
        #add to the player's inventory and remove from the map
        if len(self.inventory) >= 26:
            self.game.message('Your inventory is full, cannot pick up ' + 
                    item.owner.name + '.', colors.red)
        else:
            self.inventory.append(item)
            self.objects.remove(item.owner)
            self.game.message('You picked up ' + item.owner.name + '!', colors.green)
        
        
class BasicMonster:

    FLEE = 'flee'
    FIGHT = 'fight'

    #AI for a basic monster.
    def __init__(self, dungeon, fov_algo = constants.FOV_ALGO, vision_range = constants.TORCH_RADIUS, 
        flee_health=0.35, flee_chance=0.7, curses=['The vile beast is here!','The thing from the moors! Die, monster!', 'Kill the beast!']):
        
        self.fov = fov_algo
        self.fov_radius = vision_range
        self.dungeon = dungeon
        self.owner = None
        self.flee_health = flee_health
        self.flee_chance = flee_chance
        
        self.curses = curses
        self.cursed = False
        
        #what this monster's been doing last turn
        self.last_action = ''
        self.last_see_player = False
        
        self.leader = False

    def take_turn(self):
        #a basic monster takes its turn.
        monster = self.owner
        
        # monster pathfinding
        distance = self.dungeon.distance_to(monster, self.dungeon.player)
        
        logging.debug('%s: %s distance from player', self.owner.name, distance)
        
        # ignore if monster too far away
        if distance > constants.DEFAULT_PATHSIZE:
            self.last_action = ''
            self.last_see_player = False
            return monster.fighter.speed
        
        # monster fov if near enough to player
        monster_view = tdl.map.quickFOV(monster.x, monster.y,
                                     is_visible_tile)
        logging.info('%s tries an FOV...', self.owner.name)
                                     # self.fov,
                                     # radius=self.fov_radius,
                                     # lightWalls=constants.FOV_LIGHT_WALLS)
                                     
                                     #fov='PERMISSIVE', radius=7.5, lightWalls=True, sphere=True)
        
        # if monster sees player...
        if (self.dungeon.player.x, self.dungeon.player.y) in monster_view:
            logging.info('Player is in view of %s', self.owner.name)
            
            #notify player he's been seen...
            if not self.last_see_player:
                self.last_see_player = True
                if (monster.x,monster.y) in _dungeon.visible_tiles:
                    _dungeon.game.message(self.owner.name + ' notices you!', colors.orange)
            
            # Always fight if player is badly wounded or fighting other enemies
            pfraction = _dungeon.player.fighter.hp / _dungeon.player.fighter.max_hp
            if len(_dungeon.combatants) > 1 or pfraction < 0.4:
                return self.take_fight(distance)
            
            # Flee if badly wounded
            fraction = monster.fighter.hp / monster.fighter.max_hp
            flee = (fraction < self.flee_health and pfraction > 0.55) and (self.last_action == BasicMonster.FLEE or randfloat(0.0,1.0) < self.flee_chance)
            if flee:
                return self.take_flee(distance)
            # Otherwise, Fight!
            else:
                return self.take_fight(distance)
        else:
            # move towards allies if player position is unknown
            self.last_see_player = False
            return self.move_towards_ally(constants.DEFAULT_PATHSIZE)
                
        
    # Flee! (return turns used)
    def take_flee(self, distance):
    
        if not(self.last_action == BasicMonster.FLEE):
            self.last_action = BasicMonster.FLEE
            _dungeon.game.message(self.owner.name + ' tries to flee!', colors.orange)
                
        # run opposite direction of player
        direction = _dungeon.get_direction(self.owner, _dungeon.player.x, _dungeon.player.y)
        xdir = -direction[0]
        ydir = -direction[1]
        # cast ray out away from player, path where you can run the furthest is chosen
        # check individual paths for 'winner' of most clear squares
        tries = 0
        turn_clockwise = choice([True,False])
        PATH_LENGTH = 3
        best_path = None
        most_clear = 0
        best_idx = 0
        valid = False
        _xdir = xdir
        _ydir = ydir
       
        path = None
        while tries < 8:
            tries += 1
            clear = 0
            # check a path that starts 1 square away from monster in flee direction
            x = self.owner.x + _xdir
            y = self.owner.y + _ydir
            # path extends to 
            path = tdl.map.bresenham(x, y, x + (_xdir*PATH_LENGTH), y + (_ydir*PATH_LENGTH))
            i = 0
            for i in range(0,len(path)):
                pt = path[i]
                pdist = _dungeon.distance_to(self.owner, _dungeon.player)
                if pt and _dungeon.is_visible_tile(pt[0], pt[1]) and (i == 0 or pdist >= 2):
                    if i < len(path)-1:
                        pt2 = path[i+1]
                        if _dungeon.is_visible_tile(pt2[0], pt2[1]):
                            clear += 1 #weight tiles that have another clear tile in front of them
                    # weight tiles by distance from player early on in path
                    clear += 1 + (pdist * 2) - (i//2)
                else:
                    break
                #set new best
            if clear > most_clear:
                if not best_path is None:
                    tcod.path_delete(best_path)
            
                best_path = path
                most_clear = clear
                best_idx = i
                xdir = _xdir
                ydir = _ydir
                valid = True
                logging.info('%s Path: %s', self.owner.name, best_path)
            else:
                # free path from memory
                if not path is None:
                    tcod.path_delete(path)
                    
            # rotate the direction for next iteration
            pt = (_xdir, _ydir)
            (_xdir,_ydir) = rotate_pt(pt, turn_clockwise=turn_clockwise)
        
        if valid:
            target = best_path[best_idx]
            _dungeon.move_astar(self.owner, target[0], target[1])
            tcod.path_delete(best_path)
            return self.owner.fighter.speed
            
        return self.take_fight(distance)
        
        
    def move_towards_ally(self, max_dist=20):
        x = None
        y = None
        closest = 999
        for obj in _dungeon.objects:
            if obj.fighter and not obj == self.owner and not obj == _dungeon.player:
                dist = _dungeon.distance_to(self.owner, obj)
                if obj.fighter.hp > self.owner.fighter.max_hp:
                    dist -= 6
                if dist < closest:
                    closest = dist
                    x = obj.x
                    y = obj.y
                
        if closest < max_dist:
            _dungeon.move_astar(self.owner, x, y)
        else:
            _dungeon.move_towards(self.owner, _dungeon.player.x, _dungeon.player.y)
            
        return self.owner.fighter.speed
                
    # Fight! (return turns used)
    def take_fight(self, distance):
        curse = False
        if self.last_action != BasicMonster.FIGHT:
            self.last_action = BasicMonster.FIGHT
            curse = not(self.cursed)
        #move towards player if far away
        if curse:
            _dungeon.game.message(self.owner.name + ' shouts "' + choice(self.curses) + '"', colors.light_violet)
            self.cursed = True
        
        if distance > 1.415:
            logging.info('%s wants to move towards player. distance = %s', self.owner.name, distance)
            _dungeon.move_astar(self.owner, self.dungeon.player.x, self.dungeon.player.y)
            #return turns used
            return self.owner.fighter.speed
        else:
            #close enough, attack!
            self.owner.fighter.attack(self.dungeon.player)
            return self.owner.fighter.speed + self.owner.fighter.atk_speed
            
            
        
        
class LeaderMonster(BasicMonster):
    #AI for a 'leader' monster (other monsters try to stay near them)
    def __init__(self, dungeon, fov_algo = constants.FOV_ALGO, vision_range = constants.TORCH_RADIUS, 
        flee_health=0.2, flee_chance=0.1, curses=['The vile beast is here!','The thing from the moors! Die, monster!', 'Kill the beast!']):
        
        BasicMonster.__init__(self, dungeon, fov_algo, vision_range, 
            flee_health, flee_chance, ['Kill the beast!','Destroy the demon!','The demon returns!'])
        
        self.leader = True

### functions with  no class ###

            
### callback functions ###
def is_visible_tile(x, y):

    if x >= constants.MAP_WIDTH or x < 0:
        return False
    elif y >= constants.MAP_HEIGHT or y < 0:
        return False
    elif _dungeon.map[x][y].blocked == True:
        return False
    elif _dungeon.map[x][y].block_sight == True:
        return False
    else:
        return True
        
### FLESH POWERUPS ###
SPEED_BONUS = -0.05
SPEED_PENALTY = -SPEED_BONUS / 2
POWER_BONUS = 2
POWER_PENALTY = -POWER_BONUS / 2
VISION_BONUS = 0.5
VISION_PENALTY = -VISION_BONUS / 2
DEFENSE_BONUS = 1
DEFENSE_PENALTY = -DEFENSE_BONUS / 2


def bonus_power():
    _dungeon.player.fighter.power += POWER_BONUS
    _dungeon.game.message("Consuming your enemy's tough flesh makes you feel stronger!", colors.green)
    try_penalty(penalty_vision, penalty_speed, penalty_defense)
    return True
            
def penalty_power():
    
    _dungeon.player.fighter.power = max(_dungeon.player.fighter.power + POWER_PENALTY, constants.MIN_POWER)
    _dungeon.game.message("...but it makes you feel weaker, too.", colors.yellow)
    
def bonus_defense():
    _dungeon.player.fighter.defense += DEFENSE_BONUS
    _dungeon.game.message("Consuming your enemy's bones makes you feel more resilient!", colors.green)
    try_penalty(penalty_vision, penalty_power, penalty_speed)
    return True    
    
def penalty_defense():
    
    _dungeon.player.fighter.defense = max(_dungeon.player.fighter.defense + DEFENSE_PENALTY, constants.MIN_DEFENSE)
    _dungeon.game.message("...but it makes you feel less resilient, too.", colors.yellow)
    
def bonus_speed():
    
    _dungeon.player.fighter.speed = max(constants.MIN_SPEED, _dungeon.player.fighter.speed + SPEED_BONUS)
    _dungeon.game.message("Consuming your enemy's stringy flesh makes you feel faster!", colors.green)
    try_penalty(penalty_vision, penalty_power, penalty_defense)
    return True
    
def penalty_speed():
    
    _dungeon.player.fighter.speed = min(_dungeon.player.fighter.speed + SPEED_PENALTY, constants.MAX_SPEED)
    _dungeon.game.message("...but it makes you feel slower, too.", colors.yellow)
    
def bonus_vision():
    _dungeon.game.fov_recompute = True
    _dungeon.player.fov += VISION_BONUS
    _dungeon.game.message("Consuming your enemy's eyes improves your vision!", colors.green)
    try_penalty(penalty_speed, penalty_power, penalty_defense)
    return True
    
def penalty_vision():
    
    _dungeon.player.fov = max(_dungeon.player.fov + VISION_PENALTY, constants.MIN_VISION)
    _dungeon.game.message("...but it makes your vision worse, too.", colors.yellow)
    
def try_penalty(penalty1, penalty2, penalty3):
    pen = choice([penalty1, penalty2, penalty3])
    pen()
        

### CAST SPELLS ###
def cast_heal():
    logging.info('casting heal...')

    #heal the player
    if _dungeon.player.fighter.hp == _dungeon.player.fighter.max_hp:
        _dungeon.game.message("You should save this for when you're wounded.", colors.red)
        return False
 
    _dungeon.game.message("You feast on your enemy's warm heart! Your wounds heal.", colors.light_violet)
    _dungeon.player.fighter.heal(constants.HEAL_AMOUNT+_dungeon.level)
    
    return True
    
def cast_lightning(caster_gameobj=None):
    logging.info('casting lightning...')
    
    if not caster_gameobj:
        caster_gameobj = _dungeon.player
        
    #find closest enemy (inside a maximum range) and damage it
    monster = _dungeon.closest_monster(caster_gameobj, constants.LIGHTNING_RANGE)
    if monster is None:  #no enemy found within maximum range
        _dungeon.game.message('No enemy is close enough to strike.', colors.red)
        return False
 
    #zap it!
    _dungeon.game.message('A lighting bolt arcs towards the ' + monster.name + ' with a loud thunder!', 
            colors.light_blue)
 
    monster.fighter.take_damage('Magical lightning', choice(['strikes', 'zaps', 'fries']), 'electricity', colors.light_blue, constants.LIGHTNING_DAMAGE)
 
    return True
    
# def cast_confuse():
    # #ask the player for a target to confuse
    # _dungeon.game.message('Left-click an enemy to confuse it, or right-click to cancel.', 
            # colors.light_cyan)
    # monster = _dungeon.game.target_monster(constants.CONFUSE_RANGE)
    # if monster is None:
        # _dungeon.game.message('Cancelled')
        # return 'cancelled'
 
    # #replace the monster's AI with a "confused" one; after some turns it will 
    # #restore the old AI
    # old_ai = monster.ai
    # monster.ai = ConfusedMonster(old_ai)
    # monster.ai.owner = monster  #tell the new component who owns it
    # _dungeon.game.message('The eyes of the ' + monster.name + ' look vacant, as he starts to ' +
            # 'stumble around!', colors.light_green)
 
def cast_fireball():
    logging.info('casting fireball...')

    #ask the player for a target tile to throw a fireball at
    _dungeon.game.message('Left-click a target tile for the fireball, or right-click to ' +
            'cancel.', colors.light_cyan)
 
    (x, y) = _dungeon.game.target_tile(max_range=None, target_size=3)
    
    if x is None: 
        _dungeon.game.message('Cancelled')
        return False
    _dungeon.game.message('The fireball explodes, burning everything within ' + 
            str(constants.FIREBALL_RADIUS) + ' tiles!', colors.orange)
 
    for obj in _dungeon.objects:  #damage every fighter in range, including the player
        if _dungeon.distance(obj.x, obj.y, x, y) <= constants.FIREBALL_RADIUS and obj.fighter:
            obj.fighter.take_damage('Magical fire', choice(['burns', 'sears', 'incinerates']), choice(['flame', 'heat', 'blast']), colors.orange, constants.FIREBALL_DAMAGE)
            
    return True
    
    
clockwise = [(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)]
counter =   [(-1,0), (-1,1), (0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1)]
def rotate_pt(point, turn_clockwise=True):
    logging.info('rotate %s. clockwise=%s', point, turn_clockwise)
    if not(point in clockwise):
        #pick random position
        return choice(clockwise)
    if turn_clockwise:
        list = clockwise
    else:
        list = counter
    idx = list.index(point)+1
    if idx >= len(list):
        idx = 0
    elif idx < 0:
        idx = len(list)-1
    return list[idx]
    
    