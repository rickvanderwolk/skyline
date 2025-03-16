#!/bin/bash

mkdir -p ~/rpi_ws281x_env
cd ~/rpi_ws281x_env

sudo apt-get update
sudo apt-get install -y python3-venv

python3 -m venv venv

source venv/bin/activate

pip install rpi_ws281x adafruit-circuitpython-neopixel requests

echo "De installatie is voltooid. Activeer de virtual environment met:"
echo "source ~/rpi_ws281x_env/venv/bin/activate"
