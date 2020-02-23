import re

# CEDECT format according to https://cc-cedict.org/wiki/format:syntax
# Groups, as separated by regions of whitespace:
# 1: Traditional (Match anything not a space)
# 2: Simplified (Match anything not a space) 
# 3: Pinyin (Match anything not a closing bracket)
# deviation from official format below
# 4: English Definitions (Everything after the / until the end of the line
# (any slashed definitions are left joined together)
ENTRY_REGEX = re.compile(r"(\S+)\s+(\S+)\s+\[([^]]+)\]\s+/(.+)/")

TRAD_INDEX   = 0
PINYIN_INDEX = 1
DEF_INDEX    = 2

def load(path='cedict_1_0_ts_utf-8_mdbg.txt'):
    defs = {}

    for line in open(path):
        if len(line) < 1 or line[0] == '#':
            # skip empty or comment lines
            continue
      
        # match line according to regex, breaking it into individual strings
        match = ENTRY_REGEX.match(line)
        if match:
            # unpack the matched groups
            trad, simp, pinyin, definition = match.group(1,2,3,4)

            # repack to array
            newdef = [trad, pinyin, definition]

            # add it to the main definition dict
            if simp not in defs:
                defs[simp] = []
            defs[simp].append(newdef)
        else:
            print("Line '{}' failed to match.".format(line))

    return defs
