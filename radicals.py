import os
import pickle, json
import math

# Information about the composition of 汉字 is stored in a dict mapping characters to a list:
# [[composition_type, left_parent, right_parent], descendants_left, descendants_right, num_strokes]
#
# * If the character has no parents, the first entry in the list will be None.
# (these would be considered base radicals that can't be further divided... or characters that
# ought to have their decomposition data updated...)
# (note that if rads.json says a character only has a left parent, really it has no parents, and
# as above, the first entry in the list will be None).
#
# * If the character has no descenants, the second and third entries will be empty sets.
#
# (Note that a character does not have more than 2 immediate parents, but could have any number of
# descendants)
#
# This enables querying the 'distance' between characters, finding characters that share a radical
# with a given character, etc.
#
# Side-note: originally this used a self-referential/cyclical data structure, but as this causes
# some issues with Python's default reference-counting based garbage collector, a master dict was
# used instead.

# indexes of list described above

PARENT_INDEX           = 0
DESCENDANT_LEFT_INDEX  = 1
DESCENDANT_RIGHT_INDEX = 2
NUM_STROKES_INDEX      = 3

COMPOSITION_TYPE_INDEX = 0 # index of composition type within in character_data[PARENT_INDEX]

# cost values for computing 'distances' between characters
# these should probably be values that aren't multiples of each other so that collisions formed
# from different combinations of costs don't become the same value, but currently they're not.
COST_DIFFERENT_RADICAL     = 1    # a radical was different
COST_DIFFERENT_SIDE        = 0.5  # a radical was added to a different side
COST_DIFFERENT_COMPOSITION = 0.25 # the composition type was different
COST_DIFFERENT_STROKES     = 0.01 # cost for each difference in stroke count


# rads.json is the same as at https://zici.info/decomp/rads.json
# it is a map of characters to [num_strokes, composition_type, left_parent, right_parent]
# it's not currently distributed with this project.
def load_from_json(path="rads.json"):
    # the format of this dict is described at the top of the file
    radicals = dict()

    with open(path, 'rb') as f:
        rads_json = json.load(f)

    def make_dummy(char):
        # the first value of the list is parent characters,
        # the second value is descendant characters
        radicals[char] = [None, set(), set(), 0]

    for char, data in rads_json.items():
        # if the character lacks a right parent, the data list will only have three entries, and
        # the destructuring below will fail, so in this case add a None value to get around this.
        if len(data) < 4:
            #print("Note:", char, "had no right parent")
            if len(data) < 3:
                # shouldn't happen but handle it anyway incase
                raise Exception("radical data list somehow didn't at least 3 entries")
            data.append(None)

        # destructure data list to access its components by name
        [num_strokes, composition_type, left, right] = data

        # if a character's left 'parent' is itself, it doesn't actually have a parent
        if left == char:
            left = None
        
        # note that left or right might be things like '人*', this is left as-is for now

        # if a character is not already in the radicals dict, create a dummy value now so future
        # lookups never miss (which would cause an exception)
        if char not in radicals:
            make_dummy(char)
        
        # update the number of strokes
        radicals[char][NUM_STROKES_INDEX] = num_strokes
        
        # if a character does not have both parents, it actually has no parents, don't do anything more
        if not left or not right:
            continue

        if left not in radicals:
            make_dummy(left)
        if right not in radicals:
            make_dummy(right)
       
        radicals[char][PARENT_INDEX] = [composition_type, left, right]

        radicals[left ][DESCENDANT_LEFT_INDEX ].add(char)
        radicals[right][DESCENDANT_RIGHT_INDEX].add(char)

    return radicals

# a pickle file is used to store the data in a format actually useful to this program.
# if the pickle file is not found, it falls back to loading it from rads.json, then the pickle
# file is created for next time.
def load(path="radicals.pickle", json_path="rads.json"):
    if not os.path.isfile(path):
        radicals = load_from_json(json_path)

        # save the pickle file for later
        with open(path, 'xb') as f:
            pickle.dump(radicals, f)

        return radicals
    else:
        with open(path, 'rb') as f:
            return pickle.load(f)

