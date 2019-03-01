#!/usr/bin/env python3

import sys
import os
import yaml

# Import-Pfade setzen
sys.path.append(os.path.join(sys.path[0],"sds011"))
import time
import json
import requests
import numpy as np
from sds011 import SDS011

# Config
with open("config.yml", 'r') as ymlfile:
    config = yaml.load(ymlfile)

# Logging
import logging
logging.basicConfig(level=logging.INFO)

# Create an instance of your bme280
dusty = SDS011('/dev/ttyUSB0')

# Now we have some details about it
print("SDS011 initialized: device_id={} firmware={}".format(dusty.device_id,dusty.firmware))

# Set dutycyle to nocycle (permanent)
dusty.dutycycle = 0

class Measurement:
    def __init__(self):
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

        self.pm25_value  = np.mean(pm25_values)
        self.pm10_value  = np.mean(pm10_values)

    def sendInflux(self):
        cfg = config['influxdb']

        if not cfg['enabled']:
            return

        data = "feinstaub,node={} SDS_P1={:0.2f},SDS_P2={:0.2f}".format(
            cfg['node'],
            self.pm10_value,
            self.pm25_value,
        )

        requests.post(cfg['url'],
            auth=(cfg['username'], cfg['password']),
            data=data,
        )

    def sendLuftdaten(self):
        if not config['luftdaten']['enabled']:
            return

        self.__pushLuftdaten('https://api-rrd.madavi.de/data.php', 0, {
            "SDS_P1":             self.pm10_value,
            "SDS_P2":             self.pm25_value,
        })
        self.__pushLuftdaten('https://api.luftdaten.info/v1/push-sensor-data/', 1, {
            "P1": self.pm10_value,
            "P2": self.pm25_value,
        })


    def __pushLuftdaten(self, url, pin, values):
        requests.post(url,
            json={
                "software_version": "python-dusty 0.0.1",
                "sensordatavalues": [{"value_type": key, "value": val} for key, val in values.items()],
            },
            headers={
                "X-PIN":    str(pin),
                "X-Sensor": sensorID,
            }
        )

# extracts serial from cpuinfo
def getSerial():
    with open('/proc/cpuinfo','r') as f:
        for line in f:
            if line[0:6]=='Serial':
                return(line[10:26])
    raise Exception('CPU serial not found')

def run():
    print('Starting measurement')
    m = Measurement()
    print('Sending data to: http://www.madavi.de/sensor/graph.php?sensor={}-sds011'.format(sensorID))
    print('pm2.5     = {:f} '.format(m.pm25_value))
    print('pm10      = {:f} '.format(m.pm10_value))

    m.sendLuftdaten()
    m.sendInflux()


sensorID  = config['luftdaten'].get('sensor') or ("raspi-" + getSerial())
starttime = time.time()

while True:
    print("running ...")
    run()
    time.sleep(config['luftdaten'].get('sleepTime') - ((time.time() - starttime) % config['luftdaten'].get('sleepTime')))

print("Stopped")
