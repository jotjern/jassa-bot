FROM python:3.8-slim

VOLUME /jassa-bot
WORKDIR /usr/src/app

# Install ImageMagick and other requirements
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ffmpeg=7:4.1.6-1~deb10u1 imagemagick=8:6.9.10.23+dfsg-2.1+deb10u1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Taken from moviepy Dockerfile (modify ImageMagick policy file so that Textclips work correctly)
RUN sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml

COPY requirements.txt .

# Install pip requirements
RUN pip install -r requirements.txt

COPY src/ .

CMD [ "python","-u","./bot.py" ]
