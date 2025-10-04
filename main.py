import time
import board
import neopixel
from random import randint, choice
import threading
import random
from math import floor
import requests
import datetime
import os
import json
import copy
import logging

from config import (
    MATRIX_WIDTH, MATRIX_HEIGHT, NUM_LEDS, SAFE_MAX_LEDS,
    WEATHER_UPDATE_INTERVAL, OPEN_WEATHER_API_BASE_URL,
    OPEN_WEATHER_API_CITY, OPEN_WEATHER_API_KEY, CACHE_FILE,
    DEFAULT_BRIGHTNESS
)
from constants import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_PIN = board.D18
pixels = neopixel.NeoPixel(DATA_PIN, NUM_LEDS, auto_write=False, brightness=DEFAULT_BRIGHTNESS)
current_effect_thread = None
current_effect_name = None
current_variables = {}
stop_event = threading.Event()
last_weather_update = 0

def get_led_index(x, y):
    if x % 2 == 0:
        return x * MATRIX_HEIGHT + y
    else:
        return x * MATRIX_HEIGHT + (MATRIX_HEIGHT - 1 - y)

def safe_led_limit(requested_leds):
    return min(SAFE_MAX_LEDS, max(0, requested_leds))

def fade_out_all(steps=FADE_OUT_STEPS, delay=FADE_OUT_DELAY):
    """Fade out all LEDs gradually."""
    logger.debug("Fading out all LEDs...")
    for step in range(steps):
        for i in range(NUM_LEDS):
            r, g, b = pixels[i]
            fade_factor = 1 - step / steps
            pixels[i] = (
                int(r * fade_factor),
                int(g * fade_factor),
                int(b * fade_factor)
            )
        pixels.show()
        time.sleep(delay)

def simulate_rain(variables):
    """Simulate rain effect with optional thunder."""
    intensity = safe_led_limit(variables.get("intensity", 50))
    thunder_probability = variables.get("thunder_probability", 5)
    logger.info(f"Simulating rain with intensity {intensity} and thunder_probability {thunder_probability}")

    raindrops = [
        (randint(0, MATRIX_WIDTH - 1), randint(0, MATRIX_HEIGHT - 1))
        for _ in range(intensity)
    ]

    while not stop_event.is_set():
        pixels.fill((0, 0, 0))

        new_raindrops = []
        for x, y in raindrops:
            if y + 1 < MATRIX_HEIGHT:
                index = get_led_index(x, y + 1)
                pixels[index] = (
                    randint(RAIN_OTHER_MIN, RAIN_OTHER_MAX),
                    randint(RAIN_OTHER_MIN, RAIN_OTHER_MAX),
                    randint(RAIN_BLUE_MIN, RAIN_BLUE_MAX)
                )
                new_raindrops.append((x, y + 1))
            else:
                index = get_led_index(x, 0)
                pixels[index] = (
                    randint(RAIN_OTHER_MIN, RAIN_OTHER_MAX),
                    randint(RAIN_OTHER_MIN, RAIN_OTHER_MAX),
                    randint(RAIN_BLUE_MIN, RAIN_BLUE_MAX)
                )
                new_raindrops.append((randint(0, MATRIX_WIDTH - 1), 0))

        raindrops = new_raindrops

        if variables.get("weather_condition") == "Thunder" and random.randint(1, THUNDER_CHANCE) == 1:
            logger.debug("Thunderstorm flash!")
            for _ in range(random.randint(THUNDER_MIN_FLASHES, THUNDER_MAX_FLASHES)):
                flash_leds = random.sample(
                    range(NUM_LEDS),
                    random.randint(int(NUM_LEDS * 0.5), NUM_LEDS)
                )
                for i in range(NUM_LEDS):
                    pixels[i] = COLOR_WHITE if i in flash_leds else (0, 0, 0)
                pixels.show()
                time.sleep(random.uniform(THUNDER_MIN_FLASH_DURATION, THUNDER_MAX_FLASH_DURATION))
                pixels.fill((0, 0, 0))
                pixels.show()
                time.sleep(random.uniform(THUNDER_MIN_PAUSE, THUNDER_MAX_PAUSE))

        pixels.show()
        time.sleep(RAIN_UPDATE_DELAY)

