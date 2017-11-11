#!/usr/bin/env python3

"""
Enum class where you can refer to members as attributes
stores each element as a tuple of (ordinal value, print name)
"""
class Enum:    
    """
    Initialize with a list of tuples of (attr name, print name)
    ...OR simply a list of strings, where attribute name == print name
    """
    def __init__(self, members=None):
    
        self.all_members = []
        
        self.idx = -1
        
        if members:
            for m in members:
                self.add_element(m)
        
    def __len__(self):
        return self.count()
            
    def all(self):
        return self.all_members
        
    def nameof(self, state):
        return state[1]
        
    def valueof(self, state):
        return state[0]
        
    def from_name(self, name):
        for s in self.all_members:
            if self.nameof(s) == name:
                return s
        return None
        
    def from_value(self, value):
        for s in self.all_members:
            if self.valueof(s) == value:
                return s
        return None
        
    def count(self):
        return self.idx + 1
    
    """
    Add a new enum element at the end of the current set
    new_element is either a tuple of (attr_name,print_name) or a string (interpreted as (string,string)))
    """
    def add_element(self, new_element):
        i = self.idx + 1
        if isinstance(new_element, str):
            # set attr name element to a tuple of (index, attr name)
            attr = new_element
            element = (i, new_element)
        else:
            # set attr name element to a tuple of (index, print name)
            attr = new_element[0]
            element = (i, new_element[1])
            
        if hasattr(self, attr):
            raise ValueError('Enums must have unique element attribute names!', attr)
        
        #add new element
        setattr(self, attr, element)
        self.all_members.append(element)
            
        # set top index
        self.idx = i
        