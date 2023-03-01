FROM backend_dependices:latest

WORKDIR /flask-deploy

COPY . .

# send this command to dependicies image (if will be possible)
RUN apt-get install libgomp1

RUN pip3 install gunicorn[gevent]
