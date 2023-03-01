#FROM python:3.7.2
#FROM python:3.6.8
#FROM python:3.6.8:alpine work but all list from requremnts.txt is not installed

#FROM python:3.6-alpine3.13
#FROM python:3.8-alpine3.13
#FROM python:3.8-alpine3.13
#FROM debian:jessie

FROM osgeo/gdal:ubuntu-small-latest


RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    python3.8 python3-pip 

#WORKDIR /flask-deploy

#RUN pip install pipenv
#RUN python3 -m venv venv

#RUN venv/bin/pip3 install --upgrade pip
#RUN pip install --upgrade pip

# for lightgbm package need wheel
#RUN venv/bin/pip3 install wheel

#COPY . .

COPY requirements.txt .

#RUN pipenv install --system --skip-lock
# install gdal separatly because allocation styling name in reque...txt is not suitable for pip env
#COPY GDAL-3.1.4-cp36-cp36m-win32.whl .

#RUN apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/main openssl \
#    build-base cmake musl-dev linux-headers
# this install 3.1.4 version
#RUN apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/main gdal-dev 
# test for 3.2.2 version
#RUN apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/main gdal-dev


# version here MUST be the same as installed from apline repo
#RUN venv/bin/pip3 install gdal==3.1.4 --no-cache-dir
#RUN venv/bin/pip3 install GDAL-3.1.4-cp36-cp36m-win32.whl
#RUN pip install GDAL-3.1.4-cp36-cp36m-win32.whl
#RUN pip install gdal

#RUN pipenv install -r requirements.txt
#RUN pip install -r requirements.txt
#RUN venv/bin/pip install -r requirements.txt
RUN pip3 install -r requirements.txt --no-cache-dir
# try this for cache downloaded wheels for requerments
#RUN pip install -r requirements.txt --npcache-dir /opt/app/pip_cache

RUN pip3 install gunicorn[gevent]
#RUN venv/bin/pip3 install gunicorn[gevent]

#EXPOSE 5000

#CMD gunicorn --worker-class gevent --workers 4 --bind 0.0.0.0:5000 wsgi:app --max-requests 10000 --timeout 5 --keep-alive 5 --log-level info