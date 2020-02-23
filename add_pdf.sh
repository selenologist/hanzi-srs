#!/bin/bash

# there was a reason for using temporary files instead of pipes/stdin,
# but I dont remember if it still applies. ah well, this works for now.
TMPFILE=$(mktemp)

pdftotext "$1" $TMPFILE
echo "Generated $TMPFILE"
python3 main.py add $TMPFILE "$2"
rm $TMPFILE
