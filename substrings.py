#!/usr/bin/env python3

"""
Extract the word_count number of words (L to R) using separator sep
"""
def extract_words(text, word_count, sep=' '):
    for i in range(0, len(text)):
        # count separator
        if text[i] == sep:
            word_count -= 1
        if word_count == 0:
            # slice to just last separator
            return text[0:i]
    return ''
    
"""
Return the string to the left of the first occurrence (L to R) of the substring
"""
def strleft(text, substring):
    #index of substr
    idx_match = 0
    for i in range(0, len(text)):
        if text[i] == substring[idx_match]:
            idx_match += 1
            if idx_match >= len(substring):
                #slice to just before substr
                return text[0:i-len(substring)+1]
    return text