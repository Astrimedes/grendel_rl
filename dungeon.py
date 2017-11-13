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

import dungeon_generator as dun_gen

import numpy as np

import math

import time
from datetime import date

from barbarian_names import barb_name

from strutil import strleft_back
from strutil import strright_back
from strutil import format_list
import strutil

# GLOBALS #
# logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ai states
from enumerations import Enum
states = Enum(['SLEEP', 'WANDER', 'FIGHT', 'FLEE'])

# global dungeon instance
_dungeon = None
                
"""
Map tile without a GameObject
"""
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

"""
A consumable Item that can be picked up and used by the player
"""
class Item:
    def __init__(self, use_function=None, inv_description=''):
        self.use_function = use_function
        self.owner = None
        self.inv_description = inv_description
 
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
        
    def inventory_name(self):
        return self.name() + ' ' + self.inv_description
 
    """
    Use this item
    """
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
    
    """
    Comparison methods
    """
    def __lt__(self, other):
        return self.name() < other.name()
        
    def __gt__(self, other):
        return self.name() > other.name()
        
    def __le__(self, other):
        return self.__lt(other) or self.name() == other.name()
        
    def __ge__(self, other):
        return self.__gt(other) or self.name() == other.name()

"""
An object on the map with an x,y position.  can contain ai, fighers, item, or 'corpses'
"""
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

"""
Healing item
"""
class Heart(GameObject):
    #chr(173) - the 'drumstick'
    def __init__(self, x=0, y=0):
        itm = Item(cast_heal, inv_description='(heals damage)')
        GameObject.__init__(self, _dungeon, x, y, chr(3), constants.PART_HEALING,
            colors.flame, item=itm)
        #self, dungeon, x, y, char, name, color, blocks=False, 
                 #fighter=None, ai=None, item=None):

"""
Power bonus item
"""
class Muscle(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_power, inv_description='(+Strength,-Speed)')
        GameObject.__init__(self, _dungeon, x, y, '&', constants.PART_POWER,
            colors.light_flame, item=itm)

"""
Speed bonus item
"""
class Legs(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_speed, inv_description='(+Speed,-Strength)')
        GameObject.__init__(self, _dungeon, x, y, chr(28), constants.PART_SPEED,
            colors.light_flame, item=itm)
            
class Eyes(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_vision, inv_description='(+Vision,-Toughness)')
        GameObject.__init__(self, _dungeon, x, y, chr(248), constants.PART_FOV,
            colors.light_flame, item=itm)
            
"""
Defense bonus item
"""
class Torso(GameObject):
    def __init__(self, x=0, y=0):
        itm = Item(bonus_defense, inv_description='(+Toughness,-Vision)')
        GameObject.__init__(self, _dungeon, x, y, '#', constants.PART_DEFENSE,
            colors.light_flame, item=itm)
       

"""
A creature's combat representation: hp, power, attack, take_dmg etc
"""
class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, speed=1, death_function=None, weapon=None):
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
        self.last_turn = 0
        
    def move_speed(self):
        return self.speed
        
    def attack_speed(self):
        if self.weapon:
            return self.speed + self.weapon.speed
        else:
            return self.speed
        
    def pass_time(self):
        if self.owner.ai:
            t = self.move_speed()
            if self.owner.ai.pdistance <= constants.MIN_PDIST and self.owner.fighter.weapon:
                t = self.attack_speed()
            while self.owner.dungeon.turn - self.last_turn >= t:
                self.last_turn += self.owner.ai.take_turn()
                logging.debug('%s ai.take_turn()', self.owner.name)
        else:
            self.last_turn = self.owner.dungeon.turn
            logging.debug('%s - No ai - set last_turn = %s', self.owner.name, self.last_turn)
            
    def set_health_color(self):
        # set color according to health
        if not self.died:
            self.owner.color = self.get_health_color()
                    
    def get_health_color(self):
        fraction = (self.hp / self.max_hp)
        c = constants.THRESH_COLORS[0]
        for idx in range(len(constants.THRESH_COLORS)-1, 0, -1):
            if fraction <= constants.THRESH_HEALTH[idx]:
                c = constants.THRESH_COLORS[idx]
                break
        return c
        
 
    def take_damage(self, attacker_name, attack_verb, weapon_name, attack_color, damage):
        if damage > 0 and self.hp > 0:
        
            selfname = self.owner.name
            
            newhp = max(self.hp - damage, 0)
            
            fraction = 1 - (newhp / self.max_hp)
            
            #cc = colors.mutate_color(colors.white, attack_color, fraction)
                
            self.owner.dungeon.game.message(attacker_name + "'s " + weapon_name + ' ' + attack_verb + 
                  ' ' + selfname + ' for ' + str(damage) + ' damage.', attack_color)
                  
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
    
        logging.info('Turn ' + str(round(_dungeon.turn,2)) + ', Last Turn: ' + str(self.last_turn) + ", " + self.owner.name + ' attacks ' + target.name)
    
        if not self.weapon:
            logging.debug('%s No weapon equipped', self.owner.name)
            #a simple formula for attack damage
            damage = randint(1, self.power) - target.fighter.defense
        else:
            damage = self.weapon.roll_dmg(self, target.fighter)
            
        atk_color = colors.light_red
        if self.owner == self.owner.dungeon.player:
            atk_color = colors.light_blue
        
        shortname = strleft_back(self.owner.name, ' the ')
        if damage > 0:
            #make the target take some damage
            if not self.weapon:
                target.fighter.take_damage(shortname, choice(self.attack_verbs), choice(self.weapon_names), atk_color, damage)
            else:
                target.fighter.take_damage(shortname, self.weapon.atk_verb(), self.weapon.atk_name(), atk_color, damage)
        else:
            self.owner.dungeon.game.message(shortname + "'s " + self.weapon.atk_name() + ' ' + self.weapon.atk_verb() + ' ' + target.name + 
                  ' but it has no effect!')
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.owner == _dungeon.player:
                self.set_health_color()
        if self.hp > self.max_hp:
            self.hp = self.max_hp

