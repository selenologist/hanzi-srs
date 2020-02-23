import json
import cedict
from main import is_hanzi

vowels = ['a', 'o', 'e', 'i', 'u', 'ü']
tones = {
    'a':['ā','á','ǎ','à'],
    'o':['ō','ó','ǒ','ò'],
    'e':['ē','é','ě','è'],
    'i':['ī','í','ǐ','ì'],
    'u':['ū','ú','ǔ','ù'],
    'ü':['ǖ','ǘ','ǚ','ǜ']
}

# the cedict file normally has pinyin in a numbered format, e.g. 'shi4'
# convert this to the accent format, e.g. 'shì', also keeping the number too
def add_accents(syl):
    # force syllable lowercase
    syl = syl.lower()

    tone = syl[-1]
    if tone.isdigit():
        tone = int(tone)
    else:
        # default to neutral
        tone = 5
    
    # now we can strip the tone number off the string...
    # ...actually, it's more readable if it's left in with a space so 1 doesn:t look like i
    syl = syl[:-1] + " " + str(tone)
    
    # for neutral tone, we don't need to do anything else

    if tone != 5:
        # for non-neutral tone, find the vowel that should be replaced... and replace it

        # the tones array is zero-indexed, while tone is currently 1-indexed.
        # correct for this
        tone -= 1

        # iu is the exception to the ordering rule, so handle it first
        pos = syl.find("iu")
        if pos >= 0:
            # put the tone on the u (so add 1 to the index)
            before = syl[:pos+1]
            after  = syl[pos+2:]
            syl = before + tones['u'][tone] + after
        else:
            # try to replace vowels in priority-order, exiting after the first match
            for vowel in vowels:
                pos = syl.find(vowel)
                if pos >= 0:
                    before = syl[:pos]
                    after  = syl[pos+1:]
                    syl = before + tones[vowel][tone] + after
                    break
    return syl


def main():
    cd = cedict.load()
    pinyin = dict()

    # first use any available definitions for single characters
    for word, entries in cd.items():
        for data in entries:
            if len(word) != 1 or not is_hanzi(word[0]):
                continue # skip multiple-character words or non-hanzi characters

            char = word[0]

            # just in case, attempt to split the pinyin string and use only the first syllable
            syllable = data[cedict.PINYIN_INDEX].split()[0]

            if char not in pinyin:
                pinyin[char] = []
            
            accented = add_accents(syllable)
            if accented not in pinyin[char]:
                pinyin[char].append(accented)

    # sometimes there are characters that have no definition of their own, but occur in other
    # words which do have definitions.
    # to hack around this, we will extract the pinyin for characters that aren't defined from a
    # word that it occurs in.
    # note that this usually fails horribly when there are non-hanzi characters, because then the
    # syllables do not map directly to characters, so only words consisting wholly of hanzi are
    # used.

    for word, entries in cd.items():
        for data in entries:
            if not all(map(is_hanzi, word)):
                continue # skip words with non-hanzi characters in them

            syllables = data[cedict.PINYIN_INDEX].split()

            for syl, char in enumerate(word):
                if char not in pinyin:
                    pinyin[char] = []
                accented = add_accents(syllables[syl])
                if accented not in pinyin[char]:
                    pinyin[char].append(accented)

    json.dump(pinyin, open('pinyin.json', 'w'))

if __name__ == "__main__":
    main()
