###############################
# Character handling functions #
################################

# note: only returns True for actual Chinese characters/radicals,
# including those that are only used as kanji or hanja
# but NOT for kana/hangul/punctuation/raw strokes/weird duplicates/etc
def is_hanzi(char):
    # checks if the codepoint is within a CJK block as per https://en.wikipedia.org/wiki/Unicode_block
    codepoint = ord(char)
    
    # first eliminate regions that are definitely out of range.
    
    # CJK Unified Ideographs Extension A is the lowest block, and begins at U+3400.
    if codepoint < 0x3400:
        return False
    
    # CJK Compatibility Ideographs Supplement is the highest block, and ends at U+2FA1F.
    if codepoint > 0x2FA1F:
        return False

    # now check the limits of each block to see if it's within one.
    # only less-than comparisons will be used, eliminating out-of-range regions where possible.
    
    # CJK Unified Ideographs Extension A ends at U+4DBF
    if codepoint <= 0x4DBF: # (greater than 0x3400 implied by above 'if')
        return True

    # CJK Unified Ideographs begins at U+4E00 and ends at U+9FFF (majority are here)
    if   codepoint <  0x4E00:
        return False
    elif codepoint <= 0x9FFF:
        return True

    # CJK Compatibility Ideographs begins at U+F900, ends at U+FAFF
    if   codepoint <  0xF900:
        return False
    elif codepoint <= 0xFAFF:
        return True

    # CJK Unified Ideographs B through F as well as Supplement are joined.
    # They begin at U+20000 and end at U+2FA1F
    if   codepoint <  0x20000:
        return False
    elif codepoint <= 0x2FA1F:
        return True
    
    # no more blocks we care about above this point, return False
    return False

