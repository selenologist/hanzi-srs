import sys
import datetime

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


