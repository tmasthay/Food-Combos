#!/bin/bash

output_name=${1:-"data"}
find . -name "results.txt" -exec sh -c 'echo "{}:" && cat {} | sed "s|\(.*\)|  - \1|" && echo "\n"' \; \
 | sed 's/^  \- %\(.*\)/  \- "%\1"/' \
 | sed 's/\\//g' \
 > $output_name.yaml