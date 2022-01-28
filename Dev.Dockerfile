FROM python:3.8

WORKDIR /usr/src/app

RUN apt update -y
RUN apt install -y nodejs npm ffmpeg --no-install-recommends

RUN npm i -g nodemon

COPY requirements.txt .

RUN pip install -r requirements.txt

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

CMD [ "nodemon","bot.py" ]
