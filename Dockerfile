FROM python:3

VOLUME /jassa-bot
WORKDIR /usr/src/app

COPY requirements.txt .

# Install apt packages
RUN apt-get -y update
RUN apt-get -y install ffmpeg

# Install pip requirements
RUN pip install -r requirements.txt

COPY src/ .

CMD [ "python","-u","./bot.py" ]
