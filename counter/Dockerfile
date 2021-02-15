FROM balenalib/raspberrypi3-debian-python:3.7-buster-build

WORKDIR /usr/app/src
RUN pip install spidev RPi.GPIO influxdb python-smbus i2c-tools
COPY *.py ./

CMD ["python","counter.py"]