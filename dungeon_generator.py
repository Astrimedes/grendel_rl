#! /usr/bin/env python
# coding: utf-8
 
# adapted from a simple python dungeon generator by
# James Spencer <jamessp [at] gmail.com>.

# To the extent possible under law, the person who associated CC0 with
# pathfinder.py has waived all copyright and related or neighboring rights
# to pathfinder.py.

# You should have received a copy of the CC0 legalcode along with this
# work. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
 
from __future__ import print_function
import random

from enum import Enum

import constants

import tcod

import colors
# tuples of color configs:
# (light_ground, light_wall, dark_ground, dark_wall)
# COLORS_NORMAL = (colors.light_sepia,  colors.sepia, colors.darkest_azure, colors.darkest_gray)
# COLORS_BOSS = (colors.flame,  colors.dark_flame, colors.darkest_sepia, colors.darkest_orange)

light_floor = (158,134,100) #light_sepia
light_wall = (127,101,63) #sepia
dark_floor = (0,31,63) #darkest_azure
dark_wall = (31,31,31) #darkest_grey

light_boss_floor = (98,100,32)
dark_boss_floor = (26,21,45)
light_boss_wall = (61,52,107)
dark_boss_wall =  (31,0,61)


import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# tile types
class TileTypes(Enum):
    STONE = (True, ' ', light_wall, dark_wall)
    FLOOR = (False, '.', light_floor, dark_floor)
    BOSS_FLOOR = (False, ',', light_boss_floor, dark_boss_floor)
    WALL = (True, '#', light_wall, dark_wall)
    BOSS_WALL = (True, '+', light_boss_wall, dark_boss_wall)
    
    def __init__(self, blocked, char, color_light, color_dark):
        self.blocked = blocked
        self.char = char
        self.color_light = color_light
        self.color_dark = color_dark
    

# types of 'special rooms'
class AreaTypes(Enum):
    PLAYER = 1
    BOSS = 2
    NORMAL = 3
                   
