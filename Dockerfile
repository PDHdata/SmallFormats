FROM python:3.13-slim

RUN apt-get update && apt-get install -y curl

ENV PYTHONUNBUFFERED 1

WORKDIR /app

# begin supercronic
# Latest releases available at https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=71b0d58cc53f6bd72cf2f293e09e294b79c666d8 \
    SUPERCRONIC=supercronic-linux-amd64

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# end supercronic

COPY uv.lock pyproject.toml /app/

RUN pip3 install uv
RUN uv sync --no-editable --no-group dev --compile

COPY . .

ENV DJANGO_SETTINGS_MODULE "smallformats.settings"
ENV DJANGO_SECRET_KEY "this is a secret key for building purposes"

RUN uv run python _manage.py collectstatic --noinput

CMD tail -f /dev/null
