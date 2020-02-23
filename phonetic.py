# Map a pinyin syllable as text to a 3d coordinate so word similarity can be compared.
# uses the pinyin table as a base for assigning sounds to geometric positions.
# Try longest match first.
#
# This is a very hacky way of doing things but it works pretty well anyway.
# Better than nothing.
#
# X: initial consonant between [0,21]
# Y: vowel/diphthong/final (includes w/y next to bare vowel so they will be scored close)
# Z: tone (neutral is zero, rest are 1,2,3,4 as normal

CONSONANT_TABLE = {
    'NONE': 0,
    'b': 1,'p': 2,'m': 3,'f': 4,
    'd': 5,'t': 6,'n': 7,'l': 8,
    'g': 9,'k': 10,'h': 11,
    
    'zh': 12,'ch': 13,'sh': 16,
     'j': 14, 'q': 15, 'x': 17,
    
    'z': 18,'c': 19,'s': 20, 'r':21,
}
MAX_CONSONANT_INDEX = 21 # update this to highest value in above dict

# amount of influence of consonant coordinate;
# if these weights aren't multiples of each other then there should be less collisions
CONSONANT_WEIGHT = 0.3

VOWEL_TABLE = {
    'wang':0,'uang':1,'wan':2,'uan':3,'an':4,'wa':5,'ua':6,
    'yang':7,'iang':8,'ang':9,'yan':10,'ian':11,'ya':12,'ia':13,
    'yuan':14,'u:an':15,'uan':16,'weng':17,'ueng':18,'eng':19,'wen':20,'en':21,
    'yue':22,'u:e':23,'ue':24,'ye':25,'ie':26,
    'yun':27,'u:n':28,'un':29,'yong':30,'iong':31,'ong':32,'on':33,
    'wei':34,'ei':35,'ui':36,'wai':37,'uai':38,'ai':39,
    'wo':40,'uo':41,'wu':42, # wa and ua were duplicated and have been removed; the hole needs to be filled
    'yi':43,'yin':44,'ying':45,'ing':46,'in':47,
    'yao':48,'iao':49,'ao':50,'ou':51,'you':52,'yo':53,'iu':54,'yu':55,
    'a':56, 'o':57, 'e':58, 'i':59, 'u':60,'u:':61,
    'er':62,'r':63 # consider merging these? and other things that are basically dupes
}
MAX_VOWEL_INDEX = 63 # update this to highest value in above dict

VOWEL_WEIGHT = 0.5

TONE_TABLE = {
    '5': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
}

TONE_WEIGHT = 0.12

### build inverse tables

def inverse(d):
    i = {}
    for k,v in d.items():
        i[v] = k
    return i

#inverse_consonant = inverse(CONSONANT_TABLE)
#inverse_vowel     = inverse(VOWEL_TABLE)
#inverse_tone      = inverse(TONE_TABLE)

# single pinyin syllable to magic 3d coordinate
def syllable2coord(syllable):
    if len(syllable) < 2:
        return [-10,-10,-10] # this shouldn't happen but handle it
    orig_syllable = syllable
    
    initial    = CONSONANT_TABLE['NONE'] # default to NONE mapping
    vowelfinal = -1 # default to -1, whatever
    tone       = 0  # default to neutral tone

    # try to use the first two characters to get a consonant score
    first = syllable[:2]
    if first in CONSONANT_TABLE:
        initial = CONSONANT_TABLE[first]
        syllable = syllable[len(first):] # chop off the first chars now, since we've scored it
    else:
        # now try for just the first character
        first = first[0]
        
        # handle the care of toned r/m/n
        if len(syllable) == 2 and first in ['r','m','n']:
            initial = CONSONANT_TABLE['r']
            syllable = syllable[1:]
        # handle other single-character constants
        elif first in CONSONANT_TABLE:
            initial = CONSONANT_TABLE[first]
            syllable = syllable[1:]

    # try to grab the tone marker from the end now to simplify vowel-table handling
    last = syllable[-1]
    if last in TONE_TABLE:
        tone = TONE_TABLE[last]
        syllable = syllable[:-1] # chop off the tone marker now

    # try to match what's left against VOWEL_TABLE
    if syllable[:4] in VOWEL_TABLE:
        vowelfinal = VOWEL_TABLE[syllable[:4]]
    elif len(syllable) > 0:
        print("No match for vowel-section", syllable, "from base", orig_syllable)

    # these coords will later be unpacked so that a word is compared at a time, rather than a
    # syllable at a time
    return [vowelfinal, initial, tone]

# pinyin string to list of magic 3d coordinates (unweighted)
def pinyin2coords(pinyin):
    # skip (non-)syllable if the length is less than 2 or it starts with something in this list:
    return [syllable2coord(syl.lower())
            for syl in pinyin.split()
            if len(syl) > 1 and syl[:2] != 'xx']

def coord_distance(x,y):
    # euclidean distance
    return math.sqrt(sum([(a-b)*(a-b) for a,b in zip(x,y)]))
