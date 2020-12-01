# dusty-python

Python 3 program for the [luftdaten.info](http://luftdaten.info/) sensor network.
It has been written to run on a Raspberry Pi and to to send collected measurements to:

* luftdaten.info
* InfluxDB
* MQTT broker


## Supported Hardware

* [Nova Fitness SDS011](http://aqicn.org/sensor/sds011/) or compatible connected via `ttyUSB` for dust
* [Bosch BME 2280](https://www.bosch-sensortec.com/bst/products/all_products/bme280) connected via I²C for temperature, humidity and pressure


## Dependencies

    apt install python3 pipenv


## Configuration

Copy the `config.default.toml` to `config.toml` and adjust the settings.

## Running a systemd unit

Take a look at the [dusty.unit](contrib/dusty.unit).

## Privileges

On Raspbian the process needs privileges in the groups `i2c` and `dialout`.
