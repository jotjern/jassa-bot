FROM python:3.8.2

VOLUME /jassa-bot
WORKDIR /usr/src/app

COPY requirements.txt .

# Install ImageMagick and other requirements
RUN apt-get update -y \
    && apt-get install -y ffmpeg imagemagick

# Taken from moviepy Dockerfile (modify ImageMagick policy file so that Textclips work correctly)
RUN sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml 

# Install pip requirements
RUN pip install -r requirements.txt

COPY src/ .

CMD [ "python","-u","./bot.py" ]