"""
Player GameObject
"""
class Player(GameObject):
    def __init__(self, dungeon, x, y):
    
        #create object representing the player
        fighter_component = Fighter(hp=50, defense=constants.START_DEFENSE, power=constants.START_POWER, 
                                    speed=constants.START_SPEED, death_function=self.death)
        
        weapon = Weapon(min_dmg=4, max_dmg=6, speed=constants.START_ATK_SPEED, 
        attack_names=['claws'], 
        attack_verbs=['rake', 'slash', 'slice'], 
        map_char = 'w', map_color = colors.white)
        
        fighter_component.weapon = weapon
        
        GameObject.__init__(self, dungeon, 0, 0, chr(2), 'Grendel', constants.THRESH_COLORS[0], blocks=True, 
                        fighter=fighter_component)
                        
        self.fov = constants.START_VISION
                        
                        
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

"""
Weak enemy (GameObject)
"""
class Scout(GameObject):
    #Scout monster GameObject
    def __init__(self, dungeon, x, y):
        #barb_ai = BasicMonster(dungeon, fov_algo=constants.FOV_ALGO_BAD, 
            #vision_range=constants.FOV_RADIUS_BAD)
        
        barb_ai = NPC()
            
        barb_fighter = Fighter(hp=8, defense=1, power=3, 
            speed=1, death_function=self.death)
        
        weapon = Weapon(min_dmg=2, max_dmg=4, speed=0, 
        attack_names=['sword'], 
        attack_verbs=['slashes', 'stabs'], 
        map_char = 'w', map_color = colors.white)
        
        barb_fighter.weapon = weapon
        
        # objects that drop upon death
        self.drop_objects = []
                 
        GameObject.__init__(self, dungeon, x, y, 's', barb_name() + ' the Scout', colors.dark_orange, blocks=True, 
                 fighter=barb_fighter, ai=barb_ai, item=None)
                 
                 
    def death(self):    
        #transform it into a nasty corpse! it doesn't block, can't be
        #attacked and doesn't move
        self.dungeon.game.message(self.name + 
            choice([' dies!', 
            ' is destroyed!', 
            " dies screaming!"]), colors.orange)
            
        if self.drop_objects:
            for itm in self.drop_objects:
                # give it this position
                itm.x = self.x
                itm.y = self.y
                # add to dungeon
                _dungeon.objects.append(itm)
            # announce
            _dungeon.game.message('You see ' + format_list([itm.name for itm in self.drop_objects]) + ' in ' + self.name + "'s corpse!", colors.light_orange)
                
        # transform to corpse
        self.name = 'corpse of ' + self.name
        self.char = '%'
        self.color = constants.color_dead
        self.blocks = False
        self.fighter = None
        self.ai = None
        
        # sort this tile properly
        _dungeon.game.sort_obj_at(self.x, self.y)
        
        # now re-count enemies (since we've set our Fighter to None)
        self.dungeon.count_enemies()
        
        
"""
Strong enemy (GameObject)
"""
class Warrior(Scout):
    #Warrior monster GameObject
    def __init__(self, dungeon, x, y):
        # bt_ai = BasicMonster(dungeon, fov_algo=constants.FOV_ALGO_BAD, 
            # vision_range=constants.FOV_RADIUS_BAD, flee_health = 0.1, flee_chance = 0.4)
        bt_ai = NPC(flee_health = 0.1, flee_chance = 0.3)
        
        bt_fighter = Fighter(hp=14, defense=3, power=6,
            speed=1.5, death_function=self.death)
        
        weapon = Weapon(min_dmg=4, max_dmg=8, speed=-0.4, 
        attack_names=['greataxe'], 
        attack_verbs=['chops', 'carves'], 
        map_char = 'w', map_color = colors.white)
        
        bt_fighter.weapon = weapon
        
        # objects that drop upon death
        self.drop_objects = []
        
        GameObject.__init__(self, dungeon, x, y, 'W', barb_name() + ' the Warrior', colors.dark_orange, blocks=True, 
                 fighter=bt_fighter, ai=bt_ai, item=None)
                 
                 
"""
Bard enemy
"""
class Bard(Scout):
    #ranged monster GameObject
    def __init__(self, dungeon, x, y):
        
        bard_ai = BardNPC()
            
        bard_fighter = Fighter(hp=5, defense=1, power=2, 
            speed=1.2, death_function=self.death)
        
        weapon = Weapon(min_dmg=1, max_dmg=2, speed=0, 
        attack_names=['knife'], 
        attack_verbs=['pricks'], 
        map_char = 'w', map_color = colors.white)
        
        bard_fighter.weapon = weapon
        
        # objects that drop upon death
        self.drop_objects = []
        
        GameObject.__init__(self, dungeon, x, y, 'b', barb_name() + ' the Bard', colors.darkest_orange, blocks=True, 
                 fighter=bard_fighter, ai=bard_ai, item=None)
                 
                 
                 
    def death(self):    
        
        #transform it into a nasty corpse! it doesn't block, can't be
        #attacked and doesn't move
        self.dungeon.game.message(self.name + 
            choice([' dies!', 
            ' is silenced for good!']), colors.orange)
            
        if self.drop_objects:
            for itm in self.drop_objects:
                # give it this position
                itm.x = self.x
                itm.y = self.y
                # add to dungeon
                _dungeon.objects.append(itm)
            # announce
            names = format_list([itm.name for itm in self.drop_objects])
            # add article for single items
            if len(self.drop_objects) < 2:
                article = strutil.get_article(names)
                if article:
                    names = article + ' ' + names
            _dungeon.game.message('You see ' + names + ' in ' + self.name + "'s corpse!", colors.light_orange)
                
        # transform to corpse
        self.name = 'corpse of ' + self.name
        self.char = '%'
        self.color = constants.color_dead
        self.blocks = False
        self.fighter = None
        self.ai = None
        
        # sort this tile properly
        _dungeon.game.sort_obj_at(self.x, self.y)
        
        # now re-count enemies (since we've set our Fighter to None)
        self.dungeon.count_enemies()



