FROM python:3

WORKDIR /usr/src/app

RUN apt update -y
RUN apt install -y nodejs npm ffmpeg --no-install-recommends

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN npm i -g nodemon

CMD [ "nodemon","bot.py" ]