def simulate_snow(variables):
    """Simulate falling snow effect."""
    intensity = safe_led_limit(variables.get("intensity", 30))
    logger.info(f"Simulating snow with intensity {intensity}")
    snowflakes = []
    active_columns = set()

    while not stop_event.is_set():
        if len(snowflakes) < intensity:
            x = randint(0, MATRIX_WIDTH - 1)
            if x not in active_columns:
                y = 0
                snowflakes.append((x, y))
                active_columns.add(x)

        new_snowflakes = []
        pixels.fill((0, 0, 0))

        for x, y in snowflakes:
            if y < MATRIX_HEIGHT - 1:
                index = get_led_index(x, y)
                pixels[index] = COLOR_WHITE
                new_snowflakes.append((x, y + 1))
            else:
                index = get_led_index(x, y)
                pixels[index] = COLOR_WHITE
                active_columns.discard(x)

        snowflakes = new_snowflakes
        pixels.show()
        time.sleep(SNOW_FALL_DELAY)

def simulate_fireworks(variables):
    """Simulate colorful fireworks effect."""
    intensity = safe_led_limit(variables.get("intensity", 30))
    max_leds = safe_led_limit(int(NUM_LEDS))
    logger.info(f"Simulating fireworks with intensity {intensity}, max LEDs {max_leds}")

    while not stop_event.is_set():
        # Fade out existing LEDs
        for i in range(NUM_LEDS):
            r, g, b = pixels[i]
            pixels[i] = (
                max(0, r - FIREWORKS_FADE_R),
                max(0, g - FIREWORKS_FADE_G),
                max(0, b - FIREWORKS_FADE_B)
            )

        # Count active LEDs after fading
        active_leds = sum(1 for r, g, b in pixels if r > 0 or g > 0 or b > 0)

        if active_leds < max_leds and random.randint(0, 100) < intensity:
            index = random.randint(0, NUM_LEDS - 1)
            if all(c == 0 for c in pixels[index]):
                hue = random.random()
                r, g, b = hsv_to_rgb(hue, 1.0, 255)
                pixels[index] = (int(r), int(g), int(b))

        pixels.show()
        time.sleep(FIREWORKS_UPDATE_DELAY)

def hsv_to_rgb(h, s, v):
    if s == 0.0:
        return (v, v, v)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = int(v * (1.0 - s))
    q = int(v * (1.0 - s * f))
    t = int(v * (1.0 - s * (1.0 - f)))
    i %= 6
    if i == 0:
        return (v, t, p)
    if i == 1:
        return (q, v, p)
    if i == 2:
        return (p, v, t)
    if i == 3:
        return (p, q, v)
    if i == 4:
        return (t, p, v)
    if i == 5:
        return (v, p, q)

def simulate_lighting(variables):
    """Simulate twinkling lights effect (used for stars, Christmas lights, etc)."""
    intensity = safe_led_limit(variables.get("intensity", 10))
    max_active_leds = variables.get("max_active_leds", 5)
    fade_speed = LIGHTING_FADE_SPEED
    min_burn_time = LIGHTING_MIN_BURN_TIME
    max_burn_time = LIGHTING_MAX_BURN_TIME
    colors = variables.get("colors", [COLOR_WHITE])
    color_weights = variables.get("color_weights", [100 / len(colors)] * len(colors))

    if len(colors) != len(color_weights):
        raise ValueError("Each color must have a corresponding weight.")

    led_brightness = [0] * NUM_LEDS
    led_burn_times = [0] * NUM_LEDS
    led_states = ["off"] * NUM_LEDS
    led_colors = [(0, 0, 0)] * NUM_LEDS

    logger.info(f"Simulating lighting with intensity {intensity}, max active LEDs: {max_active_leds}")
    logger.debug(f"Available colors: {colors} with weights {color_weights}")

    while not stop_event.is_set():
        active_leds = sum(1 for state in led_states if state != "off")

        for i in range(NUM_LEDS):
            if led_states[i] == "fading_in":
                led_brightness[i] += fade_speed
                if led_brightness[i] >= 255:
                    led_brightness[i] = 255
                    led_states[i] = "burning"
                    led_burn_times[i] = random.randint(min_burn_time * 20, max_burn_time * 20)
            elif led_states[i] == "burning":
                if led_burn_times[i] > 0:
                    led_burn_times[i] -= 1
                else:
                    led_states[i] = "fading_out"
            elif led_states[i] == "fading_out":
                led_brightness[i] -= fade_speed
                if led_brightness[i] <= 0:
                    led_brightness[i] = 0
                    led_states[i] = "off"

            if led_states[i] != "off":
                base_color = led_colors[i]
                pixels[i] = (
                    int((base_color[0] / 255) * led_brightness[i]),
                    int((base_color[1] / 255) * led_brightness[i]),
                    int((base_color[2] / 255) * led_brightness[i]),
                )
            else:
                pixels[i] = (0, 0, 0)

        if active_leds < max_active_leds and random.randint(0, 100) < intensity:
            index = random.randint(0, NUM_LEDS - 1)
            if led_states[index] == "off":
                led_states[index] = "fading_in"
                led_brightness[index] = 0
                led_colors[index] = random.choices(colors, weights=color_weights, k=1)[0]

        pixels.show()
        time.sleep(LIGHTING_UPDATE_DELAY)

