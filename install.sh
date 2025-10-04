#!/bin/bash

mkdir -p ~/rpi_ws281x_env
cd ~/rpi_ws281x_env

sudo apt-get update
sudo apt-get install -y python3-venv

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env file. Please edit it and add your OpenWeather API key:"
    echo "nano .env"
fi

echo ""
echo "Installation complete. Activate the virtual environment with:"
echo "source ~/rpi_ws281x_env/venv/bin/activate"
