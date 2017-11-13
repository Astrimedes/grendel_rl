#!/usr/bin/env python3

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
Return the string to the Left of the FIRST occurrence (L to R) of the substring
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
    
"""
Return the string to the Right of the FIRST occurrence (L to R) of the substring
"""
def strright(text, substring):
    #index of substr
    idx_match = 0
    for i in range(0, len(text)):
        if text[i] == substring[idx_match]:
            idx_match += 1
            if idx_match >= len(substring):
                #slice to after substr
                return text[i+1:len(text)]
    return text
    
"""
Return the string to the Right of the LAST occurrence (L to R) of the substring
"""
def strright_back(text, substring):
    #index of substr
    idx_match = len(substring)-1
    for i in range(len(text)-1, -1, -1):
        if text[i] == substring[idx_match]:
            idx_match -= 1
            if idx_match < 0:
                #slice to after substr
                return text[i+len(substring):len(text)]
    return text
    
"""
Return the string to the Left of the LAST occurrence (L to R) of the substring
"""
def strleft_back(text, substring):
    #index of substr
    idx_match = len(substring)-1
    for i in range(len(text)-1, -1, -1):
        if text[i] == substring[idx_match]:
            idx_match -= 1
            if idx_match < 0:
                #slice to just before substr
                return text[0:i]
    return text
    
"""
Returns a string with items listed as '1, 2, and 3'
"""
def format_list(strings):
    if len(strings) > 1:
        text = ', '.join(strings)
        text = strleft_back(text, ', ') + ', and ' + strright_back(text, ', ')
        return text
    else:
        s = strings[0]
        return s
        

"""
Return 'a' or 'an' appropriately for single objects, or None for multiple objects (if text has a comma)
"""
vowels = ['a','e','i','o','u','A','E','I','O','U']
def get_article(text):
    # no text
    if not(text):
        return None
    # multiple objects - no article
    if ',' in text:
        return None
    # An for vowels
    if text[0] in vowels:
        return 'an'
    else:
        return 'a'


"""
Tests
"""
if __name__ == '__main__':
    text = 'Dude the First the Last'
    sub = ' the '
    logging.info("strleft('%s', '%s') = %s", text, sub, "'" + strleft(text, sub) + "'")
    logging.info("strleft_back('%s', '%s') = %s", text, sub, "'" + strleft_back(text, sub) + "'")
    logging.info("strright('%s', '%s') = %s", text, sub, "'" + strright(text, sub) + "'")
    logging.info("strright_back('%s', '%s') = %s", text, sub, "'" + strright_back(text, sub) + "'")
    
    text = 'first, second, third, fourth'
    sub = ', '
    logging.info("strleft_back('%s', '%s') + ', and' + strright_back('%s', '%s') = %s",
        text, sub, text, sub, strleft_back(text, sub) + ', and ' + strright_back(text, sub))
        
    list = ['first','second','third']
    logging.info("format_list(%s) = %s", list, format_list(list))
    

        
    