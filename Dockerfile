FROM python:3.8.2

WORKDIR /usr/src/app

ADD requirements.txt .

# Install ImageMagick and other requirements
RUN apt-get update -y \
    && apt-get install -y ffmpeg imagemagick \
    && pip install -r requirements.txt \
    && mkdir output && mkdir output/optimized

# Taken from moviepy Dockerfile (modify ImageMagick policy file so that Textclips work correctly)
RUN sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml 

COPY src/ .

CMD [ "python","-u","./bot.py" ]