"""
The Boss enemy (GameObject)
"""
class Beowulf(Scout):
    #Boss monster GameObject
    def __init__(self, dungeon, x, y):
        bt_ai = BossMonster(dungeon)
        
        bt_fighter = Fighter(hp=50, defense=4, power=10,
            speed=1.25, death_function=self.death)
        
        weapon = Weapon(min_dmg=4, max_dmg=8, speed=-0.2,
        attack_names=['battle axe', 'mighty axe'], 
        attack_verbs=['cleaves', 'chops', 'carves'], 
        map_char = 'w', map_color = colors.white)
        
        bt_fighter.weapon = weapon
        
        # objects that drop upon death
        self.drop_objects = []
        
        GameObject.__init__(self, dungeon, x, y, 'B', 'Beowulf the Mighty', colors.white, blocks=True, 
                 fighter=bt_fighter, ai=bt_ai, item=None)
                 
                 
    def death(self):    
        self.dungeon.game.message('Beowulf roars one last time as the blood drains from his body and he falls down dead.', colors.orange)
        self.dungeon.game.message('Their hero is dead!  Your war is won.', colors.green)
        
        self.dungeon.game.state = constants.STATE_WON
        
        # transform to corpse
        self.name = 'corpse of ' + self.name
        self.char = '%'
        self.color = constants.color_dead
        self.blocks = False
        self.fighter = None
        self.ai = None
        
        # sort this tile properly
        _dungeon.game.sort_obj_at(self.x, self.y)
        

"""
Contains attack stats and attack names for a Fighter
"""
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
        return round(randint(self.min_dmg, self.max_dmg) + (owner_ftr.power/2) - target_ftr.defense)
    
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

