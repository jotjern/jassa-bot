FROM python:3.8.2

WORKDIR /usr/src/app

ADD requirements.txt .

# Install ImageMagick and other requirements
RUN apt-get update \
    && apt-get install -y build-essential \
    && wget https://www.imagemagick.org/download/ImageMagick.tar.gz \
    && tar xf ImageMagick.tar.gz \
    && cd ImageMagick-7* \
    && ./configure \
    && make \
    && make install \
    && ldconfig /usr/local/lib \
    #&& make check \
    && cd .. \
    && pip install -r requirements.txt

COPY src/ .

CMD [ "python", "./bot.py" ]