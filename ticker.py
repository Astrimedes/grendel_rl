#!/usr/bin/env python3
import random

class Ticker(object):
    """Simple timer for roguelike games."""

    def __init__(self):
        self.ticks = 0  # current ticks--sys.maxint is 2147483647
        self.schedule = {}  # this is the dict of things to do {ticks: [obj1, obj2, ...], ticks+1: [...], ...}

    def schedule_turn(self, interval, obj):
        self.schedule.setdefault(self.ticks + interval, []).append(obj)

    def next_turn(self):
        things_to_do = self.schedule.pop(self.ticks, [])
        for obj in things_to_do:
            # act, return turns used
            ticks_used = obj.do_tick()
            # reschedule if not None
            if ticks_used:
                self.schedule_turn(ticks_used, obj)
            
#    Example main program

if __name__== "__main__":
    class Monster(object):
        """Fake monster for demo."""
        def __init__(self, ticker):
            self.ticker = ticker
            self.speed = 6 + random.randrange(1, 6)  # random speed in 7 - 12
            self.ticker.schedule_turn(self.speed, self) # schedule monsters 1st move

        def do_turn(self):
            print(str(self) + " gets a turn at " + str(self.ticker.ticks)) # just print a message
            self.ticker.schedule_turn(self.speed, self)     # and schedule the next turn
            
        def __repr__(self):
            return 'Monster speed: ' + str(self.speed)

    ticker = Ticker()  #  create our ticker
    print(str(ticker.schedule))

    monsters = []  #  create some monsters for the demo
    while len(monsters) < 5:
        monsters.append(Monster(ticker))
    print(str(ticker.schedule))

    while ticker.ticks < 51:  #  our main program loop
        ticker.ticks += 1
        ticker.next_turn()