def simulate_christmas(variables):
    """Simulate Christmas lights effect with red and green colors."""
    variables = {
        "intensity": CHRISTMAS_INTENSITY,
        "max_active_leds": CHRISTMAS_MAX_LEDS,
        "colors": [COLOR_RED, COLOR_GREEN],
        "color_weights": [CHRISTMAS_RED_WEIGHT, CHRISTMAS_GREEN_WEIGHT]
    }
    simulate_lighting(variables)

def simulate_night(variables):
    """Simulate night sky with stars."""
    variables = {
        "intensity": NIGHT_INTENSITY,
        "max_active_leds": NIGHT_MAX_LEDS,
        "colors": [
            COLOR_DARK_BLUE_1, COLOR_DARK_BLUE_2, COLOR_DARK_BLUE_3,
            COLOR_DARK_BLUE_4, COLOR_PURPLE, COLOR_WHITE
        ],
        "color_weights": NIGHT_COLOR_WEIGHTS
    }
    simulate_lighting(variables)

def simulate_day(variables):
    """Simulate daytime sky with sun and clouds based on cloud percentage."""
    cloud_percentage = variables.get("cloud_percentage", 0)

    white_weight = max(0.01, cloud_percentage / 100)
    yellow_weight = max(0.01, 1.0 - white_weight)

    total_weight = white_weight + yellow_weight
    white_weight /= total_weight
    yellow_weight /= total_weight

    variables["max_active_leds"] = int(
        DAY_MIN_LEDS + (DAY_MAX_LEDS - DAY_MIN_LEDS) * (1 - cloud_percentage / 100)
    )

    variables["intensity"] = CHRISTMAS_INTENSITY  # Reuse same intensity value
    variables["colors"] = [COLOR_YELLOW, COLOR_LIGHT_GREY]
    variables["color_weights"] = [yellow_weight, white_weight]

    simulate_lighting(variables)

def simulate_sunrise(variables):
    """Simulate sunrise transition from night (blue) to day (yellow)."""
    percentage = variables.get("sunrise_percentage", 0)
    percentage = max(0.0, min(1.0, percentage))
    transition_row = floor((1.0 - percentage) * MATRIX_HEIGHT)

    for y in range(MATRIX_HEIGHT):
        for x in range(MATRIX_WIDTH):
            index = get_led_index(x, y)
            pixels[index] = COLOR_YELLOW if y >= transition_row else COLOR_DARK_BLUE

    pixels.show()
    time.sleep(0.1)

def simulate_sunset(variables):
    """Simulate sunset transition from day (yellow) to night (blue)."""
    percentage = variables.get("sunset_percentage", 0)
    percentage = max(0.0, min(1.0, percentage))
    transition_row = floor(percentage * MATRIX_HEIGHT)

    for y in range(MATRIX_HEIGHT):
        for x in range(MATRIX_WIDTH):
            index = get_led_index(x, y)
            pixels[index] = COLOR_YELLOW if y >= transition_row else COLOR_DARK_BLUE

    pixels.show()
    time.sleep(0.1)

def variables_changed(current_vars, new_vars, keys_to_check):
    for key in keys_to_check:
        if current_vars.get(key) != new_vars.get(key):
            return True
    return False