"""
Mapping, inventory, - main in-game object
"""
class Dungeon:

    def __init__(self, game):
        global _dungeon
        
        if _dungeon:
            del _dungeon
        _dungeon = self
        
        self.generator = None
        
        self.game = game
    
        self.player = None
        self.objects = []
        self.map = None
        self.inventory = []
        self.visible_tiles = []
        self.level = 1
        
        # keeps track of turns passed (use monster/player speed to check when to act)
        self.start_time = constants.START_TIME + randint(0, 10800)
        self.turn = 0
        self.calc_date_time() #set initial time values
        
        self.combatants = []
        self.visible_enemies = []
        
        self.enemies_left = 0

    def create_player(self):
        if self.player:
            del self.player
    
        self.player = Player(self, 0, 0)
        
        # player creates the objects list when made 'new'
        self.objects.append(self.player)
        
        # give the player some items
        # self.inventory.append(Muscle().item)
        # self.inventory.append(Heart().item)
        # self.inventory.append(Legs().item)
        # self.inventory.append(Heart().item)
        # self.inventory.append(Muscle().item)
        # self.inventory.append(Legs().item)
        
    def create_Beowulf(self):
    
        room = [room for room in self.generator.room_list if room.rtype == dun_gen.rtypes.BIGROOM][0]
        pt = (1, 0)
        tries = 0
        added = False
        x, y = room.center()
        while not(added):
            added = not(self.is_blocked(x, y))
            if not(added):
                if tries % 8 == 0:
                    pt = (1,0)
                    if randint(0,1) == 0:
                        x += 1
                    else:
                        y += 1
                pt = rotate_pt(pt, True)
                x += pt[0]
                y += pt[1]
            tries += 1
        # place beowulf!
        boss = Beowulf(self, x, y)
        
        # add to dungeon!
        _dungeon.objects.append(boss)
        
    def count_enemies(self):
        fighters = [obj.fighter for obj in self.objects if obj.fighter]
        self.enemies_left = len(fighters) - 1 # subtract player
        
    ### MAP CREATION ###
    def make_map(self):
    
        if self.map:
            del self.map
            
        if self.generator:
            del self.generator
     
        #fill map with "blocked" tiles
        self.map = [[Tile(True)
            for y in range(constants.MAP_HEIGHT)]
                for x in range(constants.MAP_WIDTH)]
     
        rooms = []
        num_rooms = 0
        
        monsters_left = constants.MONSTER_COUNT
        items_left = monsters_left // 2
        
        # generate layout
        self.generator = dun_gen.Generator(width=constants.MAP_WIDTH, height=constants.MAP_HEIGHT,
                max_rooms=constants.MAX_ROOMS, min_room_xy=constants.ROOM_MIN_SIZE,
                max_room_xy=constants.ROOM_MAX_SIZE, rooms_overlap=False, random_connections=1,
                random_spurs=1)
        
        self.generator.gen_level()
        
        # populate tiles
        for row_num, row in enumerate(self.generator.level):
            for col_num, col in enumerate(row):
                if col == dun_gen.tiles.FLOOR:
                    t = self.map[col_num][row_num]
                    t.blocked = False
                    t.block_sight = False
                    
        # find furthest left room for player
        minx = constants.MAP_WIDTH
        p_room = None
        for r in self.generator.room_list:
            if r.x < minx:
                minx = r.x
                p_room = r
        # only add player to this room
        pt = (1, 0)
        tries = 0
        added_player = False
        px, py = p_room.center()
        while not(added_player):
            added_player = not(self.is_blocked(px, py))
            if not(added_player):
                if tries % 8 == 0:
                    pt = (1,0)
                    if randint(0,1) == 0:
                        px += 1
                    else:
                        py += 1
                pt = rotate_pt(pt, True)
                px += pt[0]
                py += pt[1]
            tries += 1
        # assign player room coordinates
        self.player.x, self.player.y = px, py
        
        # place beowulf in a big room
        self.create_Beowulf()
        
        # add items to rooms
        while monsters_left > 0:
            for i, new_room in enumerate(self.generator.room_list):
                if not(new_room is p_room):
                    # qty of monsters can depend on room size
                    #max_monsters = round((new_room[2] * new_room[3])/3.0)
                    max_monsters = 1
                    monsters = randint(0, min(monsters_left, max_monsters))
                    monsters_left -= monsters
                    
                    # add them!
                    self.place_objects_gen(new_room, monsters)
                
        # add items to monsters
        self.add_items_to_monsters(constants.ITEM_QTY)
        
        # print layout of dungeon
        self.generator.gen_tiles_level()
        
    def add_items_to_monsters(self, num_items):
        monsters = [obj for obj in self.objects if obj.fighter and obj != self.player]
        max_items = num_items
        # give it an item to drop on death if there are items left
        HEAL_MOD = 4 # every 4th item or so guaranteed to be heart
        monster = choice(monsters)
        while num_items > 0:
            monster = choice(monsters)
            add_items = True
            # guaranteed healing...
            if (max_items - num_items) % HEAL_MOD == 0:
                itm = Heart(-1,-1)
            else:
                itm = None
            while add_items:
                if not(itm):
                    # choose random item
                    itm = self.choose_item()
                # add item to monster
                if len(monster.drop_objects) > 0:
                    names = [itm.name for itm in monster.drop_objects]
                    tries = 0
                    while itm.name in names and tries < 20:
                        del itm
                        itm = self.choose_item()
                    if itm.name in names:
                        del itm
                if itm:
                    num_items -= 1
                    monster.drop_objects.append(itm)
                    add_items = randint(0,100) < 5
                else:
                    add_items = False
            
            

    def choose_item(self):
        itmtype = randint(0,3)
        if itmtype == 0:
            itm = Legs(-1, -1)
        elif itmtype == 1:
            itm = Eyes(-1, -1)
        elif itmtype == 2:
            itm = Muscle(-1, -1)
        elif itmtype == 3:
            itm = Torso(-1, -1)
        # else:
            # itm = Heart(-1, -1)
            
        return itm
                
                
    def place_objects_gen(self, room, num_monsters):        
        # room = (x, y, w, h)
        tries = 0
        mon_left = num_monsters
        for i in range(num_monsters):
            added = False
            while not(added) and tries < 100:
                tries += 1
            
                #choose random spot for this monster
                x = randint(room.x - room.w + 1, room.x + room.w - 1)
                y = randint(room.y - room.h + 1, room.y + room.h - 1)
         
                #only place it if the tile is not blocked
                if not self.is_blocked(x, y):
                
                    self.enemies_left += 1
                    mon_left -= 1
                    added = True
                    montype = randfloat(0, 1)
                    if montype < constants.MONSTER_SPECIAL:
                        montype = randfloat(0, 1)
                        if montype < constants.MONSTER_BARD:
                            # bard
                            monster = Bard(self, x, y)
                            # add monster to dungeon
                            self.objects.append(monster)
                            mon_left -= 1
                        montype = randfloat(0,1)
                        if montype < constants.MONSTER_TOUGH:
                            #create a tough guy
                            monster = Warrior(self, x, y)
                            # add monster to dungeon
                            self.objects.append(monster)
                            mon_left -= 1
                    
                    #create a scout regardless
                    monster = Scout(self, x, y)                                                
                    # add monster to dungeon
                    self.objects.append(monster)
                    

                
    ### MAP QUERIES ###
    def distance_to(self, game_obj, other_game_obj):
        #return the distance to another object
        return self.distance(game_obj.x, game_obj.y, other_game_obj.x, other_game_obj.y)
        
    """
    Tile distance between 2 points
    """
    def distance(self, x1, y1, x2, y2):
        return math.sqrt(self.distance2(x1,y1,x2,y2))
    
    """
    Returns the squared tile distance between two points (saves a sqrt() if not needed)
    """
    def distance2(self, x1, y1, x2, y2):
        return ((x2 - x1) ** 2) + ((y2 - y1) ** 2)

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
        if x >= constants.MAP_WIDTH or y >= constants.MAP_HEIGHT or x < 0 or y < 0:
            return True
    
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
                dist = self.distance2(from_gameobj.x, from_gameobj.y, obj.x, obj.y)
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
        distance = max(math.sqrt(dx ** 2 + dy ** 2),1)
 
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        return (dx,dy)
        
        
    def move_astar(self, game_obj, x, y, max_pathsize=999):
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
        
        logging.debug('%s moves a-star: start from %s,%s', game_obj.name, game_obj.x, game_obj.y)
        
        moved = False
 
        #Check if the path exists     
        if not(tcod.path_is_empty(my_path)):
            #Find the next coordinates in the computed full path
            x, y = tcod.path_walk(my_path, True)
            if not (x is None or y is None) and not self.is_blocked(x, y):
                #Set game_obj's coordinates to the next path tile
                game_obj.x = x
                game_obj.y = y
                self.game.sort_obj_at(x,y)
                logging.debug('A-star move to %s,%s', x, y)
                moved = True
       
        #Keep the old move function as a backup so that if there are no paths (for example another monster blocks a corridor)
        #it will still try to move towards the player
        if not(moved):
            self.move_towards(game_obj, x, y) 
            logging.debug('Simple move towards %s,%s', x, y)
 
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
        
        # recalc visible enemies when player moves or attacks
        self.calc_visible_enemies()
        
        #attack if target found, move otherwise
        if target is not None:
            self.player.fighter.attack(target)
            turns_used = self.player.fighter.attack_speed()
            # make noise!
            self.make_noise(x, y, 8)
        else:
            if self.move(self.player, dx, dy):
                turns_used = self.player.fighter.move_speed()
                self.game.fov_recompute = True
        return turns_used

    def player_wait(self):
        self.game.message('You wait.')
        
    def make_noise(self, x, y, volume):
        # find all monsters
        monsters = [obj.ai for obj in self.objects if obj.ai]
        for m in monsters:
            m.hear_noise(x,y,volume)
        
    def ai_act(self, turns_passed):
        # sort player inventory
        self.inventory = sorted(self.inventory)
    
        # advance dungeon 'clock'
        self.turn += turns_passed
        logging.info('%s turns passed in dungeon', self.turn)
        
        # date / time strings from turn count
        self.calc_date_time()
        
        # ai acts based on current turns passed
        for ftr in [obj.fighter for obj in self.objects if obj.fighter]:
            # ai will take turns, player will only update last_turn counter
            ftr.pass_time()
            
        # recalc visible enemies
        self.calc_visible_enemies()   
        
        # determine which monsters player is near or in combat with (ai uses in decisions)
        self.combatants.clear()
        fighters = [obj.fighter for obj in self.visible_enemies if obj.fighter]
        for ftr in fighters:
            if ftr != self.player.fighter and self.distance2(_dungeon.player.x, _dungeon.player.y, ftr.owner.x, ftr.owner.y) < 9:
                self.combatants.append(ftr)
            
    def calc_date_time(self):
        # time of day (dungeon turn)
        seconds = float(self.start_time + round(self.turn * 6.0))
        stime = time.gmtime(seconds)
        # day, month, year (year is offset from 1970 in order to use normal date-time structs)
        self.date_string = time.strftime("%d %b", stime) + ', ' + str(int(stime[0] - constants.TIME_SUBTRACT_YEARS)) + ' AD'
        self.time_string = time.strftime("%I:%M:%S %p", stime)
 
    def send_to_back(self, game_obj):
        #make this object be drawn first, so all others appear above it if 
        #they're in the same tile.
        self.objects.remove(game_obj)
        self.objects.insert(0, game_obj)
    
    def pick_up(self, items):
        #add to the player's inventory and remove from the map
        for item in items:
            self.inventory.append(item.item)
            self.objects.remove(item)
        
        #msg
        text = format_list([item.name for item in items])
        self.game.message('You picked up: ' + text + '!', colors.green)
            
            
    def calc_visible_enemies(self):
        del self.visible_enemies
        self.visible_enemies = [obj for obj in self.objects if (obj.x, obj.y) in self.visible_tiles and obj.fighter and obj != self.player]
        return self.visible_enemies
            
    def get_inv_count_dict(self):
        d = dict()
        for itm in self.inventory:
            if itm.name() in d:
                d[itm.name()] += 1
            else:
                d[itm.name()] = 1
        return d
        
    """
    Return a dict by inventory_name(), each element is single a item of type
    """
    def get_inv_item_dict(self):
        d = dict()
        for itm in self.inventory:
            if not(itm.inventory_name() in d):
                d[itm.inventory_name()] = itm
        return d
        

