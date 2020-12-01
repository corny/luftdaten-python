#!/usr/bin/env python3

import argparse
import time
import toml
import requests
import json
import numpy as np
import board
import busio
from sds011 import SDS011
import adafruit_bme280
from paho.mqtt import client as mqtt_client


# Parse command line args
parser = argparse.ArgumentParser(description='Lufdaten in Python')
parser.add_argument('-c', '--config', default='config.toml', help='path to config file')
args = parser.parse_args()

# Read config file
config = toml.load(args.config)

# Configure Logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Configure BME280
print("initialize BME280")
i2c    = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

# Configure SDS011
print("initialize SDS011")
dusty = SDS011(port='/dev/ttyUSB0')

# Now we have some details about it
print("SDS011 initialized: device_id={} firmware={}".format(dusty.devid, dusty.firmware))

# Configure MQTT
mqtt_conn = None
mqtt_cfg  = config["mqtt"]
if mqtt_cfg["enabled"]:
    mqtt_conn = mqtt_client.Client(mqtt_cfg["client_id"])
    mqtt_conn.connect(mqtt_cfg["broker"], mqtt_cfg["port"])

class Measurement:
    def __init__(self):
        self.pm25_value  = None
        self.pm10_value  = None

        if dusty:
            pm25_values = []
            pm10_values = []
            dusty.wakeup()
            try:
                for a in range(8):
                    values = dusty.read_measurement()
                    if values is not None:
                        pm10_values.append(values.get("pm10"))
                        pm25_values.append(values.get("pm2.5"))
            finally:
                dusty.sleep()

            self.pm25_value  = np.mean(pm25_values)
            self.pm10_value  = np.mean(pm10_values)

        self.temperature = bme280.temperature
        self.humidity    = bme280.relative_humidity
        self.pressure    = bme280.pressure

    def sendMQTT(self):
        mqtt_conn.publish(mqtt_cfg["topic"], json.dumps({
            "dust_pm10":  self.pm10_value,
            "dust_pm25":  self.pm25_value,
            "temperature": self.temperature,
            "pressure":    self.pressure,
            "humidity":    self.humidity,
        }))

    def sendInflux(self):
        cfg = config['influxdb']

        if not cfg['enabled']:
            return

        data = "feinstaub,node={} SDS_P1={:0.2f},SDS_P2={:0.2f},BME280_temperature={:0.2f},BME280_pressure={:0.2f},BME280_humidity={:0.2f}".format(
            cfg['node'],
            self.pm10_value,
            self.pm25_value,
            self.temperature,
            self.pressure,
            self.humidity,
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
            "BME280_temperature": self.temperature,
            "BME280_pressure":    self.pressure,
            "BME280_humidity":    self.humidity,
        })
        self.__pushLuftdaten('https://api.luftdaten.info/v1/push-sensor-data/', 1, {
            "P1": self.pm10_value,
            "P2": self.pm25_value,
        })
        self.__pushLuftdaten('https://api.luftdaten.info/v1/push-sensor-data/', 11, {
            "temperature": self.temperature,
            "pressure":    self.pressure,
            "humidity":    self.humidity,
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
    m = Measurement()

    print('pm2.5     = {:f} '.format(m.pm25_value))
    print('pm10      = {:f} '.format(m.pm10_value))
    print('Temp      = {:0.2f} deg C'.format(m.temperature))
    print('Humidity  = {:0.2f} %'.format(m.humidity))
    print('Pressure  = {:0.2f} hPa'.format(m.pressure/100))

    if mqtt_conn:
        m.sendMQTT()

    m.sendLuftdaten()
    m.sendInflux()


sensorID  = config['luftdaten'].get('sensor') or ("raspi-" + getSerial())
starttime = time.time()

if __name__ == "__main__":
    while True:
        print("running ...")
        run()
        time.sleep(60.0 - ((time.time() - starttime) % 60.0))
    print("Stopped")
