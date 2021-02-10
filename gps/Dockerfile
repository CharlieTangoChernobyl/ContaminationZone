# Download, install and build dependencies
FROM balenalib/raspberrypi3-alpine-python:3-build as build
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copy dependencies to run time container
# Thanks to multi-stage builds, the size of the resulting image is ~70% smaller
FROM balenalib/raspberrypi3-alpine-python:3-run
COPY *.py ./

WORKDIR /usr/src/app
COPY . .

CMD ["python3", "cli.py", "gps", "-s", "/dev/ttyS0", "-vv"]
