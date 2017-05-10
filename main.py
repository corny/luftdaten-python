#!/usr/bin/env python3

import sys

# Import-Pfade setzen
sys.path.append("sds011")
sys.path.append("bme280")

import time
import json
import requests
import numpy as np
from sds011 import SDS011
from Adafruit_BME280 import *

# Logger initialisieren
#import logging
#logger = logging.getLogger()
#logger.setLevel(logging.INFO)

bme280 = BME280(
    address=0x76,
    t_mode=BME280_OSAMPLE_8,
    p_mode=BME280_OSAMPLE_8,
    h_mode=BME280_OSAMPLE_8,
)

# Create an instance of your bme280
dusty = SDS011('/dev/ttyUSB0')

# Now we have some details about it
print("SDS011 initialized: device_id={} firmware={}".format(dusty.device_id,dusty.firmware))

# Set dutycyle to nocycle (permanent)
dusty.dutycycle = 0


def run():
    pm25_values = []
    pm10_values = []
    dusty.workstate = SDS011.WorkStates.Measuring
    try:
        for a in range(8):
            values = dusty.get_values()
            if values is not None:
                pm10_values.append(values[0])
                pm25_values.append(values[1])
    finally:
        dusty.workstate = SDS011.WorkStates.Sleeping

    pm25_value = np.mean(pm25_values)
    pm10_value = np.mean(pm10_values)

    print('pm2.5     = {:f} '.format(pm25_value))
    print('pm10      = {:f} '.format(pm10_value))

    temperature = bme280.read_temperature()
    humidity    = bme280.read_humidity()
    pressure    = bme280.read_pressure()

    print('Temp      = {:0.2f} deg C'.format(temperature))
    print('Humidity  = {:0.2f} %'.format(humidity))
    print('Pressure  = {:0.2f} hPa'.format(pressure/100))


starttime = time.time()
while True:
    print("running ...")
    run()
    time.sleep(60.0 - ((time.time() - starttime) % 60.0))

print("Stopped")
