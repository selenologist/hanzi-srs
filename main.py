#!/usr/bin/env python3

# Very hacky spaced repetition character practice system for Chinese.

import sys, datetime

from database import *
import htmlgen

# special generator for February revision pack
def feb_revision(db):
    n_chars = 30
    n_boxes = 10
    n_pages = 2

    out_dir = "feb2020/"

    pinyin = load_pinyin()

    if not os.path.isdir(out_dir):
        # if old directory doesn't exist, create it
        os.mkdir(out_dir)
    
    for day in range(0,29): # 2020 is a leap year
        date = datetime.date(2020, 2, day + 1).isoformat()
        path = out_dir + date + ".htm"
        print("Generating", path)
        htmlgen.charsheet(
                db.generate(n_chars),
                n_boxes,
                n_pages,
                pinyin,
                open(path, 'w'),
                "February Revision",
                date)
    
    print("Done")

    # ensure all characters were covered
    not_generated = []
    max_dupes = 0
    for c, d in db.chars.items():
        if c in db.blacklist:
            continue # we're SUPPOSED to not generate blacklisted characters
        if d[TIMES_USED] > max_dupes:
            max_dupes = d[TIMES_USED]
        if d[TIMES_USED] < 1:
            print("Warning: {} was not generated".format(c))
            not_generated.append(c)

    if len(not_generated) > 0:
        print("Warning: {} characters in total were NOT generated".format(not_generated))
        extra_path = out_dir + "extras.htm"
        htmlgen.charsheet(
                not_generated,
                n_boxes,
                max(1, n_pages// n_chars),
                pinyin,
                open(extra_path, 'w'),
                "February 2020 Revision Extras/Overflow")
        print("Non-generated characters are in", extra_path)

    if max_dupes > 1:
        print("Note: the maximum number of duplicates is {}".format(max_dupes - 1))

    should_commit = False
    if input("Commit to database? (Y/N) ").lower().startswith('y'):
        should_commit = True
        print("Will update database.")

    return should_commit

########
# Main #
########

# the database is saved if this function returns True
def main(db):
    # default to generate if no arguments given
    if len(sys.argv) < 2 or sys.argv[1].startswith("gen"):
        # default to 30 chars
        n_chars = int(sys.argv[2]) if len(sys.argv) >= 3 else 30
        
        gen = db.generate(n_chars)
        
        if sys.argv[1].endswith("html"):
            # default to 10 boxes for writing characters
            n_boxes = int(sys.argv[3]) if len(sys.argv) >= 4 else 10
            # default to 2 pages
            n_pages = int(sys.argv[4]) if len(sys.argv) >= 5 else 2
        
            return htmlgen.charsheet(gen, n_boxes, n_pages)
        else:
            print(gen)
            return True

    elif sys.argv[1] == "add":
        if len(sys.argv) < 3:
            print("Path of file to add required.")
            return False
        return db.add_text(sys.argv[2])
    
    elif sys.argv[1] == "dump":
        print(db.__dict__)
        return False # no need to save, we only dumped the db

    elif sys.argv[1] == "mostfreq":
        # print the list of characters and their frequency, sorted by frequency
        # (blacklisted characters are skipped)
        chars = []
        for c, d in db.chars.items():
            if c in db.blacklist:
                continue
            chars.append([c, d[TIMES_OCCURRED]])
        chars.sort(key=lambda v: v[1], reverse=True)
        for c in chars:
            print(c[0], c[1])
        return False

    elif sys.argv[1].endswith("blacklist"):
        return db.update_blacklist()
    
    elif sys.argv[1].endswith("feb"):
        return feb_revision(db)
    
    else:
        print("Invalid arguments.")
        return False

if __name__ == "__main__":
    db = load_db()
    if main(db):
        save_db(db)