"""
Monster AI
"""
class NPC:
    def __init__(self, hearing = 0.1, laziness = 0.2, 
            vision_range = constants.START_VISION, flee_health=0.4, flee_chance=0.75, 
            curses=['Kill the beast!', 'Destroy the monster!', 'Die, creature!']):
        
        self.owner = None
        
        self.fov_radius = vision_range
        
        # flee thresholds
        self.flee_health = flee_health
        self.flee_chance = flee_chance
    
        # begin sleeping
        self.state = states.SLEEP
        self.last_state = states.SLEEP
        self.state_turns = 0 # how many turns current state has been active
        
        # distance to player at last calculation
        self.pdistance = 0
        
        # turn count last time player was attacked
        self.last_attack_turn = -1
        
        # visible tiles
        self.view = None
        
        # last known player position
        self.last_px = None
        self.last_py = None
        
        # last target position (while wandering)
        self.target_x = None
        self.target_y = None
        
        # hearing chance (to wake up or be alerted that player is near)
        self.hearing = hearing
        
        # chance to fall asleep
        self.laziness = laziness
        
        # fight shouts
        self.curses = curses
        
        
    """
    Whether the player is currently in view of the monster
    """
    def player_in_view(self):
        if (self.view):
            visible = (_dungeon.player.x, _dungeon.player.y) in self.view
            if visible:
                self.last_px = _dungeon.player.x
                self.last_py = _dungeon.player.y
            return visible
        else:
            return False
        
    """
    Take a turn, return number of turns used
    """
    def take_turn(self):
        #a basic monster takes its turn.
        monster = self.owner
        
        # monster pathfinding
        self.pdistance = _dungeon.distance_to(monster, _dungeon.player)
        
        logging.debug('%s: %s distance from player', self.owner.name, self.pdistance)
        
        self.view = None
        
        # determine if it falls asleep while player far away
        if self.pdistance > constants.MAX_HEAR_DIST and not(self.state == states.SLEEP):
            if self.state_turns > 20 and randfloat(0,1) <= self.laziness:
                self.change_state(states.SLEEP)
        # if monster sees player... 
        elif self.pdistance < constants.MAX_HEAR_DIST:
            # fov (store visible tiles)
            self.view = tdl.map.quickFOV(monster.x, monster.y, is_visible_tile, radius = self.fov_radius)
            # if player could be seen...
            if self.player_in_view():
                # strong chance to wake from sleep
                if self.state == states.SLEEP:
                    if randfloat(0,1) < 0.9:
                        self.change_state(states.FIGHT)
                # fight or flee player in view...
                else:
                    # flee
                    if (self.owner.fighter.hp / self.owner.fighter.max_hp < self.flee_health) and len(_dungeon.combatants) < 2 and (self.pdistance > constants.MIN_PDIST or randfloat(0,1) <= self.flee_chance):
                        self.change_state(states.FLEE)
                    # otherwise fight
                    else:
                        self.change_state(states.FIGHT)
                    
        # record player position if visible
        if not(self.state == states.SLEEP) and self.player_in_view():
            self.last_px = _dungeon.player.x
            self.last_py = _dungeon.player.y
                    
        # count turns in state
        self.state_turns += 1
        
        # set color by state
        self.owner.color = self.calc_color()
        
        if self.state == states.SLEEP:
            return self.take_sleep()
            
        if self.state == states.WANDER:
            return self.take_movetarget()
            
        if self.state == states.FIGHT:
            return self.take_fight()
            
        if self.state == states.FLEE:
            return self.take_flee()
            
    """
    Determine color according to state
    """
    def calc_color(self):
        c = colors.black
        if self.state == states.FIGHT:
            c = colors.dark_orange
        if self.state == states.FLEE:
            c = colors.light_orange
        elif self.state == states.SLEEP:
            c = colors.darkest_grey
        elif self.state == states.WANDER:
            c = colors.dark_grey
            
        return c
            
    """
    Sleep for one turn
    """
    def take_sleep(self):
        return self.owner.fighter.move_speed()
        
    """
    Flee from player
    """
    def take_flee(self):
        # determine how in danger we are...
        if not self.player_in_view() and self.state_turns > 20 and self.pdistance > 20:
            # target a nearby ally to move towards
            self.set_ally_target()
        else:
            self.set_flee_target()
        # else:
            # # try to run directly away from player in view
            # if not(self.set_flee_target()) and self.pdistance <= constants.MIN_PDIST:
                # # fight for one turn if we can't run away
                # return self.take_fight()
                
        # move towards target
        return self.take_movetarget()
                
        
    """
    Move towards target_x and target_y
    """
    def take_movetarget(self):
        # do we need a new target?
        if not(self.target_x and self.target_y) or (self.owner.x,self.owner.y) == (self.target_x,self.target_y):
            # set random wander dest
            if self.state == states.WANDER:
                self.set_wander_target()
            # flee...
            if self.state == states.FLEE:
                # run away from player
                if not(self.set_flee_target()):
                    # find tougher ally if possible
                    self.set_ally_target()
                    
                    
        # if we still don't have a target, set randomly to wander
        if not(self.target_x and self.target_y):
            self.set_wander_target()
            
        # now we should have target coordinates...
        _dungeon.move_astar(self.owner, self.target_x, self.target_y, 9999)
        
        return self.owner.fighter.move_speed()
        
    """
    Set target_x and target_y to an ally
    """
    def set_ally_target(self, max_dist=40):
        x = None
        y = None
        closest = 99999
        for obj in _dungeon.objects:
            if obj.fighter and not obj == self.owner and not obj == _dungeon.player:
                dist = _dungeon.distance2(self.owner.x, self.owner.y, obj.x, obj.y)
                if obj.fighter.hp > self.owner.fighter.max_hp:
                    dist -= 12
                if dist < closest:
                    closest = dist
                    x = obj.x
                    y = obj.y
                
        if closest < max_dist**2 and (x and y):
            self.target_x = obj.x
            self.target_y = obj.y
            return True
        else:
            return False
            
    def set_flee_target(self):
        if self.state_turns < 2:
            _dungeon.game.message(self.owner.name + ' tries to flee!', colors.orange)
        logging.info('%s: Set flee target', self.owner.name)
        # run opposite direction of player
        direction = _dungeon.get_direction(self.owner, self.last_px, self.last_py)
        xdir = -direction[0]
        ydir = -direction[1]
        # cast ray out away from player, path where you can run the furthest is chosen
        # check individual paths for 'winner' of most clear squares
        tries = 0
        turn_clockwise = choice([True,False])
        PATH_LENGTH = 2
        best_path = None
        most_clear = 3 # require minimum decent path
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
            pdist = _dungeon.distance(x, y, _dungeon.player.x, _dungeon.player.y)
            for i in range(0,len(path)):
                pt = path[i]
                blocked = _dungeon.is_blocked(pt[0], pt[1])
                if pt and not(blocked) and (i == 0 or pdist >= 2):
                    if i < len(path)-1:
                        pt2 = path[i+1]
                        if not(_dungeon.is_blocked(pt2[0], pt2[1])):
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
                #logging.info('%s Path: %s', self.owner.name, best_path)
            else:
                # free path from memory
                if not path is None:
                    tcod.path_delete(path)
                    
            # rotate the direction for next iteration
            pt = (_xdir, _ydir)
            _xdir,_ydir = rotate_pt(pt, turn_clockwise=turn_clockwise)
        
        if valid:
            self.target_x = self.owner.x + xdir
            self.target_y = self.owner.y + ydir
            tcod.path_delete(best_path)
            return True
        else:
            self.target_x = None
            self.target_y = None
            # return False if no good flee option could be found
            return False
    
            
    """
    Make a noise at position, monster may awake if sleeping or decide to check the noise out if wandering.
    noise_strength is expected to be a float in the range of 0 -> constants.MAX_HEAR_DIST (larger = louder)
    """
    def hear_noise(self, noise_x, noise_y, noise_strength):
        dist = max(_dungeon.distance(self.owner.x, self.owner.y, noise_x, noise_y),1)
        if dist < constants.MAX_HEAR_DIST:
            if self.hearing >= (noise_strength / dist):
                if self.state == states.SLEEP:
                    self.change_state(states.WANDER)
                    self.target_x = noise_x
                    self.target_y = noise_y
                elif self.state == states.WANDER:
                    if _dungeon.distance(self.owner.x, self.owner.y, self.target_x, self.target_y) > dist:
                        # set new target to noise location
                        self.target_x = noise_x
                        self.target_y = noise_y
                
                
    def change_state(self, new_state):
        if self.state == new_state:
            return False
        
        if new_state in states.all():
        
            logging.info('AI change to %s from %s (%s)', states.nameof(new_state), states.nameof(self.state), self.owner.name)
            
            self.last_state = self.state
            self.state = new_state
            
            self.state_turns = 0
            self.target_x = None
            self.target_y = None
            
            if self.state == states.WANDER:
                self.set_wander_target()
            
        else:
            raise ValueError('Invalid State attempted!', new_state)
            
        return True
        
    """
    Set a new random patrol target (tries to pick places on 'opposite side' of dungeon)
    """
    def set_wander_target(self):
        # where are we now...
        # x pos
        xcenter = constants.MAP_WIDTH // 2
        xdir = randint(-1,1)
        rmax = 4
        r = randint(0,rmax)
        if self.owner.x > xcenter and r < rmax:
            xdir = -1
        elif self.owner.x < xcenter and r < rmax:
            xdir = 1
        # pick 'x area' of dungeon
        if xdir == -1:
            xmin = 0
            xmax = round(constants.MAP_WIDTH * 0.33)
        elif xdir == 1:
            xmin = round(constants.MAP_WIDTH * 0.66)
            xmax = constants.MAP_WIDTH - 1
        else:
            xmin = round(constants.MAP_WIDTH * 0.33)
            xmax = round(constants.MAP_WIDTH * 0.66)
        # y pos
        ycenter = constants.MAP_HEIGHT // 2
        ydir = randint(-1,1)
        rmax = 4
        r = randint(0,rmax)
        if self.owner.y > ycenter and r < rmax:
            ydir = -1
        elif self.owner.y < ycenter and r < rmax:
            ydir = 1
        # pick 'y area' of dungeon
        if ydir == -1:
            ymin = 0
            ymax = round(constants.MAP_HEIGHT * 0.33)
        elif ydir == 1:
            ymin = round(constants.MAP_HEIGHT * 0.66)
            ymax = constants.MAP_HEIGHT - 1
        else:
            ymin = round(constants.MAP_HEIGHT * 0.33)
            ymax = round(constants.MAP_HEIGHT * 0.66)
        
        # check for blocked
        invalid = True
        while invalid:
            # new coordinates
            x = randint(xmin, xmax)
            y = randint(ymin, ymax)
            invalid = _dungeon.is_blocked(x,y)
            
        # set new coordinates
        if not(invalid):
            self.target_x = x
            self.target_y = y
            
    # Fight! (return turns used)
    def take_fight(self):
        #move towards player if not close enough to strike
        if self.pdistance > constants.MIN_PDIST:
            # check for state change to wander
            if self.state_turns > 10 and _dungeon.turn - self.last_attack_turn > (self.owner.fighter.move_speed() * 12):
                self.change_state(states.WANDER)
                return self.take_movetarget()
                
            # shout a curse at player
            if self.state_turns < 2 and self.pdistance <= _dungeon.player.fov:
                _dungeon.game.message(self.owner.name + ' shouts "' + choice(self.curses) + '"', colors.light_violet)
                # shout makes a noise!
                _dungeon.make_noise(self.owner.x, self.owner.y, randint(5,10))
        
            #logging.info('%s wants to move towards player. distance = %s', self.owner.name, self.pdistance)
            _dungeon.move_astar(self.owner, self.last_px, self.last_py)
            #return turns used
            return self.owner.fighter.move_speed()
        else:
            #close enough, attack!
            self.owner.fighter.attack(_dungeon.player)
            #track turn
            self.last_attack_turn = _dungeon.turn
            return self.owner.fighter.attack_speed()

