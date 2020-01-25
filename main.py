#!/usr/bin/env python3

# Very hacky spaced repetition character practice system for Chinese.

import os, sys
import pickle
import hashlib
import math
import numpy as np
import datetime

DB_PATH = "db.pickle"

# Database contains the following keys:
# "cycle":
#   Integer representing how many times the generate feature has been used.
# "characters":
#   Dict of CJK characters mapped to a tuple (as a list) of integers:
#       [times_occurred, times_used, last_used]
#   where:
#       times_occurred is the number of times the character appears in the input files.
#       times_used     is the number of times the character has been selected
#       last_used      is the cycle value when the character was last selected
#   These are used to score characters, so that the most frequently used characters that haven't
#   been selected recently are most likely to be selected.
#   Note that it's a list instead of a tuple so that we can update part of it more conveniently.
# "max_used":
#   How many times the most frequently used character has been used.
# "max_occurrences":
#   Highest times_occurred value.
# "input_hashes":
#   Set of SHA512 hashes of input files, so that files don't get loaded more than once.

TIMES_OCCURRED = 0
TIMES_USED     = 1
LAST_USED      = 2

#####################################
# Database load and save operations #
#####################################

# note: database uses pickle, which is not very secure. Make sure the database file can be trusted.
def load_db(path=DB_PATH):
    if not os.path.isfile(path):
        print("Database file does not exist, using empty database.")
        return {
            "cycle": 0,
            "characters": dict(),
            "max_used": 1,
            "max_occurrences": 0,
            "input_hashes": set(),
        }
    try:
        f = open(path, 'rb')
        return pickle.load(f)
    except Exception as e:
        print("Failed to load database:", e)
        return False

# note: this function performs unsafe path concatenation. So don't feed it a dodgy path.
def save_db(db, path=DB_PATH):
    old_dir_path = "old/"

    try:
        if os.path.isfile(path):
            # file exists, so move it to the "old/" directory marked with its modification time
            if not os.path.isdir(old_dir_path):
                # if old directory doesn't exist, create it
                os.mkdir(old_dir_path)

            # get file stats
            stat = os.stat(path)

            os.rename(path, old_dir_path + path + '.' + str(int(stat.st_mtime)))
        f = open(path, 'xb')
        pickle.dump(db, f)
        return True        
    except Exception as e:
        print("Failed to save database:", e)
        return False

################################
# Character handling functions #
################################

# note: only returns True for actual Chinese characters/radicals,
# including those that are only used as kanji or hanji
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

#####################
# Adding characters #
#####################

# adds unique characters from a file to the db, if the file is not in input_hashes
def add_text(db, path, override_hashing = False):
    # read the file's bytes into memory
    try:
        with open(path, 'rb') as f: # binary mode, do not convert to text yet
            data = f.read()
    except:
        print("Failed to read file")
        return False

    if not override_hashing:
        # hash the file and check if we've already added it
        sha512 = hashlib.sha512(data).digest()
        if sha512 in db['input_hashes']:
            print("File already in database!")
            return False
        # we haven't added it yet, so store its hash now
        db['input_hashes'].add(sha512)

    # decode the file as utf8
    try:
        text = data.decode(encoding='utf-8')
    except:
        print("Failed to decode file as utf-8")
        return False

    # get rid of the undecoded version now, might free some memory
    del data

    # get a shorter name for db['characters']
    # this will be a reference to the dict in the db, not a copy
    chars = db["characters"]

    # ditto for max_occurrences, but this time it will have to be copied back to the db at the
    # end of the function as it's an int, which will be copied rather than referenced.
    max_occurrences = db["max_occurrences"]

    # iterate over each character, incrementing the count in the db for matching characters
    for c in text:
        if is_hanzi(c):
            if c not in chars:
                # first time we've seen this character
                chars[c] = [1, 0, 0] # seen once, never selected, considered last used on cycle 0
            else:
                occ = chars[c][TIMES_OCCURRED] + 1 # seen once more
                chars[c][TIMES_OCCURRED] = occ
                if occ > max_occurrences:
                    max_occurrences = occ

    db["max_occurrences"] = max_occurrences

    return True