class Room:
    def __init__(self, x, y, width, height, atype=AreaTypes.NORMAL):
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        
        # room type
        self.rtype = atype
        
    def center(self):
        return ( (self.x + (self.w//2), self.y + (self.h//2)) )
        
    def __repr__(self):
        return '(x: ' + str(self.x) + ', y: ' + str(self.y) + ', w: ' + str(self.w) + ', h:' + str(self.h) + ')'
        
class Corridor:
    def __init__(self, points_list, atype=AreaTypes.NORMAL):
        self.points = points_list
        self.atype = atype
        
    def __delitem__(self, key):
        self.points.remove(self.points[key])
        
    def __getitem__(self, key):
        return self.points[key]
        
    def __setitem__(self, key, value):
        self.points[key] = value
        
    def __len__(self):
        return len(self.points)
    
 
class Generator():
    def __init__(self, width=64, height=64, max_rooms=15, min_room_xy=5,
                 max_room_xy=10):
        self.width = width
        self.height = height
        
        self.max_rooms = max_rooms
        self.min_room_xy = min_room_xy
        self.max_room_xy = max_room_xy
        
        self.init_lists()
        
    def init_lists(self):
        self.level = []
        self.room_list = []
        self.corridor_list = []
        self.tiles_level = []
        self.regions = []
        
    def clear_lists(self):
        del self.level
        del self.room_list
        del self.corridor_list
        del self.tiles_level
        del self.regions
        
    def gen_room_in_region(self, region_x, region_y, region_w, region_h, atype=AreaTypes.NORMAL):
        x, y, w, h = 0, 0, 0, 0
 
        w = random.randint(self.min_room_xy, self.max_room_xy)
        h = random.randint(self.min_room_xy, self.max_room_xy)
        
        minx = region_x+1
        miny = region_y+1
        
        x = random.randint(minx, (region_x + region_w - w - 4))
        y = random.randint(miny, (region_y + region_h - h - 4))
 
        #create a room
        return Room(x, y, w, h, atype)
        
    def gen_large_room_in_region(self, region_x, region_y, region_w, region_h, atype=AreaTypes.BOSS):
        x, y, w, h = 0, 0, 0, 0
 
        newmin = min(constants.BIGROOM_MIN_W, max(region_w-6, 1))
        newmax = min(constants.BIGROOM_MAX_W, max(region_w-4, 2))
        w = random.randint(newmin, newmax)
        
        newmin = min(constants.BIGROOM_MIN_H,  max(region_h-6, 1))
        newmax = min(constants.BIGROOM_MAX_H, max(region_h-4, 2))
        h = random.randint(newmin, newmax)
        
        minx = region_x+1
        miny = region_y+1
        
        x = random.randint(minx, max((minx + region_w - w - 4),minx+1))
        y = random.randint(miny, max((miny + region_h - h - 4),miny+1))
 
        #create a room
        return Room(x, y, w, h, atype)
 
    def room_overlapping(self, room, room_list):
        x = room.x
        y = room.y
        w = room.w
        h = room.h
        
        # out of bounds
        if x + w + 1 > self.width or y + h + 1 > self.height or x - 1 < 0 or y - 1 < 0:
            return True
 
        for current_room in room_list:
 
            # The rectangles don't overlap if
            # one rectangle's minimum in some dimension
            # is greater than the other's maximum in
            # that dimension.
 
            if (x-1 < (current_room.x + current_room.w) and
                current_room.x-1 < (x + w) and
                y-1 < (current_room.y + current_room.h) and
                current_room.y-1 < (y + h)):
 
                return True
        return False
 
 
    def corridor_between_points(self, x1, y1, x2, y2, join_type='either', atype=AreaTypes.NORMAL):
        if x1 == x2 and y1 == y2 or x1 == x2 or y1 == y2:
            return Corridor([(x1, y1), (x2, y2)], atype)
        else:
            # 2 Corridors
            # NOTE: Never randomly choose a join that will go out of bounds
            # when the walls are added.
            join = None
            if join_type is 'either' and set([0, 1]).intersection(
                 set([x1, x2, y1, y2])):
 
                join = 'bottom'
            elif join_type is 'either' and set([self.width - 1,
                 self.width - 2]).intersection(set([x1, x2])) or set(
                 [self.height - 1, self.height - 2]).intersection(
                 set([y1, y2])):
 
                join = 'top'
            elif join_type is 'either':
                join = random.choice(['top', 'bottom'])
            else:
                join = join_type
 
            if join is 'top':
                return Corridor([(x1, y1), (x1, y2), (x2, y2)], atype)
            elif join is 'bottom':
                return Corridor([(x1, y1), (x2, y1), (x2, y2)], atype)
 
    def join_rooms(self, room_1, room_2, join_type='either', atype=AreaTypes.NORMAL):
        # sort by the value of x
        sorted_room = [room_1, room_2]
        sorted_room.sort(key=lambda r: r.x)
 
        x1 = sorted_room[0].x
        y1 = sorted_room[0].y
        w1 = sorted_room[0].w
        h1 = sorted_room[0].h
        x1_2 = x1 + w1 - 1
        y1_2 = y1 + h1 - 1
 
        x2 = sorted_room[1].x
        y2 = sorted_room[1].y
        w2 = sorted_room[1].w
        h2 = sorted_room[1].h
        x2_2 = x2 + w2 - 1
        y2_2 = y2 + h2 - 1
 
        # overlapping on x
        if x1 < (x2 + w2) and x2 < (x1 + w1):
            jx1 = random.randint(x2, x1_2)
            jx2 = jx1
            tmp_y = [y1, y2, y1_2, y2_2]
            tmp_y.sort()
            jy1 = tmp_y[1] + 1
            jy2 = tmp_y[2] - 1
 
            corridors = self.corridor_between_points(jx1, jy1, jx2, jy2, atype=atype)
            self.corridor_list.append(corridors)
 
        # overlapping on y
        elif y1 < (y2 + h2) and y2 < (y1 + h1):
            if y2 > y1:
                jy1 = random.randint(y2, y1_2)
                jy2 = jy1
            else:
                jy1 = random.randint(y1, y2_2)
                jy2 = jy1
            tmp_x = [x1, x2, x1_2, x2_2]
            tmp_x.sort()
            jx1 = tmp_x[1] + 1
            jx2 = tmp_x[2] - 1
 
            corridors = self.corridor_between_points(jx1, jy1, jx2, jy2, atype=atype)
            self.corridor_list.append(corridors)
 
        # no overlap
        else:
            join = None
            if join_type is 'either':
                join = random.choice(['top', 'bottom'])
            else:
                join = join_type
 
            if join is 'top':
                if y2 > y1:
                    jx1 = x1_2 + 1
                    jy1 = random.randint(y1, y1_2)
                    jx2 = random.randint(x2, x2_2)
                    jy2 = y2 - 1
                    corridors = self.corridor_between_points(
                        jx1, jy1, jx2, jy2, 'bottom', atype)
                    self.corridor_list.append(corridors)
                else:
                    jx1 = random.randint(x1, x1_2)
                    jy1 = y1 - 1
                    jx2 = x2 - 1
                    jy2 = random.randint(y2, y2_2)
                    corridors = self.corridor_between_points(
                        jx1, jy1, jx2, jy2, 'top', atype)
                    self.corridor_list.append(corridors)
 
            elif join is 'bottom':
                if y2 > y1:
                    jx1 = random.randint(x1, x1_2)
                    jy1 = y1_2 + 1
                    jx2 = x2 - 1
                    jy2 = random.randint(y2, y2_2)
                    corridors = self.corridor_between_points(
                        jx1, jy1, jx2, jy2, 'top', atype)
                    self.corridor_list.append(corridors)
                else:
                    jx1 = x1_2 + 1
                    jy1 = random.randint(y1, y1_2)
                    jx2 = random.randint(x2, x2_2)
                    jy2 = y2_2 + 1
                    corridors = self.corridor_between_points(
                        jx1, jy1, jx2, jy2, 'bottom', atype)
                    self.corridor_list.append(corridors)

    def gen_level(self):
    
        # clear out any previous generation
        self.clear_lists()
        self.init_lists()
 
        # build an empty dungeon, blank the room and corridor lists
        for i in range(self.height):
            self.level.append([TileTypes.STONE] * self.width)
        #self.level = [[TileTypes.STONE for y in range(self.height)] for x in range(self.width)]
        
        # divide the dungeon up into 4 'regions' to generate rooms inside of
        w = int(self.width * 0.45)
        h = int(self.height * 0.45)
        x1 = 0
        x2 = self.width - w - 1
        y1 = 0
        y2 = self.height - h - 1
        
        # set the 'regions' used
        r1 = (x1, y1, w, h)
        r2 = (x2, y1, w, h)
        r3 = (x2, y2, w, h)
        r4 = (x1, y2, w, h)
        self.regions.extend([r1, r2, r3, r4])
        proom_idx = 0
        # determine whether to reverse dungeon layout randomly...
        rev = random.randint(0,1) == 0
        if rev:
            self.regions.reverse()
            proom_idx = 3
            
 
        # FIRST REGIONS
        rindex = -1
        # start generating rooms in the first 'normal' regions
        max_region_rooms = self.max_rooms // 4
        max_iters = max_region_rooms * 4
        last = len(self.regions)-1
        for i, r in enumerate(self.regions):
            rr = 0
            tries = 0
            if i < last:
                while rr < max_region_rooms and tries < max_iters:
                    tries += 1
                    
                    # generate the rooms
                    tmp_room = self.gen_room_in_region(r[0], r[1], r[2], r[3])
                        
                    tmp_room_list = self.room_list[:]
     
                    if not(self.room_overlapping(tmp_room, tmp_room_list)):
                        self.room_list.append(tmp_room)
                        rr += 1
         
                    if rr >= max_region_rooms:
                        break
                        
                # connect the rooms in this region
                for a in range(rindex+1, len(self.room_list)-1):
                    self.join_rooms(self.room_list[a], self.room_list[a + 1])
                    
                # do a number of random room joins in this region
                joins = random.randint(3,4+i)
                for i in range(joins):
                    r1 = self.room_list[random.randint(rindex+1, len(self.room_list)-1)]
                    r2 = self.room_list[random.randint(rindex+1, len(self.room_list)-1)]
                    while r1 is r2:
                        r2 = self.room_list[random.randint(rindex+1, len(self.room_list)-1)]
                    self.join_rooms(r1, r2)
                
                # connect to previous region
                if i > 0:
                    for i in range(random.randint(2,3)):
                        r1 = self.room_list[rindex-i]
                        r2 = self.room_list[random.randint(rindex+1, len(self.room_list)-1)]
                        self.join_rooms(r1, r2)
                # last room in this region, for next iteration
                rindex = len(self.room_list)-1
 
        # mark first room as 'player start'
        self.room_list[proom_idx].rtype = AreaTypes.PLAYER
        
        # LAST REGION
        r = self.regions[last]
        # and now several large rooms
        target = len(self.room_list) + 3
        fits = False
        tmp_room_list = self.room_list[:]
        for a in range(max_iters):
            # generate the large rooms
            tmp_room = self.gen_large_room_in_region(r[0], r[1], r[2], r[3], atype=AreaTypes.BOSS)
            fits = not(self.room_overlapping(tmp_room, tmp_room_list))
            if fits:
                self.room_list.append(tmp_room)
                if len(self.room_list) >= target:
                    break;
        # fill in last region with several small rooms
        target = len(self.room_list) + 5
        fits = False
        tmp_room_list = self.room_list[:]
        for a in range(max_iters):
            # generate the small rooms
            tmp_room = self.gen_room_in_region(r[0], r[1], r[2], r[3], atype=AreaTypes.BOSS)
            fits = not(self.room_overlapping(tmp_room, tmp_room_list))
            if fits:
                self.room_list.append(tmp_room)
                if len(self.room_list) >= target:
                    break;
            
        # connect the rooms in the new region
        max_index = len(self.room_list)-1
        if max_index >= rindex + 2:
            for i in range(rindex+1, max_index):
                self.join_rooms(self.room_list[i], self.room_list[i+1], atype = AreaTypes.BOSS)
        
        # make one connection to a previous region
        r1 = self.room_list[rindex]
        r2 = self.room_list[random.randint(rindex+1, len(self.room_list)-1)]
        self.join_rooms(r1, r2, atype = AreaTypes.BOSS)
 
        # fill the map
        
        # paint rooms
        for room in self.room_list:
            for b in range(room.w):
                for c in range(room.h):
                    ttype = TileTypes.FLOOR
                    if room.rtype is AreaTypes.BOSS:
                        ttype = TileTypes.BOSS_FLOOR
                    self.level[room.y + c][room.x + b] = ttype
        
        # paint corridors
        for corridor in self.corridor_list:
            x1, y1 = corridor[0]
            x2, y2 = corridor[1]
            
            ttype = TileTypes.FLOOR
            if corridor.atype is AreaTypes.BOSS:
                ttype = TileTypes.BOSS_FLOOR
            
            for width in range(abs(x1 - x2) + 1):
                for height in range(abs(y1 - y2) + 1):
                    self.level[min(y1, y2) + height][
                        min(x1, x2) + width] = ttype
                        
            if len(corridor) == 3:
                x3, y3 = corridor[2]    
                for width in range(abs(x2 - x3) + 1):
                    for height in range(abs(y2 - y3) + 1):
                        self.level[min(y2, y3) + height][
                            min(x2, x3) + width] = ttype
 
        # paint the walls
        normals = [TileTypes.STONE, TileTypes.WALL]
        # paint boss areas
        for row in range(0, self.height - 1):
            for col in range(0, self.width - 1):
                if self.level[row][col] is TileTypes.BOSS_FLOOR:
                    if self.level[row - 1][col - 1] in normals:
                        self.level[row - 1][col - 1] = TileTypes.BOSS_WALL
 
                    if self.level[row - 1][col] in normals:
                        self.level[row - 1][col] = TileTypes.BOSS_WALL
 
                    if self.level[row - 1][col + 1] in normals:
                        self.level[row - 1][col + 1] = TileTypes.BOSS_WALL
 
                    if self.level[row][col - 1] in normals:
                        self.level[row][col - 1] = TileTypes.BOSS_WALL
 
                    if self.level[row][col + 1] in normals:
                        self.level[row][col + 1] = TileTypes.BOSS_WALL
 
                    if self.level[row + 1][col - 1] in normals:
                        self.level[row + 1][col - 1] = TileTypes.BOSS_WALL
 
                    if self.level[row + 1][col] in normals:
                        self.level[row + 1][col] = TileTypes.BOSS_WALL
 
                    if self.level[row + 1][col + 1] in normals:
                        self.level[row + 1][col + 1] = TileTypes.BOSS_WALL
                        
        #paint 'normal' areas
        for row in range(0, self.height - 1):
            for col in range(0, self.width - 1):
                if self.level[row][col] is TileTypes.FLOOR:
                    if self.level[row - 1][col - 1] is TileTypes.STONE:
                        self.level[row - 1][col - 1] = TileTypes.WALL
 
                    if self.level[row - 1][col] is TileTypes.STONE:
                        self.level[row - 1][col] = TileTypes.WALL
 
                    if self.level[row - 1][col + 1] is TileTypes.STONE:
                        self.level[row - 1][col + 1] = TileTypes.WALL
 
                    if self.level[row][col - 1] is TileTypes.STONE:
                        self.level[row][col - 1] = TileTypes.WALL
 
                    if self.level[row][col + 1] is TileTypes.STONE:
                        self.level[row][col + 1] = TileTypes.WALL
 
                    if self.level[row + 1][col - 1] is TileTypes.STONE:
                        self.level[row + 1][col - 1] = TileTypes.WALL
 
                    if self.level[row + 1][col] is TileTypes.STONE:
                        self.level[row + 1][col] = TileTypes.WALL
 
                    if self.level[row + 1][col + 1] is TileTypes.STONE:
                        self.level[row + 1][col + 1] = TileTypes.WALL
        
        return self.test_level()
    
    
    """
    Pathfinding check - return True if valid map and False if not
    """
    def test_level(self):
    
        success = False
        try:
            if len(self.level) != self.height:
                print('Invalid level height! Actual = {0}, Requested = {1}'.format(len(self.level), self.height))
                return False
            
            for r in self.level:
                if len(r) != self.width:
                    print('Invalid level width! Actual = {0}, Requested = {1}'.format(len(r), self.width))
                    return False
                    
            # guarantee a minimum number of rooms
            if len(self.room_list) < (constants.MAX_ROOMS // 2):
                print('Invalid room count! Actual = %i, Requested = %i'.format(len(r), self.width))
                return False
            
            # now pathfind to sanity check!
            p_room = [room for room in self.room_list if room.rtype is AreaTypes.PLAYER][0]
            b_room = [room for room in self.room_list if room.rtype is AreaTypes.BOSS][0]
            success = self.test_pathfind(p_room, b_room)
        finally:
            return success
        
        
    def test_pathfind(self, room_start, room_end):
        #Create a FOV map that has the dimensions of the map
        fov = tcod.map_new(self.width, self.height)
 
        #Scan the current map and set all the walls as unwalkable
        for y1 in range(self.height):
            for x1 in range(self.width):
                open = not (self.level[y1][x1].blocked)
                tcod.map_set_properties(fov, x1, y1, open, open)
                
        #Allocate a A* path
        my_path = tcod.path_new_using_map(fov, 1.0)

        # find at least one empty tile in room_start
        blocked = True
        while blocked:
            for x in range(room_start.w):
                x1 = room_start.x + x
                for y in range(room_start.h):
                    y1 = room_start.y + y
                    blocked = self.level[y1][x1].blocked
                    if not blocked:
                        break
                if not blocked:
                    break
                    
        # find at least one empty tile in room_end
        blocked = True
        while blocked:
            for x in range(room_end.w):
                x2 = room_end.x + x
                for y in range(room_end.h):
                    y2 = room_end.y + y
                    blocked = self.level[y2][x2].blocked
                    if not blocked:
                        break
                if not blocked:
                    break
        
        # use our two empty tiles to path
        tcod.path_compute(my_path, x1, y1, x2, y2)
 
        #Walk the path
        success = False
        if my_path and not tcod.path_is_empty(my_path):
            success = True
            while not tcod.path_is_empty(my_path):
                x, y = tcod.path_walk(my_path,True)
                if x is None :
                    print('Pathfinding failed during walk!')
                    success = False
                    break
        else:
            print('Pathfinding failed to create a path!')
        
        #Delete the path to free memory
        tcod.path_delete(my_path)
        
        return success
 
    """
    Print tile chars of map
    """
    def gen_tiles_level(self):
 
        for row_num, row in enumerate(self.level):
            tmp_tiles = []
 
            for col_num, col in enumerate(row):
                tmp_tiles.append(col.char)
 
            self.tiles_level.append(''.join(tmp_tiles))
 
        [print(row) for row in self.tiles_level]
        
    def __repr__(self):
        return 'Rooms: {0}, Corridors: {1}, Dimensions: {2}x{3}, Regions: {4}'.format(
            len(self.room_list), len(self.corridor_list), len(self.level[0]), len(self.level), self.regions)

    
def try_break_map():
    success = 0
    fail = 0
    gen = Generator(width=constants.MAP_WIDTH, height=constants.MAP_HEIGHT,
                max_rooms=constants.MAX_ROOMS, min_room_xy=constants.ROOM_MIN_SIZE,
                max_room_xy=constants.ROOM_MAX_SIZE)
                
    while True:
        check = gen.gen_level()
        if check:
            success += 1
        else:
            fail += 1
            gen.gen_tiles_level()
            print('Failed!')
            
        print('Fail: ' + str(fail) + ', Success: ' + str(success))
        
if __name__ == '__main__':
    import sys

    gen = Generator(width=constants.MAP_WIDTH, height=constants.MAP_HEIGHT,
                max_rooms=constants.MAX_ROOMS, min_room_xy=constants.ROOM_MIN_SIZE,
                max_room_xy=constants.ROOM_MAX_SIZE)
    
    sys.stdout = open('dungen_examples.log', 'w')
    
    for i in range(100):
        if not(gen.gen_level()):
            print('Failure!!! See below:')
        gen.gen_tiles_level()
        print(gen)