# yield characters similar to a given character and their 'distances', until a given distance.
# note that the result may not be ordered by distance, but characters sharing a left parent will
# come before characters sharing a right parent.
#
# exclusions argument is a set of characters to skip.
# note that the exclusions argument WILL BE MODIFIED IN PLACE. Pass eg exclusions.copy() to avoid.
#
# distance argument is starting distance, used for recursive calls.
#
# do_stroke_difference controls whether to apply a cost to differences in stroke number.
#
# do_parent_alternates controls whether to emit characters that, while they share a parent, the
# common parent is on the opposite side. (Defaults to True)
#
# do_parents controls whether the siblings of parent characters should be emitted too.
# (Defaults to True)
#
# go_deeper controls whether to queue descendants of the current character's descendants.
# it's used in recursive calls and should be left alone for the base call. (Defaults to True)
def characters_within(radicals, char, max_distance,
                      exclusions=None, distance=COST_DIFFERENT_RADICAL,
                      do_stroke_difference=False,
                      do_parent_alternates=True,
                      do_parents=True,
                      go_deeper=True):
    if not exclusions:
        # do this rather than having the default be =set() so it's a new set each time
        # (in Python, default arguments are, like other arguments, passed by reference)
        exclusions = set() 

    if not radicals[char][PARENT_INDEX]:
        # character has no parents, therefore no similar characters, so yield nothing
        yield from ()
    else:
        # get the number of strokes in the current character
        num_strokes = radicals[char][NUM_STROKES_INDEX]

        # add the starting character to the exclusions set so we don't return it as if it were a
        # neighbour of itself
        exclusions.add(char)

        # queue of characters to descend on after exhausting immediate neighbours
        next_queue = []

        # function for processing siblings (characters that descend from the same parent)
        def process_descendant(descendant, distance=distance):
            # 'distance' within this closure is different to outside

            if descendant in exclusions: 
                return None # skip excluded characters

            if do_stroke_difference:
                # add the cost for difference in stroke count, if nonzero
                # (perform the if-test to avoid possibility of floating point errors)
                stroke_difference = abs(num_strokes - radicals[descendant][NUM_STROKES_INDEX])
                if stroke_difference > 0:
                    distance += COST_DIFFERENT_STROKES * stroke_difference

            # add the cost for a different composition type, if it changed
            if radicals[descendant][PARENT_INDEX][COMPOSITION_TYPE_INDEX] != composition_type:
                distance += COST_DIFFERENT_COMPOSITION

            if distance > max_distance:
                # if the distance now exceeds the max distance, return None so the character is
                # skipped.
                return None
            else:
                # now exclude this character too
                exclusions.add(descendant)

                result = [descendant, distance]

                if go_deeper:
                    # enqueue the character for deeper searching after exhausting other
                    # immediate siblings.
                    next_queue.append(result)
                
                return result

        # destructure parent data
        [composition_type, left_parent_char, right_parent_char] = radicals[char][PARENT_INDEX]

        # lookup parent data in radical dict
        left_parent  = radicals[left_parent_char]
        right_parent = radicals[right_parent_char]

        # iterate over characters having the same radical on the left as the starting character
        for descendant in left_parent[DESCENDANT_LEFT_INDEX]:
            result = process_descendant(descendant)
            if result: # if didn't return None
                yield result

        # iterate over characters having the same radical on the right as the starting character
        for descendant in right_parent[DESCENDANT_RIGHT_INDEX]:
            # unfortunately we have to duplicate some code from the previous loop because we can't
            # put 'yield' within the process_descendant closure.
            # (well we COULD make it work via 'yield from', but it would be messier, so let's not)
            result = process_descendant(descendant)
            if result: # if didn't return None
                yield result

        if do_parent_alternates:
            # iterate over characters that have the left parent on their right side
            for descendant in left_parent[DESCENDANT_RIGHT_INDEX]:
                result = process_descendant(descendant, distance + COST_DIFFERENT_SIDE)
                if result:
                    yield result
            
            # iterate over characters that have the right parent on their left side
            for descendant in right_parent[DESCENDANT_LEFT_INDEX]:
                result = process_descendant(descendant, distance + COST_DIFFERENT_SIDE)
                if result: # if didn't return None
                    yield result

        # characters yielded beyond this point will have more than 1 radical different.
        distance += COST_DIFFERENT_RADICAL

        if distance > max_distance:
            return # exit if distance is now exceeded

        if do_parents:
            # attempt to yield siblings of the parents. if the parents have no parents, nothing will happen.
            # does not do parents of parents nor other descendants of the parents
            yield from characters_within(
                radicals, left_parent_char, max_distance, exclusions,
                distance, do_stroke_difference, do_parent_alternates,
                do_parents=False, go_deeper=False)
            yield from characters_within(
                radicals, right_parent_char, max_distance, exclusions,
                distance, do_stroke_difference, do_parent_alternates,
                do_parents=False, go_deeper=False)

        # now attempt to handle any queued characters
        for queued, distance in next_queue:
            # distance was retained when the character was queued to handle whether the
            # composition_type changed, so we still need to add the cost of a radical changing too
            distance += COST_DIFFERENT_RADICAL
            if distance > max_distance:
                # other characters might not have had additional COST_DIFFERENT_COMPOSITION
                continue 
            yield from characters_within(
                radicals, queued, max_distance, exclusions,
                distance, do_stroke_difference, do_parent_alternates,
                do_parents=False, go_deeper=go_deeper)

        return