def run_effect(effect_name, variables):
    """Switch to a new effect if needed."""
    global current_effect_thread, current_effect_name, current_variables, stop_event, pixels

    if current_effect_name != effect_name or variables_changed(
        current_variables, variables,
        ["brightness", "cloud_percentage", "sunrise_percentage", "sunset_percentage", "intensity", "weather_condition"]
    ):
        logger.info("=" * 44)
        logger.info(f"Switching to effect: {effect_name}")
        logger.info("=" * 44)
        logger.debug("Variables:")
        for key, value in variables.items():
            logger.debug(f"  {key}: {value}")

        fade_out = variables.get("fade_out", True)
        fade_out_steps = variables.get("fade_out_steps", FADE_OUT_STEPS)
        fade_out_delay = variables.get("fade_out_delay", FADE_OUT_DELAY)
        brightness = variables.get("brightness", 1.0)

        stop_event.set()
        if current_effect_thread:
            current_effect_thread.join()

        if fade_out:
            fade_out_all(steps=fade_out_steps, delay=fade_out_delay)
        pixels.brightness = brightness

        stop_event.clear()
        current_effect_name = effect_name
        current_variables = copy.deepcopy(variables)
        effect_function = globals()[effect_name]
        current_effect_thread = threading.Thread(target=effect_function, args=(variables,))
        current_effect_thread.start()

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            try:
                cache = json.load(file)
                cache["data"]["weather_data_timestamp"] = datetime.datetime.fromisoformat(cache["data"]["weather_data_timestamp"])
                cache["data"]["sunrise"] = datetime.datetime.fromisoformat(cache["data"]["sunrise"])
                cache["data"]["sunset"] = datetime.datetime.fromisoformat(cache["data"]["sunset"])
                cache["weather_data_timestamp"] = datetime.datetime.fromisoformat(cache["weather_data_timestamp"])
                return cache
            except (json.JSONDecodeError, ValueError):
                return None
    return None

def save_cache(data, weather_data_timestamp):
    cache = {
        "data": {
            "weather_data_timestamp": data["weather_data_timestamp"].isoformat(),
            "sunrise": data["sunrise"].isoformat(),
            "sunset": data["sunset"].isoformat(),
            "weather_condition": data["weather_condition"],
            "cloud_percentage": data["cloud_percentage"]
        },
        "weather_data_timestamp": weather_data_timestamp.isoformat()
    }
    with open(CACHE_FILE, "w") as file:
        json.dump(cache, file)

def get_weather_data():
    """Fetch weather data from OpenWeather API or cache."""
    cache = load_cache()
    weather_data_timestamp = datetime.datetime.now()

    if cache and (weather_data_timestamp - cache["weather_data_timestamp"]).total_seconds() < WEATHER_UPDATE_INTERVAL:
        logger.info("Using cached weather data")
        return cache["data"]

    logger.info("Fetching weather data from API")
    url = f"{OPEN_WEATHER_API_BASE_URL}q={OPEN_WEATHER_API_CITY}&appid={OPEN_WEATHER_API_KEY}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        weather_data = response.json()
        result = {
            "weather_data_timestamp": weather_data_timestamp,
            "sunrise": datetime.datetime.fromtimestamp(weather_data['sys']['sunrise']),
            "sunset": datetime.datetime.fromtimestamp(weather_data['sys']['sunset']),
            "weather_condition": weather_data['weather'][0]['main'],
            "cloud_percentage": weather_data['clouds']['all']
        }
        save_cache(result, weather_data_timestamp)
        logger.info(f"Weather data fetched: {result['weather_condition']}, clouds: {result['cloud_percentage']}%")
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch weather data: {e}")
        if cache:
            logger.warning("Falling back to cached data")
            return cache["data"]
        else:
            logger.error("No cached data available, using default values")
            return {
                "weather_data_timestamp": weather_data_timestamp,
                "sunrise": weather_data_timestamp.replace(hour=6, minute=0),
                "sunset": weather_data_timestamp.replace(hour=18, minute=0),
                "weather_condition": "Clear",
                "cloud_percentage": 0
            }
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing weather data: {e}")
        if cache:
            logger.warning("Falling back to cached data")
            return cache["data"]
        raise

