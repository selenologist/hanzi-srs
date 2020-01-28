import json
from main import is_hanzi

# this function extracts just the pinyin field from cedict.json
def load_cedict(path="cedict.json"):
    try:
        f = open(path, 'rb')
        return json.load(f)
    except Exception as e:
        print("Failed to load cedict JSON:", e)
        raise e

vowels = ['a', 'o', 'e', 'i', 'u', 'ü']
tones = {
    'a':['ā','á','ǎ','à'],
    'o':['ō','ó','ǒ','ò'],
    'e':['ē','é','ě','è'],
    'i':['ī','í','ǐ','ì'],
    'u':['ū','ú','ǔ','ù'],
    'ü':['ǖ','ǘ','ǚ','ǜ']
}

def main():
    cedict = load_cedict()

    # sometimes there are characters that have no definition of their own, but occur in other
    # words which do have definitions.
    # to hack around this, we will extract the pinyin for characters that aren't defined from a
    # word that it occurs in.
    # note that this usually fails horribly when there are non-hanzi characters, because now the
    # syllables do not map directly to characters, but this will do for now.

    fake_entries = dict()
    for word, data in cedict.items():
        for syl, char in enumerate(filter(is_hanzi, word)):
            if char not in cedict and char not in fake_entries:
                pinyin = data[2].split()[syl]
                fake_entries[char] = [None, None, pinyin]
    cedict.update(fake_entries)

    pinyin = dict()
    for word, data in cedict.items():
        # the cedict file normally has pinyin in a numbered format, e.g. 'shi4'
        # we will convert this to the accent format, e.g. 'shì'
        
        py = ""
        
        for syl in data[2].split():
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
            py += syl

        pinyin[word] = py

    json.dump(pinyin, open('pinyin.json', 'w'))

if __name__ == "__main__":
    main()
