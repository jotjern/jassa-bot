FROM python:3.8.2

WORKDIR /usr/src/app

ADD requirements.txt .

RUN apt-get update \
    apt-get install -y build-essential \
    wget https://www.imagemagick.org/download/ImageMagick.tar.gz \
    tar xf ImageMagick.tar.gz \
    cd ImageMagick-7* \
    ./configure \
    make \
    sudo make install \
    sudo ldconfig /usr/local/lib \
    pip install --no-cache-dir -r requirements.txt

COPY src/ .

CMD [ "python", "./bot.py" ]