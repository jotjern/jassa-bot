FROM python:3.8

VOLUME /jassa-bot
WORKDIR /usr/src/app


# Install apt packages
RUN apt-get -y update
RUN apt-get -y install ffmpeg --no-install-recommends

# Install requirements
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY src/ .

CMD [ "python","-u","./bot.py" ]
