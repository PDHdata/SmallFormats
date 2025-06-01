#!/usr/bin/env bash


if [ -z "$RELEASE_COMMAND" ]; then
  uv run python /app/_manage.py collectstatic
fi
