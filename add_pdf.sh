#!/bin/bash

TMPFILE=$(mktemp)

pdftotext "$1" $TMPFILE
echo "Generated $TMPFILE"
python3 main.py add $TMPFILE
rm $TMPFILE
