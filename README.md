# dusty-python

Python 3 program for the luftdaten.info sensor network.

## Supported Hardware

* [Nova Fitness SDS011](http://aqicn.org/sensor/sds011/) or compatible connected via `ttyUSB` for dust
* [Bosch BME 2280](https://www.bosch-sensortec.com/bst/products/all_products/bme280) connected via I²C for temperature, humidity and pressure

## Used libraries

* https://gitlab.com/frankrich/sds011_particle_sensor
* https://github.com/adafruit/Adafruit_Python_BME280

## Dependencies

    apt install python3-numpy python3-requests

## To-Do

* submit data to luftdaten.info
