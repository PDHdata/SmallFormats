#!/bin/bash

cd /app
./manage clear-old-logs-and-runs --no-stdout
set -e
./manage fetch-cards
set +e
./manage crawl-archidekt --no-stdout
./manage crawl-moxfield --no-stdout
./manage get-decklists --no-stdout
./manage compute-commanders --no-stdout
./manage update-site-stats
