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

from enumerations import Enum

import constants

# tile types
tiles = Enum([('STONE',' '), ('FLOOR','.'), ('WALL','#')])

# types of 'special rooms'
rtypes = Enum(['BIGROOM','NORMAL','CAMP','BEOWULF','THRONE'])

                   
class Room:
    def __init__(self, x, y, width, height, rtype=rtypes.NORMAL):
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        
        # room type
        self.rtype = rtype
        
    def center(self):
        return ( (self.x + (self.w//2), self.y + (self.h//2)) )
        
    def __repr__(self):
        return '(x: ' + str(self.x) + ', y: ' + str(self.y) + ', w: ' + str(self.w) + ', h:' + str(self.h) + ')'
 
class Generator():
    def __init__(self, width=64, height=64, max_rooms=15, min_room_xy=5,
                 max_room_xy=10, rooms_overlap=False, random_connections=1,
                 random_spurs=3):
        self.width = width
        self.height = height
        self.max_rooms = max_rooms
        self.min_room_xy = min_room_xy
        self.max_room_xy = max_room_xy
        self.rooms_overlap = rooms_overlap
        self.random_connections = random_connections
        self.random_spurs = random_spurs
        self.level = []
        self.room_list = []
        self.corridor_list = []
        self.tiles_level = []
 
    def gen_room(self):
        # x, y, w, h = 0, 0, 0, 0
 
        # w = random.randint(self.min_room_xy, self.max_room_xy)
        # h = random.randint(self.min_room_xy, self.max_room_xy)
        # x = random.randint(2, (self.width - w - 2))
        # y = random.randint(2, (self.height - h - 2))
 
        # return [x, y, w, h]
        return self.gen_room_in_region(region_x=0, region_y=0, region_w=self.width, region_h=self.height)
        
    def gen_room_in_region(self, region_x, region_y, region_w, region_h):
        x, y, w, h = 0, 0, 0, 0
 
        w = random.randint(self.min_room_xy, self.max_room_xy)
        h = random.randint(self.min_room_xy, self.max_room_xy)
        
        minx = region_x+1
        miny = region_y+1
        
        x = random.randint(minx, (region_x + region_w - w - 2))
        y = random.randint(miny, (region_y + region_h - h - 2))
 
        #create a room
        return Room(x, y, w, h)
        
    def gen_large_room_in_region(self, region_x, region_y, region_w, region_h):
        x, y, w, h = 0, 0, 0, 0
 
        newmin = min(constants.BIGROOM_MIN_W, max(region_w-6, 1))
        newmax = min(constants.BIGROOM_MAX_W, max(region_w-4, 2))
        w = random.randint(newmin, newmax)
        
        newmin = min(constants.BIGROOM_MIN_H,  max(region_h-6, 1))
        newmax = min(constants.BIGROOM_MAX_H, max(region_h-4, 2))
        h = random.randint(newmin, newmax)
        
        minx = region_x+1
        miny = region_y+1
        
        x = random.randint(minx, max((minx + region_w - w - 2),minx+1))
        y = random.randint(miny, max((miny + region_h - h - 2),miny+1))
        
        rm = Room(x, y, w, h, rtype = rtypes.BIGROOM)
 
        #create a room
        return rm
 
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
 
            if (x < (current_room.x + current_room.w) and
                current_room.x < (x + w) and
                y < (current_room.y + current_room.h) and
                current_room.y < (y + h)):
 
                return True
 
        return False
 
 
    def corridor_between_points(self, x1, y1, x2, y2, join_type='either'):
        if x1 == x2 and y1 == y2 or x1 == x2 or y1 == y2:
            return [(x1, y1), (x2, y2)]
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
                return [(x1, y1), (x1, y2), (x2, y2)]
            elif join is 'bottom':
                return [(x1, y1), (x2, y1), (x2, y2)]
 
    def join_rooms(self, room_1, room_2, join_type='either'):
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
 
            corridors = self.corridor_between_points(jx1, jy1, jx2, jy2)
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
 
            corridors = self.corridor_between_points(jx1, jy1, jx2, jy2)
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
                        jx1, jy1, jx2, jy2, 'bottom')
                    self.corridor_list.append(corridors)
                else:
                    jx1 = random.randint(x1, x1_2)
                    jy1 = y1 - 1
                    jx2 = x2 - 1
                    jy2 = random.randint(y2, y2_2)
                    corridors = self.corridor_between_points(
                        jx1, jy1, jx2, jy2, 'top')
                    self.corridor_list.append(corridors)
 
            elif join is 'bottom':
                if y2 > y1:
                    jx1 = random.randint(x1, x1_2)
                    jy1 = y1_2 + 1
                    jx2 = x2 - 1
                    jy2 = random.randint(y2, y2_2)
                    corridors = self.corridor_between_points(
                        jx1, jy1, jx2, jy2, 'top')
                    self.corridor_list.append(corridors)
                else:
                    jx1 = x1_2 + 1
                    jy1 = random.randint(y1, y1_2)
                    jx2 = random.randint(x2, x2_2)
                    jy2 = y2_2 + 1
                    corridors = self.corridor_between_points(
                        jx1, jy1, jx2, jy2, 'bottom')
                    self.corridor_list.append(corridors)

    def gen_level(self):
 
        # build an empty dungeon, blank the room and corridor lists
        for i in range(self.height):
            self.level.append([tiles.STONE] * self.width)
            
        self.room_list = []
        self.corridor_list = []
        
        # divide the dungeon up into 4 'regions' to generate rooms inside of
        regions = []
        pw = self.width // 3
        ph = self.height // 3
        regions.append((0, 0, pw, self.height))
        regions.append((pw, 0, pw, self.height))
        regions.append((pw*2, 0, pw, self.height))
        
        # 'large room' chance
        lrg_rm = 0.08
 
        # FIRST REGIONS
        # start generating rooms in the first 'normal' regions
        max_region_rooms = self.max_rooms // 3
        max_iters = max_region_rooms * 4
        last = len(regions)-1
        while len(self.room_list) < self.max_rooms:
            for i, r in enumerate(regions):
                rr = 0
                if i < last:
                    for a in range(max_iters):
                        # generate the room
                        tmp_room = self.gen_room_in_region(r[0], r[1], r[2], r[3])
             
                        if self.rooms_overlap or not self.room_list:
                            self.room_list.append(tmp_room)
                            rr += 1
                        else:
                            # generate the room
                            tmp_room = self.gen_room_in_region(r[0], r[1], r[2], r[3])
                            
                            tmp_room_list = self.room_list[:]
             
                            if not(self.room_overlapping(tmp_room, tmp_room_list)):
                                self.room_list.append(tmp_room)
                                rr += 1
             
                        if rr >= max_region_rooms:
                            break
 
        # connect the rooms thus far
        for a in range(len(self.room_list) - 1):
            self.join_rooms(self.room_list[a], self.room_list[a + 1])
 
        # do the random joins
        for a in range(self.random_connections):
            room_1 = self.room_list[random.randint(0, len(self.room_list) - 1)]
            room_2 = self.room_list[random.randint(0, len(self.room_list) - 1)]
            self.join_rooms(room_1, room_2)
        
        # do the spurs
        for a in range(self.random_spurs):
            room_1 = Room(random.randint(2, self.width - 2), random.randint(2, self.height - 2), 1, 1)
            room_2 = self.room_list[random.randint(0, len(self.room_list) - 1)]
            self.join_rooms(room_1, room_2)
            del room_1
        
        # LAST REGION
        # now fill in last region with several small rooms
        rindex = len(self.room_list)-1 # index of room previous to this region
        r = regions[last]
        sr = 0
        sr_target = 3
        for a in range(max_iters):
            fits = False
            # generate the small rooms
            if sr < sr_target:
                tmp_room_list = self.room_list[:]
                while not(fits):
                    tmp_room = self.gen_room_in_region(r[0], r[1], r[2], r[3])
                    fits = self.rooms_overlap or not(self.room_list) or not(self.room_overlapping(tmp_room, tmp_room_list))
                self.room_list.append(tmp_room)
                sr += 1
            else:
                break
        # and now several large rooms
        lr = 0
        lr_target = 2
        for a in range(max_iters):
            fits = False
            # generate the large rooms
            if lr < lr_target:
                tmp_room_list = self.room_list[:]
                while not(fits):
                    tmp_room = self.gen_large_room_in_region(r[0], r[1], r[2], r[3])
                    fits = self.rooms_overlap or not(self.room_list) or not(self.room_overlapping(tmp_room, tmp_room_list))
                self.room_list.append(tmp_room)
                lr += 1
            
        # connect the rooms in the new region
        max_index = len(self.room_list)-1
        if max_index >= rindex + 2:
            for i in range(rindex+1, max_index):
                self.join_rooms(self.room_list[i], self.room_list[i+1])
        
        # make one connection to previous rooms
        min_rm = max(0, rindex - 2)
        r1 = self.room_list[random.randint(0, rindex)]
        r2 = self.room_list[random.randint(rindex+1, len(self.room_list)-1)]
        self.join_rooms(r1, r2)
            
 
        # fill the map
        # paint rooms x,y,w,h
        for room_num, room in enumerate(self.room_list):
            for b in range(room.w):
                for c in range(room.h):
                    self.level[room.y + c][room.x + b] = tiles.FLOOR
 
        # paint corridors
        for corridor in self.corridor_list:
            x1, y1 = corridor[0]
            x2, y2 = corridor[1]
            for width in range(abs(x1 - x2) + 1):
                for height in range(abs(y1 - y2) + 1):
                    self.level[min(y1, y2) + height][
                        min(x1, x2) + width] = tiles.FLOOR
 
            if len(corridor) == 3:
                x3, y3 = corridor[2]
 
                for width in range(abs(x2 - x3) + 1):
                    for height in range(abs(y2 - y3) + 1):
                        self.level[min(y2, y3) + height][
                            min(x2, x3) + width] = tiles.FLOOR
 
        # paint the walls
        for row in range(0, self.height - 1):
            for col in range(0, self.width - 1):
                if self.level[row][col] == tiles.FLOOR:
                    if self.level[row - 1][col - 1] == tiles.STONE:
                        self.level[row - 1][col - 1] = tiles.WALL
 
                    if self.level[row - 1][col] == tiles.STONE:
                        self.level[row - 1][col] = tiles.WALL
 
                    if self.level[row - 1][col + 1] == tiles.STONE:
                        self.level[row - 1][col + 1] = tiles.WALL
 
                    if self.level[row][col - 1] == tiles.STONE:
                        self.level[row][col - 1] = tiles.WALL
 
                    if self.level[row][col + 1] == tiles.STONE:
                        self.level[row][col + 1] = tiles.WALL
 
                    if self.level[row + 1][col - 1] == tiles.STONE:
                        self.level[row + 1][col - 1] = tiles.WALL
 
                    if self.level[row + 1][col] == tiles.STONE:
                        self.level[row + 1][col] = tiles.WALL
 
                    if self.level[row + 1][col + 1] == tiles.STONE:
                        self.level[row + 1][col + 1] = tiles.WALL
 
    def gen_tiles_level(self):
 
        for row_num, row in enumerate(self.level):
            tmp_tiles = []
 
            for col_num, col in enumerate(row):
                if col == tiles.STONE:
                    tmp_tiles.append(tiles.STONE[1])
                if col == tiles.FLOOR:
                    tmp_tiles.append(tiles.FLOOR[1])
                if col == tiles.WALL:
                    tmp_tiles.append(tiles.WALL[1])
 
            self.tiles_level.append(''.join(tmp_tiles))
 
        print('Room List: ', self.room_list)
        print('\nCorridor List: ', self.corridor_list)
 
        [print(row) for row in self.tiles_level]
