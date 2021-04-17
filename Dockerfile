FROM jrottenberg/ffmpeg:4.1-scratch312 AS ffmpeg
FROM python:3-alpine

VOLUME /jassa-bot
WORKDIR /usr/src/app

COPY --from=ffmpeg / /

COPY requirements.txt .

# Install requirements
RUN apk add --update --no-cache --virtual .build-deps \
        g++ \
        libxml2 \
        libxml2-dev && \
    apk add libxslt-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# Install pip requirements
#RUN pip install -r requirements.txt

COPY src/ .

CMD [ "python","-u","./bot.py" ]
