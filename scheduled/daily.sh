#!/bin/bash

cd /app
set -e
./manage fetch-cards
set +e
./manage crawl-archidekt
./manage crawl-moxfield
./manage get-decklists
./manage update-site-stats
