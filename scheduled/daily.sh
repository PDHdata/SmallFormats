#!/bin/bash

cd /app
set -e
./manage fetch-cards
set +e
./manage crawl-archidekt --no-stdout
./manage crawl-moxfield --no-stdout
./manage get-decklists --no-stdout
./manage update-site-stats
