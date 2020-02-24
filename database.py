import os
import math
import pickle, json
import hashlib
import numpy as np

from charhandling import *

DB_PATH = "db.pickle"

# Database contains the following keys:
# "cycle":
#   Integer representing how many times the generate feature has been used.
# "chars":
#   Dict of CJK characters mapped to a tuple (as a list) of integers:
#       [times_occurred, times_used, last_used]
#   where:
#       times_occurred is the number of times the character appears in the input files.
#       times_used     is the number of times the character has been selected
#       last_used      is the cycle value when the character was last selected
#   These are used to score characters, so that the most frequently used characters that haven't
#   been selected recently are most likely to be selected.
#   Note that it's a list instead of a tuple so that we can update part of it more conveniently.
# "first_seen":
#   Dict of characters to labels of the document where this character was seen for the first time.
# "max_used":
#   How many times the most frequently used character has been used.
# "max_occurrences":
#   Highest times_occurred value.
# "input_hashes":
#   Dict of of SHA512 hashes of input files to a list containing the file's label and a list
#   of new characters introduced in this file.
#   Prevents files from being loaded more than once and helps keep track of introduced characters.
# "blacklist":
#   Characters which should never be generated (because they are too easy or whatever)

TIMES_OCCURRED = 0
TIMES_USED     = 1
LAST_USED      = 2

class Database:
    def __init__(self):
        self.cycle           = 0
        self.chars           = dict()
        self.first_seen      = dict()
        self.max_used        = 1
        self.max_occurrences = 0
        self.input_hashes    = dict()
        self.blacklist       = set()

    #####################
    # Adding characters #
    #####################

    # adds unique characters from a file to the db, if the file is not in input_hashes
    def add_text(db, path, label, override_hashing = False):
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
            if sha512 in db.input_hashes:
                print("File already in database! Label: '{}'".format(db.input_hashes[sha512][0]))
                choice = input("Change label to '{}' (Y/N)?: ".format(label))
                if choice.lower().startswith('y'):
                    db.input_hashes[sha512][0] = label
                    for char in db.input_hashes[sha512][1]:
                        db.first_seen[char] = label
                    print("Changed.")
                    return True
                print("Unchanged.")
                return False
            # we haven't added it yet, so store its hash now
            db.input_hashes[sha512] = [label]

        # decode the file as utf8
        try:
            text = data.decode(encoding='utf-8')
        except:
            print("Failed to decode file as utf-8")
            return False

        # get rid of the undecoded version now, might free some memory
        del data

        # characters first seen in this text
        new_characters = []

        # iterate over each character, incrementing the count in the db for matching characters
        for c in text:
            if is_hanzi(c):
                if c not in db.chars:
                    # first time we've seen this character
                    db.chars[c] = [1, 0, 0] # seen once, never selected, considered last used on cycle 0
                    db.first_seen[c] = label
                    new_characters.append(c)
                else:
                    occ = db.chars[c][TIMES_OCCURRED] + 1 # seen once more
                    db.chars[c][TIMES_OCCURRED] = occ
                    if occ > db.max_occurrences:
                        db.max_occurrences = occ

        if not override_hashing: # do this check to prevent possible KeyError
            db.input_hashes[sha512].append(new_characters)

        return True

    #############################3
    # Generating character lists #
    ##############################

    # not very efficient but even if all possible Chinese characters are in the database,
    # generation shouldn't take too long on human timescales.
    def generate(db, n_chars):
        db.cycle += 1

        if db.max_occurrences < 1:
            raise Exception("max_occurrences is zero, meaning there are no characters in the db!")

        # produce a score for each character indicating how likely it should be to be selected
        scores = []
        charlist = [] # keep a list of each character where the index is the same as the index for its score
        for c, d in db.chars.items():
            if c in db.blacklist:
                continue # skip blacklisted characters

            occurred, used, last = d
            
            occur_score = occurred / db.max_occurrences
            used_score  = (db.max_used - used) / db.max_used
            since_last  = (db.cycle - last) / db.cycle
            if since_last > 0:
                since_last = math.log2(since_last + 1)

            # hack: if the character hasn't been used at all, drastically increase
            # the since_last multiplier to try to ensure unused characters come first.
            if used == 0:
                since_last *= 16

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
            occur, used, _ = db.chars[c]
            used += 1
            if used > db.max_used:
                db.max_used = used
            db.chars[c] = [occur, used, db.cycle]

        return output

    #############
    # Blacklist #
    #############

    def update_blacklist(db, path="blacklist.txt"):
        # the blacklist file is just a regular text file; all the hanzi are extracted from it
        # and other characters are ignored. So it can contain comments in English without causing
        # any issues.
        new_blacklist = set(filter(is_hanzi, set(open(path, 'r').read())))
        
        print("Added:", list(new_blacklist.difference(db.blacklist)))
        print("Removed:", list(db.blacklist.difference(new_blacklist)))
        
        db.blacklist = new_blacklist

        return True

#####################################
# Database load and save operations #
#####################################

# note: database uses pickle, which is not very secure. Make sure the database file can be trusted.
def load_db(path=DB_PATH):
    if not os.path.isfile(path):
        print("Database file does not exist, using empty database.")
        return Database()
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

def load_pinyin(path="pinyin.json"):
    try:
        f = open(path, 'rb')
        return json.load(f)
    except Exception as e:
        print("Failed to load cedict JSON:", e)
        return False

