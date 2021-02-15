# THE GEIGER COUNTER (at last)

import exixe
import spidev
import time
import datetime
import RPi.GPIO as GPIO
import smbus
import time
from time import *
from collections import deque
from influxdb import InfluxDBClient

counts = deque()
hundredcount = 0
usvh_ratio = 0.00812037037037 # This is for the J305 tube


# This method fires on edge detection (the pulse from the counter board)
def countme(channel):
    global counts, hundredcount
    timestamp = datetime.datetime.now()
    counts.append(timestamp)

    # Every time we hit 100 counts, run count100 and reset
    hundredcount = hundredcount + 1
    if hundredcount >= 100:
        hundredcount = 0
        count100()

        


# Set the input with falling edge detection for geiger counter pulses
GPIO.setup(16, GPIO.IN)
GPIO.add_event_detect(16, GPIO.FALLING, callback=countme)

# Setup influx client (this is using a modified version of balenaSense)
influx_client = InfluxDBClient('influxdb', 8086, database='balena-sense')
influx_client.create_database('balena-sense')

loop_count = 0

# In order to calculate CPM we need to store a rolling count of events in the last 60 seconds
# This loop runs every second to update the Nixie display and removes elements from the queue
# that are older than 60 seconds
while True:
    loop_count = loop_count + 1
        
    try:
        while counts[0] < datetime.datetime.now() - datetime.timedelta(seconds=60):
            counts.popleft()
    except IndexError:
        pass # there are no records in the queue.
    
    if loop_count == 10:
        # Every 10th iteration (10 seconds), store a measurement in Influx
        measurements = [
            {
                'measurement': 'balena-sense',
                'fields': {
                    'cpm': int(len(counts)),
                    'usvh': "{:.2f}".format(len(counts)*usvh_ratio),                   
                }
            }
        ]
        
        influx_client.write_points(measurements)
        loop_count = 0
        
# Define some device parameters
I2C_ADDR  = 0x27 # I2C device address
LCD_WIDTH = 20   # Maximum characters per line

# Define some device constants
LCD_CHR = 1 # Mode - Sending data
LCD_CMD = 0 # Mode - Sending command

LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line

LCD_BACKLIGHT  = 0x08  # On
#LCD_BACKLIGHT = 0x00  # Off

ENABLE = 0b00000100 # Enable bit

# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005

#Open I2C interface
#bus = smbus.SMBus(0)  # Rev 1 Pi uses 0
bus = smbus.SMBus(1) # Rev 2 Pi uses 1

def lcd_init():
  # Initialise display
  lcd_byte(0x33,LCD_CMD) # 110011 Initialise
  lcd_byte(0x32,LCD_CMD) # 110010 Initialise
  lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
  lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off 
  lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
  lcd_byte(0x01,LCD_CMD) # 000001 Clear display
  time.sleep(E_DELAY)

def lcd_byte(bits, mode):
  # Send byte to data pins
  # bits = the data
  # mode = 1 for data
  #        0 for command

  bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
  bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT

  # High bits
  bus.write_byte(I2C_ADDR, bits_high)
  lcd_toggle_enable(bits_high)

  # Low bits
  bus.write_byte(I2C_ADDR, bits_low)
  lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
  # Toggle enable
  time.sleep(E_DELAY)
  bus.write_byte(I2C_ADDR, (bits | ENABLE))
  time.sleep(E_PULSE)
  bus.write_byte(I2C_ADDR,(bits & ~ENABLE))
  time.sleep(E_DELAY)

def lcd_string(message,line):
  # Send string to display

  message = message.ljust(LCD_WIDTH," ")

  lcd_byte(line, LCD_CMD)

  for i in range(LCD_WIDTH):
    lcd_byte(ord(message[i]),LCD_CHR)

def main():
  # Main program block

  # Initialise display
  lcd_init()

  while True:

    # Send some test
    lcd_string("RPiSpy         <",LCD_LINE_1)
    lcd_string("I2C LCD        <",LCD_LINE_2)

    time.sleep(3)
  
    # Send some more text
    lcd_string(">         RPiSpy",LCD_LINE_1)
    lcd_string(">        I2C LCD",LCD_LINE_2)

    time.sleep(3)

if __name__ == '__main__':

  try:
    main()
  except KeyboardInterrupt:
    pass
  finally:
    lcd_byte(0x01, LCD_CMD)