if __name__ == "__main__":
    logger.info("Starting Skyline LED Weather Display")
    logger.info(f"Matrix size: {MATRIX_WIDTH}x{MATRIX_HEIGHT} ({NUM_LEDS} LEDs)")

    try:
        while True:
            try:
                variables = get_weather_data()

                now = datetime.datetime.now()
                variables["now"] = now
                variables["brightness"] = 1
                variables["sunrise_percentage"] = 1
                variables["sunset_percentage"] = 0
                variables["fade_out"] = True
                variables["is_night"] = False

                if now <= variables["sunrise"] or now >= variables["sunset"]:
                    variables["is_night"] = True

                variables["is_christmas"] = (
                    (now.month == CHRISTMAS_MONTH and now.day == CHRISTMAS_EVE_DAY and now.hour >= CHRISTMAS_EVE_HOUR) or
                    (now.month == CHRISTMAS_MONTH and now.day in [CHRISTMAS_DAY, BOXING_DAY])
                )
                variables["is_new_year"] = now.month == NEW_YEAR_MONTH and now.day <= NEW_YEAR_MAX_DAY

                sunrise_effect_start = variables["sunrise"] - datetime.timedelta(minutes=SUNRISE_SUNSET_DURATION)
                sunrise_effect_end = variables["sunrise"] + datetime.timedelta(minutes=SUNRISE_SUNSET_DURATION)
                sunset_effect_start = variables["sunset"] - datetime.timedelta(minutes=SUNRISE_SUNSET_DURATION)
                sunset_effect_end = variables["sunset"] + datetime.timedelta(minutes=SUNRISE_SUNSET_DURATION)

                logger.debug("Updated variables:")
                for key, value in variables.items():
                    logger.debug(f"  {key}: {value}")

                if variables["is_new_year"]:
                    variables["intensity"] = INTENSITY_FIREWORKS
                    run_effect("simulate_fireworks", variables)
                elif variables["is_christmas"]:
                    run_effect("simulate_christmas", variables)
                elif sunrise_effect_start <= now <= sunrise_effect_end:
                    if current_effect_name != "simulate_sunrise":
                        variables["fade_out"] = True
                    else:
                        variables["fade_out"] = False
                    total_sunrise_duration = (sunrise_effect_end - sunrise_effect_start).total_seconds()
                    elapsed_time = (now - sunrise_effect_start).total_seconds()
                    sunrise_progress = elapsed_time / total_sunrise_duration
                    variables["sunrise_percentage"] = round(sunrise_progress, 2)
                    variables["brightness"] = BRIGHTNESS_SUNRISE_SUNSET
                    run_effect("simulate_sunrise", variables)
                elif sunset_effect_start <= now <= sunset_effect_end:
                    if current_effect_name != "simulate_sunset":
                        variables["fade_out"] = True
                    else:
                        variables["fade_out"] = False
                    total_sunset_duration = (sunset_effect_end - sunset_effect_start).total_seconds()
                    elapsed_time = (now - sunset_effect_start).total_seconds()
                    sunset_progress = elapsed_time / total_sunset_duration
                    variables["sunset_percentage"] = round(sunset_progress, 2)
                    variables["brightness"] = BRIGHTNESS_SUNRISE_SUNSET
                    run_effect("simulate_sunset", variables)
                else:
                    match variables["weather_condition"]:
                        case "Drizzle":
                            variables["intensity"] = INTENSITY_DRIZZLE
                            if variables["is_night"]:
                                variables["brightness"] = BRIGHTNESS_NIGHT
                            run_effect("simulate_rain", variables)
                        case "Rain":
                            variables["intensity"] = INTENSITY_RAIN
                            if variables["is_night"]:
                                variables["brightness"] = BRIGHTNESS_NIGHT
                            run_effect("simulate_rain", variables)
                        case "Thunder":
                            variables["intensity"] = INTENSITY_THUNDER
                            if variables["is_night"]:
                                variables["brightness"] = BRIGHTNESS_NIGHT
                            run_effect("simulate_rain", variables)
                        case "Snow":
                            variables["intensity"] = INTENSITY_SNOW
                            if variables["is_night"]:
                                variables["brightness"] = BRIGHTNESS_SNOW_NIGHT
                            else:
                                variables["brightness"] = BRIGHTNESS_SNOW
                            run_effect("simulate_snow", variables)
                        case _:
                            if variables["is_night"]:
                                run_effect("simulate_night", variables)
                            else:
                                variables["intensity"] = INTENSITY_DAY
                                run_effect("simulate_day", variables)

                time.sleep(MAIN_LOOP_INTERVAL)

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(MAIN_LOOP_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        stop_event.set()
        if current_effect_thread:
            current_effect_thread.join(timeout=5)
        fade_out_all()
        pixels.fill((0, 0, 0))
        pixels.show()
        logger.info("Shutdown complete")
