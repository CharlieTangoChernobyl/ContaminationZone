import asyncio
import logging
import os
import subprocess
from json import JSONDecodeError

import geojson
import pynmea2
import RPi.GPIO as gpio
from serial.serialutil import SerialException

logger = logging.getLogger(__name__)

PIN_LED_GREEN = 17
PIN_LED_RED = 27
# Setup influx client (this is using a modified version of balenaSense)
influx_client = InfluxDBClient('influxdb', 8086, database='balena-sense')
influx_client.create_database('balena-sense')

class GPS:
    def __init__(self, ser):
        self.ser = ser
        self.filename = None

        # Set up GPIO
        gpio.setmode(gpio.BCM)
        gpio.setup(PIN_LED_RED, gpio.OUT)
        gpio.output(PIN_LED_RED, False)
        gpio.setup(PIN_LED_GREEN, gpio.OUT)
        gpio.output(PIN_LED_GREEN, False)

    async def parse(self):
        while True:
            try:
                raw = self.ser.readline()
            except SerialException as e:
                logger.warning("Data not available: {}".format(e))
                await asyncio.sleep(1)
                continue

            try:
                pos = pynmea2.parse(raw.decode())
                logger.debug(raw)
            except pynmea2.nmea.ParseError:
                continue
            except UnicodeDecodeError:
                continue

            # Parse only Global Positioning System Fix Data sentences
            if type(pos) != pynmea2.RMC:
                continue

            point = geojson.Point((pos.longitude, pos.latitude))
            if pos.status == 'V':  # Invalid position
                logger.warning("GPS not ready yet")
                gpio.output(PIN_LED_RED, True)
                gpio.output(PIN_LED_GREEN, False)
                await asyncio.sleep(1)
                continue

            if self.filename is None:
                filename = 'gps-log-' + str(pos.datestamp) + '.json'
                self.load(filename)

            gpio.output(PIN_LED_RED, False)
            gpio.output(PIN_LED_GREEN, True)
            logger.info('(lat, lon) = ({}, {})'.format(pos.latitude,
                                                       pos.longitude))

            #Store data in Influx
        measurements = [
            {
                'measurement': 'balena-sense',
                'fields': {
                    'latitide': .format(pos.latitude),
                    'longitude': .format(pos.longitude),                   
                }
            }
        ]
        
        influx_client.write_points(measurements)
        loop_count = 0
            
            # Build Feature (point + metadata)
            time = str(pos.timestamp)
            temp = subprocess.Popen(
                "cat /sys/class/thermal/thermal_zone0/temp",
                shell=True,
                stdout=subprocess.PIPE)
            temp = temp.stdout.read().decode()[:-1]
            temp = int(temp) / 1000
            props = {'ts': time, 'tmp': temp}
            feat = geojson.Feature(geometry=point, properties=props)

            # Save new data
            self.data.features.append(feat)
            self.dump()

            # Reduce sampling rate
            await asyncio.sleep(5)

    def dump(self):
        with open('/data/' + self.filename, 'w') as f:
            geojson.dump(self.data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

    def load(self, filename):
        self.filename = filename

        try:
            with open('/data/' + self.filename, 'r+') as f:
                try:
                    self.data = geojson.load(f)
                    assert self.data.type == "FeatureCollection"
                except JSONDecodeError as e:
                    logger.error(e)
                    logger.info("Initializing database {}".format(self.filename))
                    self.data = geojson.FeatureCollection([])
        except FileNotFoundError:
            logger.info("Initializing database {}".format(self.filename))
            self.data = geojson.FeatureCollection([])
