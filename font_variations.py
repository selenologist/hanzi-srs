# Script for using a font's Unicode Ideographic Variation Sequences file to show differences
# between e.g. regional variants.
# This was used on my website to show the differences in Adobe Source Han Serif between
# Simplified Chinese and Japanese.
#
# Note that this only shows variations for the same unicode code point, not characters that are
# different between e.g. Simplified and Shinjitai in general.
#
# The CMapResources files are also used to find non-IVS variant characters, and also to filter out
# variants that map to the same CID.
#
# The relevant files can be obtained from https://github.com/adobe-fonts/source-han-serif, namely:
#   1. SourceHanSerif_JP_sequences.txt
#   2. UniSourceHanSerifCN-UTF32-H
#   3. UniSourceHanSerifJP-UTF32-H

import math
import re
import radicals

# refer to https://www.unicode.org/reports/tr37/#w1aac11b1 (for IVD_Sequences.txt)
# for a description of the format handled by this regex.
SEQ_REGEX = re.compile(r"\s*([0-9A-Fa-f]+) ([0-9A-F]+)\s*;\s*(\S+)\s*;\s*(\S+)\s*")

def process_ivs_file(path="SourceHanSerif_JP_sequences.txt"):
    # dictionary of base characters to a list of (selector, collection, sequence) tuples
    chars = dict()

    for line in open(path):
        if line.startswith('#'):
            # skip comments
            continue
        m = SEQ_REGEX.match(line)
        if m: # only process if the regex matched, otherwise skip the line
            # base character (converted from hex in the file to an int)
            base = int(m.group(1), 16)
            # variation selector
            sel  = int(m.group(2), 16)
            # collection identifier
            col  = m.group(3)
            # sequence identifier
            seq  = m.group(4)

            # if seq begins with "CID+", strip that, keeping just the hex CID value
            if seq.startswith("CID+"):
                seq = seq[4:]

            # if the base characer is not already in the chars dict, add a dummy value for it
            if base not in chars:
                chars[base] = []
            # now add the (selector, collection, sequence) tuple to the dict
            chars[base].append((sel, col, seq))

    return chars

# I'm actually totally guessing at the format for this one, looking at the file:
# https://github.com/adobe-fonts/source-han-serif/blob/master/UniSourceHanSerifJP-UTF32-H
# but there is actual documentation here:
# https://www.adobe.com/content/dam/acom/en/devnet/font/pdfs/5099.CMapResources.pdf
CIDCHAR_REGEX  = re.compile(r"<([0-9A-Fa-f]+)>\s*([0-9]+).*") # matches begincidchar lines
CIDRANGE_REGEX = re.compile(r"<([0-9a-fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*([0-9]+).*") # begincidrange

def process_cmap_file(path):
    cmap = dict()

    for line in open(path):
        char_match  = CIDCHAR_REGEX.match(line)
        range_match = CIDRANGE_REGEX.match(line) if not char_match else None # skip if above match
        if char_match:
            alias  = int(char_match.group(1), 16) # hex to int
            target = int(char_match.group(2), 10) # dec to int
            cmap[alias] = target
        elif range_match:
            begin  = int(range_match.group(1), 16) # hex to int
            end    = int(range_match.group(2), 16) # hex to int
            start  = int(range_match.group(3), 10) # dec to int
            dist   = end - begin
            # python for is exclusive, add 1 to make inclusive
            for alias, target in zip(range(begin, end+1), range(start, start + dist + 1)):
                cmap[alias] = target
        # non-matching lines are skipped
    return cmap

# yields alias codepoints that are in both 'a' and 'b' cmaps, but which have different targets.
def diff_cmap(a, b):
    common_keys = set(a.keys()) & set(b.keys())
    for key in common_keys:
        if a[key] != b[key]:
            yield key

# convert Variation Selector codepoint to its selector number
def sel_number(sel):
    # https://en.wikipedia.org/wiki/Variation_Selectors_(Unicode_block)
    if sel >= 0xFE00 and sel <= 0xFE0F:
        return sel - 0xFE00  + 1  # VS1 -> VS16
    # https://en.wikipedia.org/wiki/Variation_Selectors_Supplement
    elif sel >= 0xE0100 and sel <= 0xE01EF:
        return sel - 0xE0100 + 17 # VS17->VS256
    # if the selector is somehow outside these ranges just return 0
    else:
        return 0

# convert Variation Selector codepoint to a string like "VS1"
def sel_string(sel):
    num = sel_number(sel)
    if num: 
        return "VS{}".format(num)
    else:
        return '?'

