import sys
import datetime
import cedict
from cedict2pinyin import add_accents

#########################
# HTML table generation #
#########################

# Generates HTML output for a character practice sheet
def charsheet(chars, n_boxes, n_pages,
              pinyin=None, f=open("/dev/stdout", "w"),
              title="Randomly Generated Spaced-Repetition Character Sheet",
              date=datetime.date.today().isoformat()):
    td_width  = 100 / (n_boxes + 1)
    td_height = 65  / (len(chars) / n_pages)

    # The value 65 for td_height was found experimentally.
    # This seems to actually work for making everything fit on the page,
    # but it's not really guaranteed and will probably break.
    # this will do for now

    # height scaling for pinyin text; by default this is unused
    py_height = 1
    if pinyin:
        # if we're including pinyin for each character, allocate vertical space for it
        # just like before this is a hack that seems to work in practice, but isn't really ideal
        td_height = 70 / (len(chars) / n_pages)
        py_height = td_height * 0.25
        td_height = td_height * 0.75

    # generate start of HTML page including CSS
    f.write(\
"""<!DOCTYPE html>
<html lang="zh">
<head><title>{} {}</title>
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
    vertical-align: top;
}}
a {{
    color: black;
    text-decoration: none;
}}
.p {{
    display: block;
    font-size: {}vh;
}}
</style>
</head>
<body><table>""".format(title, date, td_width, td_height, py_height))
   
    # generate the empty boxes / td-terminators once, rather than every loop
    boxes = "</td>" + "<td></td>" * n_boxes + "</tr>"
    
    # generate rows for each character
    for i, c in enumerate(chars):
        a = """<a href="https://zici.info/decomp/#{}N">{}</a>""".format(hex(ord(c))[2:], c)
        
        if pinyin:
            # if a dictionary is present, look up the pinyin for the character
            py = '?'
            if c in pinyin:
                py = pinyin[c][0] # use the first definition available
            else:
                sys.stderr.write("no pinyin found for {}\n".format(c))

            # clicking the pinyin shows the yellowbridge dictionary entry
            a += '<a class="p" href="https://yellowbridge.com/chinese/sentsearch.php?word={}">{}</a>'\
                .format(c, py)

        f.write("<tr><td>" + a + boxes)

    # finally terminate the HTML page
    f.write("</table></body></html>")

    return True

# defs is cedict.load() format
def summary(words, defs,
        f=open("/dev/stdout", "w"),
        title="Randomly Generated Summary"):

    # generate start of HTML page including CSS
    f.write(\
"""<!DOCTYPE html>
<html lang="zh">
<head><title>{}</title>
<style>
table {{
    width: 100%;
    border-spacing: 0px;
    border-collapse: collapse;
    margin: 0px;
    padding: 0px;
    page-break-inside:auto;
}}
tr {{
    page-break-inside:avoid;
    page-break-after:auto;
}}
td {{
    border: 1px solid black;
    text-align: center;
    padding: 0px;
    margin: 0px;
    vertical-align: top;
}}
th {{
    font-size: 150%;
}}

.c {{
    font-size: 250%;
    font-family: "FandolFang R", fangsong, serif;
}}

.p {{
    font-size: 150%;
}}
.p a {{
    display: block; 
    min-width: max-content;
}}

a {{
    color: black;
    text-decoration: none;
}}
</style>
</head>
<body><table>
<tr><th>词</th><th>拼音</th><th>定义</th></tr>""".format(title))
   
    # generate rows for each character
    for word in words:
        row = '<tr><td class="c">'
        for c in word:
            row += '<a href="https://zici.info/decomp/#{}N">{}</a>'.format(hex(ord(c))[2:], c)
        row += "</td>"
        
        py, definition = '?', None
        if word in defs:
            for entry in defs[word]:
                py, definition = entry[cedict.PINYIN_INDEX], entry[cedict.DEF_INDEX]
                
                if definition.startswith("variant"):
                    continue # skip variant definitions

                # split slashes in definitions over lines, skipping 'variant' definitions again
                definitions =\
                    filter(lambda d: not d.startswith("variant"), definition.split(sep='/'))
                definition = ""
                line = ""
                LINE_CUTOFF = 80
                for d in definitions:
                    if len(line) + len(d) + 3 < LINE_CUTOFF:
                        if len(line):
                            line += " / "
                        line += d
                    else:
                        if len(definition):
                            definition += "<br>"
                        definition += line
                        line = ""
                if len(line):
                    if len(definition):
                        definition += "<br>"
                    definition += line

                py = "<br>".join(map(add_accents, py.split()))
                
                # clicking the pinyin shows the yellowbridge dictionary entry
                row += '<td class="p"><a href="https://www.yellowbridge.com/chinese/dictionary.php?word=={}">{}</a></td>'\
                    .format(word, py)
                row += '<td>{}</td></tr>'.format(definition)
                f.write(row)

                row = "<tr><td>↑</td>"
        else:
            sys.stderr.write("no pinyin found for {}\n".format(word))
    # finally terminate the HTML page
    f.write("</table></body></html>")

    return False


