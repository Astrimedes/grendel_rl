#!/usr/bin/env python3
# This game started from the excellent python roguelike tutorial at: http://www.roguebasin.com/index.php?title=Roguelike_Tutorial,_using_python3%2Btdl #

import tcod
import tdl

import constants
import colors
import game

from random import randint

import math

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
            return False
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner)  #destroy after use, unless it was 
                                              #cancelled for some reason
                return True
                
 
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
        
        self.max_pathsize = constants.DEFAULT_PATHSIZE
 
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self
 
        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self
 
        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self 
        
        
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
            self.owner.dungeon.game.message(self.owner.name.capitalize() + ' attacks ' + target.name + 
                  ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage)
        else:
            self.owner.dungeon.game.message(self.owner.name.capitalize() + ' attacks ' + target.name + 
                  ' but it has no effect!')
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
            
            
class Dungeon:

    def __init__(self, game):
        global _dungeon
        _dungeon = self
        
        self.game = game
    
        self.player = None
        self.objects = []
        self.map = None
        self.inventory = None
        self.visible_tiles = []
        self.fov_recompute = True

    def create_player(self):
        #create object representing the player
        fighter_component = Fighter(hp=30, defense=2, power=5, 
                                    death_function=self.player_death)
     
        self.player = GameObject(self, 0, 0, '@', 'player', colors.white, blocks=True, 
                        fighter=fighter_component)
        
        # player creates the objects list when made 'new'
        self.objects.append(self.player)
            
    ### MAP CREATION ###
    def make_map(self):
     
        #fill map with "blocked" tiles
        self.map = [[ Tile(True)
            for y in range(constants.MAP_HEIGHT) ]
                for x in range(constants.MAP_WIDTH) ]
     
        rooms = []
        num_rooms = 0
     
        for r in range(constants.MAX_ROOMS):
            #random width and height
            w = randint(constants.ROOM_MIN_SIZE, constants.ROOM_MAX_SIZE)
            h = randint(constants.ROOM_MIN_SIZE, constants.ROOM_MAX_SIZE)
            #random position without going out of the boundaries of the map
            x = randint(0, constants.MAP_WIDTH-w-1)
            y = randint(0, constants.MAP_HEIGHT-h-1)
     
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
                self.create_room(new_room)
     
                #center coordinates of new room, will be useful later
                (new_x, new_y) = new_room.center()
     
                if num_rooms == 0:
                    #this is the first room, where the player starts at
                    self.player.x = new_x
                    self.player.y = new_y
     
                else:
                    #all rooms after the first:
                    #connect it to the previous room with a tunnel
     
                    #center coordinates of previous room
                    (prev_x, prev_y) = rooms[num_rooms-1].center()
     
                    #draw a coin (random number that is either 0 or 1)
                    if randint(0, 1):
                        #first move horizontally, then vertically
                        self.create_h_tunnel(prev_x, new_x, prev_y)
                        self.create_v_tunnel(prev_y, new_y, new_x)
                    else:
                        #first move vertically, then horizontally
                        self.create_v_tunnel(prev_y, new_y, prev_x)
                        self.create_h_tunnel(prev_x, new_x, new_y)
     
                #add some contents to this room, such as monsters
                self.place_objects(new_room)
     
                #finally, append the new room to the list
                rooms.append(new_room)
                num_rooms += 1

    def create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.map[x][y].blocked = False
            self.map[x][y].block_sight = False
     
    def create_v_tunnel(self, y1, y2, x):
        #vertical tunnel
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.map[x][y].blocked = False
            self.map[x][y].block_sight = False
            
    def create_room(self, room):
        #go through the tiles in the rectangle and make them passable
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.map[x][y].blocked = False
                self.map[x][y].block_sight = False
                
    def place_objects(self, room):
        #choose random number of monsters
        num_monsters = randint(0, constants.MAX_ROOM_MONSTERS)
     
        for i in range(num_monsters):
            #choose random spot for this monster
            x = randint(room.x1+1, room.x2-1)
            y = randint(room.y1+1, room.y2-1)
     
     
            #only place it if the tile is not blocked
            if not self.is_blocked(x, y):
                if randint(0, 100) < 80:  #80% chance of getting an orc
                    #create an orc
                    fighter_component = Fighter(hp=10, defense=0, power=3, 
                                                death_function=self.monster_death)
                                                
                    # random vision range for some variety
                    ai_component = BasicMonster(self, constants.FOV_ALGO, randint(3, 6))
     
                    monster = GameObject(self, x, y, 'o', 'orc', colors.desaturated_green,
                        blocks=True, fighter=fighter_component, ai=ai_component)
                else:
                    #create a troll
                    fighter_component = Fighter(hp=16, defense=1, power=4,
                                                death_function=self.monster_death)
                    
                    # troll is better at tracking the player down
                    ai_component = BasicMonster(constants.FOV_ALGO, randint(6, 10))
     
                    monster = GameObject(self, x, y, 'T', 'troll', colors.darker_green,
                        blocks=True, fighter=fighter_component, ai=ai_component)
     
                self.objects.append(monster)
     
        #choose random number of items
        num_items = randint(0, constants.MAX_ROOM_ITEMS)
     
        for i in range(num_items):
            #choose random spot for this item
            x = randint(room.x1+1, room.x2-1)
            y = randint(room.y1+1, room.y2-1)
     
            #only place it if the tile is not blocked
            if not self.is_blocked(x, y):
                dice = randint(0, 100)
                if dice < 70:
                    #create a healing potion (70% chance)
                    item_component = Item(use_function=self.cast_heal)
     
                    item = GameObject(self, x, y, '!', 'healing potion', 
                                      colors.violet, item=item_component)
     
                elif dice < 70+10:
                    #create a lightning bolt scroll (15% chance)
                    item_component = Item(use_function=self.cast_lightning)
     
                    item = GameObject(self, x, y, '#', 'scroll of lightning bolt', 
                                      colors.light_yellow, item=item_component)
     
                elif dice < 70+10+10:
                    #create a fireball scroll (10% chance)
                    item_component = Item(use_function=self.cast_fireball)
     
                    item = GameObject(self, x, y, '#', 'scroll of fireball', 
                                      colors.light_yellow, item=item_component)
     
                else:
                    #create a confuse scroll (15% chance)
                    item_component = Item(use_function=self.cast_confuse)
     
                    item = GameObject(self, x, y, '#', 'scroll of confusion', 
                                      colors.light_yellow, item=item_component)
     
                self.objects.append(item)
                self.send_to_back(item)  #items appear below other self.objects

                
    ### MAP QUERIES ###
    def distance(self, game_obj, x, y):
        #return the distance to some coordinates
        return math.sqrt((x - game_obj.x) ** 2 + (y - game_obj.y) ** 2)
     
    def distance_to(self, game_obj, other_game_obj):
        #return the distance to another object
        return self.distance(game_obj, other_game_obj.x, other_game_obj.y)

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
        
    def closest_monster(max_range):
        #find closest enemy, up to a maximum range, and in the player's FOV
        closest_enemy = None
        closest_dist = max_range + 1  #start with (slightly more than) maximum range
     
        for obj in self.objects:
            if obj.fighter and not obj == self.player and (obj.x, obj.y) in self.visible_tiles:
                #calculate distance between this object and the player
                dist = player.distance_to(obj)
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
            return True
        return False
 
    def move_towards(self,  game_obj, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
 
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(game_obj, dx, dy)
        
        
    def move_astar(self, game_obj, target):
        #Create a FOV map that has the dimensions of the map
        fov = tcod.map_new(constants.MAP_WIDTH, constants.MAP_HEIGHT)
 
        #Scan the current map each turn and set all the walls as unwalkable
        for y1 in range(constants.MAP_HEIGHT):
            for x1 in range(constants.MAP_WIDTH):
                tcod.map_set_properties(fov, x1, y1, not self.map[x1][y1].block_sight, not self.map[x1][y1].blocked)
 
        #Scan all the self.objects to see if there are self.objects that must be navigated around
        #Check also that the object isn't self or the target (so that the start and the end points are free)
        #The AI class handles the situation if self is next to the target so it will not use this A* function anyway   
        for obj in self.objects:
            if obj.blocks and obj != self and obj != target:
                #Set the tile as a wall so it must be navigated around
                tcod.map_set_properties(fov, obj.x, obj.y, True, False)
 
        #Allocate a A* path
        my_path = tcod.path_new_using_map(fov, 1.0)
        
        #Compute the path between self's coordinates and the target's coordinates
        tcod.path_compute(my_path, game_obj.x, game_obj.y, target.x, target.y)
 
        #Check if the path exists, and in this case, also the path is shorter than 25 tiles
        #The path size matters if you want the monster to use alternative longer paths (for example through other rooms) if for example the player is in a corridor
        #It makes sense to keep path size relatively low to keep the monsters from running around the map if there's an alternative path really far away        
        if not tcod.path_is_empty(my_path) and tcod.path_size(my_path) < game_obj.max_pathsize:
            #Find the next coordinates in the computed full path
            x, y = tcod.path_walk(my_path, True)
            if x or y:
                #Set game_obj's coordinates to the next path tile
                game_obj.x = x
                game_obj.y = y
        else:
            #Keep the old move function as a backup so that if there are no paths (for example another monster blocks a corridor)
            #it will still try to move towards the player (closer to the corridor opening)
            self.move_towards(game_obj, target.x, target.y)  
 
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
        
        acted = False
        
        #attack if target found, move otherwise
        if target is not None:
            self.player.fighter.attack(target)
            acted = True
        else:
            acted = self.move(self.player, dx, dy)
            if acted:
                self.fov_recompute = True
        
        return acted

    def player_wait(self):
        self.game.message('You wait.')
        
    def player_death(self):
        #the game ended!
        self.game.message('You died!', colors.red)
        self.game.game_state = constants.STATE_DEAD
     
        #for added effect, transform the player into a corpse!
        self.player.char = '%'
        self.player.color = colors.dark_red
        
    def ai_act(self):
        for obj in self.objects:
            if obj.ai:
                obj.ai.take_turn()
     
    def monster_death(self, monster):
        #transform it into a nasty corpse! it doesn't block, can't be
        #attacked and doesn't move
        self.game.message(monster.name.capitalize() + ' is dead!', colors.orange)
        
        monster.char = '%'
        monster.color = colors.dark_red
        monster.blocks = False
        monster.fighter = None
        monster.ai = None
        monster.name = 'remains of ' + monster.name
        monster.send_to_back()


     ### CAST SPELLS ###
    def cast_heal(self):
        #heal the player
        if self.player.fighter.hp == self.player.fighter.max_hp:
            self.game.message('You are already at full health.', colors.red)
            return 'cancelled'
     
        self.game.message('Your wounds start to feel better!', colors.light_violet)
        self.player.fighter.heal(constants.HEAL_AMOUNT)
     
    def cast_lightning():
        #find closest enemy (inside a maximum range) and damage it
        monster = self.closest_monster(constants.LIGHTNING_RANGE)
        if monster is None:  #no enemy found within maximum range
            self.game.message('No enemy is close enough to strike.', colors.red)
            return 'cancelled'
     
        #zap it!
        self.game.message('A lighting bolt strikes the ' + monster.name + ' with a loud ' +
                'thunder! The damage is ' + str(constants.LIGHTNING_DAMAGE) + ' hit points.', 
                colors.light_blue)
     
        monster.fighter.take_damage(constants.LIGHTNING_DAMAGE)
     
    def cast_confuse():
        #ask the player for a target to confuse
        self.game.message('Left-click an enemy to confuse it, or right-click to cancel.', 
                colors.light_cyan)
        monster = target_monster(constants.CONFUSE_RANGE)
        if monster is None:
            self.game.message('Cancelled')
            return 'cancelled'
     
        #replace the monster's AI with a "confused" one; after some turns it will 
        #restore the old AI
        old_ai = monster.ai
        monster.ai = ConfusedMonster(old_ai)
        monster.ai.owner = monster  #tell the new component who owns it
        self.game.message('The eyes of the ' + monster.name + ' look vacant, as he starts to ' +
                'stumble around!', colors.light_green)
     
    def cast_fireball():
        #ask the player for a target tile to throw a fireball at
        self.game.message('Left-click a target tile for the fireball, or right-click to ' +
                'cancel.', colors.light_cyan)
     
        (x, y) = self.target_tile()
        if x is None: 
            self.game.message('Cancelled')
            return 'cancelled'
        self.game.message('The fireball explodes, burning everything within ' + 
                str(constants.FIREBALL_RADIUS) + ' tiles!', colors.orange)
     
        for obj in self.objects:  #damage every fighter in range, including the player
            if self.distance(obj, x, y) <= constants.FIREBALL_RADIUS and obj.fighter:
                self.game.message('The ' + obj.name + ' gets burned for ' + 
                        str(constants.FIREBALL_DAMAGE) + ' hit points.', colors.orange)
     
                obj.fighter.take_damage(constants.FIREBALL_DAMAGE)

 
    def send_to_back(self, game_obj):
        #make this object be drawn first, so all others appear above it if 
        #they're in the same tile.
        self.objects.remove(game_obj)
        self.objects.insert(0, game_obj)
        
        
class BasicMonster:

    def __init__(self, dungeon, fov_algo = constants.FOV_ALGO, vision_range = constants.TORCH_RADIUS):
        self.fov = fov_algo
        self.fov_radius = vision_range
        self.dungeon = dungeon

    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn.
        monster = self.owner
        
        # monster pathfinding
        monster_view = tdl.map.quickFOV(monster.x, monster.y,
                                         is_visible_tile,
                                         self.fov,
                                         radius=self.fov_radius,
                                         lightWalls=constants.FOV_LIGHT_WALLS)
        
        if (self.dungeon.player.x, self.dungeon.player.y) in monster_view:
 
            #move towards player if far away
            if self.dungeon.distance_to(monster, self.dungeon.player) >= 2:
                #monster.move_towards(player.x, player.y)
                self.dungeon.move_astar(monster, self.dungeon.player)
 
            #close enough, attack! (if the player is still alive.)
            elif self.dungeon.player.fighter.hp > 0:
                monster.fighter.attack(self.dungeon.player)
        
 
class ConfusedMonster:
    #AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=constants.CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns
        self.dungeon = old_ai.dungeon
 
    def take_turn(self):
        if self.num_turns > 0:  #still confused...
            #move in a random direction, and decrease the number of turns confused
            self.dungeon.move(self.owner, randint(-1, 1), randint(-1, 1))
            self.num_turns -= 1
 
        else:  
            #restore the previous AI (this one will be deleted because it's not 
            #referenced anymore)
            self.owner.ai = self.old_ai
            self.dungeon.game.message('The ' + self.owner.name + ' is no longer confused!', colors.red)
            
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