# chars should be the output of process_ivs_file()
# rads is an optional radicals dict from radicals.py:load(), used to sort the characters by
# radical. if it is omitted then the unicode ordering will be used.
def gen_variations_html(ivs_chars, cmap_base, cmap_variant,
        f=open("/dev/stdout", "w"),
        rads=None,
        title="Variations for Japanese",
        variant_lang="JP"):
    # helper to convert an int to uppercase hex, without the "0x" at the start
    tohex = lambda i: hex(i)[2:].upper()

    # compute difference of base and variant cmaps
    cmap_diff = set(diff_cmap(cmap_base, cmap_variant))

    # as the chars dict is keyed by integer unicode codepoint rather than by str, using None
    # as the default for the sorting keyfunction is equivalent to defaulting to sorting by
    # codepoint. Turns out this is more useful than the radical sort anyway.
    key = None

    # if the rads argument is present, use it for sorting
    if rads:
        # obtain an ordering index for each character based on radical sorting
        ordering = dict()
        for index, char in enumerate(radicals.enumerate_sorted(rads)):
            ordering[ord(char)] = index

        def key(codepoint):
            if codepoint in ordering:
                return ordering[codepoint]
            else:
                return math.inf
    
    # will contain, in order, (codepoint, [list of (selector, collection, sequence)]) tuples.
    # the collection and sequence parts of the tuple in the chars dict are ignored.
    # if the codepoint is not in ivs_chars, there will just be an empty list instead of the
    # data that usually comes from the ivs file.
    sorted_chars = []
    for codepoint in sorted(set(ivs_chars.keys()) | cmap_diff, key=key):
        sorted_chars.append((codepoint, ivs_chars[codepoint] if codepoint in ivs_chars else []))

    # generate start of HTML page including CSS
    f.write(\
"""<!DOCTYPE html>
<html>
<head><title>{}</title>
<style>
table {{
    border-spacing: 0px;
    border-collapse: collapse;
    margin: 0px;
    padding: 0px;
    counter-reset: rowNumber -1;
}}

tr {{
    counter-increment: rowNumber;
}}

tr td:first-child::before {{
    content: counter(rowNumber);
}}

td {{
    border: 1px solid black;
    text-align: center;
    padding: 0px;
    margin: 0px;
}}
span {{
    font-size: 400%;
    font-family: "Source Han Serif", serif;
}}
</style>
</head>
<body><table><tr>
<th>#</th>
<th>ZH</th>
<th>{}</th>
<th>Codepoint</th>
<th><a href="https://en.wikipedia.org/wiki/Variant_form_(Unicode)">Selectors</a></th>
<th>Base CID→Variant CIDs</th>
</tr>""".format(title, variant_lang))
   
    # convert variation to lowercase form for html lang tag
    variant_lang = variant_lang.lower()

    # template string for a row
    # format args: char, variant_lang, variants, codepoint, selectors, sequences
    template = "<tr><td></td>" +\
        "<td><span lang=\"zh\">{}</span></td>" +\
        "<td><span lang=\"{}\">{}</span></td>" +\
        "<td><tt>{}</tt></td>" +\
        "<td>{}</td>" +\
        "<td>{}</td></tr>"

    # generate the table rows for each character
    for codepoint, variant_data in sorted_chars:
        # CIDs to skip if encountered
        forbid_cids = set([cmap_base[codepoint], cmap_variant[codepoint]])
        skip_variants = set() # indices in variant_data to skip
        for i, data in enumerate(variant_data):
            try: # handle failure to convert string to int
                cid = int(data[2])
                if cid in forbid_cids:
                    skip_variants.add(i)
                forbid_cids.add(cid)
            except ValueError:
                pass
        
        # skip entries from variant_data according to skip_variants
        variant_data = [d for i, d in enumerate(variant_data) if i not in skip_variants]

        # whether CIDs are equal between base and variant without adding selectors
        cids_equal = cmap_base[codepoint] == cmap_variant[codepoint]

        # if there are no real selectors and the CIDs are equal between base and variant, skip.
        if len(variant_data) == 0 and cids_equal:
            continue # skip identical variants

        # obtain character for codepoint
        char = chr(codepoint)

        # get selectors from the variant data (zero-length if no variant data present)
        selectors = [data[0] for data in variant_data]
        # get sequences from the variant data (zero-length if no variant data present)
        sequences = [data[2] for data in variant_data]
        
        # get characters with each Variant Selector added to it (or just the char if no selectors)
        variants = char if not cids_equal else ""
        if len(selectors):
            variants += "".join([char + chr(sel) for sel in selectors])

        # obtain codepoint as a string formatted like "U+<hex>"
        codepoint_str = "U+" + tohex(codepoint)

        # get selector numbers as a comma-separated string
        sels = ",".join([str(sel_number(sel)) for sel in selectors]) if len(selectors) else "N/A"
        
        # get base CID and variant CID, (put CIDs of selector-based variants in parentheses)
        seqs = str(cmap_base[codepoint]) + "↓<br>"
        if len(sequences): # if sequence data is available
            seqs += "({},{})".format(str(cmap_variant[codepoint]), ",".join(sequences))
        else:
            seqs += str(cmap_variant[codepoint])
        
        # output the table row
        f.write(template.format(char, variant_lang, variants, codepoint_str, sels, seqs))

    # finally terminate the HTML page
    f.write("</table></body></html>")

# generate HTML output for differences in Source Han Serif between CN and JP
def source_han_serif_diff():
    ivs = process_ivs_file()
    cn  = process_cmap_file("UniSourceHanSerifCN-UTF32-H")
    jp  = process_cmap_file("UniSourceHanSerifJP-UTF32-H")
    gen_variations_html(ivs, cn, jp, open("SourceHanSerifDifferencesCNtoJP.html", "w"))