"""
Bard AI
"""
class BardNPC(NPC):
        def __init__(self, hearing = 0.1, laziness = 0.2, 
                vision_range = constants.START_VISION+1, flee_health=0.7, flee_chance=0.8, 
                curses=['It hates the music!']):
                
            # bard's music stats
            self.music_range = 4
            self.music_power = 4
            self.music_speed = 1.1
            
            # flee distance
            self.flee_dist = randint(2,self.music_range)
            
            self.owner = None
            
            self.fov_radius = vision_range
            
            # flee thresholds
            self.flee_health = flee_health
            self.flee_chance = flee_chance
        
            # begin sleeping
            self.state = states.SLEEP
            self.last_state = states.SLEEP
            self.state_turns = 0 # how many turns current state has been active
            
            # distance to player at last calculation
            self.pdistance = 0
            
            # turn count last time player was attacked
            self.last_attack_turn = -1
            
            # visible tiles
            self.view = None
            
            # last known player position
            self.last_px = None
            self.last_py = None
            
            # last target position (while wandering)
            self.target_x = None
            self.target_y = None
            
            # hearing chance (to wake up or be alerted that player is near)
            self.hearing = hearing
            
            # chance to fall asleep
            self.laziness = laziness
            
            # fight shouts
            self.curses = curses
            
        def take_turn(self):
            monster = self.owner
            
            # monster pathfinding
            self.pdistance = _dungeon.distance_to(monster, _dungeon.player)
            
            logging.debug('%s: %s distance from player', self.owner.name, self.pdistance)
            
            self.view = None
            
            # determine if it falls asleep while player far away
            if self.pdistance > constants.MAX_HEAR_DIST and not(self.state == states.SLEEP):
                if self.state_turns > 20 and randfloat(0,1) <= self.laziness:
                    self.change_state(states.SLEEP)
            # if monster sees player... 
            elif self.pdistance < constants.MAX_HEAR_DIST:
                # fov (store visible tiles)
                self.view = tdl.map.quickFOV(monster.x, monster.y, is_visible_tile, radius = self.fov_radius)
                # if player could be seen...
                if self.player_in_view():
                    # strong chance to wake from sleep
                    if self.state == states.SLEEP:
                        if randfloat(0,1) < 0.9:
                            self.change_state(states.FIGHT)
                    # fight or flee player in view...
                    else:
                        # flee - Bard flees based on distance from player!
                        if self.pdistance < self.flee_dist and len(_dungeon.combatants) < 2 and (self.pdistance > constants.MIN_PDIST or randfloat(0,1) <= self.flee_chance):
                            self.change_state(states.FLEE)
                        # otherwise fight
                        else:
                            self.change_state(states.FIGHT)
                        
            # record player position if visible
            if not(self.state == states.SLEEP) and self.player_in_view():
                self.last_px = _dungeon.player.x
                self.last_py = _dungeon.player.y
                        
            # count turns in state
            self.state_turns += 1
            
            # set color by state
            self.owner.color = self.calc_color()
            
            if self.state == states.SLEEP:
                return self.take_sleep()
                
            if self.state == states.WANDER:
                return self.take_movetarget()
                
            if self.state == states.FIGHT:
                return self.take_fight()
                
            if self.state == states.FLEE:
                return self.take_flee()
                
        # Fight! (return turns used)
        def take_fight(self):
            
            #move towards player if not close enough to strike
            if self.pdistance > constants.MIN_PDIST:
                # check for state change to wander
                if self.state_turns > 10 and _dungeon.turn - self.last_attack_turn > (self.owner.fighter.move_speed() * 12):
                    self.change_state(states.WANDER)
                    return self.take_movetarget()
                    
                # shout a curse at player
                if self.state_turns < 2 and self.pdistance <= _dungeon.player.fov:
                    _dungeon.game.message(self.owner.name + ' shouts "' + choice(self.curses) + '"', colors.light_violet)
                    # shout makes a noise!
                    _dungeon.make_noise(self.owner.x, self.owner.y, randint(5,10))
            
                # see if we need to move in range of music...
                if self.pdistance <= self.music_range and self.player_in_view():
                    # play music! (attack ranged)
                    dmg = randint(1, self.music_power)
                    shortname = (chr(14)*dmg) + ' ' + strleft_back(self.owner.name, ' the ')
                    atk_color = colors.light_flame
                    _dungeon.player.fighter.take_damage(shortname, 'pierces', 'merry music', atk_color, dmg)
                    return self.music_speed
                else:
                    _dungeon.move_astar(self.owner, self.last_px, self.last_py)
                    return self.owner.fighter.move_speed()
                    
            else:
                #forced to attack with bad dagger weapon
                self.owner.fighter.attack(_dungeon.player)
                #track turn
                self.last_attack_turn = _dungeon.turn
                return self.owner.fighter.attack_speed()
        
        
            
            
        