# print characters sorted by distance, grouped so characters of the same distance are printed together.
# (works on iterables of lists where the second element of the list is the distance)
def print_distance_sorted(iterable):
    last_distance = None
    same_distance = []
    for char, distance in sorted(iterable, key=lambda l: l[1]):
        if not last_distance:
            last_distance = distance
        elif distance != last_distance:
            print("{}:".format(last_distance), "".join(same_distance))
            last_distance = distance
            same_distance.clear()
        same_distance.append(char)
    if len(same_distance) > 0:
        print("{}:".format(last_distance), "".join(same_distance))

# yields characters that have no parents
def find_roots(radicals):
    for char, data in radicals.items():
        if not data[PARENT_INDEX]:
            yield char

# yields characters that have no descendants
def find_leaves(radicals):
    for char, data in radicals.items():
        if (len(data[DESCENDANT_LEFT_INDEX]) + len(data[DESCENDANT_RIGHT_INDEX])) < 1:
            yield char

# yields instances of special parents like '人*' that aren't real radicals by themselves
# (their stroke count is zero because it has never been set)
def find_special(radicals):
    for char in find_roots(radicals):
        if radicals[char][NUM_STROKES_INDEX] == 0:
            yield char

# deduplicate an iterable, preserving the original order
# OP = Order Preserving
# (turns out the program doesn't use this, but it's kept in case it's useful from a REPL)
def op_dedupe(iterable):
    seen = set()
    for v in iterable:
        if v not in seen:
            seen.add(v)
            yield v

# enumerate all characters sorted by radicals, and optionally filtered by an object with a
# __contains__ method; specifically, characters not in it will be skipped.
def enumerate_sorted(radicals, whitelist=None):
    if not whitelist:
        class ContainsEverything:
            def __contains__(self, _):
                return True
        whitelist = ContainsEverything()
   
    seen = set()

    # sort by stroke count, putting special (zero-stroke) radicals at the end
    def stroke_sort(iterable):
        def key(v):
            s = radicals[v][NUM_STROKES_INDEX]
            if s == 0:
                return math.inf
            else:
                return s

        return sorted(iterable, key=key)

    # left-then-right breadth-first-ish search
    # firstly all left-branches are explored breadth-first, while right-branches are also queued
    # for later.
    # After exhausting all left-branches, the previously-queued right-branches are explored.
    # Previously unseen characters have their branches added to the respective queues.
    # This process repeats until there are no longer any characters in either queue.
    def explore_lr_bfs(start):
        lq = [start]
        rq = [start]

        def do_queued(v):
            if v not in seen:
                seen.add(v)

                lq.extend(stroke_sort(radicals[v][DESCENDANT_LEFT_INDEX]))
                rq.extend(stroke_sort(radicals[v][DESCENDANT_RIGHT_INDEX]))

                # skip non-whitelisted and special radicals
                if v in whitelist and radicals[v][NUM_STROKES_INDEX]:
                    return v
                else:
                    return None

        while len(lq) + len(rq) > 0:
            while len(lq) > 0:
                v = lq.pop(0)
                v = do_queued(v)
                if v:
                    yield v
            while len(rq) > 0:
                v = rq.pop(0)
                v = do_queued(v)
                if v:
                    yield v

    # descend down each root seperately, ordered by stroke count
    for root in stroke_sort(find_roots(radicals)):
        yield from explore_lr_bfs(root)
