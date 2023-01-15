FROM python:3.11

ENV PYTHONUNBUFFERED 1

WORKDIR /app

# begin supercronic
# see https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.1/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=d7f4c0886eb85249ad05ed592902fa6865bb9d70

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# COPY scheduled/ scheduled/
# end supercronic

COPY poetry.lock pyproject.toml /app/

RUN pip3 install poetry
RUN poetry install --no-root

COPY . .

ENV DJANGO_SETTINGS_MODULE "smallformats.settings"
ENV DJANGO_SECRET_KEY "this is a secret key for building purposes"

RUN poetry run python _manage.py collectstatic --noinput

CMD poetry run daphne -b 0.0.0.0 -p 8080 smallformats.asgi:application