"""
Monster AI (tough monster)
"""
class BossMonster(NPC):
    #AI for boss monster
    def __init__(self, dungeon, fov_algo = constants.FOV_ALGO, vision_range = constants.START_VISION+1, 
        flee_health=0, flee_chance=0, curses=['Tonight you die by my hand, monster!']):
        
        NPC.__init__(self, hearing = 0.9, laziness = 0.05, 
            vision_range = constants.START_VISION+1, flee_health=0.08, flee_chance=0.1)
            
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
        


COLOR_BONUS = colors.dark_green
COLOR_PENALTY = colors.dark_flame

"""
Bonus to Power method
"""
def bonus_power():
    # penalize speed
    penalty_speed()

    _dungeon.player.fighter.power += constants.POWER_BONUS
    _dungeon.game.message("Consuming your enemy's " + constants.PART_POWER + ' makes you feel stronger!', COLOR_BONUS)
    
    #try_penalty(penalty_vision, penalty_speed, penalty_defense)
    return True
            
"""
Penalty to Power method
"""
def penalty_power():
    _dungeon.player.fighter.power = max(_dungeon.player.fighter.power + constants.POWER_PENALTY, constants.MIN_POWER)
    _dungeon.game.message("Eating the " + constants.PART_SPEED + " makes you feel weaker, too.", COLOR_PENALTY)

