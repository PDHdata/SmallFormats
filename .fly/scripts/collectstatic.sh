#!/usr/bin/env bash


if [ -z "$RELEASE_COMMAND" ]; then
  poetry run python /app/_manage.py collectstatic
fi