#############################3
# Generating character lists #
##############################

def generate(db, n_chars):
    cycle = db["cycle"] + 1
    max_used = db["max_used"]
    max_occurrences = db["max_occurrences"]
    db_chars = db["characters"]

    if max_occurrences < 1:
        raise Exception("max_occurrences is zero, meaning there are no characters in the db!")

    # produce a score for each character indicating how likely it should be to be selected
    scores = []
    charlist  = [] # keep a list of each character where the index is the same as the index for its score
    for c, d in db["characters"].items():
        occurred, used, last = d
        
        occur_score = occurred / max_occurrences
        used_score  = (max_used - used) / max_used
        since_last  = (cycle - last) / cycle
        if since_last > 0:
            since_last = math.log2(since_last + 1)

        scores.append((occur_score * 2 + used_score) * since_last)
        charlist.append(c)

    # convert scores array to np.array then normalize it so the probabilities sum to 1
    scores = np.array(scores)
    scores /= scores.sum(0)

    # select n_chars randomly, weighted by the score.
    # the selection is made without replacement, i.e., there will not be duplicates
    indices = list(np.random.choice(len(charlist), n_chars, False, scores))

    output = []
    for index in indices:
        c = charlist[index]
        output.append(c)

        # update character usage info
        occur, used, _ = db_chars[c]
        used += 1
        if used > max_used:
            max_used = used
        db_chars[c] = [occur, used, cycle]

    db["cycle"] = cycle
    db["max_used"] = max_used

    return output

#########################
# HTML table generation #
#########################

# Generates HTML output for a character practice sheet
def html_table(chars, n_boxes, n_pages):
    td_width  = (n_boxes + 1)
    td_height = len(chars) / n_pages
    date = datetime.date.today().isoformat()

    # The font-size value for td was found experimentally.
    # This seems to actually work for making everything fit on the page,
    # but I have *no idea* why. HTML/CSS is TERRIBLE.

    print(\
"""<!DOCTYPE html>
<html>
<head><title>Randomly Generated Spaced-Repetition Character Sheet {}</title>
<style>
table {{
    width: 100%;
    border-spacing: 0px;
    border-collapse: collapse;
    margin: 0px;
    padding: 0px;
}}
td {{
    border: 1px solid black;
    width: {}%;
    font-size: {}vh;
    text-align: center;
    padding: 0px;
    margin: 0px;
}}
a {{
    color: black;
    text-decoration: none;
}}
</style>
</head>
<body><table>""".format(date, 100 / td_width, 65 / td_height))
   
    # generate the boxes / terminators once, rather than every loop
    boxes = "</td>" + "<td></td>" * n_boxes + "</tr>"
    for i, c in enumerate(chars):
        a = """<a href="https://zici.info/decomp/#{}N">{}</a>""".format(hex(ord(c))[2:], c)
        print("<tr><td>" + a + boxes)
    print("</table></body></html>")
    return True

########
# Main #
########

# the database is saved if this function returns True
def main(db):
    # default to generate if no arguments given
    if len(sys.argv) < 2 or sys.argv[1].startswith("gen"):
        # default to 30 chars
        n_chars = int(sys.argv[2]) if len(sys.argv) >= 3 else 30
        gen = generate(db, n_chars)
        if sys.argv[1].endswith("html"):
            # default to 5 boxes for writing characters
            n_boxes = int(sys.argv[3]) if len(sys.argv) >= 4 else 10
            n_pages = int(sys.argv[4]) if len(sys.argv) >= 5 else 2
            return html_table(gen, n_boxes, n_pages)
        else:
            print(gen)
            return True
    elif sys.argv[1] == "add":
        if len(sys.argv) < 3:
            print("Path of file to add required.")
            return False
        return add_text(db, sys.argv[2])
    elif sys.argv[1] == "dump":
        print(db)
        return False # no need to save, we only dumped the db
    else:
        print("Invalid arguments.")
        return False

if __name__ == "__main__":
    db = load_db()
    if main(db):
        save_db(db)