"""
Bonus to Defense method
"""
def bonus_defense():
    # penalize vision
    penalty_vision()

    _dungeon.player.fighter.defense += constants.DEFENSE_BONUS
    _dungeon.game.message("Consuming your enemy's " + constants.PART_DEFENSE + ' makes you feel tougher!', COLOR_BONUS)
   
    #try_penalty(penalty_vision, penalty_power, penalty_speed)
    return True    
    
"""
Penalty to Defense method
"""
def penalty_defense():
    _dungeon.player.fighter.defense = max(_dungeon.player.fighter.defense + constants.DEFENSE_PENALTY, constants.MIN_DEFENSE)
    _dungeon.game.message("Eating the " + constants.PART_FOV + " makes you feel less tough, too.", COLOR_PENALTY)

"""
Bonus to Speed method
"""
def bonus_speed():
    # penalize power
    penalty_power()
    
    # boost speed
    _dungeon.player.fighter.speed = max(constants.MIN_SPEED, _dungeon.player.fighter.speed + constants.SPEED_BONUS)
    
    _dungeon.game.message("Consuming your enemy's " + constants.PART_SPEED + ' makes you feel faster!', COLOR_BONUS)
   
    #try_penalty(penalty_vision, penalty_power, penalty_defense)
    return True
    
"""
Penalty to Speed method
"""
def penalty_speed():
    _dungeon.player.fighter.speed = min(_dungeon.player.fighter.speed + constants.SPEED_PENALTY, constants.MAX_SPEED)
    _dungeon.game.message("Eating the " + constants.PART_POWER + " makes you feel slower, too.", COLOR_PENALTY)
    
"""
Bonus to Vision method
"""
def bonus_vision():
    # penalize defense
    penalty_defense()

    _dungeon.game.fov_recompute = True
    _dungeon.player.fov += constants.VISION_BONUS
    _dungeon.game.message("Consuming your enemy's " + constants.PART_FOV + ' improves your vision!', COLOR_BONUS)
    
    #try_penalty(penalty_speed, penalty_power, penalty_defense)
    return True
    
"""
Penalty to Speed method
"""
def penalty_vision():
    _dungeon.game.fov_recompute = True
    _dungeon.player.fov = max(_dungeon.player.fov + constants.VISION_PENALTY, constants.MIN_VISION)
    _dungeon.game.message("Eating the " + constants.PART_DEFENSE + " makes your vision worse, too.", COLOR_PENALTY)
    
"""
Randomly select a paramaterless function from choices...
"""
def try_penalty(penalty1, penalty2, penalty3):
    pen = choice([penalty1, penalty2, penalty3])
    pen()
        

### CAST SPELLS ###
def cast_heal():
    #logging.info('casting heal...')

    #heal the player
    if _dungeon.player.fighter.hp == _dungeon.player.fighter.max_hp:
        _dungeon.game.message("You should save this for when you're wounded.", colors.red)
        return False
 
    _dungeon.game.message("You consume your enemy's heart! Your heal " + str(constants.HEAL_AMOUNT) + ' damage.', colors.light_violet)
    _dungeon.player.fighter.heal(constants.HEAL_AMOUNT)
    
    return True
    
def cast_lightning(caster_gameobj=None):
    #logging.info('casting lightning...')
    
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
    #logging.info('casting fireball...')

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
    
    
"""
Randomly rotate a point (x,y) within a set of clockface 'positions'
"""
clockwise = [(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)]
counter =   [(-1,0), (-1,1), (0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1)]
def rotate_pt(point, turn_clockwise=True):
    #logging.debug('rotate %s. clockwise=%s', point, turn_clockwise)
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
    
    