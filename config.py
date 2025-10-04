"""Configuration for the Skyline LED weather display."""
import os

# OpenWeather API configuration
OPEN_WEATHER_API_KEY = os.getenv("OPEN_WEATHER_API_KEY", "<your-open-weather-api-key>")
OPEN_WEATHER_API_CITY = os.getenv("OPEN_WEATHER_API_CITY", "<your-city>")
OPEN_WEATHER_API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather?"
WEATHER_UPDATE_INTERVAL = 300  # seconds

# Cache configuration
CACHE_FILE = "weather_cache.json"

# LED Matrix configuration
MATRIX_WIDTH = 32
MATRIX_HEIGHT = 8
NUM_LEDS = MATRIX_WIDTH * MATRIX_HEIGHT

# Safety configuration
SAFE_MAX_LEDS_PERCENTAGE = 0.40
SAFE_MAX_LEDS = int(NUM_LEDS * SAFE_MAX_LEDS_PERCENTAGE)

# Default LED settings
DEFAULT_BRIGHTNESS = 0.25
